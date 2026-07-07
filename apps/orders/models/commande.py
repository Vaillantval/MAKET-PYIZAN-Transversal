from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Commande(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE     = 'en_attente',     _('En attente de confirmation')
        CONFIRMEE      = 'confirmee',      _('Confirmee')
        EN_PREPARATION = 'en_preparation', _('En preparation')
        PRETE          = 'prete',          _('Prete pour collecte')
        EN_COLLECTE    = 'en_collecte',    _('En cours de collecte')
        LIVREE         = 'livree',         _('Livree')
        ANNULEE        = 'annulee',        _('Annulee')
        LITIGE         = 'litige',         _('En litige')

    class ModeLivraison(models.TextChoices):
        LIVRAISON_DOMICILE = 'domicile', _('Livraison a domicile')
        RETRAIT_PRODUCTEUR = 'retrait',  _('Retrait chez le producteur')
        POINT_COLLECTE     = 'collecte', _('Point de collecte')

    class MethodePaiement(models.TextChoices):
        MONCASH    = 'moncash',    _('MonCash')
        NATCASH    = 'natcash',    _('NatCash')
        VIREMENT   = 'virement',   _('Virement bancaire')
        CASH       = 'cash',       _('Especes')
        VOUCHER    = 'voucher',    _('e-Voucher')
        HORS_LIGNE = 'hors_ligne', _('Paiement hors ligne')
        WALLET     = 'wallet',     _('Portefeuille')

    class StatutPaiement(models.TextChoices):
        NON_PAYE       = 'non_paye',       _('Non paye')
        EN_ATTENTE     = 'en_attente',     _('En attente de verification')
        PREUVE_SOUMISE = 'preuve_soumise', _('Preuve soumise')
        VERIFIE        = 'verifie',        _('Verifie')
        PAYE           = 'paye',           _('Paye')
        REMBOURSE      = 'rembourse',      _('Rembourse')

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
    montant_wallet_utilise = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text=_('Solde wallet réservé sur cette commande (paiement partiel) — le complément part vers MonCash/NatCash.'))
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
        verbose_name        = _('Commande')
        verbose_name_plural = _('Commandes')
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.numero_commande} — {self.acheteur.user.get_full_name()} -> {self.producteur.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.numero_commande:
            import uuid
            from django.utils import timezone
            annee = timezone.now().year
            # 8 hex chars = 16^8 ≈ 4 milliards de combinaisons → sans collision
            # Format : CMD-2026-A3F7B2C1 (18 chars, bien en-dessous de max_length=30)
            self.numero_commande = f'CMD-{annee}-{uuid.uuid4().hex[:8].upper()}'
        from decimal import Decimal
        self.total = max(Decimal('0'), self.sous_total + self.frais_livraison - self.remise)
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
