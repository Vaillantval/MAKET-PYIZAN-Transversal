from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.wallet.utils import generer_code_bon_cadeau


class BonCadeau(models.Model):
    """
    Bon cadeau acheté (solde wallet ou Plopplop), échangeable contre du
    crédit wallet. Le code n'est actif qu'une fois le paiement confirmé.
    """

    class Statut(models.TextChoices):
        ATTENTE_PAIEMENT = 'attente_paiement', _('En attente de paiement')
        ACTIF            = 'actif',            _('Actif')
        UTILISE          = 'utilise',          _('Utilisé')
        EXPIRE           = 'expire',           _('Expiré')
        ANNULE           = 'annule',           _('Annulé')

    code                 = models.CharField(max_length=20, unique=True, default=generer_code_bon_cadeau)
    montant              = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Montant (HTG)'))
    statut               = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ATTENTE_PAIEMENT)
    achete_par           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='bons_cadeaux_achetes')
    email_destinataire   = models.EmailField(blank=True, default='', help_text=_('Email du destinataire — le code lui est envoyé à l\'activation. Vide : le code est envoyé à l\'acheteur.'))
    message_destinataire = models.CharField(max_length=255, blank=True, default='')
    encaisse_par         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bons_cadeaux_encaisses')
    date_encaissement    = models.DateTimeField(null=True, blank=True)
    date_expiration      = models.DateTimeField(null=True, blank=True)
    reference_plopplop   = models.CharField(max_length=64, null=True, blank=True, unique=True, help_text=_('Référence envoyée à Plopplop (format GFT{id}-{uuid8}).'))
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = _('Bon cadeau')
        verbose_name_plural = _('Bons cadeaux')

    def __str__(self):
        return f"{self.code} — {self.montant} HTG ({self.get_statut_display()})"

    @property
    def est_expire(self) -> bool:
        return bool(self.date_expiration and timezone.now() > self.date_expiration)
