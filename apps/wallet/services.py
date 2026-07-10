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


def _planifier_apres_commit(tache, pk):
    """
    Planifie une tâche Celery après commit sans jamais faire échouer
    l'opération métier (broker indisponible, etc.).
    """
    def _envoyer():
        try:
            tache.delay(pk)
        except Exception as e:
            logger.error("Tâche %s(%s) non planifiée : %s", tache.name, pk, e)

    transaction.on_commit(_envoyer)


class WalletService:

    # ── Accès ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_wallet(user) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    # ── Mouvement bas niveau ─────────────────────────────────────────────────

    @staticmethod
    def _appliquer(wallet, montant, type_tx, commande=None, pos_sale=None,
                   description='', reference='',
                   autoriser_negatif=False) -> WalletTransaction:
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
                pos_sale=pos_sale,
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

    MONTANT_RECHARGE_MIN = Decimal('25')
    MONTANT_RECHARGE_MAX = Decimal('1000000')
    MAX_RECHARGES_HORS_LIGNE_EN_ATTENTE = 3

    @classmethod
    def initier_recharge_plopplop(cls, user, montant, methode):
        """
        Crée une intention de recharge et initie le paiement MonCash/NatCash
        via Plopplop. Retourne (recharge, redirect_url) — l'utilisateur doit
        être redirigé vers redirect_url pour payer. La recharge passe en
        'echouee' si la passerelle refuse.
        """
        import uuid

        from apps.payments.services.plopplop_service import PlopplopService
        from apps.wallet.models import WalletRecharge

        montant = _en_montant(montant)
        if not (cls.MONTANT_RECHARGE_MIN <= montant <= cls.MONTANT_RECHARGE_MAX):
            raise WalletError(
                f"Le montant doit être compris entre {cls.MONTANT_RECHARGE_MIN} "
                f"et {cls.MONTANT_RECHARGE_MAX} HTG."
            )

        plopplop = PlopplopService()
        if not plopplop.is_configured():
            raise WalletError("La passerelle de paiement n'est pas configurée.")

        wallet = cls.get_wallet(user)
        if not wallet.is_active:
            raise WalletError("Ce portefeuille est désactivé.")

        recharge = WalletRecharge.objects.create(
            wallet=wallet, montant=montant, methode=methode,
        )
        recharge.reference_plopplop = f"WAL{recharge.pk}-{uuid.uuid4().hex[:8]}"
        recharge.save(update_fields=['reference_plopplop'])

        try:
            result = plopplop.initier_paiement(
                commande_ref=recharge.reference_plopplop,
                montant=float(montant),
                payment_method=methode,
            )
        except Exception as e:
            logger.error("Recharge Plopplop #%s échouée : %s", recharge.pk, e)
            recharge.statut = WalletRecharge.Statut.ECHOUEE
            recharge.save(update_fields=['statut', 'updated_at'])
            raise WalletError(f"Erreur de la passerelle de paiement : {e}")

        return recharge, result['redirect_url']

    @classmethod
    def verifier_recharge_plopplop(cls, recharge) -> bool:
        """
        Vérifie le statut du paiement auprès de Plopplop et crédite le wallet
        si la transaction est confirmée (trans_status='ok'). Retourne True si
        la recharge est créditée (maintenant ou lors d'un appel précédent).
        """
        from apps.payments.services.plopplop_service import PlopplopService
        from apps.wallet.models import WalletRecharge

        if recharge.statut == WalletRecharge.Statut.CREDITEE:
            return True
        if recharge.methode == WalletRecharge.Methode.HORS_LIGNE:
            raise WalletError("Une recharge hors ligne se valide par l'admin, pas par Plopplop.")

        plopplop = PlopplopService()
        result = plopplop.verifier_paiement(recharge.reference_plopplop)
        if result.get('trans_status') != 'ok':
            return False

        cls.completer_recharge(
            recharge,
            reference=result.get('id_transaction', '') or recharge.reference_plopplop,
        )
        return True

    @classmethod
    def soumettre_recharge_hors_ligne(cls, user, montant, preuve_image):
        """
        Enregistre une recharge par dépôt hors ligne (MonCash/NatCash sur le
        compte de la plateforme) avec preuve à valider par l'admin. Limite le
        nombre de recharges en attente pour éviter le spam.
        """
        from apps.wallet.models import WalletRecharge

        montant = _en_montant(montant)
        if not (cls.MONTANT_RECHARGE_MIN <= montant <= cls.MONTANT_RECHARGE_MAX):
            raise WalletError(
                f"Le montant doit être compris entre {cls.MONTANT_RECHARGE_MIN} "
                f"et {cls.MONTANT_RECHARGE_MAX} HTG."
            )

        wallet = cls.get_wallet(user)
        if not wallet.is_active:
            raise WalletError("Ce portefeuille est désactivé.")

        en_attente = WalletRecharge.objects.filter(
            wallet=wallet, statut=WalletRecharge.Statut.PREUVE_SOUMISE,
        ).count()
        if en_attente >= cls.MAX_RECHARGES_HORS_LIGNE_EN_ATTENTE:
            raise WalletError(
                f"Vous avez déjà {en_attente} recharge(s) en attente de validation. "
                "Attendez leur traitement avant d'en soumettre une nouvelle."
            )

        recharge = WalletRecharge.objects.create(
            wallet=wallet,
            montant=montant,
            methode=WalletRecharge.Methode.HORS_LIGNE,
            statut=WalletRecharge.Statut.PREUVE_SOUMISE,
            preuve_image=preuve_image,
        )
        from apps.wallet.tasks import task_notifier_recharge_preuve_soumise
        _planifier_apres_commit(task_notifier_recharge_preuve_soumise, recharge.pk)
        return recharge

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

    # ── Paiement de commande ─────────────────────────────────────────────────

    @classmethod
    def payer_commande(cls, user, commande) -> WalletTransaction:
        """
        Paie une commande avec le wallet de l'acheteur (la totalité, ou le
        reste si un paiement partiel a déjà réservé une partie). Crée un
        Paiement type 'wallet' confirmé — la traçabilité comptable et les
        notifications existantes (signal Paiement) sont préservées — puis
        confirme la commande (débit du stock).
        """
        from apps.orders.models import Commande
        from apps.payments.models import Paiement
        from apps.payments.services.paiement_service import PaiementService

        if commande.acheteur.user_id != user.id:
            raise WalletError("Cette commande ne vous appartient pas.")
        if commande.est_payee:
            raise WalletError("Cette commande est déjà payée.")
        if commande.statut == Commande.Statut.ANNULEE:
            raise WalletError("Cette commande est annulée.")

        reste = _en_montant(commande.total) - _en_montant(commande.montant_wallet_utilise or 0)
        if reste <= 0:
            raise WalletError("Le montant restant à payer est nul.")

        wallet = cls.get_wallet(user)

        with transaction.atomic():
            tx = cls.debiter(
                wallet,
                reste,
                type_tx=WalletTransaction.Type.PAIEMENT,
                commande=commande,
                description=f"Paiement commande {commande.numero_commande}",
            )
            paiement = Paiement.objects.create(
                commande=commande,
                effectue_par=user,
                type_paiement=Paiement.TypePaiement.WALLET,
                statut=Paiement.Statut.INITIE,
                montant=reste,
                notes=f"Wallet tx #{tx.pk}",
            )
            # Basculer la méthode AVANT la confirmation : le signal cashback
            # se déclenche à la transition statut_paiement → PAYE et doit voir
            # que la commande est payée par wallet (pas de cashback sur son
            # propre solde).
            commande.methode_paiement = Commande.MethodePaiement.WALLET
            commande.save(update_fields=['methode_paiement', 'updated_at'])
            PaiementService.confirmer_paiement(
                paiement,
                verifie_par=None,
                note_verification=f"Payé par wallet — transaction #{tx.pk}",
            )

        # Confirmer la commande (débit stock) — hors du bloc financier : un
        # problème de stock ne doit pas annuler le paiement, l'admin arbitre
        # (même comportement que la confirmation Plopplop).
        from apps.orders.services.commande_service import CommandeService
        try:
            if commande.statut == Commande.Statut.EN_ATTENTE:
                CommandeService.confirmer_commande(commande)
        except Exception as e:
            logger.warning(
                "payer_commande : confirmer_commande échoué pour %s : %s",
                commande.numero_commande, e,
            )
        return tx

    # ── Paiement d'une vente POS (comptoir) ──────────────────────────────────

    @classmethod
    def payer_vente_pos(cls, user, pos_sale, montant) -> WalletTransaction:
        """
        Débite le wallet du client pour une vente au comptoir (totale ou part
        wallet d'un paiement hybride). SYNCHRONE et ONLINE uniquement — la
        synchronisation batch offline rejette toute vente wallet pour empêcher
        le double-spending. Lève SoldeInsuffisant si le solde ne couvre pas.
        """
        montant = _en_montant(montant)
        if montant <= 0:
            raise WalletError("Le montant du paiement POS doit être strictement positif.")
        wallet = cls.get_wallet(user)
        return cls._appliquer(
            wallet,
            -montant,
            WalletTransaction.Type.PAIEMENT_POS,
            pos_sale=pos_sale,
            description=f"Paiement POS — vente {pos_sale.numero_vente}",
            reference=f"pos-{pos_sale.pk}",
        )

    # ── Paiement partiel (wallet + complément MonCash/NatCash) ──────────────

    @classmethod
    def appliquer_paiement_partiel(cls, user, commande) -> WalletTransaction | None:
        """
        Réserve le solde disponible sur la commande : débite le wallet de
        min(solde, total) et l'enregistre dans commande.montant_wallet_utilise.
        Le complément part vers MonCash/NatCash (Plopplop). No-op si un
        montant est déjà réservé.
        """
        if commande.acheteur.user_id != user.id:
            raise WalletError("Cette commande ne vous appartient pas.")
        if commande.est_payee:
            raise WalletError("Cette commande est déjà payée.")
        if commande.montant_wallet_utilise and commande.montant_wallet_utilise > 0:
            return None  # déjà réservé

        wallet = cls.get_wallet(user)
        total = _en_montant(commande.total)
        reserve = min(wallet.solde, total)
        if reserve <= 0:
            raise SoldeInsuffisant("Aucun solde disponible à utiliser.")

        with transaction.atomic():
            tx = cls.debiter(
                wallet,
                reserve,
                type_tx=WalletTransaction.Type.PAIEMENT,
                commande=commande,
                description=f"Paiement partiel commande {commande.numero_commande}",
            )
            commande.montant_wallet_utilise = reserve
            commande.save(update_fields=['montant_wallet_utilise', 'updated_at'])
        return tx

    @classmethod
    def liberer_paiement_partiel(cls, commande, description='') -> WalletTransaction | None:
        """
        Re-crédite le montant réservé d'une commande non payée (complément
        jamais arrivé, commande annulée...). Idempotent : le champ
        montant_wallet_utilise est remis à zéro dans la même transaction.
        """
        from apps.orders.models import Commande

        with transaction.atomic():
            verrouillee = Commande.objects.select_for_update().get(pk=commande.pk)
            reserve = _en_montant(verrouillee.montant_wallet_utilise or 0)
            if reserve <= 0 or verrouillee.est_payee:
                return None

            wallet = cls.get_wallet(verrouillee.acheteur.user)
            tx = cls.crediter(
                wallet,
                reserve,
                # Type distinct de REMBOURSEMENT : rembourser_commande s'appuie
                # sur l'absence de transaction REMBOURSEMENT pour son
                # idempotence — une libération de réserve ne doit pas bloquer
                # un vrai remboursement ultérieur.
                type_tx=WalletTransaction.Type.LIBERATION_RESERVE,
                commande=verrouillee,
                description=description or (
                    f"Libération du solde réservé — commande {verrouillee.numero_commande}"
                ),
            )
            verrouillee.montant_wallet_utilise = Decimal('0')
            verrouillee.save(update_fields=['montant_wallet_utilise', 'updated_at'])

        commande.montant_wallet_utilise = Decimal('0')
        return tx

    # ── Remboursement ────────────────────────────────────────────────────────

    @classmethod
    def rembourser_commande(cls, commande, description='') -> WalletTransaction | None:
        """
        Crédite le wallet de l'acheteur du total de la commande payée
        (annulation/litige) et passe le paiement en 'remboursé'. Idempotent :
        ne fait rien si un remboursement existe déjà pour cette commande.
        """
        from apps.orders.models import Commande

        # Idempotence d'abord : un remboursement déjà passé (statut REMBOURSE
        # ou transaction existante) est un no-op, pas une erreur — le signal
        # d'annulation peut être rejoué.
        if WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.REMBOURSEMENT,
        ).exists():
            logger.info(
                "Commande %s déjà remboursée vers le wallet — ignoré.",
                commande.numero_commande,
            )
            return None

        if not commande.est_payee:
            if commande.statut_paiement == Commande.StatutPaiement.REMBOURSE:
                return None
            raise WalletError("Impossible de rembourser une commande non payée.")

        wallet = cls.get_wallet(commande.acheteur.user)
        with transaction.atomic():
            tx = cls.crediter(
                wallet,
                _en_montant(commande.total),
                type_tx=WalletTransaction.Type.REMBOURSEMENT,
                commande=commande,
                description=description or (
                    f"Remboursement commande {commande.numero_commande}"
                ),
            )
            commande.statut_paiement = Commande.StatutPaiement.REMBOURSE
            commande.save(update_fields=['statut_paiement', 'updated_at'])
        return tx

    # ── Cashback fidélité ────────────────────────────────────────────────────

    @classmethod
    def appliquer_cashback(cls, commande) -> WalletTransaction | None:
        """
        Crédite le cashback fidélité à l'acheteur d'une commande payée
        (taux dans SiteSettings). Ignoré si le wallet a financé tout ou
        partie de la commande — pas de cashback sur son propre solde.
        Idempotent.
        """
        from apps.core.models import SiteSettings
        from apps.orders.models import Commande

        reglages = SiteSettings.get_solo()
        if not reglages.cashback_enabled:
            return None
        taux = Decimal(str(reglages.taux_cashback or 0))
        if taux <= 0:
            return None

        if commande.methode_paiement == Commande.MethodePaiement.WALLET:
            return None
        if (commande.montant_wallet_utilise or 0) > 0:
            return None
        if WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.CASHBACK,
        ).exists():
            return None

        montant = _en_montant(Decimal(str(commande.total)) * taux / 100)
        plafond = _en_montant(reglages.cashback_montant_max or 0)
        if plafond > 0:
            montant = min(montant, plafond)
        if montant <= 0:
            return None

        wallet = cls.get_wallet(commande.acheteur.user)
        tx = cls.crediter(
            wallet,
            montant,
            type_tx=WalletTransaction.Type.CASHBACK,
            commande=commande,
            description=f"Cashback {taux}% — commande {commande.numero_commande}",
        )
        from apps.wallet.tasks import task_notifier_cashback_credite
        _planifier_apres_commit(task_notifier_cashback_credite, tx.pk)
        return tx

    @classmethod
    def reprendre_cashback(cls, commande) -> WalletTransaction | None:
        """
        Reprend le cashback accordé sur une commande (annulation/remboursement).
        Le solde peut passer en négatif si le client l'a déjà dépensé. Idempotent.
        """
        cashback_tx = WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.CASHBACK,
        ).first()
        if not cashback_tx:
            return None
        if WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.REPRISE_CASHBACK,
        ).exists():
            return None

        return cls._appliquer(
            cashback_tx.wallet,
            -cashback_tx.montant,
            WalletTransaction.Type.REPRISE_CASHBACK,
            commande=commande,
            description=f"Reprise cashback — commande {commande.numero_commande}",
            autoriser_negatif=True,
        )

    # ── Parrainage ───────────────────────────────────────────────────────────

    @classmethod
    def appliquer_bonus_parrainage(cls, commande) -> None:
        """
        Crédite le bonus de parrainage (% du total) au parrain ET au filleul
        à la première commande payée du filleul. Idempotent via la référence
        `parrainage-{filleul_id}` — un seul bonus par filleul, à vie.
        """
        from apps.core.models import SiteSettings

        reglages = SiteSettings.get_solo()
        if not reglages.parrainage_enabled:
            return
        taux = Decimal(str(reglages.taux_bonus_parrainage or 0))
        if taux <= 0:
            return

        filleul = commande.acheteur.user
        parrain = filleul.parraine_par
        if not parrain:
            return

        reference = f"parrainage-{filleul.pk}"
        if WalletTransaction.objects.filter(
            type=WalletTransaction.Type.BONUS_PARRAINAGE, reference=reference,
        ).exists():
            return

        montant = _en_montant(Decimal(str(commande.total)) * taux / 100)
        plafond = _en_montant(reglages.parrainage_bonus_montant_max or 0)
        if plafond > 0:
            montant = min(montant, plafond)
        if montant <= 0:
            return

        tx_parrain = cls.crediter(
            cls.get_wallet(parrain),
            montant,
            type_tx=WalletTransaction.Type.BONUS_PARRAINAGE,
            commande=commande,
            description=f"Bonus parrainage {taux}% — filleul {filleul.username}",
            reference=reference,
        )
        tx_filleul = cls.crediter(
            cls.get_wallet(filleul),
            montant,
            type_tx=WalletTransaction.Type.BONUS_PARRAINAGE,
            commande=commande,
            description=f"Bonus de bienvenue {taux}% — parrainé par {parrain.username}",
            reference=reference,
        )
        from apps.wallet.tasks import task_notifier_bonus_parrainage
        _planifier_apres_commit(task_notifier_bonus_parrainage, tx_parrain.pk)
        _planifier_apres_commit(task_notifier_bonus_parrainage, tx_filleul.pk)

    @classmethod
    def reprendre_bonus_parrainage(cls, commande) -> None:
        """
        Reprend les bonus de parrainage accordés sur une commande annulée.
        Débite les wallets du parrain et du filleul (négatif autorisé).
        Idempotent par wallet.
        """
        bonus_txs = WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.BONUS_PARRAINAGE,
        )
        for tx in bonus_txs:
            deja_reprise = WalletTransaction.objects.filter(
                wallet=tx.wallet,
                commande=commande,
                type=WalletTransaction.Type.REPRISE_BONUS_PARRAINAGE,
            ).exists()
            if deja_reprise:
                continue
            cls._appliquer(
                tx.wallet,
                -tx.montant,
                WalletTransaction.Type.REPRISE_BONUS_PARRAINAGE,
                commande=commande,
                description=(
                    f"Reprise bonus parrainage — commande "
                    f"{commande.numero_commande} annulée"
                ),
                autoriser_negatif=True,
            )

    # ── Vente créditée au producteur ─────────────────────────────────────────

    @classmethod
    def crediter_vente_producteur(cls, commande) -> WalletTransaction | None:
        """
        Crédite le wallet du producteur quand une commande payée est livrée :
        sous_total − commission plateforme (taux dans SiteSettings). Les
        frais de livraison ne reviennent pas au producteur ; la remise
        (voucher) est absorbée par la plateforme. Idempotent.
        """
        from apps.core.models import SiteSettings
        from apps.orders.models import Commande

        if commande.statut != Commande.Statut.LIVREE or not commande.est_payee:
            return None

        if WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.VENTE,
        ).exists():
            return None

        reglages = SiteSettings.get_solo()
        taux = Decimal(str(reglages.taux_commission or 0))
        base = _en_montant(commande.sous_total)
        commission = _en_montant(base * taux / 100)
        montant = base - commission
        if montant <= 0:
            return None

        wallet = cls.get_wallet(commande.producteur.user)
        description = f"Vente — commande {commande.numero_commande}"
        if commission > 0:
            description += f" (commission {taux}% : -{commission} HTG)"

        tx = cls.crediter(
            wallet,
            montant,
            type_tx=WalletTransaction.Type.VENTE,
            commande=commande,
            description=description,
        )

        try:
            from apps.wallet.tasks import task_notifier_vente_creditee
            _planifier_apres_commit(task_notifier_vente_creditee, tx.pk)
        except Exception as e:
            logger.error("Notification vente créditée non planifiée : %s", e)
        return tx

    @classmethod
    def reprendre_vente_producteur(cls, commande) -> WalletTransaction | None:
        """
        Reprend le crédit de vente accordé au producteur (commande annulée /
        remboursée après livraison). Le solde peut passer en négatif si le
        producteur a déjà dépensé ou retiré le montant. Idempotent.
        """
        vente_tx = WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.VENTE,
        ).first()
        if not vente_tx:
            return None
        if WalletTransaction.objects.filter(
            commande=commande, type=WalletTransaction.Type.REPRISE_VENTE,
        ).exists():
            return None

        return cls._appliquer(
            vente_tx.wallet,
            -vente_tx.montant,
            WalletTransaction.Type.REPRISE_VENTE,
            commande=commande,
            description=f"Reprise vente — commande {commande.numero_commande} annulée",
            autoriser_negatif=True,
        )

    # ── Retraits ─────────────────────────────────────────────────────────────

    MONTANT_RETRAIT_MIN = Decimal('100')
    MONTANT_RETRAIT_MAX = Decimal('1000000')

    @classmethod
    def demander_retrait(cls, user, montant, canal, numero_telephone):
        """
        Crée une demande de retrait et débite immédiatement le wallet
        (réservation) — le montant ne peut plus être dépensé en attendant
        le traitement admin. Lève SoldeInsuffisant si le solde ne suit pas.
        """
        from apps.wallet.models import WalletRetrait

        montant = _en_montant(montant)
        if not (cls.MONTANT_RETRAIT_MIN <= montant <= cls.MONTANT_RETRAIT_MAX):
            raise WalletError(
                f"Le montant d'un retrait doit être compris entre "
                f"{cls.MONTANT_RETRAIT_MIN} et {cls.MONTANT_RETRAIT_MAX} HTG."
            )
        numero_telephone = (numero_telephone or '').strip()
        if not numero_telephone:
            raise WalletError("Le numéro MonCash/NatCash est obligatoire.")
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

            from apps.wallet.tasks import task_notifier_retrait_demande
            _planifier_apres_commit(task_notifier_retrait_demande, retrait.pk)
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
    MONTANT_BON_MIN = Decimal('100')
    MONTANT_BON_MAX = Decimal('100000')

    @classmethod
    def _valider_montant_bon(cls, montant) -> Decimal:
        montant = _en_montant(montant)
        if not (cls.MONTANT_BON_MIN <= montant <= cls.MONTANT_BON_MAX):
            raise WalletError(
                f"Le montant d'un bon cadeau doit être compris entre "
                f"{cls.MONTANT_BON_MIN} et {cls.MONTANT_BON_MAX} HTG."
            )
        return montant

    @classmethod
    def creer_et_acheter_bon_wallet(cls, user, montant, email_destinataire='',
                                    message=''):
        """
        Crée un bon cadeau et le paie immédiatement avec le solde wallet.
        Le bon est annulé si le débit échoue (pas de bon orphelin en attente).
        """
        from apps.wallet.models import BonCadeau

        montant = cls._valider_montant_bon(montant)
        bon = BonCadeau.objects.create(
            montant=montant,
            achete_par=user,
            email_destinataire=(email_destinataire or '').strip(),
            message_destinataire=(message or '').strip()[:255],
        )
        try:
            cls.acheter_bon_cadeau_avec_wallet(user, bon)
        except WalletError:
            bon.statut = BonCadeau.Statut.ANNULE
            bon.save(update_fields=['statut', 'updated_at'])
            raise
        return bon

    @classmethod
    def initier_bon_cadeau_plopplop(cls, user, montant, methode,
                                    email_destinataire='', message=''):
        """
        Crée un bon cadeau en attente de paiement et initie le paiement
        MonCash/NatCash via Plopplop. Retourne (bon, redirect_url).
        """
        import uuid

        from apps.payments.services.plopplop_service import PlopplopService
        from apps.wallet.models import BonCadeau

        montant = cls._valider_montant_bon(montant)

        plopplop = PlopplopService()
        if not plopplop.is_configured():
            raise WalletError("La passerelle de paiement n'est pas configurée.")

        bon = BonCadeau.objects.create(
            montant=montant,
            achete_par=user,
            email_destinataire=(email_destinataire or '').strip(),
            message_destinataire=(message or '').strip()[:255],
        )
        bon.reference_plopplop = f"GFT{bon.pk}-{uuid.uuid4().hex[:8]}"
        bon.save(update_fields=['reference_plopplop'])

        try:
            result = plopplop.initier_paiement(
                commande_ref=bon.reference_plopplop,
                montant=float(montant),
                payment_method=methode,
            )
        except Exception as e:
            logger.error("Achat bon cadeau Plopplop #%s échoué : %s", bon.pk, e)
            bon.statut = BonCadeau.Statut.ANNULE
            bon.save(update_fields=['statut', 'updated_at'])
            raise WalletError(f"Erreur de la passerelle de paiement : {e}")

        return bon, result['redirect_url']

    @classmethod
    def verifier_bon_cadeau_plopplop(cls, bon) -> bool:
        """
        Vérifie le paiement du bon auprès de Plopplop et l'active si la
        transaction est confirmée. Retourne True si le bon est actif (ou
        déjà activé/utilisé lors d'un appel précédent).
        """
        from apps.payments.services.plopplop_service import PlopplopService
        from apps.wallet.models import BonCadeau

        if bon.statut in (BonCadeau.Statut.ACTIF, BonCadeau.Statut.UTILISE):
            return True
        if bon.statut != BonCadeau.Statut.ATTENTE_PAIEMENT:
            return False
        if not bon.reference_plopplop:
            raise WalletError("Ce bon n'a pas été initié via Plopplop.")

        plopplop = PlopplopService()
        result = plopplop.verifier_paiement(bon.reference_plopplop)
        if result.get('trans_status') != 'ok':
            return False

        cls.activer_bon_cadeau(
            bon,
            reference=result.get('id_transaction', '') or bon.reference_plopplop,
        )
        return True

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
