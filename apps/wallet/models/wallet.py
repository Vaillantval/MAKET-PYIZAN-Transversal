from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Wallet(models.Model):
    """
    Solde prépayé d'un utilisateur (acheteur ou producteur), en HTG.
    Le solde n'est jamais modifié directement : toute opération passe
    par WalletService qui crée une WalletTransaction (ledger).
    """

    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    solde      = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Solde (HTG)'))
    is_active  = models.BooleanField(default=True, verbose_name=_('Actif'), help_text=_('Désactiver pour bloquer les paiements, recharges et retraits de cet utilisateur.'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Portefeuille')
        verbose_name_plural = _('Portefeuilles')

    def __str__(self):
        return f"Wallet de {self.user.username} — {self.solde} HTG"
