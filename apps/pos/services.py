"""
POSService — toute la logique métier du point de vente physique.

Règles :
- Les vues restent minces : validation par serializer, puis délégation ici.
- Chaque vente est idempotente via idempotency_key (générée côté client) —
  une resoumission (retry réseau, re-sync offline) renvoie la vente existante.
- Le paiement wallet est SYNCHRONE et ONLINE uniquement : la synchronisation
  batch offline rejette toute vente wallet (anti double-spending).
- Le stock est décrémenté par le signal post_save sur POSItem (apps.pos.signals).
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.pos.models import POSDevice, POSItem, POSSale, POSSession

logger = logging.getLogger(__name__)

DEUX_DECIMALES = Decimal('0.01')


class POSError(Exception):
    """Erreur métier POS (session, terminal, vente invalide...)."""


def _en_montant(valeur) -> Decimal:
    return Decimal(str(valeur)).quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


class POSService:

    # ── Terminaux ────────────────────────────────────────────────────────────

    @staticmethod
    def get_device(operateur, device_uid) -> POSDevice:
        device = POSDevice.objects.filter(
            device_uid=(device_uid or '').strip(), is_active=True,
        ).first()
        if device is None:
            raise POSError("Terminal inconnu ou révoqué.")
        est_superadmin = (
            operateur.is_superuser or operateur.is_staff
            or getattr(operateur, 'role', '') == 'superadmin'
        )
        if device.operateur_id != operateur.id and not est_superadmin:
            raise POSError("Ce terminal appartient à un autre opérateur.")
        return device

    # ── Sessions ─────────────────────────────────────────────────────────────

    @classmethod
    def ouvrir_session(cls, operateur, device_uid, fonds_ouverture) -> POSSession:
        fonds = _en_montant(fonds_ouverture)
        if fonds < 0:
            raise POSError("Le fonds de caisse initial ne peut pas être négatif.")

        device = cls.get_device(operateur, device_uid)

        with transaction.atomic():
            deja_ouverte = (
                POSSession.objects.select_for_update()
                .filter(operateur=operateur, statut=POSSession.Statut.OUVERTE)
                .first()
            )
            if deja_ouverte:
                raise POSError(
                    f"Une session est déjà ouverte (#{deja_ouverte.pk}, "
                    f"terminal {deja_ouverte.device.nom}). Fermez-la d'abord."
                )
            return POSSession.objects.create(
                device=device, operateur=operateur, fonds_ouverture=fonds,
            )

    @classmethod
    def session_ouverte(cls, operateur) -> POSSession | None:
        return POSSession.objects.filter(
            operateur=operateur, statut=POSSession.Statut.OUVERTE,
        ).first()

    @classmethod
    def _session_pour_vente(cls, operateur, vendue_le) -> POSSession | None:
        """
        Session de rattachement d'une vente offline synchronisée : celle qui
        couvrait l'horodatage réel de la vente (même si elle a été fermée
        entre-temps), sinon la session ouverte courante, sinon la dernière
        session de l'opérateur (la vente physique a eu lieu — l'admin arbitre).
        """
        couvrante = (
            POSSession.objects
            .filter(operateur=operateur, ouverte_le__lte=vendue_le)
            .filter(Q(fermee_le__isnull=True) | Q(fermee_le__gte=vendue_le))
            .order_by('-ouverte_le')
            .first()
        )
        if couvrante:
            return couvrante
        return (
            cls.session_ouverte(operateur)
            or POSSession.objects.filter(operateur=operateur)
            .order_by('-ouverte_le').first()
        )

    @classmethod
    def recalculer_ecart(cls, session) -> None:
        """
        Recalcule l'écart d'une session FERMEE après une sync tardive : la
        vente offline était bien dans le tiroir au moment du comptage, le
        cash attendu change donc rétroactivement. (Ne pas appeler à
        l'annulation d'une vente : le comptage historique, lui, incluait
        cet argent.)
        """
        with transaction.atomic():
            verrouillee = POSSession.objects.select_for_update().get(pk=session.pk)
            if (
                verrouillee.statut != POSSession.Statut.FERMEE
                or verrouillee.fonds_fermeture is None
            ):
                return
            recap = cls.totaux_session(verrouillee)
            verrouillee.ecart_caisse = verrouillee.fonds_fermeture - (
                verrouillee.fonds_ouverture + Decimal(recap['total_cash'])
            )
            verrouillee.save(update_fields=['ecart_caisse'])

    @classmethod
    def totaux_session(cls, session) -> dict:
        """
        Totaux des ventes confirmées d'une session. La part wallet des
        paiements hybrides est comptée dans le bucket 'wallet', le reste
        dans la méthode déclarée — le cash en caisse est donc exact.
        """
        ventes = session.ventes.filter(statut=POSSale.Statut.CONFIRMEE)
        par_methode = {}
        total_wallet = Decimal('0.00')
        for v in ventes.values('methode_paiement').annotate(
            total=Sum('montant_total'), wallet=Sum('montant_wallet'), nb=Count('id'),
        ):
            hors_wallet = _en_montant((v['total'] or 0) - (v['wallet'] or 0))
            total_wallet += _en_montant(v['wallet'] or 0)
            if hors_wallet > 0 or v['methode_paiement'] != POSSale.MethodePaiement.WALLET:
                par_methode[v['methode_paiement']] = {
                    'nb': v['nb'], 'montant': str(hors_wallet),
                }
        if total_wallet > 0:
            existant = par_methode.get(POSSale.MethodePaiement.WALLET)
            deja = Decimal(existant['montant']) if existant else Decimal('0.00')
            par_methode[POSSale.MethodePaiement.WALLET] = {
                'nb': ventes.filter(
                    Q(methode_paiement=POSSale.MethodePaiement.WALLET)
                    | Q(montant_wallet__gt=0)
                ).count(),
                'montant': str(_en_montant(deja + total_wallet)),
            }

        agregats = ventes.aggregate(total=Sum('montant_total'), nb=Count('id'))
        total_cash = ventes.filter(
            methode_paiement=POSSale.MethodePaiement.CASH,
        ).aggregate(t=Sum(F('montant_total') - F('montant_wallet')))['t'] or Decimal('0')

        return {
            'nb_ventes':    agregats['nb'] or 0,
            'total_ventes': str(_en_montant(agregats['total'] or 0)),
            'total_cash':   str(_en_montant(total_cash)),
            'par_methode':  par_methode,
        }

    @classmethod
    def fermer_session(cls, operateur, fonds_fermeture) -> tuple[POSSession, dict]:
        fonds = _en_montant(fonds_fermeture)
        if fonds < 0:
            raise POSError("Le comptage de clôture ne peut pas être négatif.")

        with transaction.atomic():
            session = (
                POSSession.objects.select_for_update()
                .filter(operateur=operateur, statut=POSSession.Statut.OUVERTE)
                .first()
            )
            if session is None:
                raise POSError("Aucune session ouverte à fermer.")

            recap = cls.totaux_session(session)
            session.fonds_fermeture = fonds
            session.ecart_caisse = fonds - (
                session.fonds_ouverture + Decimal(recap['total_cash'])
            )
            session.fermee_le = timezone.now()
            session.statut = POSSession.Statut.FERMEE
            session.save(update_fields=[
                'fonds_fermeture', 'ecart_caisse', 'fermee_le', 'statut',
            ])
            recap['ecart_caisse'] = str(session.ecart_caisse)
        return session, recap

    # ── Ventes ───────────────────────────────────────────────────────────────

    @staticmethod
    def _trouver_client(telephone='', email=''):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        telephone = (telephone or '').strip()
        email = (email or '').strip()
        if telephone:
            client = User.objects.filter(telephone=telephone).first()
            if client:
                return client
        if email:
            return User.objects.filter(email__iexact=email).first()
        return None

    @classmethod
    def enregistrer_vente(cls, operateur, session, donnees, offline=False):
        """
        Crée une vente POS (données déjà validées par le serializer).
        Retourne (vente, created) — created=False si l'idempotency_key est
        déjà connue (retry / re-sync). Tout est atomique : lignes, débit
        wallet éventuel et décrément du stock (signal) réussissent ou
        échouent ensemble.
        """
        from apps.catalog.models import Produit
        from apps.stock.models import Lot

        existante = POSSale.objects.filter(
            idempotency_key=donnees['idempotency_key'],
        ).first()
        if existante is not None:
            return existante, False

        methode = donnees['methode_paiement']
        montant_wallet = _en_montant(donnees.get('montant_wallet') or 0)
        est_wallet = (
            methode == POSSale.MethodePaiement.WALLET or montant_wallet > 0
        )

        # RÈGLE MÉTIER STRICTE : pas de wallet en synchronisation offline —
        # le solde ne peut pas être vérifié au moment de la vente réelle.
        if offline and est_wallet:
            raise POSError(
                "Paiement wallet refusé en synchronisation offline : "
                "le paiement wallet est synchrone et online uniquement."
            )

        if est_wallet:
            from apps.core.models import SiteSettings
            if not SiteSettings.get_solo().wallet_enabled:
                raise POSError("Le portefeuille n'est pas disponible pour le moment.")

        # Client : un paiement wallet exige le CODE DE PAIEMENT généré par le
        # client depuis son portefeuille (consentement) — jamais un simple
        # téléphone/email, sinon n'importe quel opérateur pourrait débiter
        # n'importe qui. téléphone/email ne servent qu'au rattachement des
        # ventes SANS wallet (vente nominative).
        client = None
        telephone = (donnees.get('client_telephone') or '').strip()
        email = (donnees.get('client_email') or '').strip()
        code_paiement = (donnees.get('code_paiement') or '').strip()
        if est_wallet:
            if telephone or email:
                raise POSError(
                    "Pour un paiement wallet, le client s'identifie uniquement "
                    "par son code de paiement (code_paiement) — pas de "
                    "client_telephone/client_email."
                )
            if not code_paiement:
                raise POSError(
                    "code_paiement requis pour un paiement wallet — le client "
                    "le génère depuis son portefeuille (valide 5 minutes)."
                )
            from apps.wallet.services import CodeInvalide, WalletService
            try:
                client, _wallet = WalletService.consulter_code_paiement(code_paiement)
            except CodeInvalide as e:
                raise POSError(str(e))
        elif telephone or email:
            client = cls._trouver_client(telephone, email)

        # Lignes : produits/lots vérifiés, totaux calculés côté serveur
        lignes = []
        montant_total = Decimal('0.00')
        for item in donnees['items']:
            produit = Produit.objects.filter(pk=item['produit_id']).first()
            if produit is None:
                raise POSError(f"Produit #{item['produit_id']} introuvable.")
            lot = None
            if item.get('lot_id'):
                lot = Lot.objects.filter(pk=item['lot_id'], produit=produit).first()
                if lot is None:
                    raise POSError(
                        f"Lot #{item['lot_id']} introuvable pour le produit {produit.nom}."
                    )
            prix = _en_montant(item['prix_unitaire'])
            sous_total = _en_montant(prix * item['quantite'])
            montant_total += sous_total
            lignes.append((produit, lot, item['quantite'], prix, sous_total))

        if methode == POSSale.MethodePaiement.WALLET:
            montant_wallet = montant_total
        if montant_wallet > montant_total:
            raise POSError("La part wallet dépasse le montant total de la vente.")

        with transaction.atomic():
            vente = POSSale.objects.create(
                idempotency_key=donnees['idempotency_key'],
                session=session,
                operateur=operateur,
                client=client,
                montant_total=montant_total,
                methode_paiement=methode,
                montant_wallet=montant_wallet,
                vendue_le=donnees['vendue_le'],
            )
            for produit, lot, quantite, prix, sous_total in lignes:
                POSItem.objects.create(
                    vente=vente, produit=produit, lot=lot,
                    quantite=quantite, prix_unitaire=prix, sous_total=sous_total,
                )
            if montant_wallet > 0:
                from apps.wallet.services import CodeInvalide, WalletService
                # Consommer le code DANS la transaction du débit : si le
                # débit échoue (solde...), le rollback rend le code au
                # client ; si le code a été consommé par une autre caisse
                # entre la consultation et ici, la vente est annulée.
                try:
                    client_confirme, _wallet = WalletService.valider_code_paiement(
                        code_paiement, pos_sale=vente,
                    )
                except CodeInvalide as e:
                    raise POSError(str(e))
                WalletService.payer_vente_pos(client_confirme, vente, montant_wallet)
        return vente, True

    @classmethod
    def annuler_vente(cls, vente, motif='') -> bool:
        """
        Annule une vente confirmée : le signal re-crédite les lots et le
        wallet du client est remboursé de la part wallet (idempotent).
        Retourne False si la vente est déjà annulée.
        """
        with transaction.atomic():
            verrouillee = POSSale.objects.select_for_update().get(pk=vente.pk)
            if verrouillee.statut == POSSale.Statut.ANNULEE:
                return False
            verrouillee.statut = POSSale.Statut.ANNULEE
            verrouillee.save(update_fields=['statut'])
        vente.statut = POSSale.Statut.ANNULEE
        return True

    @classmethod
    def sync_ventes(cls, operateur, ventes_donnees) -> list[dict]:
        """
        Traite un batch de ventes offline, chacune indépendamment (une vente
        rejetée n'empêche pas les autres). Les ventes wallet sont rejetées
        (cf. enregistrer_vente offline=True) ; un stock insuffisant ne rejette
        PAS la vente — elle est créée avec stock_conflict=True (signal).

        Chaque vente est rattachée à la session qui couvrait son vendue_le —
        y compris une session déjà FERMEE (terminal resté hors ligne après la
        clôture) : l'écart de caisse de ces sessions est alors recalculé.
        """
        resultats = []
        sessions_fermees_touchees = set()
        for donnees in ventes_donnees:
            cle = str(donnees['idempotency_key'])
            try:
                existante = POSSale.objects.filter(idempotency_key=cle).first()
                if existante is not None:
                    resultats.append({
                        'idempotency_key': cle, 'status': 'duplicate',
                        'vente_id': existante.pk,
                        'numero_vente': existante.numero_vente,
                        'stock_conflict': existante.stock_conflict,
                    })
                    continue

                session = cls._session_pour_vente(operateur, donnees['vendue_le'])
                if session is None:
                    raise POSError(
                        "Aucune session de caisse à laquelle rattacher cette "
                        "vente — ouvrez une session avant de vendre."
                    )
                vente, created = cls.enregistrer_vente(
                    operateur, session, donnees, offline=True,
                )
                if created and session.statut == POSSession.Statut.FERMEE:
                    sessions_fermees_touchees.add(session.pk)
                resultats.append({
                    'idempotency_key': cle,
                    'status': 'created' if created else 'duplicate',
                    'vente_id': vente.pk,
                    'numero_vente': vente.numero_vente,
                    'session_id': vente.session_id,
                    'stock_conflict': vente.stock_conflict,
                })
            except POSError as e:
                resultats.append({
                    'idempotency_key': cle, 'status': 'rejected', 'erreur': str(e),
                })
            except Exception as e:
                logger.error("Sync POS — vente %s en erreur : %s", cle, e)
                resultats.append({
                    'idempotency_key': cle, 'status': 'rejected',
                    'erreur': "Erreur interne lors de l'enregistrement de la vente.",
                })

        for session_pk in sessions_fermees_touchees:
            try:
                cls.recalculer_ecart(POSSession.objects.get(pk=session_pk))
            except Exception as e:
                logger.error("Sync POS — recalcul écart session #%s : %s", session_pk, e)
        return resultats

    # ── Rapports ─────────────────────────────────────────────────────────────

    @classmethod
    def rapport(cls, ventes) -> dict:
        """Totaux + répartition par méthode + top produits d'un queryset de ventes."""
        confirmees = ventes.filter(statut=POSSale.Statut.CONFIRMEE)
        agregats = confirmees.aggregate(ca=Sum('montant_total'), nb=Count('id'))

        par_methode = {
            v['methode_paiement']: {
                'nb': v['nb'], 'montant': str(_en_montant(v['total'] or 0)),
            }
            for v in confirmees.values('methode_paiement').annotate(
                total=Sum('montant_total'), nb=Count('id'),
            )
        }

        top_produits = [
            {
                'produit_id':      p['produit_id'],
                'produit':         p['produit__nom'],
                'quantite_vendue': p['quantite_totale'],
                'montant':         str(_en_montant(p['montant'] or 0)),
            }
            for p in POSItem.objects.filter(vente__in=confirmees)
            .values('produit_id', 'produit__nom')
            .annotate(quantite_totale=Sum('quantite'), montant=Sum('sous_total'))
            .order_by('-quantite_totale')[:10]
        ]

        # Liste détaillée pour la réconciliation mobile (200 plus récentes,
        # annulées comprises — le statut permet de les distinguer).
        ventes_liste = [
            {
                'id':               v.pk,
                'idempotency_key':  str(v.idempotency_key),
                'numero_vente':     v.numero_vente,
                'statut':           v.statut,
                'montant_total':    str(v.montant_total),
                'montant_wallet':   str(v.montant_wallet),
                'methode_paiement': v.methode_paiement,
                'stock_conflict':   v.stock_conflict,
                'vendue_le':        v.vendue_le.isoformat(),
            }
            for v in ventes.order_by('-vendue_le')[:200]
        ]

        return {
            'nb_ventes':        agregats['nb'] or 0,
            'chiffre_affaires': str(_en_montant(agregats['ca'] or 0)),
            'nb_annulees':      ventes.filter(statut=POSSale.Statut.ANNULEE).count(),
            'nb_stock_conflict': confirmees.filter(stock_conflict=True).count(),
            'par_methode':      par_methode,
            'top_produits':     top_produits,
            'ventes':           ventes_liste,
        }
