from django.db import models
from django.conf import settings


class Commande(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE     = 'en_attente',     'En attente de confirmation'
        CONFIRMEE      = 'confirmee',      'Confirmee'
        EN_PREPARATION = 'en_preparation', 'En preparation'
        PRETE          = 'prete',          'Prete pour collecte'
        EN_COLLECTE    = 'en_collecte',    'En cours de collecte'
        LIVREE         = 'livree',         'Livree'
        ANNULEE        = 'annulee',        'Annulee'
        LITIGE         = 'litige',         'En litige'

    class ModeLivraison(models.TextChoices):
        LIVRAISON_DOMICILE = 'domicile', 'Livraison a domicile'
        RETRAIT_PRODUCTEUR = 'retrait',  'Retrait chez le producteur'
        POINT_COLLECTE     = 'collecte', 'Point de collecte'

    class MethodePaiement(models.TextChoices):
        MONCASH    = 'moncash',    'MonCash'
        NATCASH    = 'natcash',    'NatCash'
        VIREMENT   = 'virement',   'Virement bancaire'
        CASH       = 'cash',       'Especes'
        VOUCHER    = 'voucher',    'e-Voucher'
        HORS_LIGNE = 'hors_ligne', 'Paiement hors ligne'

    class StatutPaiement(models.TextChoices):
        NON_PAYE       = 'non_paye',       'Non paye'
        EN_ATTENTE     = 'en_attente',     'En attente de verification'
        PREUVE_SOUMISE = 'preuve_soumise', 'Preuve soumise'
        VERIFIE        = 'verifie',        'Verifie'
        PAYE           = 'paye',           'Paye'
        REMBOURSE      = 'rembourse',      'Rembourse'

    numero_commande        = models.CharField(max_length=30, unique=True, blank=True)
    acheteur               = models.ForeignKey('accounts.Acheteur', on_delete=models.PROTECT, related_name='commandes')
    producteur             = models.ForeignKey('accounts.Producteur', on_delete=models.PROTECT, related_name='commandes_recues')
    collecte               = models.ForeignKey('collectes.Collecte', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    statut                 = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    statut_paiement        = models.CharField(max_length=20, choices=StatutPaiement.choices, default=StatutPaiement.NON_PAYE)
    methode_paiement       = models.CharField(max_length=20, choices=MethodePaiement.choices)
    preuve_paiement        = models.ImageField(upload_to='commandes/preuves/', null=True, blank=True)
    voucher                = models.ForeignKey('payments.Voucher', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    reference_paiement     = models.CharField(max_length=100, blank=True)
    sous_total             = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_livraison        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remise                 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total                  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mode_livraison         = models.CharField(max_length=20, choices=ModeLivraison.choices, default=ModeLivraison.POINT_COLLECTE)
    adresse_livraison      = models.TextField(blank=True)
    ville_livraison        = models.CharField(max_length=100, blank=True)
    departement_livraison  = models.CharField(max_length=100, blank=True)
    notes_acheteur         = models.TextField(blank=True)
    notes_admin            = models.TextField(blank=True)
    date_confirmation      = models.DateTimeField(null=True, blank=True)
    date_livraison_prevue  = models.DateField(null=True, blank=True)
    date_livraison_reelle  = models.DateTimeField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Commande'
        verbose_name_plural = 'Commandes'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.numero_commande} — {self.acheteur.user.get_full_name()} -> {self.producteur.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.numero_commande:
            from django.utils import timezone
            annee = timezone.now().year
            count = Commande.objects.filter(numero_commande__startswith=f'CMD-{annee}-').count()
            self.numero_commande = f'CMD-{annee}-{str(count + 1).zfill(5)}'
        self.total = self.sous_total + self.frais_livraison - self.remise
        super().save(*args, **kwargs)

    @property
    def est_annulable(self):
        return self.statut in [self.Statut.EN_ATTENTE, self.Statut.CONFIRMEE]

    @property
    def est_payee(self):
        return self.statut_paiement == self.StatutPaiement.PAYE

    @property
    def nb_articles(self):
        return self.details.count()
