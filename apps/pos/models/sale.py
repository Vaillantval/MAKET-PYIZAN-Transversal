import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.pos.models.session import POSSession


class POSSale(models.Model):
    """
    Vente au comptoir. L'idempotency_key est TOUJOURS générée côté client :
    elle rend la synchronisation offline rejouable sans doublon.
    vendue_le est l'horodatage réel de la vente (fourni par le client),
    synced_le celui de son arrivée sur le serveur.
    """

    class MethodePaiement(models.TextChoices):
        # Mêmes valeurs que Commande.MethodePaiement, restreintes au comptoir
        # (pas de virement ni de paiement hors ligne en caisse).
        MONCASH = 'moncash', _('MonCash')
        NATCASH = 'natcash', _('NatCash')
        CASH    = 'cash',    _('Especes')
        VOUCHER = 'voucher', _('e-Voucher')
        WALLET  = 'wallet',  _('Portefeuille')

    class Statut(models.TextChoices):
        CONFIRMEE = 'confirmee', _('Confirmée')
        ANNULEE   = 'annulee',   _('Annulée')

    idempotency_key  = models.UUIDField(unique=True, default=uuid.uuid4, verbose_name=_('Clé d\'idempotence'), help_text=_('Générée côté client — une resoumission renvoie la vente existante.'))
    session          = models.ForeignKey(POSSession, on_delete=models.PROTECT, related_name='ventes', verbose_name=_('Session'))
    operateur        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventes_pos', verbose_name=_('Opérateur'))
    client           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='achats_pos', verbose_name=_('Client'), help_text=_('Acheteur identifié par téléphone/email — vide : vente anonyme.'))
    numero_vente     = models.CharField(max_length=30, unique=True, blank=True, verbose_name=_('Numéro de vente'))
    montant_total    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Montant total (HTG)'))
    methode_paiement = models.CharField(max_length=20, choices=MethodePaiement.choices, verbose_name=_('Méthode de paiement'))
    montant_wallet   = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_('Part payée par wallet (HTG)'), help_text=_('Paiement hybride wallet + cash.'))
    statut           = models.CharField(max_length=20, choices=Statut.choices, default=Statut.CONFIRMEE, verbose_name=_('Statut'))
    stock_conflict   = models.BooleanField(default=False, verbose_name=_('Conflit de stock'), help_text=_('Vente synchronisée alors que le stock serveur était insuffisant — à arbitrer par le superadmin.'))
    vendue_le        = models.DateTimeField(verbose_name=_('Vendue le'), help_text=_('Horodatage réel de la vente, fourni par le terminal (ventes offline synchronisées plus tard).'))
    synced_le        = models.DateTimeField(auto_now_add=True, verbose_name=_('Synchronisée le'))

    class Meta:
        ordering            = ['-vendue_le']
        verbose_name        = _('Vente POS')
        verbose_name_plural = _('Ventes POS')

    def __str__(self):
        return f"{self.numero_vente} — {self.montant_total} HTG ({self.get_methode_paiement_display()})"

    def save(self, *args, **kwargs):
        if not self.numero_vente:
            from django.utils import timezone
            annee = timezone.now().year
            count = POSSale.objects.filter(numero_vente__startswith=f'POS-{annee}-').count()
            self.numero_vente = f'POS-{annee}-{str(count + 1).zfill(5)}'
        super().save(*args, **kwargs)


class POSItem(models.Model):
    """Ligne d'une vente POS. Le prix appliqué (détail ou gros) est figé ici."""

    vente         = models.ForeignKey(POSSale, on_delete=models.CASCADE, related_name='items', verbose_name=_('Vente'))
    produit       = models.ForeignKey('catalog.Produit', on_delete=models.PROTECT, related_name='ventes_pos', verbose_name=_('Produit'))
    lot           = models.ForeignKey('stock.Lot', on_delete=models.PROTECT, null=True, blank=True, related_name='ventes_pos', verbose_name=_('Lot'), help_text=_('Vide : le lot disponible le plus ancien est décrémenté (FIFO).'))
    quantite      = models.PositiveIntegerField(verbose_name=_('Quantité'))
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Prix unitaire appliqué (HTG)'))
    sous_total    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Sous-total (HTG)'))

    class Meta:
        ordering            = ['pk']
        verbose_name        = _('Ligne de vente POS')
        verbose_name_plural = _('Lignes de vente POS')

    def __str__(self):
        return f"{self.produit.nom} × {self.quantite} — {self.sous_total} HTG"
