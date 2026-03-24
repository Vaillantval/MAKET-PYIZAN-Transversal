from django.db import transaction
from django.utils import timezone
from apps.orders.models import Commande, CommandeDetail, HistoriqueStatutCommande
from apps.stock.services.stock_service import StockService
from apps.stock.models import MouvementStock


class CommandeService:
    @staticmethod
    @transaction.atomic
    def creer_commande(acheteur, producteur, items, methode_paiement, mode_livraison, adresse_livraison='', notes=''):
        commande   = Commande.objects.create(acheteur=acheteur, producteur=producteur, methode_paiement=methode_paiement, mode_livraison=mode_livraison, adresse_livraison=adresse_livraison, notes_acheteur=notes)
        sous_total = 0
        for item in items:
            produit  = item['produit']
            quantite = item['quantite']
            lot      = item.get('lot')
            if produit.stock_reel < quantite:
                raise ValueError(f"Stock insuffisant pour '{produit.nom}'. Disponible : {produit.stock_reel}, demande : {quantite}")
            detail = CommandeDetail.objects.create(commande=commande, produit=produit, lot=lot, prix_unitaire=produit.prix_affiche, quantite=quantite, unite_vente=produit.unite_vente)
            sous_total += detail.sous_total
            produit.stock_reserve += quantite
            produit.save(update_fields=['stock_reserve'])
        commande.sous_total = sous_total
        commande.save()
        return commande

    @staticmethod
    @transaction.atomic
    def confirmer_commande(commande, effectue_par=None):
        if commande.statut != Commande.Statut.EN_ATTENTE:
            raise ValueError("Seules les commandes en attente peuvent etre confirmees.")
        statut_avant = commande.statut
        for detail in commande.details.all():
            lot = detail.lot or detail.produit.lots.filter(statut='disponible', quantite_actuelle__gte=detail.quantite).first()
            if not lot:
                raise ValueError(f"Aucun lot disponible pour '{detail.produit.nom}'")
            StockService.sortie_stock(lot=lot, quantite=detail.quantite, type_mouvement=MouvementStock.TypeMouvement.SORTIE_VENTE, commande=commande, effectue_par=effectue_par)
            detail.produit.stock_reserve -= detail.quantite
            detail.produit.save(update_fields=['stock_reserve'])
        commande.statut            = Commande.Statut.CONFIRMEE
        commande.date_confirmation = timezone.now()
        commande.save()
        HistoriqueStatutCommande.objects.create(commande=commande, statut_avant=statut_avant, statut_apres=commande.statut, effectue_par=effectue_par, commentaire="Commande confirmee et stock debite.")
        return commande

    @staticmethod
    @transaction.atomic
    def changer_statut(commande, nouveau_statut, effectue_par=None, commentaire=''):
        statut_avant    = commande.statut
        commande.statut = nouveau_statut
        if nouveau_statut == Commande.Statut.LIVREE:
            commande.date_livraison_reelle = timezone.now()
        commande.save()
        HistoriqueStatutCommande.objects.create(commande=commande, statut_avant=statut_avant, statut_apres=nouveau_statut, effectue_par=effectue_par, commentaire=commentaire)
        return commande

    @staticmethod
    @transaction.atomic
    def annuler_commande(commande, effectue_par=None, motif=''):
        if not commande.est_annulable:
            raise ValueError("Cette commande ne peut plus etre annulee.")
        statut_avant = commande.statut
        for detail in commande.details.all():
            detail.produit.stock_reserve = max(0, detail.produit.stock_reserve - detail.quantite)
            detail.produit.save(update_fields=['stock_reserve'])
        commande.statut = Commande.Statut.ANNULEE
        commande.save()
        HistoriqueStatutCommande.objects.create(commande=commande, statut_avant=statut_avant, statut_apres=Commande.Statut.ANNULEE, effectue_par=effectue_par, commentaire=motif or "Commande annulee.")
        return commande
