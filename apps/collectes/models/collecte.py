from django.db import models
from django.conf import settings
from apps.accounts.models.producteur import Departement


class ZoneCollecte(models.Model):
    nom         = models.CharField(max_length=150)
    departement = models.CharField(max_length=20, choices=Departement.choices)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Zone de collecte'
        verbose_name_plural = 'Zones de collecte'
        ordering            = ['departement', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_departement_display()})"


class PointCollecte(models.Model):
    zone        = models.ForeignKey(ZoneCollecte, on_delete=models.CASCADE, related_name='points')
    nom         = models.CharField(max_length=150)
    adresse     = models.TextField()
    commune     = models.CharField(max_length=100)
    latitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    responsable = models.CharField(max_length=200, blank=True)
    telephone   = models.CharField(max_length=20, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Point de collecte'
        verbose_name_plural = 'Points de collecte'
        ordering            = ['zone', 'nom']

    def __str__(self):
        return f"{self.nom} — {self.commune} ({self.zone.nom})"


class Collecte(models.Model):
    class Statut(models.TextChoices):
        PLANIFIEE  = 'planifiee',  'Planifiee'
        EN_COURS   = 'en_cours',   'En cours'
        TERMINEE   = 'terminee',   'Terminee'
        ANNULEE    = 'annulee',    'Annulee'
        REPORTEE   = 'reportee',   'Reportee'

    reference       = models.CharField(max_length=30, unique=True, blank=True)
    zone            = models.ForeignKey(ZoneCollecte, on_delete=models.PROTECT, related_name='collectes')
    point_collecte  = models.ForeignKey(PointCollecte, on_delete=models.SET_NULL, null=True, blank=True, related_name='collectes')
    collecteur      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='collectes_assignees')
    date_planifiee  = models.DateField()
    heure_debut     = models.TimeField(null=True, blank=True)
    heure_fin       = models.TimeField(null=True, blank=True)
    date_debut_reel = models.DateTimeField(null=True, blank=True)
    date_fin_reel   = models.DateTimeField(null=True, blank=True)
    statut          = models.CharField(max_length=20, choices=Statut.choices, default=Statut.PLANIFIEE)
    notes           = models.TextField(blank=True)
    rapport         = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Collecte'
        verbose_name_plural = 'Collectes'
        ordering            = ['-date_planifiee']

    def __str__(self):
        return f"{self.reference} — {self.zone.nom} — {self.date_planifiee}"

    def save(self, *args, **kwargs):
        if not self.reference:
            from django.utils import timezone
            annee = timezone.now().year
            count = Collecte.objects.filter(reference__startswith=f'COL-{annee}-').count()
            self.reference = f'COL-{annee}-{str(count + 1).zfill(4)}'
        super().save(*args, **kwargs)

    @property
    def nb_producteurs(self):
        return self.participations.count()

    @property
    def nb_commandes(self):
        return self.commandes.count()

    @property
    def montant_total(self):
        from django.db.models import Sum
        return self.commandes.aggregate(total=Sum('total'))['total'] or 0

    @property
    def est_en_retard(self):
        from django.utils import timezone
        if self.statut in [self.Statut.TERMINEE, self.Statut.ANNULEE]:
            return False
        return self.date_planifiee < timezone.now().date()


class ParticipationCollecte(models.Model):
    class Statut(models.TextChoices):
        INSCRIT   = 'inscrit',   'Inscrit'
        CONFIRME  = 'confirme',  'Confirme'
        PRESENT   = 'present',   'Present'
        ABSENT    = 'absent',    'Absent'
        ANNULE    = 'annule',    'Annule'

    collecte    = models.ForeignKey(Collecte, on_delete=models.CASCADE, related_name='participations')
    producteur  = models.ForeignKey('accounts.Producteur', on_delete=models.CASCADE, related_name='participations_collectes')
    statut      = models.CharField(max_length=20, choices=Statut.choices, default=Statut.INSCRIT)
    quantite_prevue   = models.PositiveIntegerField(default=0, help_text="Quantite estimee a apporter (kg ou unites)")
    quantite_collectee = models.PositiveIntegerField(default=0, help_text="Quantite reellement collectee")
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Participation collecte'
        verbose_name_plural = 'Participations collectes'
        unique_together     = ('collecte', 'producteur')
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.collecte.reference} — {self.producteur.user.get_full_name()} — {self.get_statut_display()}"

    @property
    def taux_realisation(self):
        if self.quantite_prevue == 0: return 0
        return round((self.quantite_collectee / self.quantite_prevue) * 100, 1)
