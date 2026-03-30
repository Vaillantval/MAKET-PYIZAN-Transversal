from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from apps.accounts.models import Adresse
from apps.orders.models import Panier, Commande
from apps.orders.serializers import PasserCommandeSerializer
from apps.orders.services.commande_service import CommandeService


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

    METHODE_MAP = {
        'cash':       Commande.MethodePaiement.CASH,
        'moncash':    Commande.MethodePaiement.MONCASH,
        'hors_ligne': Commande.MethodePaiement.VIREMENT,
    }
    MODE_MAP = {
        'domicile': Commande.ModeLivraison.LIVRAISON_DOMICILE,
        'collecte': Commande.ModeLivraison.POINT_COLLECTE,
        'retrait':  Commande.ModeLivraison.RETRAIT_PRODUCTEUR,
    }

    methode_django = METHODE_MAP.get(methode_paiement, Commande.MethodePaiement.CASH)
    mode_django    = MODE_MAP.get(mode_livraison, Commande.ModeLivraison.LIVRAISON_DOMICILE)

    try:
        with transaction.atomic():
            for pid, groupe in items_par_producteur.items():
                commande = CommandeService.creer_commande(
                    acheteur=acheteur,
                    producteur=groupe['producteur'],
                    items=groupe['items'],
                    methode_paiement=methode_django,
                    mode_livraison=mode_django,
                    adresse_livraison=adresse_texte,
                    notes=notes,
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

            # Vider le panier après commande réussie
            panier.items.all().delete()

    except ValueError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

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

    # Pour MonCash — initier le paiement et retourner le redirect_url
    if methode_paiement == 'moncash' and commandes_creees:
        try:
            from apps.payments.services.moncash_service import MonCashService
            premiere_commande = commandes_creees[0]
            moncash = MonCashService()
            result  = moncash.initier_paiement(
                commande_ref=premiere_commande.numero_commande,
                montant_htg=premiere_commande.total,
            )
            response_data['redirect_url']  = result['redirect_url']
            response_data['moncash_token'] = result['token']
        except Exception:
            response_data['moncash_erreur'] = (
                "Paiement MonCash temporairement indisponible. "
                "Vos commandes ont été créées. Contactez-nous."
            )

    return Response(
        {'success': True, 'data': response_data},
        status=status.HTTP_201_CREATED,
    )
