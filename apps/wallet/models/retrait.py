from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.wallet.models.wallet import Wallet
from apps.wallet.models.transaction import WalletTransaction


class WalletRetrait(models.Model):
    """
    Demande de retrait du solde wallet (producteur principalement).
    Le solde est débité dès la demande (réservation) pour empêcher une
    double dépense. L'admin effectue le transfert MonCash/NatCash
    manuellement, joint la preuve et marque le retrait payé — ou le
    rejette, ce qui re-crédite le wallet.
    """

    class Canal(models.TextChoices):
        MONCASH = 'moncash', _('MonCash')
        NATCASH = 'natcash', _('NatCash')

    class Statut(models.TextChoices):
        DEMANDE = 'demande', _('Demandé')
        PAYE    = 'paye',    _('Payé')
        REJETE  = 'rejete',  _('Rejeté')

    wallet              = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='retraits')
    montant             = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Montant (HTG)'))
    canal               = models.CharField(max_length=10, choices=Canal.choices)
    numero_telephone    = models.CharField(max_length=20, verbose_name=_('Numéro MonCash/NatCash'), help_text=_('Numéro qui recevra le transfert.'))
    statut              = models.CharField(max_length=10, choices=Statut.choices, default=Statut.DEMANDE)
    preuve_transfert    = models.ImageField(upload_to='wallet/retraits/', null=True, blank=True, help_text=_('Preuve du transfert effectué par l\'admin (capture MonCash/NatCash).'))
    note_admin          = models.TextField(blank=True, verbose_name=_('Note admin'), help_text=_('Motif de rejet ou remarque interne.'))
    traite_par          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='retraits_traites')
    date_traitement     = models.DateTimeField(null=True, blank=True)
    transaction         = models.OneToOneField(WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='retrait', help_text=_('Transaction de débit créée à la demande.'))
    transaction_reprise = models.OneToOneField(WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='retrait_rejete', help_text=_('Transaction de re-crédit créée si le retrait est rejeté.'))
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Retrait wallet')
        verbose_name_plural = _('Retraits wallet')

    def __str__(self):
        return f"Retrait #{self.pk} — {self.montant} HTG ({self.get_statut_display()})"
