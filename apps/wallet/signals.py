"""
Signaux wallet sur le cycle de vie des commandes :

- statut → annulée : remboursement automatique vers le wallet de l'acheteur
  si la commande était payée, sinon libération du solde réservé (paiement
  partiel). Idempotent — le service vérifie l'existence des transactions.

Branchés dans les phases suivantes :
- crédit du producteur à la livraison d'une commande payée (phase 4) ;
- cashback fidélité et bonus parrainage à la confirmation du paiement (phase 5).
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.orders.models import Commande

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Commande)
def wallet_capturer_ancien_etat(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancienne = sender.objects.get(pk=instance.pk)
            instance._wallet_ancien_statut = ancienne.statut
            instance._wallet_ancien_statut_paiement = ancienne.statut_paiement
        except sender.DoesNotExist:
            instance._wallet_ancien_statut = None
            instance._wallet_ancien_statut_paiement = None
    else:
        instance._wallet_ancien_statut = None
        instance._wallet_ancien_statut_paiement = None


@receiver(post_save, sender=Commande)
def wallet_commande_post_save(sender, instance, created, **kwargs):
    from apps.wallet.services import WalletService

    if created:
        return

    try:
        ancien_statut = getattr(instance, '_wallet_ancien_statut', None)
        ancien_statut_paiement = getattr(instance, '_wallet_ancien_statut_paiement', None)

        # ── Annulation : rembourser l'acheteur + reprendre la vente ─────────
        if (
            ancien_statut is not None
            and ancien_statut != Commande.Statut.ANNULEE
            and instance.statut == Commande.Statut.ANNULEE
        ):
            if instance.est_payee:
                WalletService.rembourser_commande(
                    instance,
                    description=(
                        f"Remboursement — commande {instance.numero_commande} annulée"
                    ),
                )
            elif (instance.montant_wallet_utilise or 0) > 0:
                WalletService.liberer_paiement_partiel(
                    instance,
                    description=f"Annulation — commande {instance.numero_commande}",
                )
            # Si le producteur avait déjà été crédité (annulation après
            # livraison), reprendre le crédit de vente.
            WalletService.reprendre_vente_producteur(instance)
            return

        # ── Livraison d'une commande payée : créditer le producteur ─────────
        vient_d_etre_livree = (
            ancien_statut is not None
            and ancien_statut != Commande.Statut.LIVREE
            and instance.statut == Commande.Statut.LIVREE
        )
        vient_d_etre_payee = (
            ancien_statut_paiement is not None
            and ancien_statut_paiement != Commande.StatutPaiement.PAYE
            and instance.statut_paiement == Commande.StatutPaiement.PAYE
        )
        if vient_d_etre_livree or (
            vient_d_etre_payee and instance.statut == Commande.Statut.LIVREE
        ):
            WalletService.crediter_vente_producteur(instance)
    except Exception as e:
        logger.error("Erreur signal wallet (commande #%s) : %s", instance.pk, e)
