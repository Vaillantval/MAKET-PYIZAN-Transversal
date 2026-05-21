"""
Tâches Celery pour l'envoi asynchrone de notifications (email + FCM).

Convention :
  - Chaque tâche reçoit des IDs (pas des instances) → re-query dans la tâche
  - bind=True + max_retries=3 → retry automatique avec backoff exponentiel
  - Les imports de modèles sont locaux pour éviter les imports circulaires au démarrage
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


# ── Utilitaire de retry ────────────────────────────────────────────────────────

def _retry(self, exc):
    """Retry avec backoff : 1 min → 2 min → 4 min."""
    raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ── Producteurs ───────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.producteur_inscrit')
def task_producteur_inscrit(self, producteur_id):
    """Email bienvenue au producteur + alerte admin à l'inscription."""
    try:
        from apps.accounts.models import Producteur
        from apps.emails.utils import email_producteur_bienvenue, email_admin_nouveau_producteur
        producteur = Producteur.objects.get(pk=producteur_id)
        email_producteur_bienvenue(producteur)
        email_admin_nouveau_producteur(producteur)
    except Exception as exc:
        logger.exception("task_producteur_inscrit(%s) échec", producteur_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='emails.producteur_statut_change')
def task_producteur_statut_change(self, producteur_id, nouveau_statut):
    """Email au producteur lors d'un changement de statut (validé / suspendu / rejeté)."""
    try:
        from apps.accounts.models import Producteur
        from apps.emails.utils import (
            email_producteur_valide,
            email_producteur_suspendu,
            email_producteur_rejete,
        )
        producteur = Producteur.objects.get(pk=producteur_id)
        if nouveau_statut == 'actif':
            email_producteur_valide(producteur)
        elif nouveau_statut == 'suspendu':
            email_producteur_suspendu(producteur)
        elif nouveau_statut == 'inactif':
            email_producteur_rejete(producteur)
    except Exception as exc:
        logger.exception("task_producteur_statut_change(%s, %s) échec", producteur_id, nouveau_statut)
        _retry(self, exc)


# ── Commandes ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.commande_statut_change')
def task_commande_statut_change(self, commande_id, statut_avant_display):
    """Email acheteur lors d'un changement de statut de commande."""
    try:
        from apps.orders.models import Commande
        from apps.emails.utils import email_statut_commande_change
        commande = Commande.objects.select_related('acheteur__user').get(pk=commande_id)
        email_statut_commande_change(commande, statut_avant_display)
    except Exception as exc:
        logger.exception("task_commande_statut_change(%s) échec", commande_id)
        _retry(self, exc)


# ── Paiements ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.paiement_confirme')
def task_paiement_confirme(self, paiement_id):
    """
    Email confirmation paiement + emails nouvelle commande (acheteur + admin)
    + push FCM admin — déclenché après confirmation de paiement.
    """
    try:
        from apps.payments.models import Paiement
        from apps.emails.utils import (
            email_paiement_confirme,
            email_nouvelle_commande_acheteur,
            email_nouvelle_commande_admin,
        )
        from apps.emails.fcm_notifications import push_nouvelle_commande_admin
        paiement = Paiement.objects.select_related(
            'commande__acheteur__user'
        ).get(pk=paiement_id)
        email_paiement_confirme(paiement)
        email_nouvelle_commande_acheteur(paiement.commande)
        email_nouvelle_commande_admin(paiement.commande)
        push_nouvelle_commande_admin(paiement.commande)
    except Exception as exc:
        logger.exception("task_paiement_confirme(%s) échec", paiement_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='emails.preuve_paiement_soumise')
def task_preuve_paiement_soumise(self, paiement_id):
    """Email admin quand une preuve de paiement est soumise."""
    try:
        from apps.payments.models import Paiement
        from apps.emails.utils import email_preuve_paiement_admin
        paiement = Paiement.objects.select_related('commande__acheteur').get(pk=paiement_id)
        email_preuve_paiement_admin(paiement)
    except Exception as exc:
        logger.exception("task_preuve_paiement_soumise(%s) échec", paiement_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='emails.paiement_echec')
def task_paiement_echec(self, commande_ids, methode, prenom, email_dest, acheteur_id, raison=''):
    """Email acheteur + admin pour un paiement MonCash/NatCash échoué."""
    try:
        from apps.orders.models import Commande
        from apps.accounts.models import CustomUser
        from apps.emails.utils import email_paiement_echec_acheteur, email_paiement_echec_admin
        commandes    = list(Commande.objects.filter(pk__in=commande_ids))
        acheteur_user = CustomUser.objects.get(pk=acheteur_id)
        email_paiement_echec_acheteur(
            commandes=commandes,
            methode=methode,
            prenom=prenom,
            email_dest=email_dest,
        )
        email_paiement_echec_admin(
            commandes=commandes,
            methode=methode,
            acheteur=acheteur_user,
            raison=raison,
        )
    except Exception as exc:
        logger.exception("task_paiement_echec(%s) échec", commande_ids)
        _retry(self, exc)


# ── Stock ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.alerte_stock')
def task_alerte_stock(self, alerte_id):
    """Email + push FCM (producteur + admin) pour alerte stock critique/épuisé."""
    try:
        from apps.stock.models import AlerteStock
        from apps.emails.utils import email_alerte_stock, email_alerte_stock_admin
        from apps.emails.fcm_notifications import push_alerte_stock_producteur, push_alerte_stock_admin
        alerte = AlerteStock.objects.select_related('produit__producteur__user').get(pk=alerte_id)
        email_alerte_stock(alerte)
        email_alerte_stock_admin(alerte)
        push_alerte_stock_producteur(alerte)
        push_alerte_stock_admin(alerte)
    except Exception as exc:
        logger.exception("task_alerte_stock(%s) échec", alerte_id)
        _retry(self, exc)


# ── Collectes ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.invitation_collecte')
def task_invitation_collecte(self, participation_id):
    """Email + push FCM producteur pour une invitation à une collecte."""
    try:
        from apps.collectes.models import ParticipationCollecte
        from apps.emails.utils import email_invitation_collecte
        from apps.emails.fcm_notifications import push_invitation_collecte_producteur
        participation = ParticipationCollecte.objects.select_related(
            'producteur__user', 'collecte__zone'
        ).get(pk=participation_id)
        email_invitation_collecte(participation)
        push_invitation_collecte_producteur(participation)
    except Exception as exc:
        logger.exception("task_invitation_collecte(%s) échec", participation_id)
        _retry(self, exc)


@shared_task(bind=True, max_retries=3, name='emails.collecte_confirmee_admin')
def task_collecte_confirmee_admin(self, participation_id):
    """Email + push FCM admin quand un producteur confirme sa participation."""
    try:
        from apps.collectes.models import ParticipationCollecte
        from apps.emails.utils import email_collecte_confirme_admin
        from apps.emails.fcm_notifications import push_collecte_confirmee_admin
        participation = ParticipationCollecte.objects.select_related(
            'producteur__user', 'collecte'
        ).get(pk=participation_id)
        email_collecte_confirme_admin(participation)
        push_collecte_confirmee_admin(participation)
    except Exception as exc:
        logger.exception("task_collecte_confirmee_admin(%s) échec", participation_id)
        _retry(self, exc)


# ── Contact ───────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.push_reponse_contact')
def task_push_reponse_contact(self, reponse_id):
    """Push FCM uniquement pour la réponse à un message de contact.
    L'email est géré de façon synchrone dans la view (rollback si échec)."""
    try:
        from apps.home.models import ContactReponse
        from apps.emails.fcm_notifications import push_reponse_contact
        reponse = ContactReponse.objects.select_related('message').get(pk=reponse_id)
        push_reponse_contact(reponse.message, reponse)
    except Exception as exc:
        logger.exception("task_push_reponse_contact(%s) échec", reponse_id)
        _retry(self, exc)


# ── Vouchers ──────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, name='emails.voucher_cree')
def task_voucher_cree(self, voucher_id):
    """Email bénéficiaire à la création d'un voucher."""
    try:
        from apps.payments.models import Voucher
        from apps.emails.utils import email_voucher_cree
        voucher = Voucher.objects.select_related('beneficiaire__user').get(pk=voucher_id)
        email_voucher_cree(voucher)
    except Exception as exc:
        logger.exception("task_voucher_cree(%s) échec", voucher_id)
        _retry(self, exc)
