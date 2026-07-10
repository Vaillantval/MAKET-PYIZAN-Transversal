import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

DUREE_VALIDITE_MINUTES = 5


def generer_code_6_chiffres() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def expiration_par_defaut():
    return timezone.now() + timedelta(minutes=DUREE_VALIDITE_MINUTES)


class WalletCodePaiement(models.Model):
    """
    Code à usage unique (6 chiffres, 5 minutes) que le client génère depuis
    son portefeuille pour CONSENTIR à un débit wallet au comptoir POS.
    L'opérateur ne peut débiter personne sans ce code — il remplace
    l'identification par téléphone/email pour tout paiement wallet.
    Consommé atomiquement (select_for_update) : un seul usage, même si
    deux caisses le soumettent en même temps.
    """

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='codes_paiement_wallet', verbose_name=_('Client'))
    code       = models.CharField(max_length=6, default=generer_code_6_chiffres, verbose_name=_('Code'))
    expire_le  = models.DateTimeField(default=expiration_par_defaut, verbose_name=_('Expire le'))
    utilise    = models.BooleanField(default=False, verbose_name=_('Utilisé'))
    pos_sale   = models.ForeignKey('pos.POSSale', on_delete=models.SET_NULL, null=True, blank=True, related_name='codes_paiement', verbose_name=_('Vente POS'), help_text=_('Renseigné à l\'utilisation du code.'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Code de paiement wallet')
        verbose_name_plural = _('Codes de paiement wallet')
        indexes             = [models.Index(fields=['code', 'utilise'])]

    def __str__(self):
        etat = 'utilisé' if self.utilise else ('expiré' if self.est_expire else 'actif')
        return f"{self.code} — {self.user.username} ({etat})"

    @property
    def est_expire(self) -> bool:
        return timezone.now() >= self.expire_le
