"""
Tâches Celery wallet — même convention que apps/emails/tasks.py :
  - Chaque tâche reçoit des IDs (pas des instances) → re-query dans la tâche
  - bind=True + max_retries=3 → retry avec backoff exponentiel
  - Imports de modèles locaux pour éviter les imports circulaires
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _retry(self, exc):
    """Retry avec backoff : 1 min → 2 min → 4 min."""
    raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _push_wallet(user, title, body, data_extra=None):
    """Push FCM vers l'utilisateur (deep-link écran wallet Flutter)."""
    if not user.fcm_token:
        return
    from apps.emails.fcm_service import send_to_token
    data = {"screen": "wallet"}
    if data_extra:
        data.update(data_extra)
    send_to_token(user.fcm_token, title, body, data)


# ── Recharges ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='wallet.recharge_preuve_soumise')
def task_notifier_recharge_preuve_soumise(self, recharge_id):
    """Email admin : preuve de recharge hors ligne à valider."""
    try:
        from apps.wallet.emails import email_admin_recharge_preuve
        from apps.wallet.models import WalletRecharge
        recharge = WalletRecharge.objects.select_related('wallet__user').get(pk=recharge_id)
        email_admin_recharge_preuve(recharge)
    except Exception as exc:
        logger.exception("task_notifier_recharge_preuve_soumise(%s) échec", recharge_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='wallet.recharge_validee')
def task_notifier_recharge_validee(self, recharge_id):
    """Email + push client : recharge hors ligne validée et créditée."""
    try:
        from apps.wallet.emails import email_recharge_validee
        from apps.wallet.models import WalletRecharge
        recharge = WalletRecharge.objects.select_related('wallet__user').get(pk=recharge_id)
        email_recharge_validee(recharge)
        _push_wallet(
            recharge.wallet.user,
            "Recharge créditée ✅",
            f"Votre recharge de {recharge.montant} HTG a été créditée sur votre portefeuille.",
            {"recharge_id": str(recharge.pk)},
        )
    except Exception as exc:
        logger.exception("task_notifier_recharge_validee(%s) échec", recharge_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='wallet.recharge_rejetee')
def task_notifier_recharge_rejetee(self, recharge_id):
    """Email + push client : recharge hors ligne rejetée."""
    try:
        from apps.wallet.emails import email_recharge_rejetee
        from apps.wallet.models import WalletRecharge
        recharge = WalletRecharge.objects.select_related('wallet__user').get(pk=recharge_id)
        email_recharge_rejetee(recharge)
        _push_wallet(
            recharge.wallet.user,
            "Recharge non validée",
            f"Votre recharge de {recharge.montant} HTG n'a pas pu être validée. "
            "Vérifiez votre preuve de dépôt.",
            {"recharge_id": str(recharge.pk)},
        )
    except Exception as exc:
        logger.exception("task_notifier_recharge_rejetee(%s) échec", recharge_id)
        _retry(self, exc)


# ── Retraits ──────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='wallet.retrait_demande')
def task_notifier_retrait_demande(self, retrait_id):
    """Email admin : demande de retrait à traiter."""
    try:
        from apps.wallet.emails import email_admin_retrait_demande
        from apps.wallet.models import WalletRetrait
        retrait = WalletRetrait.objects.select_related('wallet__user').get(pk=retrait_id)
        email_admin_retrait_demande(retrait)
    except Exception as exc:
        logger.exception("task_notifier_retrait_demande(%s) échec", retrait_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='wallet.retrait_paye')
def task_notifier_retrait_paye(self, retrait_id):
    """Email + push client : retrait payé (transfert effectué)."""
    try:
        from apps.wallet.emails import email_retrait_paye
        from apps.wallet.models import WalletRetrait
        retrait = WalletRetrait.objects.select_related('wallet__user').get(pk=retrait_id)
        email_retrait_paye(retrait)
        _push_wallet(
            retrait.wallet.user,
            "Retrait payé ✅",
            f"Votre retrait de {retrait.montant} HTG a été envoyé sur "
            f"{retrait.get_canal_display()} {retrait.numero_telephone}.",
            {"retrait_id": str(retrait.pk)},
        )
    except Exception as exc:
        logger.exception("task_notifier_retrait_paye(%s) échec", retrait_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='wallet.retrait_rejete')
def task_notifier_retrait_rejete(self, retrait_id):
    """Email + push client : retrait rejeté, solde re-crédité."""
    try:
        from apps.wallet.emails import email_retrait_rejete
        from apps.wallet.models import WalletRetrait
        retrait = WalletRetrait.objects.select_related('wallet__user').get(pk=retrait_id)
        email_retrait_rejete(retrait)
        _push_wallet(
            retrait.wallet.user,
            "Retrait rejeté",
            f"Votre demande de retrait de {retrait.montant} HTG a été rejetée. "
            "Le montant a été re-crédité sur votre portefeuille.",
            {"retrait_id": str(retrait.pk)},
        )
    except Exception as exc:
        logger.exception("task_notifier_retrait_rejete(%s) échec", retrait_id)
        _retry(self, exc)


# ── Réserves de paiement partiel ──────────────────────────────────────────────

@shared_task(name='wallet.liberer_reserves_expirees')
def task_liberer_reserves_expirees():
    """
    Libère les montants wallet réservés (paiement partiel) sur les commandes
    restées impayées plus de 24 h : le complément MonCash/NatCash n'est
    jamais arrivé, on rend l'argent au client. Planifiée par Celery Beat.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.orders.models import Commande
    from apps.wallet.services import WalletService

    limite = timezone.now() - timedelta(hours=24)
    commandes = Commande.objects.filter(
        montant_wallet_utilise__gt=0,
        updated_at__lt=limite,
    ).exclude(
        statut_paiement__in=(
            Commande.StatutPaiement.PAYE, Commande.StatutPaiement.REMBOURSE,
        ),
    ).exclude(statut=Commande.Statut.ANNULEE)

    liberees = 0
    for commande in commandes:
        try:
            tx = WalletService.liberer_paiement_partiel(
                commande,
                description=(
                    f"Complément non payé sous 24 h — commande {commande.numero_commande}"
                ),
            )
            if tx:
                liberees += 1
        except Exception as e:
            logger.error(
                "Libération réserve commande %s échouée : %s",
                commande.numero_commande, e,
            )

    if liberees:
        logger.info("%s réservation(s) wallet libérée(s).", liberees)
    return liberees


# ── Bons cadeaux ──────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='wallet.envoyer_bon_cadeau')
def task_envoyer_bon_cadeau(self, bon_id):
    """Email du code cadeau au destinataire (ou à l'acheteur)."""
    try:
        from apps.wallet.emails import email_bon_cadeau
        from apps.wallet.models import BonCadeau
        bon = BonCadeau.objects.select_related('achete_par').get(pk=bon_id)
        email_bon_cadeau(bon)
    except Exception as exc:
        logger.exception("task_envoyer_bon_cadeau(%s) échec", bon_id)
        _retry(self, exc)


@shared_task(name='wallet.expirer_bons_cadeaux')
def task_expirer_bons_cadeaux():
    """
    Passe en 'expire' les bons cadeaux actifs dont la date d'expiration est
    dépassée. Planifiée par Celery Beat (une fois par jour).
    """
    from django.utils import timezone

    from apps.wallet.models import BonCadeau

    expires = BonCadeau.objects.filter(
        statut=BonCadeau.Statut.ACTIF,
        date_expiration__lt=timezone.now(),
    ).update(statut=BonCadeau.Statut.EXPIRE)

    if expires:
        logger.info("%s bon(s) cadeau(x) expiré(s).", expires)
    return expires
