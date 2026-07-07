from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.wallet.models.wallet import Wallet


class WalletTransaction(models.Model):
    """
    Ligne de ledger immuable : chaque mouvement du solde est enregistré ici
    avec le solde résultant. Ne jamais modifier ni supprimer une ligne —
    une erreur se corrige par une transaction d'ajustement inverse.
    """

    class Type(models.TextChoices):
        RECHARGE                 = 'recharge',                 _('Recharge')
        PAIEMENT                 = 'paiement',                 _('Paiement commande')
        REMBOURSEMENT            = 'remboursement',            _('Remboursement')
        LIBERATION_RESERVE       = 'liberation_reserve',       _('Libération solde réservé')
        VENTE                    = 'vente',                    _('Vente créditée (producteur)')
        REPRISE_VENTE            = 'reprise_vente',            _('Reprise vente (commande annulée)')
        RETRAIT                  = 'retrait',                  _('Retrait')
        REPRISE_RETRAIT          = 'reprise_retrait',          _('Retrait rejeté (re-crédit)')
        CASHBACK                 = 'cashback',                 _('Cashback fidélité')
        REPRISE_CASHBACK         = 'reprise_cashback',         _('Reprise cashback')
        BONUS_PARRAINAGE         = 'bonus_parrainage',         _('Bonus parrainage')
        REPRISE_BONUS_PARRAINAGE = 'reprise_bonus_parrainage', _('Reprise bonus parrainage')
        BON_CADEAU_ACHAT         = 'bon_cadeau_achat',         _('Achat bon cadeau')
        BON_CADEAU_ENCAISSE      = 'bon_cadeau_encaisse',      _('Bon cadeau encaissé')
        AJUSTEMENT               = 'ajustement',               _('Ajustement manuel')

    wallet      = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type        = models.CharField(max_length=30, choices=Type.choices)
    montant     = models.DecimalField(max_digits=12, decimal_places=2, help_text=_('Montant signé : positif = crédit, négatif = débit.'))
    solde_apres = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Solde après'))
    commande    = models.ForeignKey('orders.Commande', on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')
    description = models.CharField(max_length=255, blank=True, default='')
    reference   = models.CharField(max_length=128, blank=True, default='', help_text=_('Référence externe (transaction Plopplop, référence Paiement...).'))
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Transaction wallet')
        verbose_name_plural = _('Transactions wallet')

    def __str__(self):
        return f"{self.get_type_display()} {self.montant} — {self.wallet.user.username}"
