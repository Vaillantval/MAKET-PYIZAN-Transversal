from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class ProgrammeVoucher(models.Model):
    class TypeProgramme(models.TextChoices):
        ONG          = 'ong',        'Organisation Non Gouvernementale'
        GOUVERNEMENT = 'gouv',       'Programme gouvernemental'
        COOPERATIVE  = 'coop',       'Cooperative agricole'
        ENTREPRISE   = 'entreprise', 'Entreprise privee'

    nom             = models.CharField(max_length=200)
    code_programme  = models.CharField(max_length=50, unique=True)
    type_programme  = models.CharField(max_length=20, choices=TypeProgramme.choices)
    description     = models.TextField(blank=True)
    logo            = models.ImageField(upload_to='vouchers/logos/', null=True, blank=True)
    contact_nom     = models.CharField(max_length=200, blank=True)
    contact_email   = models.EmailField(blank=True)
    contact_tel     = models.CharField(max_length=20, blank=True)
    budget_total    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    budget_utilise  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active       = models.BooleanField(default=True)
    date_debut      = models.DateField()
    date_fin        = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Programme Voucher'
        verbose_name_plural = 'Programmes Voucher'
        ordering            = ['-created_at']

    def __str__(self): return f"{self.nom} ({self.code_programme})"

    @property
    def budget_restant(self):
        if self.budget_total is None: return None
        return self.budget_total - self.budget_utilise

    @property
    def est_en_cours(self):
        aujourd_hui = timezone.now().date()
        return self.is_active and self.date_debut <= aujourd_hui <= self.date_fin


class Voucher(models.Model):
    class Statut(models.TextChoices):
        ACTIF    = 'actif',    'Actif'
        UTILISE  = 'utilise',  'Utilise'
        EXPIRE   = 'expire',   'Expire'
        ANNULE   = 'annule',   'Annule'
        SUSPENDU = 'suspendu', 'Suspendu'

    class TypeValeur(models.TextChoices):
        FIXE        = 'fixe',    'Montant fixe'
        POURCENTAGE = 'pourcent','Pourcentage de reduction'

    code                  = models.CharField(max_length=20, unique=True, blank=True)
    programme             = models.ForeignKey(ProgrammeVoucher, on_delete=models.PROTECT, related_name='vouchers')
    beneficiaire          = models.ForeignKey('accounts.Acheteur', on_delete=models.PROTECT, related_name='vouchers', null=True, blank=True)
    type_valeur           = models.CharField(max_length=10, choices=TypeValeur.choices, default=TypeValeur.FIXE)
    valeur                = models.DecimalField(max_digits=10, decimal_places=2)
    montant_max           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    categories_autorisees = models.ManyToManyField('catalog.Categorie', blank=True)
    montant_commande_min  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    statut                = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF)
    date_expiration       = models.DateField()
    date_utilisation      = models.DateTimeField(null=True, blank=True)
    cree_par              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_crees')
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Voucher'
        verbose_name_plural = 'Vouchers'
        ordering            = ['-created_at']

    def __str__(self): return f"{self.code} — {self.valeur} HTG — {self.get_statut_display()}"

    def save(self, *args, **kwargs):
        if not self.code: self.code = self._generer_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generer_code():
        while True:
            uid  = uuid.uuid4().hex[:8].upper()
            code = f"VCH-{uid[:4]}-{uid[4:]}"
            if not Voucher.objects.filter(code=code).exists():
                return code

    @property
    def est_valide(self):
        return self.statut == self.Statut.ACTIF and self.date_expiration >= timezone.now().date()

    def calculer_remise(self, montant_commande):
        if not self.est_valide: return 0
        if montant_commande < self.montant_commande_min: return 0
        if self.type_valeur == self.TypeValeur.FIXE:
            return min(self.valeur, montant_commande)
        else:
            remise = montant_commande * (self.valeur / 100)
            if self.montant_max: remise = min(remise, self.montant_max)
            return remise
