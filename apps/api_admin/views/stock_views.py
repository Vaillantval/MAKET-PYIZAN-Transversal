from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.stock.models import Lot, MouvementStock, AlerteStock
from apps.stock.services.stock_service import StockService
from django.utils.translation import gettext as _


def _lot_data(lot):
    p = lot.produit
    return {
        'id':                lot.pk,
        'numero_lot':        lot.numero_lot,
        'produit_id':        p.pk,
        'produit_nom':       p.nom,
        'producteur_nom':    p.producteur.user.get_full_name(),
        'producteur_code':   p.producteur.code_producteur,
        'categorie':         p.categorie.nom,
        'quantite_initiale': lot.quantite_initiale,
        'quantite_actuelle': lot.quantite_actuelle,
        'quantite_vendue':   lot.quantite_vendue,
        'taux_ecoulement':   lot.taux_ecoulement,
        'statut':            lot.statut,
        'statut_label':      lot.get_statut_display(),
        'date_recolte':      str(lot.date_recolte) if lot.date_recolte else None,
        'date_expiration':   str(lot.date_expiration) if lot.date_expiration else None,
        'lieu_stockage':     lot.lieu_stockage,
        'notes':             lot.notes,
        'created_at':        lot.created_at.isoformat(),
    }


# ── GET /api/admin/stocks/lots/ ──────────────────────────────────
@extend_schema(operation_id='admin_lots_list', tags=['Admin — Stocks'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def lots_list(request):
    """Liste des lots avec filtres."""
    search        = request.query_params.get('search', '')
    statut        = request.query_params.get('statut', '')
    producteur_id = request.query_params.get('producteur_id', '')

    qs = Lot.objects.select_related(
        'produit__producteur__user'
    ).order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(numero_lot__icontains=search) |
            Q(produit__nom__icontains=search)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if producteur_id:
        qs = qs.filter(produit__producteur__pk=producteur_id)

    return Response({
        'success': True,
        'data': [_lot_data(l) for l in qs]
    })


# ── POST /api/admin/stocks/lots/create/ ─────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def lot_create(request):
    """Créer un nouveau lot de stock."""
    from apps.catalog.models import Produit
    produit_id = request.data.get('produit_id')
    produit    = get_object_or_404(Produit, pk=produit_id)

    quantite = int(request.data.get('quantite_initiale', 0))
    if quantite <= 0:
        return Response(
            {'success': False, 'error': _("La quantité doit être > 0.")},
            status=status.HTTP_400_BAD_REQUEST
        )

    statut_lot = request.data.get('statut', 'disponible')
    STATUTS_LOT = ['en_cours', 'disponible', 'epuise', 'expire', 'rappel']
    if statut_lot not in STATUTS_LOT:
        statut_lot = 'disponible'

    lot = Lot.objects.create(
        produit=produit,
        quantite_initiale=quantite,
        quantite_actuelle=quantite,
        date_recolte=request.data.get('date_recolte') or None,
        date_expiration=request.data.get('date_expiration') or None,
        lieu_stockage=request.data.get('lieu_stockage', ''),
        notes=request.data.get('notes', ''),
        cree_par=request.user,
        statut=statut_lot,
    )

    return Response(
        {'success': True, 'data': _lot_data(lot)},
        status=status.HTTP_201_CREATED
    )


# ── GET/PATCH /api/admin/stocks/lots/<id>/ ──────────────────────
@extend_schema(operation_id='admin_lot_detail', tags=['Admin — Stocks'])
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def lot_detail(request, pk):
    """Détail ou ajustement d'un lot."""
    lot = get_object_or_404(Lot, pk=pk)

    if request.method == 'GET':
        return Response({'success': True, 'data': _lot_data(lot)})

    # PATCH — ajustement du stock et mise à jour des champs
    nouvelle_quantite = request.data.get('quantite_actuelle')
    motif             = request.data.get('motif', 'Ajustement admin')

    if nouvelle_quantite is not None:
        try:
            StockService.ajustement_stock(
                lot=lot,
                nouvelle_quantite=int(nouvelle_quantite),
                motif=motif,
                effectue_par=request.user,
            )
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Champs directement éditables
    STATUTS_LOT = ['en_cours', 'disponible', 'epuise', 'expire', 'rappel']
    update_fields = []

    if 'statut' in request.data and request.data['statut'] in STATUTS_LOT:
        lot.statut = request.data['statut']
        update_fields.append('statut')
    if 'date_recolte' in request.data:
        lot.date_recolte = request.data['date_recolte'] or None
        update_fields.append('date_recolte')
    if 'date_expiration' in request.data:
        lot.date_expiration = request.data['date_expiration'] or None
        update_fields.append('date_expiration')
    if 'lieu_stockage' in request.data:
        lot.lieu_stockage = request.data['lieu_stockage']
        update_fields.append('lieu_stockage')
    if 'notes' in request.data:
        lot.notes = request.data['notes']
        update_fields.append('notes')

    if update_fields:
        lot.save(update_fields=update_fields)

    lot.refresh_from_db()
    return Response({'success': True, 'data': _lot_data(lot)})


# ── GET /api/admin/stocks/alertes/ ──────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def alertes_stock(request):
    """Alertes stock actives."""
    niveau = request.query_params.get('niveau', '')

    qs = AlerteStock.objects.filter(
        statut__in=['nouvelle', 'vue']
    ).select_related(
        'produit__producteur__user'
    ).order_by('-created_at')

    if niveau:
        qs = qs.filter(niveau=niveau)

    data = [
        {
            'id':              a.pk,
            'produit_nom':     a.produit.nom,
            'producteur_nom':  a.produit.producteur.user.get_full_name(),
            'producteur_tel':  a.produit.producteur.user.telephone if hasattr(a.produit.producteur.user, 'telephone') else '',
            'niveau':          a.niveau,
            'stock_actuel':    a.stock_actuel,
            'seuil':           a.seuil,
            'message':         a.message,
            'statut':          a.statut,
            'created_at':      a.created_at.isoformat(),
        }
        for a in qs
    ]
    return Response({'success': True, 'data': data})


# ── POST /api/admin/stocks/recalculer-reserves/ ─────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def recalculer_reserves(request):
    """
    Réconcilie stock_reserve pour tous les produits depuis les commandes actives.
    À appeler si stock_reserve s'est désynchronisé (suppression manuelle, rollback partiel, etc.)
    """
    from apps.catalog.models import Produit
    produits = list(Produit.objects.all())
    corrections = []
    for produit in produits:
        ancien = produit.stock_reserve
        nouveau = produit.recalculer_stock_reserve()
        if ancien != nouveau:
            corrections.append({
                'produit_id':  produit.pk,
                'produit_nom': produit.nom,
                'avant':       ancien,
                'apres':       nouveau,
            })
    return Response({
        'success': True,
        'data': {
            'produits_verifies':  len(produits),
            'corrections':        len(corrections),
            'detail':             corrections,
        }
    })


# ── GET /api/admin/stocks/mouvements/ ───────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def mouvements_stock(request):
    """Historique des mouvements de stock."""
    qs = MouvementStock.objects.select_related(
        'produit', 'effectue_par'
    ).order_by('-created_at')[:100]

    data = [
        {
            'id':             m.pk,
            'produit_nom':    m.produit.nom,
            'type_mouvement': m.get_type_mouvement_display(),
            'quantite':       m.quantite,
            'stock_avant':    m.stock_avant,
            'stock_apres':    m.stock_apres,
            'motif':          m.motif,
            'effectue_par':   m.effectue_par.get_full_name() if m.effectue_par else None,
            'created_at':     m.created_at.isoformat(),
        }
        for m in qs
    ]
    return Response({'success': True, 'data': data})
