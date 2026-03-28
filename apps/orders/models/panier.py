from django.db import models
from django.conf import settings


class PanierItem(models.Model):
    """
    Article dans le panier persistant (lié à un utilisateur authentifié).
    Remplace le panier session pour les clients mobiles (Flutter/JWT).
    Le panier session reste utilisé pour les visiteurs anonymes du site web.
    """
    user    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='panier_items',
    )
    produit = models.ForeignKey(
        'catalog.Produit',
        on_delete=models.CASCADE,
        related_name='panier_items',
    )
    quantite   = models.DecimalField(max_digits=10, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together  = ('user', 'produit')
        verbose_name     = 'Article panier'
        verbose_name_plural = 'Articles panier'
        ordering         = ['created_at']

    def __str__(self):
        return f"{self.user} — {self.produit} × {self.quantite}"

    @property
    def sous_total(self):
        return self.quantite * self.produit.prix_unitaire
