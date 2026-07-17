"""Endpoints superadmin du point de vente — supervision sessions/écarts/conflits."""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsSuperAdmin
from apps.pos.models import POSDevice, POSSale, POSSession
from apps.pos.services import POSService


def _montant(v) -> str:
    """Montant agrégé normalisé à 2 décimales (Sum SQLite ne quantize pas)."""
    return str(Decimal(v or 0).quantize(Decimal('0.01')))


def _operateur_info(user):
    return {
        'operateur_id':  user.pk,
        'operateur':     user.get_full_name() or user.username,
        'operateur_username': user.username,
    }


def _bornes_periode(request):
    """?date_debut=YYYY-MM-DD & ?date_fin=YYYY-MM-DD (défaut : 30 derniers jours)."""
    fin = parse_date(request.query_params.get('date_fin', '') or '') or timezone.localdate()
    debut = parse_date(request.query_params.get('date_debut', '') or '') or (
        fin - timezone.timedelta(days=30)
    )
    return debut, fin


# ── GET /api/admin/pos/stats/ ────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def pos_stats(request):
    """Vue d'ensemble : activité du jour, sessions ouvertes, à arbitrer."""
    aujourd_hui = timezone.localdate()
    ventes_jour = POSSale.objects.filter(
        statut=POSSale.Statut.CONFIRMEE, vendue_le__date=aujourd_hui,
    ).aggregate(nb=Count('id'), ca=Sum('montant_total'))

    ecart_30j = POSSession.objects.filter(
        statut=POSSession.Statut.FERMEE,
        fermee_le__date__gte=aujourd_hui - timezone.timedelta(days=30),
    ).aggregate(s=Sum('ecart_caisse'))['s'] or Decimal('0')

    return Response({'success': True, 'data': {
        'sessions_ouvertes':  POSSession.objects.filter(
            statut=POSSession.Statut.OUVERTE).count(),
        'ventes_jour':        ventes_jour['nb'] or 0,
        'ca_jour_htg':        _montant(ventes_jour['ca']),
        'conflits_a_arbitrer': POSSale.objects.filter(
            stock_conflict=True, statut=POSSale.Statut.CONFIRMEE).count(),
        'terminaux_actifs':   POSDevice.objects.filter(is_active=True).count(),
        'ecart_cumule_30j_htg': _montant(ecart_30j),
    }})


# ── GET /api/admin/pos/sessions/ ─────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def pos_sessions_list(request):
    """
    Sessions (shifts) avec totaux — filtres : ?date_debut/?date_fin (sur
    l'ouverture), ?operateur_id=, ?statut=ouverte|fermee.
    """
    debut, fin = _bornes_periode(request)
    qs = (
        POSSession.objects.select_related('operateur', 'device')
        .filter(ouverte_le__date__gte=debut, ouverte_le__date__lte=fin)
        .order_by('-ouverte_le')
    )
    statut = request.query_params.get('statut', '')
    if statut in (POSSession.Statut.OUVERTE, POSSession.Statut.FERMEE):
        qs = qs.filter(statut=statut)
    operateur_id = request.query_params.get('operateur_id', '')
    if operateur_id.isdigit():
        qs = qs.filter(operateur_id=operateur_id)

    data = []
    for s in qs[:100]:
        totaux = POSService.totaux_session(s)
        data.append({
            'id':              s.pk,
            **_operateur_info(s.operateur),
            'device':          s.device.nom,
            'device_id':       s.device_id,
            'commune':         s.device.commune,
            'fonds_ouverture': str(s.fonds_ouverture),
            'fonds_fermeture': str(s.fonds_fermeture) if s.fonds_fermeture is not None else None,
            'ecart_caisse':    str(s.ecart_caisse) if s.ecart_caisse is not None else None,
            'statut':          s.statut,
            'ouverte_le':      s.ouverte_le,
            'fermee_le':       s.fermee_le,
            'nb_ventes':       totaux['nb_ventes'],
            'total_ventes':    totaux['total_ventes'],
            'total_cash':      totaux['total_cash'],
        })
    return Response({'success': True, 'data': data})


# ── GET /api/admin/pos/ecarts/ ───────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def pos_ecarts_par_agent(request):
    """
    Écarts de caisse consolidés PAR AGENT sur la période (sessions fermées) —
    l'indicateur anti-coulage : un agent qui « perd » un peu chaque jour se
    voit ici, pas session par session.
    """
    debut, fin = _bornes_periode(request)
    sessions = POSSession.objects.filter(
        statut=POSSession.Statut.FERMEE,
        fermee_le__date__gte=debut, fermee_le__date__lte=fin,
    )
    agregats = (
        sessions.values('operateur_id', 'operateur__username',
                        'operateur__first_name', 'operateur__last_name')
        .annotate(
            nb_sessions=Count('id'),
            ecart_total=Sum('ecart_caisse'),
            nb_sessions_avec_ecart=Count('id', filter=~Q(ecart_caisse=0)),
        )
        .order_by('ecart_total')
    )
    data = [{
        'operateur_id':   a['operateur_id'],
        'operateur':      (f"{a['operateur__first_name']} {a['operateur__last_name']}".strip()
                           or a['operateur__username']),
        'operateur_username': a['operateur__username'],
        'nb_sessions':    a['nb_sessions'],
        'nb_sessions_avec_ecart': a['nb_sessions_avec_ecart'],
        'ecart_total':    _montant(a['ecart_total']),
    } for a in agregats]
    return Response({'success': True, 'data': {
        'date_debut': debut, 'date_fin': fin, 'agents': data,
    }})


# ── GET /api/admin/pos/conflits/ ─────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def pos_conflits_list(request):
    """Ventes confirmées en conflit de stock, à arbitrer."""
    ventes = (
        POSSale.objects.filter(stock_conflict=True, statut=POSSale.Statut.CONFIRMEE)
        .select_related('operateur', 'session__device')
        .prefetch_related('items__produit')
        .order_by('-vendue_le')[:100]
    )
    data = [{
        'id':            v.pk,
        'numero_vente':  v.numero_vente,
        **_operateur_info(v.operateur),
        'device':        v.session.device.nom,
        'montant_total': str(v.montant_total),
        'methode_paiement': v.methode_paiement,
        'vendue_le':     v.vendue_le,
        'items':         [f"{i.produit.nom} × {i.quantite}" for i in v.items.all()],
    } for v in ventes]
    return Response({'success': True, 'data': data})


# ── POST /api/admin/pos/ventes/<pk>/lever-conflit/ ───────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def pos_vente_lever_conflit(request, pk):
    vente = get_object_or_404(POSSale, pk=pk)
    if not vente.stock_conflict:
        return Response(
            {'success': False, 'error': _("Cette vente n'est pas en conflit.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    POSSale.objects.filter(pk=vente.pk).update(stock_conflict=False)
    return Response({'success': True, 'data': {'id': vente.pk, 'stock_conflict': False}})


# ── POST /api/admin/pos/ventes/<pk>/annuler/ ─────────────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def pos_vente_annuler(request, pk):
    """Annule la vente : re-crédit des lots + remboursement wallet (signal)."""
    vente = get_object_or_404(POSSale, pk=pk)
    if not POSService.annuler_vente(vente):
        return Response(
            {'success': False, 'error': _("Cette vente est déjà annulée.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({'success': True, 'data': {'id': vente.pk, 'statut': vente.statut}})
