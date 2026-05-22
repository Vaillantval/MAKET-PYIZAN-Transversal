from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.catalog.models import Produit, Categorie
from apps.catalog.serializers import (
    ProduitListSerializer,
    ProduitDetailSerializer,
    ProduitCreateUpdateSerializer,
    CategorieSerializer,
)
from apps.accounts.models import Producteur
from django.utils.translation import gettext as _


# ── GET /api/admin/catalogue/ ────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def catalogue_list(request):
    """Tous les produits (tous statuts) avec filtres."""
    search        = request.query_params.get('search', '')
    statut        = request.query_params.get('statut', '')
    producteur_id = request.query_params.get('producteur_id', '')

    qs = Produit.objects.select_related(
        'categorie', 'producteur__user'
    ).order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(nom__icontains=search) |
            Q(variete__icontains=search) |
            Q(producteur__user__first_name__icontains=search)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if producteur_id:
        qs = qs.filter(producteur__pk=producteur_id)

    serializer = ProduitListSerializer(
        qs, many=True, context={'request': request}
    )
    return Response({'success': True, 'data': serializer.data})


# ── POST /api/admin/catalogue/create/ ───────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def catalogue_create(request):
    """Créer un produit (multipart/form-data)."""
    producteur_id = request.data.get('producteur_id')
    producteur    = get_object_or_404(Producteur, pk=producteur_id)

    serializer = ProduitCreateUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    produit = serializer.save(
        producteur=producteur,
        statut='actif',
        is_active=True
    )
    return Response(
        {
            'success': True,
            'data': ProduitDetailSerializer(
                produit, context={'request': request}
            ).data
        },
        status=status.HTTP_201_CREATED
    )


# ── GET/PATCH /api/admin/catalogue/<id>/detail/ ─────────────────
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def catalogue_detail(request, pk):
    """Détail ou mise à jour d'un produit."""
    produit = get_object_or_404(Produit, pk=pk)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': ProduitDetailSerializer(
                produit, context={'request': request}
            ).data
        })

    serializer = ProduitCreateUpdateSerializer(
        produit, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer.save()
    return Response({
        'success': True,
        'data': ProduitDetailSerializer(
            produit, context={'request': request}
        ).data
    })


# ── PATCH /api/admin/catalogue/<id>/statut/ ─────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def catalogue_statut(request, pk):
    """Changer le statut d'un produit."""
    produit        = get_object_or_404(Produit, pk=pk)
    nouveau_statut = request.data.get('statut')

    STATUTS = ['brouillon', 'en_attente', 'actif', 'epuise', 'inactif']
    if nouveau_statut not in STATUTS:
        return Response(
            {'success': False, 'error': f"Statut invalide : {STATUTS}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    produit.statut    = nouveau_statut
    produit.is_active = (nouveau_statut == 'actif')
    produit.save(update_fields=['statut', 'is_active'])

    return Response({
        'success': True,
        'data': {
            'id':     produit.pk,
            'statut': produit.statut,
        }
    })


# ── PATCH /api/admin/catalogue/<id>/toggle/ ─────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def catalogue_toggle(request, pk):
    """
    Basculer is_active ou is_featured d'un produit.
    Body : { "champ": "is_active" | "is_featured" }
    """
    produit = get_object_or_404(Produit, pk=pk)
    champ   = request.data.get('champ')

    if champ not in ['is_active', 'is_featured']:
        return Response(
            {'success': False, 'error': _("Champ : 'is_active' ou 'is_featured'.")},
            status=status.HTTP_400_BAD_REQUEST
        )

    nouvelle_val = not getattr(produit, champ)
    setattr(produit, champ, nouvelle_val)
    update_fields = [champ]

    # Sync statut when toggling is_active so filters stay consistent
    if champ == 'is_active':
        produit.statut = Produit.Statut.ACTIF if nouvelle_val else Produit.Statut.INACTIF
        update_fields.append('statut')

    produit.save(update_fields=update_fields)

    return Response({
        'success': True,
        'data': {
            'id':     produit.pk,
            champ:    getattr(produit, champ),
            'statut': produit.statut,
        }
    })


# ── GET/POST /api/admin/categories/ ─────────────────────────────
@extend_schema(operation_id='admin_categories_list', tags=['Admin — Catalogue'])
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def categories_admin(request):
    if request.method == 'GET':
        cats = Categorie.objects.all().order_by('ordre', 'nom')
        return Response({
            'success': True,
            'data': CategorieSerializer(cats, many=True).data
        })

    serializer = CategorieSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    cat = serializer.save()
    return Response(
        {'success': True, 'data': CategorieSerializer(cat).data},
        status=status.HTTP_201_CREATED
    )


# ── GET/PATCH/DELETE /api/admin/categories/<id>/ ────────────────
@extend_schema(operation_id='admin_categorie_detail', tags=['Admin — Catalogue'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def categorie_detail(request, pk):
    cat = get_object_or_404(Categorie, pk=pk)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': CategorieSerializer(cat).data
        })

    if request.method == 'DELETE':
        nb = cat.produits.count()
        if nb > 0:
            return Response(
                {'success': False, 'error': f'Impossible de supprimer : {nb} produit(s) lié(s).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CategorieSerializer(cat, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer.save()
    return Response({'success': True, 'data': serializer.data})
