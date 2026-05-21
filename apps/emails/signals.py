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
        from apps.emails.tasks import task_producteur_inscrit
        task_producteur_inscrit.delay(instance.pk)


# ── Signal : Statut producteur changé (validation/rejet/suspension) ─────────
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

    from apps.emails.tasks import task_producteur_statut_change
    # Passer le nouveau statut en paramètre — à l'exécution de la tâche,
    # le save() sera terminé et l'instance en base aura le bon statut.
    task_producteur_statut_change.delay(instance.pk, instance.statut)


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

    from apps.emails.tasks import task_commande_statut_change
    task_commande_statut_change.delay(instance.pk, ancienne.get_statut_display())


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

    from apps.emails.tasks import task_paiement_confirme, task_preuve_paiement_soumise

    if instance.statut == Paiement.Statut.CONFIRME:
        task_paiement_confirme.delay(instance.pk)

    if instance.statut == Paiement.Statut.SOUMIS:
        task_preuve_paiement_soumise.delay(instance.pk)


# ── Signal : Nouvelle alerte stock ─────────────────────────────
@receiver(post_save, sender=AlerteStock)
def on_alerte_stock_creee(sender, instance, created, **kwargs):
    if created and instance.niveau in [
        AlerteStock.Niveau.CRITIQUE,
        AlerteStock.Niveau.EPUISE,
    ]:
        from apps.emails.tasks import task_alerte_stock
        task_alerte_stock.delay(instance.pk)


# ── Signal : Invitation collecte ───────────────────────────────
@receiver(post_save, sender=ParticipationCollecte)
def on_participation_creee(sender, instance, created, **kwargs):
    if created:
        from apps.emails.tasks import task_invitation_collecte
        task_invitation_collecte.delay(instance.pk)
