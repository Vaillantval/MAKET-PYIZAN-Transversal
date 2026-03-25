from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.accounts.models import Producteur
from apps.orders.models import Commande
from apps.payments.models import Paiement
from apps.stock.models import AlerteStock
from apps.collectes.models import ParticipationCollecte


# ── Signal : Nouveau producteur inscrit ────────────────────────
@receiver(post_save, sender=Producteur)
def on_producteur_cree(sender, instance, created, **kwargs):
    if created:
        from apps.emails.utils import (
            email_producteur_bienvenue,
            email_admin_nouveau_producteur,
        )
        email_producteur_bienvenue(instance)
        email_admin_nouveau_producteur(instance)


# ── Signal : Statut producteur changé (validation/rejet/suspension) ───────
@receiver(pre_save, sender=Producteur)
def on_producteur_statut_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        ancien = Producteur.objects.get(pk=instance.pk)
    except Producteur.DoesNotExist:
        return

    if ancien.statut == instance.statut:
        return

    from apps.emails.utils import (
        email_producteur_valide,
        email_producteur_suspendu,
        email_producteur_rejete,
    )

    if instance.statut == Producteur.Statut.ACTIF:
        email_producteur_valide(instance)
    elif instance.statut == Producteur.Statut.SUSPENDU:
        email_producteur_suspendu(instance)
    elif instance.statut == Producteur.Statut.INACTIF:
        email_producteur_rejete(instance)


# ── Signal : Nouvelle commande créée ───────────────────────────
@receiver(post_save, sender=Commande)
def on_commande_creee(sender, instance, created, **kwargs):
    if created:
        from apps.emails.utils import (
            email_nouvelle_commande_acheteur,
            email_nouvelle_commande_producteur
        )
        email_nouvelle_commande_acheteur(instance)
        email_nouvelle_commande_producteur(instance)


# ── Signal : Statut commande changé ────────────────────────────
@receiver(pre_save, sender=Commande)
def on_commande_statut_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        ancienne = Commande.objects.get(pk=instance.pk)
    except Commande.DoesNotExist:
        return

    if ancienne.statut == instance.statut:
        return

    from apps.emails.utils import email_statut_commande_change
    email_statut_commande_change(instance, ancienne.get_statut_display())


# ── Signal : Paiement changé ────────────────────────────────────
@receiver(pre_save, sender=Paiement)
def on_paiement_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        ancien = Paiement.objects.get(pk=instance.pk)
    except Paiement.DoesNotExist:
        return

    if ancien.statut == instance.statut:
        return

    from apps.emails.utils import (
        email_paiement_confirme,
        email_preuve_paiement_admin
    )

    if instance.statut == Paiement.Statut.CONFIRME:
        email_paiement_confirme(instance)

    if instance.statut == Paiement.Statut.SOUMIS:
        email_preuve_paiement_admin(instance)


# ── Signal : Nouvelle alerte stock ─────────────────────────────
@receiver(post_save, sender=AlerteStock)
def on_alerte_stock_creee(sender, instance, created, **kwargs):
    if created and instance.niveau in [
        AlerteStock.Niveau.CRITIQUE,
        AlerteStock.Niveau.EPUISE
    ]:
        from apps.emails.utils import email_alerte_stock
        email_alerte_stock(instance)


# ── Signal : Invitation collecte ───────────────────────────────
@receiver(post_save, sender=ParticipationCollecte)
def on_participation_creee(sender, instance, created, **kwargs):
    if created:
        from apps.emails.utils import email_invitation_collecte
        email_invitation_collecte(instance)
