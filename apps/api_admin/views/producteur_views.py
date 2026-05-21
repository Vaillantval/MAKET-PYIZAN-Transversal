from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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
@permission_classes([IsSuperAdmin])
def producteur_create(request):
    """
    Créer un producteur depuis le panel admin.
    Deux modes :
      - user_id fourni  → associer un utilisateur existant
      - sinon           → créer un nouvel utilisateur via RegisterSerializer
    """
    STATUTS_VALIDES = ['actif', 'en_attente', 'suspendu', 'inactif']
    statut_choisi   = request.data.get('statut', 'en_attente')
    if statut_choisi not in STATUTS_VALIDES:
        statut_choisi = 'en_attente'

    user_id = request.data.get('user_id')

    if user_id:
        # ── Mode A : utilisateur existant ──────────────────────
        from apps.accounts.models import CustomUser
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Utilisateur introuvable.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(user, 'profil_producteur'):
            return Response(
                {'success': False, 'error': 'Cet utilisateur possède déjà un profil producteur.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.data.get('departement') or not request.data.get('commune'):
            return Response(
                {'success': False, 'error': {'departement': ['Le département et la commune sont requis.']}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.role != 'producteur':
            user.role = 'producteur'
            user.save(update_fields=['role'])

        sup = request.data.get('superficie_ha') or None
        producteur = Producteur.objects.create(
            user              = user,
            departement       = request.data.get('departement', ''),
            commune           = request.data.get('commune', ''),
            localite          = request.data.get('localite', ''),
            superficie_ha     = sup,
            description       = request.data.get('description', ''),
            num_identification = request.data.get('num_identification', ''),
            adresse_complete  = request.data.get('adresse_complete', ''),
            note_admin        = request.data.get('note_admin', ''),
            statut            = statut_choisi,
        )
        if statut_choisi == 'actif':
            producteur.valide_par      = request.user
            producteur.date_validation = timezone.now()
            producteur.save()

    else:
        # ── Mode B : nouvel utilisateur ────────────────────────
        data = request.data.copy()
        data['role'] = 'producteur'
        if 'password2' not in data and 'password' in data:
            data['password2'] = data['password']

        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user       = serializer.save()
        producteur = user.profil_producteur

        if request.data.get('adresse_complete'):
            producteur.adresse_complete = request.data['adresse_complete']
        if request.data.get('note_admin'):
            producteur.note_admin = request.data['note_admin']

        producteur.statut = statut_choisi
        if statut_choisi == 'actif':
            producteur.valide_par      = request.user
            producteur.date_validation = timezone.now()
        producteur.save()

    return Response(
        {
            'success': True,
            'data': ProducteurProfilSerializer(
                producteur, context={'request': request}
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


# ── GET/PATCH /api/admin/producteurs/<id>/detail/ ───────────────
@api_view(['GET', 'PATCH'])
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
