"""
Signaux stock du point de vente :

- création d'un POSItem (vente confirmée) : décrément du lot précisé, ou du
  lot DISPONIBLE le plus ancien du produit (FIFO). Jamais de quantité
  négative — si le stock serveur ne couvre pas la vente physique, la vente
  est marquée stock_conflict=True (arbitrage superadmin) et le lot est
  ramené à 0.
- POSSale confirmée → annulée : re-crédit des lots et remboursement de la
  part wallet du client (idempotent).

Les quantités sont manipulées sous select_for_update pour éviter les races.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.pos.models import POSItem, POSSale

logger = logging.getLogger(__name__)


def _decrementer_stock(item):
    from apps.stock.models import Lot

    restant = item.quantite
    conflit = False

    with transaction.atomic():
        if item.lot_id:
            lots = list(Lot.objects.select_for_update().filter(pk=item.lot_id))
        else:
            lots = list(
                Lot.objects.select_for_update()
                .filter(produit=item.produit, statut=Lot.Statut.DISPONIBLE)
                .order_by('created_at')
            )

        premier_lot = None
        for lot in lots:
            if restant <= 0:
                break
            pris = min(lot.quantite_actuelle, restant)
            if pris <= 0:
                continue
            lot.quantite_actuelle -= pris
            lot.quantite_vendue += pris
            lot.save()  # statut EPUISE à 0 + resynchronisation du stock produit
            restant -= pris
            if premier_lot is None:
                premier_lot = lot

        # Retenir le lot réellement décrémenté (FIFO) pour le re-crédit
        # en cas d'annulation. Update queryset : ne redéclenche pas le signal.
        if premier_lot is not None and not item.lot_id:
            POSItem.objects.filter(pk=item.pk).update(lot=premier_lot)
            item.lot_id = premier_lot.pk

        if restant > 0:
            conflit = True

    if conflit:
        POSSale.objects.filter(pk=item.vente_id).update(stock_conflict=True)
        item.vente.stock_conflict = True
        logger.warning(
            "POS — stock insuffisant pour %s × %s (vente %s) : conflit à arbitrer.",
            item.produit.nom, item.quantite, item.vente.numero_vente,
        )


def _recrediter_stock(vente):
    from apps.stock.models import Lot

    for item in vente.items.all():
        if not item.lot_id:
            continue
        with transaction.atomic():
            lot = Lot.objects.select_for_update().get(pk=item.lot_id)
            # Ne jamais re-créditer plus que ce qui a été réellement vendu
            # sur ce lot (une vente en conflit de stock a décrémenté moins
            # que la quantité de la ligne).
            repris = min(item.quantite, lot.quantite_vendue)
            if repris <= 0:
                continue
            lot.quantite_actuelle += repris
            lot.quantite_vendue -= repris
            if lot.statut == Lot.Statut.EPUISE and lot.quantite_actuelle > 0:
                lot.statut = Lot.Statut.DISPONIBLE
            lot.save()


def _rembourser_wallet(vente):
    """Re-crédite la part wallet d'une vente annulée. Idempotent."""
    from apps.wallet.models import WalletTransaction
    from apps.wallet.services import WalletService

    if (vente.montant_wallet or 0) <= 0 or vente.client_id is None:
        return
    if WalletTransaction.objects.filter(
        pos_sale=vente, type=WalletTransaction.Type.REMBOURSEMENT,
    ).exists():
        return
    WalletService.crediter(
        WalletService.get_wallet(vente.client),
        vente.montant_wallet,
        type_tx=WalletTransaction.Type.REMBOURSEMENT,
        pos_sale=vente,
        description=f"Remboursement — vente POS {vente.numero_vente} annulée",
        reference=f"pos-remb-{vente.pk}",
    )


@receiver(post_save, sender=POSItem)
def pos_item_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.vente.statut != POSSale.Statut.CONFIRMEE:
        return
    try:
        _decrementer_stock(instance)
    except Exception as e:
        # La vente physique a eu lieu : un problème de stock ne doit pas
        # l'annuler — on la marque en conflit et l'admin arbitre.
        logger.error("POS — décrément stock impossible (item #%s) : %s", instance.pk, e)
        POSSale.objects.filter(pk=instance.vente_id).update(stock_conflict=True)


@receiver(pre_save, sender=POSSale)
def pos_sale_capturer_ancien_statut(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._pos_ancien_statut = sender.objects.get(pk=instance.pk).statut
        except sender.DoesNotExist:
            instance._pos_ancien_statut = None
    else:
        instance._pos_ancien_statut = None


@receiver(post_save, sender=POSSale)
def pos_sale_post_save(sender, instance, created, **kwargs):
    if created:
        return
    ancien = getattr(instance, '_pos_ancien_statut', None)
    if ancien == POSSale.Statut.ANNULEE or instance.statut != POSSale.Statut.ANNULEE:
        return
    try:
        _recrediter_stock(instance)
        _rembourser_wallet(instance)
    except Exception as e:
        logger.error("POS — annulation vente #%s : %s", instance.pk, e)
