from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from apps.accounts.permissions import IsSuperAdmin
from apps.accounts.models import Producteur
from apps.accounts.serializers import ProducteurProfilSerializer
from apps.accounts.serializers.auth_serializers import RegisterSerializer
from django.utils.translation import gettext as _


# ── GET /api/admin/producteurs/ ─────────────────────────────────
@api_view(['GET'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsSuperAdmin])
def producteurs_list(request):
    """Liste des producteurs avec filtres."""
    statut = request.query_params.get('statut', '')
    search = request.query_params.get('search', '')

    qs = Producteur.objects.select_related('user').order_by('-created_at')

    if statut:
        qs = qs.filter(statut=statut)
    if search:
        qs = qs.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)  |
            Q(code_producteur__icontains=search)  |
            Q(commune__icontains=search)
        )

    data = ProducteurProfilSerializer(
        qs, many=True, context={'request': request}
    ).data
    return Response({'success': True, 'data': data})


# ── POST /api/admin/producteurs/create/ ─────────────────────────
@api_view(['POST'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsSuperAdmin])
def producteur_create(request):
    """Créer un producteur depuis le panel admin."""
    data = request.data.copy()
    data['role'] = 'producteur'
    # L'admin n'a pas de champ password2 dans la modale — on le duplique
    if 'password2' not in data and 'password' in data:
        data['password2'] = data['password']

    serializer = RegisterSerializer(data=data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    user       = serializer.save()
    producteur = user.profil_producteur

    # Champs non gérés par RegisterSerializer
    if request.data.get('adresse_complete'):
        producteur.adresse_complete = request.data['adresse_complete']
    if request.data.get('note_admin'):
        producteur.note_admin = request.data['note_admin']

    # Honorer le statut choisi par l'admin (défaut : en_attente)
    STATUTS_VALIDES = ['actif', 'en_attente', 'suspendu', 'inactif']
    statut_choisi = request.data.get('statut', 'en_attente')
    producteur.statut = statut_choisi if statut_choisi in STATUTS_VALIDES else 'en_attente'
    if producteur.statut == 'actif':
        producteur.valide_par      = request.user
        producteur.date_validation = timezone.now()

    producteur.save()

    return Response(
        {
            'success': True,
            'data': ProducteurProfilSerializer(
                producteur, context={'request': request}
            ).data
        },
        status=status.HTTP_201_CREATED
    )


# ── GET/PATCH /api/admin/producteurs/<id>/detail/ ───────────────
@api_view(['GET', 'PATCH'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsSuperAdmin])
def producteur_detail(request, pk):
    """Détail ou mise à jour d'un producteur."""
    producteur = get_object_or_404(Producteur, pk=pk)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': ProducteurProfilSerializer(
                producteur, context={'request': request}
            ).data
        })

    serializer = ProducteurProfilSerializer(
        producteur, data=request.data,
        partial=True,
        context={'request': request}
    )
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer.save()

    # Mettre à jour les champs du compte utilisateur
    user = producteur.user
    user_updated = False
    for field in ('first_name', 'last_name', 'email', 'telephone'):
        if field in request.data:
            setattr(user, field, request.data[field])
            user_updated = True
    if user_updated:
        user.save()

    return Response({
        'success': True,
        'data': ProducteurProfilSerializer(producteur, context={'request': request}).data,
    })


# ── PATCH /api/admin/producteurs/<id>/statut/ ───────────────────
@api_view(['PATCH'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsSuperAdmin])
def producteur_statut(request, pk):
    """
    Changer le statut d'un producteur.
    Body : { "statut": "actif" | "suspendu" | "en_attente" | "inactif",
             "note": "..." }
    """
    producteur     = get_object_or_404(Producteur, pk=pk)
    nouveau_statut = request.data.get('statut')
    note           = request.data.get('note', '')

    STATUTS_VALIDES = ['actif', 'suspendu', 'en_attente', 'inactif']
    if nouveau_statut not in STATUTS_VALIDES:
        return Response(
            {
                'success': False,
                'error': f"Statut invalide. Valeurs : {STATUTS_VALIDES}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    ancien_statut     = producteur.statut
    producteur.statut = nouveau_statut

    if note:
        producteur.note_admin = note

    if nouveau_statut == 'actif' and ancien_statut != 'actif':
        producteur.valide_par      = request.user
        producteur.date_validation = timezone.now()

    producteur.save()

    return Response({
        'success': True,
        'data': {
            'id':              producteur.pk,
            'code_producteur': producteur.code_producteur,
            'statut':          producteur.statut,
            'message':         f"Statut mis à jour : {nouveau_statut}."
        }
    })
