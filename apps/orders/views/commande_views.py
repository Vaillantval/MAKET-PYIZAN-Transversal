import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

logger = logging.getLogger(__name__)

from apps.accounts.models import Adresse
from apps.orders.models import Panier, Commande
from apps.orders.serializers import PasserCommandeSerializer
from apps.orders.services.commande_service import CommandeService
from apps.payments.models import Paiement
from apps.payments.services.paiement_service import PaiementService, VoucherService


# ── POST /api/orders/commander/ ─────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def commander(request):
    """
    Passer commande depuis le panier.
    Crée une commande par producteur présent dans le panier.
    """
    # Vérifier le rôle acheteur
    if not hasattr(request.user, 'profil_acheteur'):
        return Response(
            {'success': False, 'error': "Seuls les acheteurs peuvent passer commande."},
            status=status.HTTP_403_FORBIDDEN,
        )

    acheteur = request.user.profil_acheteur

    # Valider les données
    serializer = PasserCommandeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = serializer.validated_data

    # Récupérer le panier
    try:
        panier = Panier.objects.prefetch_related(
            'items__produit__producteur__user'
        ).get(user=request.user)
    except Panier.DoesNotExist:
        return Response(
            {'success': False, 'error': "Votre panier est vide."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    items = list(panier.items.all())
    if not items:
        return Response(
            {'success': False, 'error': "Votre panier est vide."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Résoudre l'adresse de livraison
    adresse_texte = ''
    ville         = ''
    departement   = ''

    addr_id = data.get('adresse_livraison_id')
    if addr_id:
        try:
            adresse       = Adresse.objects.get(pk=addr_id, user=request.user)
            adresse_texte = adresse.rue
            ville         = adresse.commune
            departement   = adresse.departement
        except Adresse.DoesNotExist:
            return Response(
                {'success': False, 'error': "Adresse introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        adresse_texte = data.get('adresse_livraison_text', '')
        ville         = data.get('ville_livraison', '')
        departement   = data.get('departement_livraison', '')

    # Regrouper les items par producteur
    items_par_producteur = {}
    for item in items:
        pid = item.produit.producteur.pk
        if pid not in items_par_producteur:
            items_par_producteur[pid] = {
                'producteur': item.produit.producteur,
                'items':      [],
            }
        items_par_producteur[pid]['items'].append({
            'produit':  item.produit,
            'quantite': item.quantite,
        })

    commandes_creees = []
    methode_paiement = data['methode_paiement']
    mode_livraison   = data['mode_livraison']
    notes            = data.get('notes', '')

    # ── Voucher ─────────────────────────────────────────────────────
    voucher_obj    = None
    remise_totale  = Decimal('0')
    code_voucher   = data.get('code_voucher', '').strip()

    if code_voucher:
        # Calculer le sous-total du panier pour valider le voucher
        panier_sous_total = sum(
            item.produit.prix_affiche * item.quantite
            for item in items
        )
        try:
            voucher_obj, remise_totale = VoucherService.valider_voucher(
                code=code_voucher,
                acheteur=acheteur,
                montant_commande=panier_sous_total,
            )
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    # ────────────────────────────────────────────────────────────────

    METHODE_MAP = {
        'cash':       Commande.MethodePaiement.CASH,
        'moncash':    Commande.MethodePaiement.MONCASH,
        'natcash':    Commande.MethodePaiement.NATCASH,
        'hors_ligne': Commande.MethodePaiement.VIREMENT,
    }
    MODE_MAP = {
        'domicile': Commande.ModeLivraison.LIVRAISON_DOMICILE,
        'collecte': Commande.ModeLivraison.POINT_COLLECTE,
        'retrait':  Commande.ModeLivraison.RETRAIT_PRODUCTEUR,
    }

    methode_django = METHODE_MAP.get(methode_paiement, Commande.MethodePaiement.CASH)
    mode_django    = MODE_MAP.get(mode_livraison, Commande.ModeLivraison.LIVRAISON_DOMICILE)

    # Pour MonCash / NatCash — préparer le type de paiement avant la transaction
    type_paiement_django = None
    if methode_paiement in ('moncash', 'natcash'):
        TYPE_PAI_MAP = {
            'moncash': Paiement.TypePaiement.MONCASH,
            'natcash': Paiement.TypePaiement.NATCASH,
        }
        type_paiement_django = TYPE_PAI_MAP[methode_paiement]

    # Pré-calcul des sous-totaux par producteur pour répartir la remise
    sous_totaux_par_producteur = {}
    total_panier = Decimal('0')
    for pid, groupe in items_par_producteur.items():
        st = sum(
            Decimal(str(it['produit'].prix_affiche)) * it['quantite']
            for it in groupe['items']
        )
        sous_totaux_par_producteur[pid] = st
        total_panier += st

    try:
        with transaction.atomic():
            for pid, groupe in items_par_producteur.items():
                # Distribuer la remise proportionnellement au sous-total du producteur
                remise_prod = Decimal('0')
                if voucher_obj and total_panier > 0:
                    ratio        = sous_totaux_par_producteur[pid] / total_panier
                    remise_prod  = (remise_totale * ratio).quantize(Decimal('0.01'))

                commande = CommandeService.creer_commande(
                    acheteur=acheteur,
                    producteur=groupe['producteur'],
                    items=groupe['items'],
                    methode_paiement=methode_django,
                    mode_livraison=mode_django,
                    adresse_livraison=adresse_texte,
                    notes=notes,
                    remise=remise_prod if voucher_obj else None,
                )
                commande.ville_livraison       = ville
                commande.departement_livraison = departement
                commande.save(update_fields=[
                    'ville_livraison', 'departement_livraison',
                ])

                # Gérer la preuve hors ligne
                if methode_paiement == 'hors_ligne':
                    preuve = data.get('preuve_paiement')
                    if preuve:
                        commande.preuve_paiement = preuve
                        commande.statut_paiement = Commande.StatutPaiement.PREUVE_SOUMISE
                        commande.save(update_fields=[
                            'preuve_paiement', 'statut_paiement',
                        ])

                commandes_creees.append(commande)

            # Créer les enregistrements Paiement à l'intérieur de la transaction
            # pour que tout soit atomique (rollback si échec)
            if type_paiement_django is not None:
                for commande in commandes_creees:
                    PaiementService.initier_paiement(
                        commande=commande,
                        type_paiement=type_paiement_django,
                        notes='Initié depuis le checkout',
                    )

            # Vider le panier après commande réussie
            panier.items.all().delete()

    except ValueError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception(
            "commander: erreur inattendue — acheteur=%s methode=%s mode=%s",
            acheteur.pk, methode_paiement, mode_livraison,
        )
        return Response(
            {'success': False, 'error': "Une erreur interne est survenue. Veuillez réessayer."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Marquer le voucher comme utilisé (hors transaction principale pour ne pas bloquer en cas d'erreur mineure)
    if voucher_obj and commandes_creees:
        try:
            VoucherService.utiliser_voucher(
                voucher=voucher_obj,
                remise_totale=remise_totale,
                commandes=commandes_creees,
            )
        except Exception:
            logger.exception(
                "commander: erreur lors de l'utilisation du voucher=%s — commandes=%s",
                voucher_obj.code,
                [c.numero_commande for c in commandes_creees],
            )
            # Ne pas bloquer la commande — les commandes sont déjà créées

    # Construire la réponse
    response_commandes = [
        {
            'numero_commande': c.numero_commande,
            'producteur':      c.producteur.user.get_full_name(),
            'total':           str(c.total),
            'statut':          c.get_statut_display(),
        }
        for c in commandes_creees
    ]

    response_data = {
        'message':   f"{len(commandes_creees)} commande(s) créée(s) avec succès !",
        'commandes': response_commandes,
    }
    if voucher_obj:
        response_data['voucher'] = {
            'code':   voucher_obj.code,
            'remise': str(remise_totale),
        }

    # Voucher couvre l'intégralité — passer en PAYE directement, skip Plopplop
    voucher_couvre_tout = (
        voucher_obj is not None
        and all(c.total == Decimal('0') for c in commandes_creees)
    )
    if voucher_couvre_tout:
        for c in commandes_creees:
            c.methode_paiement = Commande.MethodePaiement.VOUCHER
            c.statut_paiement  = Commande.StatutPaiement.PAYE
            c.save(update_fields=['methode_paiement', 'statut_paiement'])
        response_data['voucher_couvre_tout'] = True
        return Response(
            {'success': True, 'data': response_data},
            status=status.HTTP_201_CREATED,
        )

    # Pour MonCash / NatCash — initier le paiement via Plopplop (appel externe)
    if type_paiement_django is not None and commandes_creees:
        # Initier le paiement Plopplop sur la première commande (redirect unique)
        try:
            from apps.payments.services.plopplop_service import PlopplopService
            premiere_commande = commandes_creees[0]
            plopplop = PlopplopService()
            result   = plopplop.initier_paiement(
                commande_ref=premiere_commande.numero_commande,
                montant=float(premiere_commande.total),
                payment_method=methode_paiement,
            )
            response_data['redirect_url']   = result['redirect_url']
            response_data['transaction_id'] = result['transaction_id']
        except Exception as e:
            logger.error(
                "Plopplop initiation échouée [%s] ref=%s erreur=%s",
                methode_paiement,
                commandes_creees[0].numero_commande if commandes_creees else '?',
                e,
                exc_info=True,
            )
            # Notifier l'acheteur et les admins que le lien de paiement n'a pas pu être généré
            try:
                from apps.emails.utils import (
                    email_paiement_echec_acheteur,
                    email_paiement_echec_admin,
                )
                acheteur_user = premiere_commande.acheteur.user
                email_paiement_echec_acheteur(
                    commandes=commandes_creees,
                    methode=methode_paiement,
                    prenom=acheteur_user.first_name,
                    email_dest=acheteur_user.email,
                )
                email_paiement_echec_admin(
                    commandes=commandes_creees,
                    methode=methode_paiement,
                    acheteur=acheteur_user,
                    raison=str(e) or "Passerelle Plopplop indisponible lors de l'initiation",
                )
            except Exception:
                logger.exception("Erreur envoi notification echec initiation plopplop")

            response_data['paiement_erreur'] = (
                f"La passerelle {methode_paiement.capitalize()} est temporairement indisponible. "
                "Vos commandes ont bien été créées (références ci-dessus). "
                "Vous pouvez réessayer plus tard ou utiliser le paiement hors ligne "
                "depuis « Mes commandes »."
            )

    return Response(
        {'success': True, 'data': response_data},
        status=status.HTTP_201_CREATED,
    )
