from django.db import transaction
from apps.stock.models import Lot, MouvementStock, AlerteStock


class StockService:
    @staticmethod
    @transaction.atomic
    def entree_stock(lot, quantite, effectue_par=None, motif='', reference=''):
        stock_avant = lot.quantite_actuelle
        lot.quantite_initiale += quantite
        lot.quantite_actuelle += quantite
        lot.statut = Lot.Statut.DISPONIBLE
        lot.save()
        MouvementStock.objects.create(lot=lot, produit=lot.produit, type_mouvement=MouvementStock.TypeMouvement.ENTREE, quantite=quantite, stock_avant=stock_avant, stock_apres=lot.quantite_actuelle, motif=motif, reference=reference, effectue_par=effectue_par)
        AlerteStock.verifier_et_creer(lot.produit)
        return lot

    @staticmethod
    @transaction.atomic
    def sortie_stock(lot, quantite, type_mouvement, commande=None, collecte=None, effectue_par=None, motif=''):
        if lot.quantite_actuelle < quantite:
            raise ValueError(f"Stock insuffisant. Disponible : {lot.quantite_actuelle}, demande : {quantite}")
        stock_avant = lot.quantite_actuelle
        lot.quantite_actuelle -= quantite
        if type_mouvement == MouvementStock.TypeMouvement.SORTIE_VENTE:
            lot.quantite_vendue += quantite
        lot.save()
        MouvementStock.objects.create(lot=lot, produit=lot.produit, type_mouvement=type_mouvement, quantite=quantite, stock_avant=stock_avant, stock_apres=lot.quantite_actuelle, commande=commande, collecte=collecte, motif=motif, effectue_par=effectue_par)
        AlerteStock.verifier_et_creer(lot.produit)
        return lot

    @staticmethod
    @transaction.atomic
    def ajustement_stock(lot, nouvelle_quantite, motif, effectue_par=None):
        stock_avant = lot.quantite_actuelle
        difference  = nouvelle_quantite - stock_avant
        type_mvt    = MouvementStock.TypeMouvement.AJUSTEMENT_POS if difference >= 0 else MouvementStock.TypeMouvement.AJUSTEMENT_NEG
        lot.quantite_actuelle = nouvelle_quantite
        lot.save()
        MouvementStock.objects.create(lot=lot, produit=lot.produit, type_mouvement=type_mvt, quantite=abs(difference), stock_avant=stock_avant, stock_apres=nouvelle_quantite, motif=motif, effectue_par=effectue_par)
        AlerteStock.verifier_et_creer(lot.produit)
        return lot
