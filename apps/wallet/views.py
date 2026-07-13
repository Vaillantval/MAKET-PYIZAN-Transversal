import logging

from django.core.cache import cache
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import SiteSettings
from apps.core.pagination import PaginationUniforme
from apps.orders.models import Commande
from apps.wallet.models import BonCadeau, WalletRetrait
from apps.wallet.serializers import (
    BonAcheterSerializer,
    BonCadeauRecuSerializer,
    BonCadeauSerializer,
    BonEncaisserSerializer,
    BonVerifierSerializer,
    PayerCommandeSerializer,
    RechargeHorsLigneSerializer,
    RechargeInitierSerializer,
    RechargeVerifierSerializer,
    RetraitSerializer,
    WalletRetraitSerializer,
    WalletTransactionSerializer,
)
from apps.wallet.services import SoldeInsuffisant, WalletError, WalletService

logger = logging.getLogger(__name__)

ENCAISSEMENT_MAX_ESSAIS = 10     # tentatives de code par heure et par user
ENCAISSEMENT_FENETRE    = 3600   # secondes


def _wallet_indisponible():
    reglages = SiteSettings.get_solo()
    if not reglages.wallet_enabled:
        return Response(
            {'success': False, 'error': _("Le portefeuille n'est pas disponible pour le moment.")},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return None


def _erreurs(serializer):
    return Response(
        {'success': False, 'error': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _commande_de(request, numero):
    """Retourne (commande, None) ou (None, Response 4xx)."""
    try:
        acheteur = request.user.profil_acheteur
    except Exception:
        return None, Response(
            {'success': False, 'error': _("Profil acheteur requis.")},
            status=status.HTTP_403_FORBIDDEN,
        )
    commande = Commande.objects.filter(
        numero_commande=numero, acheteur=acheteur,
    ).first()
    if not commande:
        return None, Response(
            {'success': False, 'error': _("Commande introuvable.")},
            status=status.HTTP_404_NOT_FOUND,
        )
    return commande, None


# ── GET /api/wallet/ ────────────────────────────────────────────

@extend_schema(tags=['Wallet'], summary='Solde et dernières transactions')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_detail(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    wallet = WalletService.get_wallet(request.user)
    reglages = SiteSettings.get_solo()

    parrainage = None
    if reglages.parrainage_enabled:
        parrainage = {
            'code':       request.user.get_or_create_code_parrainage(),
            'taux_bonus': str(reglages.taux_bonus_parrainage or 0),
        }

    recentes = wallet.transactions.select_related('commande')[:10]
    return Response({
        'success': True,
        'data': {
            'solde':      str(wallet.solde),
            'devise':     'HTG',
            'is_active':  wallet.is_active,
            'cashback': {
                'actif':   reglages.cashback_enabled,
                'taux':    str(reglages.taux_cashback or 0),
                'plafond': str(reglages.cashback_montant_max or 0),
            },
            'parrainage': parrainage,
            'depot_hors_ligne': {
                'numero_moncash': reglages.numero_moncash_depot,
                'numero_natcash': reglages.numero_natcash_depot,
            },
            'transactions_recentes': WalletTransactionSerializer(recentes, many=True).data,
        },
    })


# ── GET /api/wallet/transactions/ ───────────────────────────────

@extend_schema(tags=['Wallet'], summary='Historique complet des transactions',
               responses={200: WalletTransactionSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_transactions(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    wallet = WalletService.get_wallet(request.user)
    paginator = PaginationUniforme()
    page = paginator.paginate_queryset(
        wallet.transactions.select_related('commande'), request,
    )
    return paginator.get_paginated_response(
        WalletTransactionSerializer(page, many=True).data,
    )


# ── POST /api/wallet/recharge/initier/ ──────────────────────────

@extend_schema(tags=['Wallet'], request=RechargeInitierSerializer,
               summary='Initier une recharge MonCash/NatCash (Plopplop)',
               description='Retourne redirect_url à ouvrir pour payer, puis '
                           'appeler /api/wallet/recharge/verifier/.')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recharge_initier(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = RechargeInitierSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    try:
        recharge, redirect_url = WalletService.initier_recharge_plopplop(
            request.user,
            serializer.validated_data['montant'],
            serializer.validated_data['methode'],
        )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'success': True,
        'data': {
            'recharge_id':  recharge.pk,
            'reference':    recharge.reference_plopplop,
            'redirect_url': redirect_url,
        },
    }, status=status.HTTP_201_CREATED)


# ── POST /api/wallet/recharge/verifier/ ─────────────────────────

@extend_schema(tags=['Wallet'], request=RechargeVerifierSerializer,
               summary='Vérifier une recharge Plopplop et créditer le solde')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recharge_verifier(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = RechargeVerifierSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    recharge = serializer.validated_data['recharge_id']
    if recharge.wallet.user_id != request.user.id:
        return Response(
            {'success': False, 'error': _("Recharge non autorisée.")},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        confirmee = WalletService.verifier_recharge_plopplop(recharge)
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error("Vérification recharge #%s : %s", recharge.pk, e)
        return Response(
            {'success': False, 'error': f"Erreur de vérification : {e}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    recharge.refresh_from_db()
    recharge.wallet.refresh_from_db()
    return Response({
        'success': True,
        'data': {
            'confirmee': confirmee,
            'statut':    recharge.statut,
            'solde':     str(recharge.wallet.solde),
        },
    })


# ── POST /api/wallet/recharge/hors-ligne/ ───────────────────────

@extend_schema(tags=['Wallet'], request=RechargeHorsLigneSerializer,
               summary='Recharge par dépôt hors ligne (preuve à valider)',
               description='Upload de la preuve de dépôt (JPG/PNG, max 5 MB). '
                           'Le solde est crédité après validation admin. Les '
                           'numéros de dépôt sont dans GET /api/wallet/.')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def recharge_hors_ligne(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = RechargeHorsLigneSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    try:
        recharge = WalletService.soumettre_recharge_hors_ligne(
            request.user,
            serializer.validated_data['montant'],
            serializer.validated_data['preuve_image'],
        )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'success': True,
        'data': {
            'recharge_id': recharge.pk,
            'statut':      recharge.statut,
            'message':     _("Preuve reçue. Votre solde sera crédité après validation."),
        },
    }, status=status.HTTP_201_CREATED)


# ── POST /api/wallet/payer/ ─────────────────────────────────────

@extend_schema(tags=['Wallet'], request=PayerCommandeSerializer,
               summary='Payer une commande avec le solde wallet')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payer_commande(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = PayerCommandeSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    commande, erreur = _commande_de(request, serializer.validated_data['commande_numero'])
    if erreur:
        return erreur

    try:
        tx = WalletService.payer_commande(request.user, commande)
    except SoldeInsuffisant as e:
        return Response(
            {'success': False, 'error': str(e), 'code': 'SOLDE_INSUFFISANT'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    commande.refresh_from_db()
    return Response({
        'success': True,
        'data': {
            'commande_numero': commande.numero_commande,
            'statut':          commande.statut,
            'statut_paiement': commande.statut_paiement,
            'montant_paye':    str(-tx.montant),
            'solde':           str(tx.solde_apres),
        },
    })


# ── POST /api/wallet/payer-partiel/ ─────────────────────────────

@extend_schema(tags=['Wallet'], request=PayerCommandeSerializer,
               summary='Réserver le solde wallet sur une commande (paiement partiel)',
               description='Débite min(solde, total) — le complément se paie '
                           'via /api/payments/initier/ (MonCash/NatCash).')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payer_partiel(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = PayerCommandeSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    commande, erreur = _commande_de(request, serializer.validated_data['commande_numero'])
    if erreur:
        return erreur

    try:
        WalletService.appliquer_paiement_partiel(request.user, commande)
    except (SoldeInsuffisant, WalletError) as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    commande.refresh_from_db()
    return Response({
        'success': True,
        'data': {
            'commande_numero':        commande.numero_commande,
            'montant_wallet_utilise': str(commande.montant_wallet_utilise),
            'reste_a_payer':          str(commande.total - commande.montant_wallet_utilise),
        },
    })


# ── POST /api/wallet/liberer-partiel/ ───────────────────────────

@extend_schema(tags=['Wallet'], request=PayerCommandeSerializer,
               summary='Annuler la réservation wallet sur une commande (re-crédit)')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def liberer_partiel(request):
    serializer = PayerCommandeSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    commande, erreur = _commande_de(request, serializer.validated_data['commande_numero'])
    if erreur:
        return erreur

    tx = WalletService.liberer_paiement_partiel(
        commande,
        description=f"Solde retiré du paiement — commande {commande.numero_commande}",
    )
    return Response({
        'success': True,
        'data': {
            'libere': tx is not None,
            'solde':  str(tx.solde_apres) if tx else None,
        },
    })


# ── POST /api/wallet/retrait/ + GET /api/wallet/retraits/ ──────

@extend_schema(tags=['Wallet'], request=RetraitSerializer,
               summary='Demander un retrait MonCash/NatCash',
               description='Le montant est débité (réservé) immédiatement. '
                           'L\'admin effectue le transfert puis marque le '
                           'retrait payé — ou le rejette (re-crédit).')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retrait_demander(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = RetraitSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    try:
        retrait = WalletService.demander_retrait(
            request.user,
            serializer.validated_data['montant'],
            serializer.validated_data['canal'],
            serializer.validated_data['numero_telephone'],
        )
    except SoldeInsuffisant as e:
        return Response(
            {'success': False, 'error': str(e), 'code': 'SOLDE_INSUFFISANT'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {'success': True, 'data': WalletRetraitSerializer(retrait).data},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(tags=['Wallet'], summary='Mes demandes de retrait',
               responses={200: WalletRetraitSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retraits_liste(request):
    retraits = WalletRetrait.objects.filter(wallet__user=request.user)
    paginator = PaginationUniforme()
    page = paginator.paginate_queryset(retraits, request)
    return paginator.get_paginated_response(
        WalletRetraitSerializer(page, many=True).data,
    )


# ── Bons cadeaux ────────────────────────────────────────────────

@extend_schema(tags=['Wallet'], request=BonAcheterSerializer,
               summary='Acheter un bon cadeau',
               description='methode=wallet : payé et activé immédiatement. '
                           'moncash/natcash : retourne redirect_url puis '
                           'appeler /api/wallet/bon/verifier/. Le code est '
                           'envoyé par email au destinataire (ou à l\'acheteur).')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bon_acheter(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = BonAcheterSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    montant = serializer.validated_data['montant']
    methode = serializer.validated_data['methode']
    email   = serializer.validated_data.get('email_destinataire', '')
    message = serializer.validated_data.get('message', '')

    try:
        if methode == 'wallet':
            bon = WalletService.creer_et_acheter_bon_wallet(
                request.user, montant, email, message,
            )
            return Response({
                'success': True,
                'data': {'methode': 'wallet', 'bon': BonCadeauSerializer(bon).data},
            }, status=status.HTTP_201_CREATED)

        bon, redirect_url = WalletService.initier_bon_cadeau_plopplop(
            request.user, montant, methode, email, message,
        )
        return Response({
            'success': True,
            'data': {
                'methode':      methode,
                'bon_id':       bon.pk,
                'reference':    bon.reference_plopplop,
                'redirect_url': redirect_url,
            },
        }, status=status.HTTP_201_CREATED)

    except SoldeInsuffisant as e:
        return Response(
            {'success': False, 'error': str(e), 'code': 'SOLDE_INSUFFISANT'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=['Wallet'], request=BonVerifierSerializer,
               summary='Vérifier le paiement d\'un bon cadeau et l\'activer')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bon_verifier(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = BonVerifierSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    bon = serializer.validated_data['bon_id']
    if bon.achete_par_id != request.user.id:
        return Response(
            {'success': False, 'error': _("Bon cadeau non autorisé.")},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        WalletService.verifier_bon_cadeau_plopplop(bon)
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error("Vérification bon cadeau #%s : %s", bon.pk, e)
        return Response(
            {'success': False, 'error': f"Erreur de vérification : {e}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    bon.refresh_from_db()
    return Response({'success': True, 'data': BonCadeauSerializer(bon).data})


@extend_schema(tags=['Wallet'], request=BonEncaisserSerializer,
               summary='Encaisser un code cadeau (crédite le wallet)')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bon_encaisser(request):
    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    serializer = BonEncaisserSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    cle_essais = f"wallet_bon_essais_{request.user.id}"
    essais = cache.get(cle_essais, 0)
    if essais >= ENCAISSEMENT_MAX_ESSAIS:
        return Response(
            {'success': False, 'error': _("Trop de tentatives. Réessayez dans une heure.")},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        tx = WalletService.encaisser_bon_cadeau(
            request.user, serializer.validated_data['code'],
        )
        cache.delete(cle_essais)
    except WalletError as e:
        cache.set(cle_essais, essais + 1, ENCAISSEMENT_FENETRE)
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'success': True,
        'data': {'montant': str(tx.montant), 'solde': str(tx.solde_apres)},
    })


@extend_schema(tags=['Wallet'], summary='Mes bons cadeaux achetés',
               responses={200: BonCadeauSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bons_achetes(request):
    bons = request.user.bons_cadeaux_achetes.exclude(
        statut=BonCadeau.Statut.ATTENTE_PAIEMENT,
    )
    paginator = PaginationUniforme()
    page = paginator.paginate_queryset(bons, request)
    return paginator.get_paginated_response(
        BonCadeauSerializer(page, many=True).data,
    )


@extend_schema(tags=['Wallet'], summary='Mes bons cadeaux reçus (code masqué tant que non encaissé)',
               responses={200: BonCadeauRecuSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bons_recus(request):
    from django.db.models import Q

    filtre = Q(encaisse_par=request.user)
    if request.user.email:
        filtre |= Q(
            email_destinataire__iexact=request.user.email,
            statut=BonCadeau.Statut.ACTIF,
        )
    bons = BonCadeau.objects.filter(filtre).select_related('achete_par')
    paginator = PaginationUniforme()
    page = paginator.paginate_queryset(bons, request)
    return paginator.get_paginated_response(
        BonCadeauRecuSerializer(page, many=True).data,
    )


# ── POST /api/wallet/code-paiement/ ─────────────────────────────

@extend_schema(tags=['Wallet'],
               summary='Générer un code de paiement POS (usage unique, 5 min)',
               description='Code à 6 chiffres à montrer/dicter à l\'opérateur '
                           'de caisse pour autoriser un débit wallet au '
                           'comptoir. En générer un nouveau invalide les '
                           'précédents non utilisés.')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def code_paiement_generer(request):
    from django.utils import timezone

    indisponible = _wallet_indisponible()
    if indisponible:
        return indisponible

    try:
        cp = WalletService.generer_code_paiement(request.user)
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    wallet = WalletService.get_wallet(request.user)
    return Response({
        'success': True,
        'data': {
            'code':        cp.code,
            'expire_dans': max(0, int((cp.expire_le - timezone.now()).total_seconds())),
            'expire_le':   cp.expire_le,
            'solde':       str(wallet.solde),
        },
    })
