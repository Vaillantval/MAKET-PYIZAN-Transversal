from django.db import models
from django.conf import settings


class Lot(models.Model):
    class Statut(models.TextChoices):
        EN_COURS   = 'en_cours',   'En cours'
        DISPONIBLE = 'disponible', 'Disponible'
        EPUISE     = 'epuise',     'Epuise'
        EXPIRE     = 'expire',     'Expire'
        RAPPEL     = 'rappel',     'Rappele'

    produit            = models.ForeignKey('catalog.Produit', on_delete=models.CASCADE, related_name='lots')
    numero_lot         = models.CharField(max_length=50, unique=True, blank=True)
    code_barres        = models.CharField(max_length=100, blank=True, unique=True, null=True)
    quantite_initiale  = models.PositiveIntegerField()
    quantite_actuelle  = models.PositiveIntegerField()
    quantite_vendue    = models.PositiveIntegerField(default=0)
    date_recolte       = models.DateField(null=True, blank=True)
    date_expiration    = models.DateField(null=True, blank=True)
    lieu_stockage      = models.CharField(max_length=200, blank=True)
    notes              = models.TextField(blank=True)
    statut             = models.CharField(max_length=20, choices=Statut.choices, default=Statut.DISPONIBLE)
    cree_par           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lots_crees')
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Lot'
        verbose_name_plural = 'Lots'
        ordering            = ['-created_at']

    def __str__(self): return f"{self.numero_lot} — {self.produit.nom}"

    def save(self, *args, **kwargs):
        if not self.numero_lot:
            from django.utils import timezone
            annee = timezone.now().year
            count = Lot.objects.filter(numero_lot__startswith=f'LOT-{annee}-').count()
            self.numero_lot = f'LOT-{annee}-{str(count + 1).zfill(5)}'
        if self.quantite_actuelle == 0:
            self.statut = self.Statut.EPUISE
        super().save(*args, **kwargs)
        self._sync_stock_produit()

    def _sync_stock_produit(self):
        from django.db.models import Sum
        total = Lot.objects.filter(
            produit=self.produit,
            statut__in=[self.Statut.DISPONIBLE, self.Statut.EN_COURS]
        ).aggregate(total=Sum('quantite_actuelle'))['total'] or 0
        self.produit.stock_disponible = total
        self.produit.save(update_fields=['stock_disponible'])

    @property
    def taux_ecoulement(self):
        if self.quantite_initiale == 0: return 0
        return round((self.quantite_vendue / self.quantite_initiale) * 100, 1)
