import hashlib
import logging

from django.db.models import Max
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.pos.models import POSSale, POSSession
from apps.pos.permissions import IsPOSOperator
from apps.pos.serializers import (
    POSSaleSerializer,
    POSSessionSerializer,
    SessionFermerSerializer,
    SessionOuvrirSerializer,
    SyncSerializer,
    VenteInputSerializer,
)
from apps.pos.services import POSError, POSService

logger = logging.getLogger(__name__)


def _erreurs(serializer):
    return Response(
        {'success': False, 'error': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _erreur(message, code=None, http_status=status.HTTP_400_BAD_REQUEST):
    payload = {'success': False, 'error': str(message)}
    if code:
        payload['code'] = code
    return Response(payload, status=http_status)


def _session_ouverte_ou_erreur(request):
    """Retourne (session, None) ou (None, Response 400)."""
    session = POSService.session_ouverte(request.user)
    if session is None:
        return None, _erreur(_("Aucune session de caisse ouverte. Ouvrez une session d'abord."))
    return session, None


# ── POST /api/pos/session/ouvrir/ ───────────────────────────────

@extend_schema(tags=['POS'], request=SessionOuvrirSerializer,
               summary='Ouvrir une session de caisse')
@api_view(['POST'])
@permission_classes([IsPOSOperator])
def session_ouvrir(request):
    serializer = SessionOuvrirSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)
    try:
        session = POSService.ouvrir_session(
            request.user,
            serializer.validated_data['device_uid'],
            serializer.validated_data['fonds_ouverture'],
        )
    except POSError as e:
        return _erreur(e)
    return Response(
        {'success': True, 'data': POSSessionSerializer(session).data},
        status=status.HTTP_201_CREATED,
    )


# ── POST /api/pos/session/fermer/ ───────────────────────────────

@extend_schema(tags=['POS'], request=SessionFermerSerializer,
               summary='Fermer la session de caisse (écart calculé)')
@api_view(['POST'])
@permission_classes([IsPOSOperator])
def session_fermer(request):
    serializer = SessionFermerSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)
    try:
        session, recap = POSService.fermer_session(
            request.user, serializer.validated_data['fonds_fermeture'],
        )
    except POSError as e:
        return _erreur(e)
    return Response({
        'success': True,
        'data': {
            'session': POSSessionSerializer(session).data,
            'recap':   recap,
        },
    })


# ── POST /api/pos/vente/ ────────────────────────────────────────

@extend_schema(tags=['POS'], request=VenteInputSerializer,
               summary='Enregistrer une vente au comptoir (online)',
               description='Idempotent : une idempotency_key déjà connue '
                           'renvoie la vente existante sans doublon. '
                           'Le paiement wallet exige un client identifié.')
@api_view(['POST'])
@permission_classes([IsPOSOperator])
def vente_creer(request):
    from apps.wallet.services import SoldeInsuffisant, WalletError

    serializer = VenteInputSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    session, erreur = _session_ouverte_ou_erreur(request)
    if erreur:
        return erreur

    try:
        vente, created = POSService.enregistrer_vente(
            request.user, session, serializer.validated_data,
        )
    except POSError as e:
        return _erreur(e)
    except SoldeInsuffisant as e:
        return _erreur(e, code='SOLDE_INSUFFISANT')
    except WalletError as e:
        return _erreur(e)

    return Response(
        {
            'success': True,
            'data': {
                'vente':   POSSaleSerializer(vente).data,
                'created': created,
            },
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# ── POST /api/pos/sync/ ─────────────────────────────────────────

@extend_schema(tags=['POS'], request=SyncSerializer,
               summary='Synchroniser un batch de ventes offline',
               description='Chaque vente est traitée indépendamment. Les '
                           'ventes wallet sont rejetées (paiement wallet '
                           'online uniquement). Un stock insuffisant crée '
                           'la vente avec stock_conflict=True. Une vente '
                           'synchronisée après la clôture est rattachée à la '
                           'session qui couvrait son vendue_le et l\'écart '
                           'de caisse est recalculé.')
@api_view(['POST'])
@permission_classes([IsPOSOperator])
def sync_ventes(request):
    serializer = SyncSerializer(data=request.data)
    if not serializer.is_valid():
        return _erreurs(serializer)

    resultats = POSService.sync_ventes(
        request.user, serializer.validated_data['ventes'],
    )
    return Response({'success': True, 'data': {'resultats': resultats}})


# ── GET /api/pos/catalogue/ ─────────────────────────────────────

@extend_schema(tags=['POS'], summary='Catalogue allégé pour cache local (ETag)',
               description='Produits actifs, prix détail/gros et lots '
                           'disponibles. Renvoyer le header If-None-Match '
                           'avec le dernier ETag reçu : 304 si inchangé.')
@api_view(['GET'])
@permission_classes([IsPOSOperator])
def catalogue(request):
    from apps.catalog.models import Produit
    from apps.stock.models import Lot

    produits = (
        Produit.objects.filter(statut=Produit.Statut.ACTIF, is_active=True)
        .select_related('categorie')
        .order_by('nom')
    )

    empreinte_produits = produits.aggregate(m=Max('updated_at'), n=Max('id'))
    empreinte_lots = Lot.objects.filter(
        statut=Lot.Statut.DISPONIBLE,
    ).aggregate(m=Max('updated_at'), n=Max('id'))
    etag = '"{}"'.format(hashlib.md5(
        f"{empreinte_produits['m']}-{empreinte_produits['n']}-"
        f"{empreinte_lots['m']}-{empreinte_lots['n']}-{produits.count()}".encode()
    ).hexdigest())

    if request.headers.get('If-None-Match') == etag:
        return Response(status=status.HTTP_304_NOT_MODIFIED, headers={'ETag': etag})

    lots_par_produit = {}
    for lot in Lot.objects.filter(
        produit__in=produits, statut=Lot.Statut.DISPONIBLE,
    ).order_by('created_at').values(
        'id', 'produit_id', 'numero_lot', 'code_barres', 'quantite_actuelle',
    ):
        lots_par_produit.setdefault(lot['produit_id'], []).append({
            'id':                lot['id'],
            'numero_lot':        lot['numero_lot'],
            'code_barres':       lot['code_barres'],
            'quantite_actuelle': lot['quantite_actuelle'],
        })

    data = [
        {
            'id':               p.id,
            'nom':              p.nom,
            'categorie':        {'id': p.categorie_id, 'nom': p.categorie.nom},
            'prix_unitaire':    str(p.prix_unitaire),
            'prix_gros':        str(p.prix_gros) if p.prix_gros is not None else None,
            'unite_vente':      p.unite_vente,
            'stock_disponible': p.stock_disponible,
            'lots':             lots_par_produit.get(p.id, []),
        }
        for p in produits
    ]
    return Response({'success': True, 'data': data}, headers={'ETag': etag})


# ── GET /api/pos/rapports/ ──────────────────────────────────────

@extend_schema(tags=['POS'], summary='Rapports de vente POS',
               description='Filtres : ?session_id= ou ?date=YYYY-MM-DD ou '
                           '?device_id=. Un opérateur ne voit que ses '
                           'propres ventes, le superadmin voit tout.')
@api_view(['GET'])
@permission_classes([IsPOSOperator])
def rapports(request):
    ventes = POSSale.objects.all()

    est_superadmin = (
        request.user.is_superuser or request.user.is_staff
        or getattr(request.user, 'role', '') == 'superadmin'
    )
    if not est_superadmin:
        ventes = ventes.filter(operateur=request.user)

    session_id = request.query_params.get('session_id')
    date = request.query_params.get('date')
    device_id = request.query_params.get('device_id')

    if session_id:
        if not session_id.isdigit():
            return _erreur(_("session_id invalide."))
        session = POSSession.objects.filter(pk=session_id).first()
        if session is None or (not est_superadmin and session.operateur_id != request.user.id):
            return _erreur(_("Session introuvable."), http_status=status.HTTP_404_NOT_FOUND)
        ventes = ventes.filter(session=session)
    if date:
        from django.utils.dateparse import parse_date
        jour = parse_date(date)
        if jour is None:
            return _erreur(_("Format de date invalide (attendu : YYYY-MM-DD)."))
        ventes = ventes.filter(vendue_le__date=jour)
    if device_id:
        if not device_id.isdigit():
            return _erreur(_("device_id invalide."))
        ventes = ventes.filter(session__device_id=device_id)

    return Response({'success': True, 'data': POSService.rapport(ventes)})
