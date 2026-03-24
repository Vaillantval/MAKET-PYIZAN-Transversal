from django.db import models
from django.conf import settings


class Paiement(models.Model):
    class TypePaiement(models.TextChoices):
        MONCASH  = 'moncash',  'MonCash'
        NATCASH  = 'natcash',  'NatCash'
        VIREMENT = 'virement', 'Virement bancaire'
        CASH     = 'cash',     'Especes'
        VOUCHER  = 'voucher',  'e-Voucher'

    class Statut(models.TextChoices):
        INITIE     = 'initie',     'Initie'
        EN_ATTENTE = 'en_attente', 'En attente'
        SOUMIS     = 'soumis',     'Preuve soumise'
        VERIFIE    = 'verifie',    'Verifie'
        CONFIRME   = 'confirme',   'Confirme'
        ECHOUE     = 'echoue',     'Echoue'
        ANNULE     = 'annule',     'Annule'
        REMBOURSE  = 'rembourse',  'Rembourse'

    reference           = models.CharField(max_length=100, unique=True, blank=True)
    commande            = models.ForeignKey('orders.Commande', on_delete=models.PROTECT, related_name='paiements')
    effectue_par        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_effectues')
    verifie_par         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_verifies')
    type_paiement       = models.CharField(max_length=20, choices=TypePaiement.choices)
    statut              = models.CharField(max_length=20, choices=Statut.choices, default=Statut.INITIE)
    montant             = models.DecimalField(max_digits=12, decimal_places=2)
    montant_recu        = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    numero_expediteur   = models.CharField(max_length=20, blank=True)
    id_transaction      = models.CharField(max_length=100, blank=True)
    preuve_image        = models.ImageField(upload_to='paiements/preuves/', null=True, blank=True)
    notes               = models.TextField(blank=True)
    note_verification   = models.TextField(blank=True)
    date_verification   = models.DateTimeField(null=True, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.get_type_paiement_display()} — {self.montant} HTG — {self.get_statut_display()}"

    def save(self, *args, **kwargs):
        if not self.reference:
            import uuid
            from django.utils import timezone
            annee    = timezone.now().year
            uid      = str(uuid.uuid4()).upper()[:8]
            self.reference = f"PAY-{annee}-{uid}"
        super().save(*args, **kwargs)

    @property
    def est_confirme(self):
        return self.statut == self.Statut.CONFIRME

    @property
    def difference_montant(self):
        if self.montant_recu is None: return None
        return self.montant_recu - self.montant
