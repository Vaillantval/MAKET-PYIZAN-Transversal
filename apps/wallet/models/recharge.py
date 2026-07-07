from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.wallet.models.wallet import Wallet
from apps.wallet.models.transaction import WalletTransaction


class WalletRecharge(models.Model):
    """
    Intention de recharge en attente de confirmation. Le wallet n'est crédité
    (WalletTransaction créée) que lorsque le paiement est vérifié :
    - moncash/natcash : confirmation Plopplop (verifier_paiement) ;
    - hors_ligne : preuve de dépôt validée manuellement par l'admin.
    """

    class Methode(models.TextChoices):
        MONCASH    = 'moncash',    _('MonCash (Plopplop)')
        NATCASH    = 'natcash',    _('NatCash (Plopplop)')
        HORS_LIGNE = 'hors_ligne', _('Dépôt hors ligne')

    class Statut(models.TextChoices):
        EN_ATTENTE     = 'en_attente',     _('En attente')
        PREUVE_SOUMISE = 'preuve_soumise', _('Preuve soumise')
        CREDITEE       = 'creditee',       _('Créditée')
        REJETEE        = 'rejetee',        _('Rejetée')
        ECHOUEE        = 'echouee',        _('Échouée')

    wallet             = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='recharges')
    montant            = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Montant (HTG)'))
    methode            = models.CharField(max_length=12, choices=Methode.choices)
    statut             = models.CharField(max_length=16, choices=Statut.choices, default=Statut.EN_ATTENTE)
    reference_plopplop = models.CharField(max_length=64, null=True, blank=True, unique=True, help_text=_('Référence envoyée à Plopplop (format WAL{id}-{uuid8}).'))
    preuve_image       = models.ImageField(upload_to='wallet/recharges/', null=True, blank=True, help_text=_('Preuve de dépôt pour les recharges hors ligne (JPG/PNG, max 5 MB).'))
    transaction        = models.OneToOneField(WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='recharge', help_text=_('Transaction de crédit créée à la confirmation.'))
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Recharge wallet')
        verbose_name_plural = _('Recharges wallet')

    def __str__(self):
        return f"Recharge #{self.pk} — {self.montant} HTG ({self.get_statut_display()})"
