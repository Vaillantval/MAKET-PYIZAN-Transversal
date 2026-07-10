from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.pos.models.device import POSDevice


class POSSession(models.Model):
    """
    Session de caisse : ouverte avec un fonds initial, fermée avec un
    comptage. L'écart de caisse est calculé à la clôture :
    fonds_fermeture − (fonds_ouverture + total des ventes cash de la session).
    L'unicité de la session OUVERTE par opérateur est garantie par POSService.
    """

    class Statut(models.TextChoices):
        OUVERTE = 'ouverte', _('Ouverte')
        FERMEE  = 'fermee',  _('Fermée')

    device           = models.ForeignKey(POSDevice, on_delete=models.PROTECT, related_name='sessions', verbose_name=_('Terminal'))
    operateur        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pos_sessions', verbose_name=_('Opérateur'))
    fonds_ouverture  = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Fonds de caisse initial (HTG)'))
    fonds_fermeture  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_('Comptage à la clôture (HTG)'))
    ecart_caisse     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_('Écart de caisse (HTG)'), help_text=_('fonds_fermeture − (fonds_ouverture + ventes cash de la session).'))
    ouverte_le       = models.DateTimeField(auto_now_add=True, verbose_name=_('Ouverte le'))
    fermee_le        = models.DateTimeField(null=True, blank=True, verbose_name=_('Fermée le'))
    statut           = models.CharField(max_length=20, choices=Statut.choices, default=Statut.OUVERTE, verbose_name=_('Statut'))

    class Meta:
        ordering            = ['-ouverte_le']
        verbose_name        = _('Session de caisse')
        verbose_name_plural = _('Sessions de caisse')

    def __str__(self):
        return f"Session #{self.pk} — {self.operateur.username} ({self.get_statut_display()})"
