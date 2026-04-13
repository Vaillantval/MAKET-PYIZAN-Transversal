import logging

from django.db import transaction
from django.utils import timezone
from apps.orders.models import Commande, CommandeDetail, HistoriqueStatutCommande
from apps.stock.services.stock_service import StockService
from apps.stock.models import MouvementStock

logger = logging.getLogger(__name__)


class CommandeService:
    @staticmethod
    @transaction.atomic
    def creer_commande(acheteur, producteur, items, methode_paiement, mode_livraison, adresse_livraison='', notes=''):
        logger.info(
            "creer_commande: début — acheteur=%s producteur=%s nb_items=%d methode=%s mode=%s",
            acheteur.pk, producteur.pk, len(items), methode_paiement, mode_livraison,
        )
        try:
            commande = Commande.objects.create(
                acheteur=acheteur,
                producteur=producteur,
                methode_paiement=methode_paiement,
                mode_livraison=mode_livraison,
                adresse_livraison=adresse_livraison,
                notes_acheteur=notes,
            )
            logger.info("creer_commande: Commande créée — ref=%s", commande.numero_commande)
        except Exception:
            logger.exception(
                "creer_commande: échec création Commande — acheteur=%s producteur=%s",
                acheteur.pk, producteur.pk,
            )
            raise

        sous_total = 0
        for item in items:
            produit  = item['produit']
            quantite = item['quantite']
            lot      = item.get('lot')

            logger.debug(
                "creer_commande: vérification stock — produit=%s (pk=%s) stock_reel=%s "
                "stock_reserve=%s quantite_demandee=%s lot=%s",
                produit.nom, produit.pk, produit.stock_reel,
                produit.stock_reserve, quantite, lot,
            )

            if produit.stock_reel < quantite:
                logger.warning(
                    "creer_commande: stock insuffisant — produit=%s (pk=%s) disponible=%s demande=%s",
                    produit.nom, produit.pk, produit.stock_reel, quantite,
                )
                raise ValueError(
                    f"Stock insuffisant pour '{produit.nom}'. "
                    f"Disponible : {produit.stock_reel}, demande : {quantite}"
                )

            try:
                detail = CommandeDetail.objects.create(
                    commande=commande,
                    produit=produit,
                    lot=lot,
                    prix_unitaire=produit.prix_affiche,
                    quantite=quantite,
                    unite_vente=produit.unite_vente,
                )
                logger.debug(
                    "creer_commande: CommandeDetail créé — pk=%s produit=%s quantite=%s "
                    "prix_unitaire=%s sous_total=%s",
                    detail.pk, produit.nom, quantite, detail.prix_unitaire, detail.sous_total,
                )
            except Exception:
                logger.exception(
                    "creer_commande: échec création CommandeDetail — commande=%s "
                    "produit=%s (pk=%s) quantite=%s",
                    commande.numero_commande, produit.nom, produit.pk, quantite,
                )
                raise

            sous_total += detail.sous_total

            try:
                produit.stock_reserve += quantite
                produit.save(update_fields=['stock_reserve'])
                logger.debug(
                    "creer_commande: stock_reserve mis à jour — produit=%s (pk=%s) "
                    "nouveau_stock_reserve=%s",
                    produit.nom, produit.pk, produit.stock_reserve,
                )
            except Exception:
                logger.exception(
                    "creer_commande: échec mise à jour stock_reserve — produit=%s (pk=%s)",
                    produit.nom, produit.pk,
                )
                raise

        try:
            commande.sous_total = sous_total
            commande.save()
            logger.info(
                "creer_commande: succès — ref=%s sous_total=%s nb_details=%d",
                commande.numero_commande, sous_total, len(items),
            )
        except Exception:
            logger.exception(
                "creer_commande: échec sauvegarde sous_total — commande=%s sous_total=%s",
                commande.numero_commande, sous_total,
            )
            raise

        return commande

    @staticmethod
    @transaction.atomic
    def confirmer_commande(commande, effectue_par=None):
        if commande.statut != Commande.Statut.EN_ATTENTE:
            raise ValueError("Seules les commandes en attente peuvent etre confirmees.")
        statut_avant = commande.statut
        for detail in commande.details.select_related('produit', 'lot').all():
            lot = detail.lot or detail.produit.lots.filter(statut='disponible', quantite_actuelle__gte=detail.quantite).first()
            if not lot:
                raise ValueError(f"Aucun lot disponible pour '{detail.produit.nom}'")
            StockService.sortie_stock(lot=lot, quantite=detail.quantite, type_mouvement=MouvementStock.TypeMouvement.SORTIE_VENTE, commande=commande, effectue_par=effectue_par)
            # Sauvegarder le lot utilisé pour traçabilité (utile si annulation ultérieure)
            if not detail.lot:
                detail.lot = lot
                detail.save(update_fields=['lot'])
            detail.produit.stock_reserve = max(0, detail.produit.stock_reserve - detail.quantite)
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

        if statut_avant == Commande.Statut.EN_ATTENTE:
            # Stock jamais débité du lot — libérer uniquement la réserve
            for detail in commande.details.select_related('produit').all():
                detail.produit.stock_reserve = max(0, detail.produit.stock_reserve - detail.quantite)
                detail.produit.save(update_fields=['stock_reserve'])
        else:
            # Stock déjà débité du lot via confirmer_commande — restaurer chaque lot
            # On retrouve les mouvements SORTIE_VENTE liés à cette commande
            mouvements = MouvementStock.objects.filter(
                commande=commande,
                type_mouvement=MouvementStock.TypeMouvement.SORTIE_VENTE,
            ).select_related('lot')
            for mvt in mouvements:
                StockService.retour_stock(
                    lot=mvt.lot,
                    quantite=mvt.quantite,
                    commande=commande,
                    effectue_par=effectue_par,
                    motif=motif or f"Annulation commande {commande.numero_commande}",
                )

        commande.statut = Commande.Statut.ANNULEE
        commande.save()
        HistoriqueStatutCommande.objects.create(commande=commande, statut_avant=statut_avant, statut_apres=Commande.Statut.ANNULEE, effectue_par=effectue_par, commentaire=motif or "Commande annulee.")
        return commande
