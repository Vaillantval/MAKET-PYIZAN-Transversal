from django.db import transaction
from django.utils import timezone
from apps.payments.models import Paiement
from apps.orders.models import Commande


class PaiementService:
    @staticmethod
    @transaction.atomic
    def initier_paiement(commande, type_paiement, numero_expediteur='', notes=''):
        paiement = Paiement.objects.create(commande=commande, effectue_par=commande.acheteur.user, type_paiement=type_paiement, statut=Paiement.Statut.INITIE, montant=commande.total, numero_expediteur=numero_expediteur, notes=notes)
        commande.statut_paiement   = Commande.StatutPaiement.EN_ATTENTE
        commande.methode_paiement  = type_paiement
        commande.save(update_fields=['statut_paiement', 'methode_paiement'])
        return paiement

    @staticmethod
    @transaction.atomic
    def soumettre_preuve(paiement, preuve_image, id_transaction='', montant_recu=None):
        paiement.preuve_image   = preuve_image
        paiement.statut         = Paiement.Statut.SOUMIS
        paiement.id_transaction = id_transaction
        paiement.montant_recu   = montant_recu
        paiement.save()
        paiement.commande.statut_paiement = Commande.StatutPaiement.PREUVE_SOUMISE
        paiement.commande.preuve_paiement = preuve_image
        paiement.commande.save(update_fields=['statut_paiement', 'preuve_paiement'])
        return paiement

    @staticmethod
    @transaction.atomic
    def confirmer_paiement(paiement, verifie_par, note_verification=''):
        paiement.statut            = Paiement.Statut.CONFIRME
        paiement.verifie_par       = verifie_par
        paiement.date_verification = timezone.now()
        paiement.note_verification = note_verification
        paiement.save()
        commande = paiement.commande
        commande.statut_paiement    = Commande.StatutPaiement.PAYE
        commande.reference_paiement = paiement.reference
        commande.save(update_fields=['statut_paiement', 'reference_paiement'])
        return paiement

    @staticmethod
    @transaction.atomic
    def rejeter_paiement(paiement, verifie_par, motif=''):
        paiement.statut            = Paiement.Statut.ECHOUE
        paiement.verifie_par       = verifie_par
        paiement.date_verification = timezone.now()
        paiement.note_verification = motif
        paiement.save()
        paiement.commande.statut_paiement = Commande.StatutPaiement.NON_PAYE
        paiement.commande.save(update_fields=['statut_paiement'])
        return paiement


class VoucherService:
    @staticmethod
    def valider_voucher(code, acheteur, montant_commande):
        from apps.payments.models import Voucher
        try:
            voucher = Voucher.objects.get(code=code.upper())
        except Voucher.DoesNotExist:
            raise ValueError("Code voucher invalide.")
        if not voucher.est_valide:
            raise ValueError("Ce voucher est expire ou deja utilise.")
        if voucher.beneficiaire and voucher.beneficiaire != acheteur:
            raise ValueError("Ce voucher n'est pas assigne a votre compte.")
        remise = voucher.calculer_remise(montant_commande)
        if remise == 0:
            raise ValueError(f"Montant minimum requis : {voucher.montant_commande_min} HTG.")
        return voucher, remise

    @staticmethod
    @transaction.atomic
    def utiliser_voucher(voucher, commande):
        voucher.statut            = voucher.Statut.UTILISE
        voucher.date_utilisation  = timezone.now()
        voucher.save()
        programme = voucher.programme
        remise    = voucher.calculer_remise(commande.sous_total)
        programme.budget_utilise += remise
        programme.save(update_fields=['budget_utilise'])
