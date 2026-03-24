from django.db import models
from django.conf import settings


class MouvementStock(models.Model):
    class TypeMouvement(models.TextChoices):
        ENTREE          = 'entree',          'Entree — Nouvelle recolte'
        SORTIE_VENTE    = 'sortie_vente',    'Sortie — Vente'
        SORTIE_COLLECTE = 'sortie_collecte', 'Sortie — Collecte'
        AJUSTEMENT_POS  = 'ajust_pos',       'Ajustement positif'
        AJUSTEMENT_NEG  = 'ajust_neg',       'Ajustement negatif'
        PERTE           = 'perte',           'Perte / Deterioration'
        RETOUR          = 'retour',          'Retour client'
        TRANSFERT       = 'transfert',       'Transfert de lot'

    lot            = models.ForeignKey('stock.Lot', on_delete=models.CASCADE, related_name='mouvements')
    produit        = models.ForeignKey('catalog.Produit', on_delete=models.CASCADE, related_name='mouvements_stock')
    commande       = models.ForeignKey('orders.Commande', on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_stock')
    collecte       = models.ForeignKey('collectes.Collecte', on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_stock')
    type_mouvement = models.CharField(max_length=20, choices=TypeMouvement.choices)
    quantite       = models.PositiveIntegerField()
    stock_avant    = models.PositiveIntegerField()
    stock_apres    = models.PositiveIntegerField()
    motif          = models.TextField(blank=True)
    reference      = models.CharField(max_length=100, blank=True)
    effectue_par   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='mouvements_effectues')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mouvement de stock'
        verbose_name_plural = 'Mouvements de stock'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.get_type_mouvement_display()} | {self.produit.nom} | {self.quantite} unites | {self.created_at.strftime('%d/%m/%Y')}"
