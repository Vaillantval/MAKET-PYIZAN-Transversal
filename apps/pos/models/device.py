from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models.producteur import Departement


class POSDevice(models.Model):
    """
    Terminal de caisse physique (tablette/téléphone) rattaché à un opérateur.
    Le device_uid est vérifié à chaque requête (header X-POS-Device) —
    désactiver le terminal (is_active) le révoque immédiatement.
    """

    device_uid       = models.CharField(max_length=64, unique=True, verbose_name=_('Identifiant du terminal'), help_text=_('Identifiant matériel unique du terminal (généré côté application).'))
    nom              = models.CharField(max_length=100, verbose_name=_('Nom'))
    operateur        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pos_devices', verbose_name=_('Opérateur'))
    departement      = models.CharField(max_length=20, choices=Departement.choices, verbose_name=_('Département'))
    commune          = models.CharField(max_length=100, verbose_name=_('Commune'))
    section_communale = models.CharField(max_length=150, blank=True, verbose_name=_('Section communale'))
    adresse_detail   = models.CharField(max_length=255, blank=True, verbose_name=_('Précision du lieu'), help_text=_('Ex : Marché Croix-des-Bossales, stand 12'))
    is_active        = models.BooleanField(default=True, verbose_name=_('Actif'), help_text=_('Désactiver pour révoquer un terminal perdu ou volé.'))
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Terminal POS')
        verbose_name_plural = _('Terminaux POS')

    def __str__(self):
        return f"{self.nom} ({self.device_uid[:12]}…) — {self.commune}"
