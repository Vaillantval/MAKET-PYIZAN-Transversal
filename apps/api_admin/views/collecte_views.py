from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.collectes.models import (
    Collecte, ParticipationCollecte,
    ZoneCollecte, PointCollecte,
)
from apps.collectes.services.collecte_service import CollecteService
from apps.accounts.models import Producteur
from django.utils.translation import gettext as _


def _participation_data(p):
    return {
        'id':                 p.pk,
        'producteur_id':      p.producteur_id,
        'producteur_nom':     p.producteur.user.get_full_name(),
        'producteur_code':    p.producteur.code_producteur,
        'producteur_commune': getattr(p.producteur, 'commune', '') or '',
        'statut':             p.statut,
        'statut_label':       p.get_statut_display(),
        'quantite_prevue':    p.quantite_prevue,
        'quantite_collectee': p.quantite_collectee,
    }


def _collecte_data(c, with_participations=False):
    """Sérialisation complète d'une collecte."""
    data = {
        'id':             c.pk,
        'reference':      c.reference,
        'statut':         c.statut,
        'statut_label':   c.get_statut_display(),
        'est_en_retard':  c.est_en_retard,
        'zone_id':        c.zone_id,
        'zone':           c.zone.nom if c.zone else None,
        'departement':    c.zone.get_departement_display() if c.zone else None,
        'point_id':       c.point_collecte_id,
        'point':          c.point_collecte.nom if c.point_collecte else None,
        'commune':        c.point_collecte.commune if c.point_collecte else None,
        'collecteur_id':  c.collecteur_id,
        'collecteur':     c.collecteur.get_full_name() if c.collecteur else None,
        'date_planifiee': str(c.date_planifiee),
        'heure_debut':    str(c.heure_debut) if c.heure_debut else None,
        'heure_fin':      str(c.heure_fin) if c.heure_fin else None,
        'nb_producteurs': c.participations.count(),
        'montant_total':  c.montant_total,
        'notes':          c.notes,
        'rapport':        c.rapport,
        'created_at':     c.created_at.isoformat(),
        'participations': [],
    }
    if with_participations:
        data['participations'] = [
            _participation_data(p)
            for p in c.participations.select_related('producteur__user').all()
        ]
    return data


# ── GET /api/admin/collectes/ ────────────────────────────────────
@extend_schema(operation_id='admin_collectes_list', tags=['Admin — Collectes'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def collectes_list(request):
    """Toutes les collectes avec filtre par statut."""
    statut = request.query_params.get('statut', '')

    qs = Collecte.objects.select_related(
        'zone', 'point_collecte', 'collecteur'
    ).prefetch_related('participations').order_by('-created_at')

    if statut:
        qs = qs.filter(statut=statut)

    return Response({
        'success': True,
        'data': [_collecte_data(c) for c in qs]
    })


# ── POST /api/admin/collectes/create/ ───────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def collecte_create(request):
    """Planifier une nouvelle collecte."""
    zone_id = request.data.get('zone_id')
    zone    = get_object_or_404(ZoneCollecte, pk=zone_id)

    point_id       = request.data.get('point_collecte_id')
    point_collecte = get_object_or_404(
        PointCollecte, pk=point_id
    ) if point_id else None

    collecteur = None
    agent_id   = request.data.get('collecteur_id') or request.data.get('agent_id')
    if agent_id:
        from apps.accounts.models import CustomUser
        collecteur = get_object_or_404(CustomUser, pk=agent_id)

    try:
        collecte = CollecteService.planifier_collecte(
            zone=zone,
            point_collecte=point_collecte,
            date_planifiee=request.data.get('date_planifiee') or request.data.get('date_prevue'),
            collecteur=collecteur,
            heure_debut=request.data.get('heure_debut') or None,
            heure_fin=request.data.get('heure_fin') or None,
            notes=request.data.get('notes', '') or request.data.get('instructions', ''),
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    for item in request.data.get('producteurs', []):
        p = Producteur.objects.filter(pk=item.get('producteur_id')).first()
        if p:
            CollecteService.inscrire_producteur(
                collecte=collecte,
                producteur=p,
                quantite_prevue=item.get('quantite_prevue', 0),
            )

    return Response(
        {'success': True, 'data': _collecte_data(collecte)},
        status=status.HTTP_201_CREATED
    )


# ── GET / PATCH /api/admin/collectes/<id>/ ──────────────────────
@extend_schema(operation_id='admin_collecte_detail', tags=['Admin — Collectes'])
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def collecte_detail(request, pk):
    collecte = get_object_or_404(
        Collecte.objects.select_related('zone', 'point_collecte', 'collecteur'),
        pk=pk,
    )

    if request.method == 'GET':
        return Response({'success': True, 'data': _collecte_data(collecte, with_participations=True)})

    # PATCH — mise à jour des champs éditables (admin override direct, sans service)
    update_fields = []

    zone_id = request.data.get('zone_id')
    if zone_id:
        collecte.zone = get_object_or_404(ZoneCollecte, pk=zone_id)
        update_fields.append('zone')

    if 'point_collecte_id' in request.data:
        point_collecte_id = request.data['point_collecte_id']
        collecte.point_collecte = (
            get_object_or_404(PointCollecte, pk=point_collecte_id)
            if point_collecte_id else None
        )
        update_fields.append('point_collecte')

    if 'collecteur_id' in request.data:
        collecteur_id = request.data['collecteur_id']
        if collecteur_id:
            from apps.accounts.models import CustomUser
            collecte.collecteur = get_object_or_404(CustomUser, pk=collecteur_id)
        else:
            collecte.collecteur = None
        update_fields.append('collecteur')

    if 'date_planifiee' in request.data and request.data['date_planifiee']:
        collecte.date_planifiee = request.data['date_planifiee']
        update_fields.append('date_planifiee')

    for field in ('heure_debut', 'heure_fin'):
        if field in request.data:
            setattr(collecte, field, request.data[field] or None)
            update_fields.append(field)

    for field in ('notes', 'rapport'):
        if field in request.data:
            setattr(collecte, field, request.data[field] or '')
            update_fields.append(field)

    STATUTS_VALIDES = [s[0] for s in Collecte.Statut.choices]
    if 'statut' in request.data and request.data['statut'] in STATUTS_VALIDES:
        collecte.statut = request.data['statut']
        update_fields.append('statut')

    if update_fields:
        collecte.save(update_fields=update_fields)
        collecte.refresh_from_db()

    return Response({'success': True, 'data': _collecte_data(collecte, with_participations=True)})


# ── PATCH /api/admin/collectes/<id>/statut/ ─────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def collecte_statut(request, pk):
    """Changer le statut d'une collecte (avec logique de service pour les transitions clés)."""
    collecte = get_object_or_404(Collecte, pk=pk)
    statut   = request.data.get('statut')

    STATUTS_VALIDES = [s[0] for s in Collecte.Statut.choices]
    if statut not in STATUTS_VALIDES:
        return Response(
            {'success': False, 'error': _("Statut invalide : planifiee|en_cours|terminee|annulee|reportee")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        if statut == Collecte.Statut.EN_COURS and collecte.statut == Collecte.Statut.PLANIFIEE:
            CollecteService.demarrer_collecte(collecte, request.user)
        elif statut == Collecte.Statut.TERMINEE and collecte.statut == Collecte.Statut.EN_COURS:
            CollecteService.terminer_collecte(
                collecte,
                rapport=request.data.get('rapport', ''),
            )
        else:
            collecte.statut = statut
            collecte.save()
    except ValueError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    collecte.refresh_from_db()
    return Response({'success': True, 'data': _collecte_data(collecte)})


# ── POST /api/admin/collectes/<id>/participations/ ──────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def collecte_add_participation(request, pk):
    """Ajouter un producteur à une collecte."""
    collecte      = get_object_or_404(Collecte, pk=pk)
    producteur_id = request.data.get('producteur_id')
    producteur    = get_object_or_404(Producteur, pk=producteur_id)

    part, created = ParticipationCollecte.objects.get_or_create(
        collecte=collecte,
        producteur=producteur,
        defaults={'statut': ParticipationCollecte.Statut.INSCRIT},
    )

    return Response(
        {
            'success': True,
            'data': {
                'id':             part.pk,
                'producteur_nom': producteur.user.get_full_name(),
                'statut':         part.statut,
                'created':        created,
            }
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


# ── PATCH /api/admin/collectes/participations/<id>/statut/ ──────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def participation_statut(request, pk):
    """Changer le statut d'une participation."""
    part   = get_object_or_404(ParticipationCollecte, pk=pk)
    statut = request.data.get('statut')

    STATUTS = [s[0] for s in ParticipationCollecte.Statut.choices]
    if statut not in STATUTS:
        return Response(
            {'success': False, 'error': f"Statut invalide : {STATUTS}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    part.statut = statut
    part.save()
    return Response({
        'success': True,
        'data': {'id': part.pk, 'statut': part.statut, 'statut_label': part.get_statut_display()}
    })


# ── DELETE /api/admin/collectes/participations/<id>/ ────────────
@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def participation_delete(request, pk):
    """Retirer un producteur d'une collecte."""
    part = get_object_or_404(ParticipationCollecte, pk=pk)
    part.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── GET /api/admin/zones/ ────────────────────────────────────────
@extend_schema(operation_id='admin_zones_list', tags=['Admin — Collectes'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def zones_list(request):
    zones = ZoneCollecte.objects.filter(is_active=True)
    data  = [
        {'id': z.pk, 'nom': z.nom, 'departement': z.departement}
        for z in zones
    ]
    return Response({'success': True, 'data': data})


@extend_schema(operation_id='admin_zone_detail', tags=['Admin — Collectes'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def zone_detail(request, pk):
    z = get_object_or_404(ZoneCollecte, pk=pk)
    return Response({
        'success': True,
        'data': {
            'id':          z.pk,
            'nom':         z.nom,
            'departement': z.departement,
            'description': z.description,
        }
    })


# ── GET /api/admin/points/ ───────────────────────────────────────
@extend_schema(operation_id='admin_points_list', tags=['Admin — Collectes'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def points_list(request):
    points = PointCollecte.objects.filter(is_active=True)
    data   = [
        {
            'id':      p.pk,
            'nom':     p.nom,
            'commune': p.commune,
            'adresse': p.adresse,
        }
        for p in points
    ]
    return Response({'success': True, 'data': data})


@extend_schema(operation_id='admin_point_detail', tags=['Admin — Collectes'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def point_detail(request, pk):
    p = get_object_or_404(PointCollecte, pk=pk)
    return Response({
        'success': True,
        'data': {
            'id':          p.pk,
            'nom':         p.nom,
            'commune':     p.commune,
            'adresse':     p.adresse,
            'responsable': p.responsable,
            'telephone':   p.telephone,
            'is_active':   p.is_active,
        }
    })
