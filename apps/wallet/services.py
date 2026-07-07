"""
WalletService — point d'entrée unique pour tout mouvement d'argent wallet.

Règles :
- Le solde n'est jamais modifié sans créer une WalletTransaction (ledger).
- Chaque mouvement verrouille la ligne Wallet (select_for_update) pour
  empêcher deux débits concurrents de dépasser le solde.
- Les opérations liées à une commande ou à un objet métier (recharge,
  retrait, bon cadeau) sont idempotentes.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.wallet.models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)

DEUX_DECIMALES = Decimal('0.01')


class WalletError(Exception):
    """Erreur générique wallet (wallet inactif, opération invalide...)."""


class SoldeInsuffisant(WalletError):
    """Le solde du wallet ne couvre pas le débit demandé."""


def _en_montant(valeur) -> Decimal:
    """Convertit float/str/Decimal en Decimal 2 décimales (ROUND_HALF_UP)."""
    return Decimal(str(valeur)).quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


class WalletService:

    # ── Accès ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_wallet(user) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    # ── Mouvement bas niveau ─────────────────────────────────────────────────

    @staticmethod
    def _appliquer(wallet, montant, type_tx, commande=None, description='',
                   reference='', autoriser_negatif=False) -> WalletTransaction:
        """
        Applique un mouvement signé sur le wallet et écrit la ligne de ledger.
        `autoriser_negatif` n'est utilisé que pour les reprises (cashback,
        bonus, vente) et les ajustements admin.
        """
        montant = _en_montant(montant)
        if montant == 0:
            raise WalletError("Le montant du mouvement ne peut pas être nul.")

        with transaction.atomic():
            verrouille = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if not verrouille.is_active:
                raise WalletError("Ce portefeuille est désactivé.")

            nouveau_solde = verrouille.solde + montant
            if nouveau_solde < 0 and not autoriser_negatif:
                raise SoldeInsuffisant(
                    f"Solde insuffisant : {verrouille.solde} HTG disponible, "
                    f"{-montant} HTG demandé."
                )

            verrouille.solde = nouveau_solde
            verrouille.save(update_fields=['solde', 'updated_at'])

            tx = WalletTransaction.objects.create(
                wallet=verrouille,
                type=type_tx,
                montant=montant,
                solde_apres=nouveau_solde,
                commande=commande,
                description=description,
                reference=reference,
            )

        # Rafraîchit l'instance passée par l'appelant
        wallet.solde = nouveau_solde
        return tx

    @classmethod
    def crediter(cls, wallet, montant, type_tx=WalletTransaction.Type.AJUSTEMENT,
                 **kwargs) -> WalletTransaction:
        montant = _en_montant(montant)
        if montant <= 0:
            raise WalletError("Un crédit doit être strictement positif.")
        return cls._appliquer(wallet, montant, type_tx, **kwargs)

    @classmethod
    def debiter(cls, wallet, montant, type_tx=WalletTransaction.Type.AJUSTEMENT,
                **kwargs) -> WalletTransaction:
        montant = _en_montant(montant)
        if montant <= 0:
            raise WalletError("Un débit doit être strictement positif.")
        return cls._appliquer(wallet, -montant, type_tx, **kwargs)

    # ── Recharges ────────────────────────────────────────────────────────────

    @classmethod
    def completer_recharge(cls, recharge, reference='') -> WalletTransaction | None:
        """
        Crédite le wallet une fois la recharge confirmée (Plopplop vérifié ou
        preuve hors ligne validée par l'admin). Idempotent : une recharge déjà
        `creditee` est ignorée (double callback, verify + webhook, etc.).
        """
        from apps.wallet.models import WalletRecharge

        with transaction.atomic():
            verrouillee = WalletRecharge.objects.select_for_update().get(pk=recharge.pk)
            if verrouillee.statut == WalletRecharge.Statut.CREDITEE:
                return None

            tx = cls.crediter(
                verrouillee.wallet,
                verrouillee.montant,
                type_tx=WalletTransaction.Type.RECHARGE,
                description=f"Recharge {verrouillee.get_methode_display()}",
                reference=reference or (verrouillee.reference_plopplop or ''),
            )
            verrouillee.statut = WalletRecharge.Statut.CREDITEE
            verrouillee.transaction = tx
            verrouillee.save(update_fields=['statut', 'transaction', 'updated_at'])

        recharge.statut = WalletRecharge.Statut.CREDITEE
        return tx

    # ── Retraits ─────────────────────────────────────────────────────────────

    @classmethod
    def demander_retrait(cls, user, montant, canal, numero_telephone):
        """
        Crée une demande de retrait et débite immédiatement le wallet
        (réservation) — le montant ne peut plus être dépensé en attendant
        le traitement admin. Lève SoldeInsuffisant si le solde ne suit pas.
        """
        from apps.wallet.models import WalletRetrait

        montant = _en_montant(montant)
        wallet = cls.get_wallet(user)

        with transaction.atomic():
            retrait = WalletRetrait.objects.create(
                wallet=wallet,
                montant=montant,
                canal=canal,
                numero_telephone=numero_telephone,
            )
            tx = cls.debiter(
                wallet,
                montant,
                type_tx=WalletTransaction.Type.RETRAIT,
                description=f"Retrait #{retrait.pk} — {retrait.get_canal_display()} {numero_telephone}",
                reference=f"retrait-{retrait.pk}",
            )
            retrait.transaction = tx
            retrait.save(update_fields=['transaction', 'updated_at'])
        return retrait

    @classmethod
    def payer_retrait(cls, retrait, traite_par, preuve_transfert=None, note='') -> bool:
        """
        Marque le retrait payé après le transfert manuel MonCash/NatCash.
        Aucun mouvement d'argent : le débit a eu lieu à la demande.
        Idempotent : retourne False si le retrait n'est plus en 'demande'.
        """
        from apps.wallet.models import WalletRetrait

        with transaction.atomic():
            verrouille = WalletRetrait.objects.select_for_update().get(pk=retrait.pk)
            if verrouille.statut != WalletRetrait.Statut.DEMANDE:
                return False
            verrouille.statut = WalletRetrait.Statut.PAYE
            verrouille.traite_par = traite_par
            verrouille.date_traitement = timezone.now()
            if preuve_transfert:
                verrouille.preuve_transfert = preuve_transfert
            if note:
                verrouille.note_admin = note
            verrouille.save()
        return True

    @classmethod
    def rejeter_retrait(cls, retrait, traite_par, motif='') -> bool:
        """
        Rejette la demande et re-crédite le montant réservé sur le wallet.
        Idempotent : retourne False si le retrait n'est plus en 'demande'.
        """
        from apps.wallet.models import WalletRetrait

        with transaction.atomic():
            verrouille = WalletRetrait.objects.select_for_update().get(pk=retrait.pk)
            if verrouille.statut != WalletRetrait.Statut.DEMANDE:
                return False

            tx = cls.crediter(
                verrouille.wallet,
                verrouille.montant,
                type_tx=WalletTransaction.Type.REPRISE_RETRAIT,
                description=f"Retrait #{verrouille.pk} rejeté — re-crédit",
                reference=f"retrait-{verrouille.pk}",
            )
            verrouille.statut = WalletRetrait.Statut.REJETE
            verrouille.traite_par = traite_par
            verrouille.date_traitement = timezone.now()
            verrouille.note_admin = motif or verrouille.note_admin
            verrouille.transaction_reprise = tx
            verrouille.save()
        return True

    # ── Bons cadeaux ─────────────────────────────────────────────────────────

    DUREE_VALIDITE_BON_JOURS = 365  # 12 mois

    @classmethod
    def activer_bon_cadeau(cls, bon, reference='') -> bool:
        """
        Active un bon cadeau après confirmation du paiement et planifie
        l'envoi du code par email. Idempotent : retourne False si le bon
        n'est plus en attente de paiement.
        """
        from apps.wallet.models import BonCadeau

        with transaction.atomic():
            verrouille = BonCadeau.objects.select_for_update().get(pk=bon.pk)
            if verrouille.statut != BonCadeau.Statut.ATTENTE_PAIEMENT:
                return False
            verrouille.statut = BonCadeau.Statut.ACTIF
            verrouille.date_expiration = timezone.now() + timezone.timedelta(
                days=cls.DUREE_VALIDITE_BON_JOURS
            )
            verrouille.save(update_fields=['statut', 'date_expiration', 'updated_at'])

        try:
            from apps.wallet.tasks import task_envoyer_bon_cadeau
            task_envoyer_bon_cadeau.delay(bon.pk)
        except Exception as e:
            logger.error("Email bon cadeau #%s non planifié : %s", bon.pk, e)
        return True

    @classmethod
    def acheter_bon_cadeau_avec_wallet(cls, user, bon) -> WalletTransaction:
        """
        Achète un bon cadeau en débitant le solde du wallet, puis l'active
        (l'activation envoie le code par email). Lève SoldeInsuffisant si
        le solde ne couvre pas le montant.
        """
        wallet = cls.get_wallet(user)
        tx = cls.debiter(
            wallet,
            bon.montant,
            type_tx=WalletTransaction.Type.BON_CADEAU_ACHAT,
            description=f"Achat bon cadeau {bon.code}",
            reference=f"bon-{bon.pk}",
        )
        cls.activer_bon_cadeau(bon, reference=f"wallet-tx-{tx.pk}")
        return tx

    @classmethod
    def encaisser_bon_cadeau(cls, user, code) -> WalletTransaction:
        """
        Échange un code cadeau contre du crédit wallet. Le verrou sur la ligne
        BonCadeau garantit qu'un code ne peut être utilisé qu'une seule fois,
        même en cas de soumissions simultanées.
        """
        from apps.wallet.models import BonCadeau

        normalise = (code or '').strip().upper()
        if not normalise:
            raise WalletError("Veuillez saisir un code.")

        with transaction.atomic():
            bon = (
                BonCadeau.objects.select_for_update()
                .filter(code=normalise)
                .first()
            )
            if not bon:
                raise WalletError("Code invalide.")
            if bon.statut == BonCadeau.Statut.UTILISE:
                raise WalletError("Ce bon cadeau a déjà été utilisé.")
            if bon.statut == BonCadeau.Statut.ANNULE:
                raise WalletError("Ce bon cadeau a été annulé.")
            if bon.statut == BonCadeau.Statut.ATTENTE_PAIEMENT:
                raise WalletError("Ce bon cadeau n'a pas encore été payé.")
            if bon.statut == BonCadeau.Statut.EXPIRE or bon.est_expire:
                if bon.statut != BonCadeau.Statut.EXPIRE:
                    bon.statut = BonCadeau.Statut.EXPIRE
                    bon.save(update_fields=['statut', 'updated_at'])
                raise WalletError("Ce bon cadeau a expiré.")

            wallet = cls.get_wallet(user)
            tx = cls.crediter(
                wallet,
                bon.montant,
                type_tx=WalletTransaction.Type.BON_CADEAU_ENCAISSE,
                description=f"Bon cadeau {bon.code}",
                reference=bon.code,
            )
            bon.statut = BonCadeau.Statut.UTILISE
            bon.encaisse_par = user
            bon.date_encaissement = timezone.now()
            bon.save(update_fields=['statut', 'encaisse_par', 'date_encaissement', 'updated_at'])
        return tx
