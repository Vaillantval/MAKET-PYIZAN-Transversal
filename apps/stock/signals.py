"""
Signal stock à la création d'un produit : le stock saisi est matérialisé
en « lot initial » automatique. Le POS et la traçabilité décrémentent par
lots — un produit actif sans lot générerait de faux conflits de stock à
chaque vente comptoir (l'admin peut oublier de créer le lot à la main).

Volet complémentaire volontairement différé (cf. README — proposition
stock/lots) : matérialiser aussi les hausses manuelles de stock_disponible
par des lots d'ajustement.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.catalog.models import Produit

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Produit)
def creer_lot_initial(sender, instance, created, **kwargs):
    # Uniquement à la création : Lot.save() resynchronise stock_disponible
    # en re-sauvegardant le produit (created=False) — pas de boucle.
    if not created or instance.stock_disponible <= 0:
        return

    from apps.stock.models import Lot

    if Lot.objects.filter(produit=instance).exists():
        return
    try:
        lot = Lot.objects.create(
            produit=instance,
            quantite_initiale=instance.stock_disponible,
            quantite_actuelle=instance.stock_disponible,
            cree_par=instance.producteur.user,
            notes="Lot initial créé automatiquement à l'enregistrement du produit.",
        )
        logger.info(
            "Lot initial %s créé automatiquement pour le produit %s (%s unités).",
            lot.numero_lot, instance.nom, lot.quantite_initiale,
        )
    except Exception as e:
        # Ne jamais faire échouer la création du produit pour un lot raté —
        # l'admin peut le créer à la main, le POS signalera le conflit.
        logger.error("Lot initial non créé pour le produit #%s : %s", instance.pk, e)
