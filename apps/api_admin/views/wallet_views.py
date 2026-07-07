"""Endpoints superadmin du wallet — miroir des actions de l'admin Django."""

from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.permissions import IsSuperAdmin
from apps.wallet.models import (
    BonCadeau,
    Wallet,
    WalletRecharge,
    WalletRetrait,
    WalletTransaction,
)
from apps.wallet.services import WalletError, WalletService


def _url(request, fichier):
    return request.build_absolute_uri(fichier.url) if fichier else None


def _user_info(user):
    return {
        'user_id':  user.pk,
        'username': user.username,
        'nom':      user.get_full_name() or user.username,
        'email':    user.email,
        'role':     user.role,
        'role_label': user.get_role_display(),
    }


def _tx_dict(tx):
    return {
        'id':              tx.pk,
        'type':            tx.type,
        'type_label':      tx.get_type_display(),
        'montant':         str(tx.montant),
        'solde_apres':     str(tx.solde_apres),
        'commande_numero': tx.commande.numero_commande if tx.commande else None,
        'description':     tx.description,
        'reference':       tx.reference,
        'created_at':      tx.created_at,
        **_user_info(tx.wallet.user),
        'wallet_id':       tx.wallet_id,
    }


# ── GET /api/admin/wallet/stats/ ─────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def wallet_stats(request):
    """Vue d'ensemble : encours, éléments à traiter."""
    aggregats = Wallet.objects.aggregate(
        total_soldes=Sum('solde'),
        nb_wallets=Count('id'),
        nb_actifs=Count('id', filter=Q(is_active=True)),
    )
    return Response({'success': True, 'data': {
        'total_soldes': str(aggregats['total_soldes'] or 0),
        'nb_wallets':   aggregats['nb_wallets'],
        'nb_actifs':    aggregats['nb_actifs'],
        'recharges_a_valider': WalletRecharge.objects.filter(
            statut=WalletRecharge.Statut.PREUVE_SOUMISE).count(),
        'retraits_a_traiter': WalletRetrait.objects.filter(
            statut=WalletRetrait.Statut.DEMANDE).count(),
        'retraits_en_attente_htg': str(WalletRetrait.objects.filter(
            statut=WalletRetrait.Statut.DEMANDE,
        ).aggregate(s=Sum('montant'))['s'] or 0),
        'bons_actifs': BonCadeau.objects.filter(
            statut=BonCadeau.Statut.ACTIF).count(),
    }})


# ── GET /api/admin/wallet/wallets/ ───────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def wallets_list(request):
    """Liste des portefeuilles (recherche username/email/nom, filtre actif)."""
    qs = Wallet.objects.select_related('user').order_by('-updated_at')

    recherche = request.query_params.get('search', '').strip()
    if recherche:
        qs = qs.filter(
            Q(user__username__icontains=recherche)
            | Q(user__email__icontains=recherche)
            | Q(user__first_name__icontains=recherche)
            | Q(user__last_name__icontains=recherche)
        )
    actif = request.query_params.get('actif', '')
    if actif in ('true', 'false'):
        qs = qs.filter(is_active=(actif == 'true'))

    data = [{
        'id':         w.pk,
        'solde':      str(w.solde),
        'is_active':  w.is_active,
        'updated_at': w.updated_at,
        **_user_info(w.user),
    } for w in qs[:300]]
    return Response({'success': True, 'data': data})


# ── POST /api/admin/wallet/wallets/<pk>/toggle/ ──────────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def wallet_toggle(request, pk):
    """Activer/désactiver un portefeuille (bloque paiements, recharges, retraits)."""
    wallet = get_object_or_404(Wallet, pk=pk)
    wallet.is_active = not wallet.is_active
    wallet.save(update_fields=['is_active', 'updated_at'])
    return Response({'success': True, 'data': {
        'id': wallet.pk, 'is_active': wallet.is_active,
    }})


# ── POST /api/admin/wallet/ajustement/ ───────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def wallet_ajustement(request):
    """
    Ajustement manuel du solde (montant signé : positif = crédit,
    négatif = débit, solde négatif autorisé). Passe par le service —
    jamais d'écriture directe du solde.
    """
    wallet = get_object_or_404(Wallet, pk=request.data.get('wallet_id'))
    try:
        montant = Decimal(str(request.data.get('montant', '')).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return Response(
            {'success': False, 'error': _("Montant invalide.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    description = (request.data.get('description') or '').strip() \
        or f"Ajustement manuel ({request.user.username})"

    try:
        if montant > 0:
            tx = WalletService.crediter(
                wallet, montant,
                type_tx=WalletTransaction.Type.AJUSTEMENT,
                description=description,
            )
        else:
            tx = WalletService._appliquer(
                wallet, montant, WalletTransaction.Type.AJUSTEMENT,
                description=description, autoriser_negatif=True,
            )
    except WalletError as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({'success': True, 'data': {
        'transaction_id': tx.pk, 'solde': str(tx.solde_apres),
    }})


# ── GET /api/admin/wallet/transactions/ ──────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def wallet_transactions(request):
    """Ledger global (filtres : type, wallet_id, recherche user). 300 dernières."""
    qs = WalletTransaction.objects.select_related(
        'wallet__user', 'commande',
    ).order_by('-created_at')

    type_tx = request.query_params.get('type', '')
    if type_tx:
        qs = qs.filter(type=type_tx)
    wallet_id = request.query_params.get('wallet_id', '')
    if wallet_id:
        qs = qs.filter(wallet_id=wallet_id)
    recherche = request.query_params.get('search', '').strip()
    if recherche:
        qs = qs.filter(
            Q(wallet__user__username__icontains=recherche)
            | Q(wallet__user__email__icontains=recherche)
            | Q(description__icontains=recherche)
            | Q(reference__icontains=recherche)
        )

    return Response({'success': True, 'data': [_tx_dict(t) for t in qs[:300]]})


# ── Recharges ────────────────────────────────────────────────────

def _recharge_dict(request, r):
    return {
        'id':            r.pk,
        'montant':       str(r.montant),
        'methode':       r.methode,
        'methode_label': r.get_methode_display(),
        'statut':        r.statut,
        'statut_label':  r.get_statut_display(),
        'reference':     r.reference_plopplop,
        'preuve_url':    _url(request, r.preuve_image),
        'created_at':    r.created_at,
        **_user_info(r.wallet.user),
    }


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def recharges_list(request):
    """Toutes les recharges (filtre statut/méthode)."""
    qs = WalletRecharge.objects.select_related('wallet__user').order_by('-created_at')
    statut = request.query_params.get('statut', '')
    if statut:
        qs = qs.filter(statut=statut)
    methode = request.query_params.get('methode', '')
    if methode:
        qs = qs.filter(methode=methode)
    return Response({'success': True,
                     'data': [_recharge_dict(request, r) for r in qs[:300]]})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def recharge_valider(request, pk):
    """Valide la preuve d'une recharge hors ligne et crédite le wallet."""
    recharge = get_object_or_404(WalletRecharge, pk=pk)
    if recharge.methode != WalletRecharge.Methode.HORS_LIGNE:
        return Response(
            {'success': False,
             'error': _("Seules les recharges hors ligne se valident manuellement.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if recharge.statut not in (
        WalletRecharge.Statut.PREUVE_SOUMISE, WalletRecharge.Statut.EN_ATTENTE,
    ):
        return Response(
            {'success': False, 'error': _("Cette recharge est déjà traitée.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        tx = WalletService.completer_recharge(recharge, reference=f"hors-ligne-{recharge.pk}")
    except WalletError as e:
        return Response({'success': False, 'error': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    if tx:
        try:
            from apps.wallet.tasks import task_notifier_recharge_validee
            task_notifier_recharge_validee.delay(recharge.pk)
        except Exception:
            pass
    recharge.refresh_from_db()
    return Response({'success': True, 'data': _recharge_dict(request, recharge)})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def recharge_rejeter(request, pk):
    """Rejette une recharge hors ligne (preuve invalide)."""
    recharge = get_object_or_404(WalletRecharge, pk=pk)
    if recharge.statut not in (
        WalletRecharge.Statut.PREUVE_SOUMISE, WalletRecharge.Statut.EN_ATTENTE,
    ):
        return Response(
            {'success': False, 'error': _("Cette recharge est déjà traitée.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    recharge.statut = WalletRecharge.Statut.REJETEE
    recharge.save(update_fields=['statut', 'updated_at'])
    try:
        from apps.wallet.tasks import task_notifier_recharge_rejetee
        task_notifier_recharge_rejetee.delay(recharge.pk)
    except Exception:
        pass
    return Response({'success': True, 'data': _recharge_dict(request, recharge)})


# ── Retraits ─────────────────────────────────────────────────────

def _retrait_dict(request, r):
    return {
        'id':              r.pk,
        'montant':         str(r.montant),
        'canal':           r.canal,
        'canal_label':     r.get_canal_display(),
        'numero_telephone': r.numero_telephone,
        'statut':          r.statut,
        'statut_label':    r.get_statut_display(),
        'note_admin':      r.note_admin,
        'preuve_url':      _url(request, r.preuve_transfert),
        'traite_par':      r.traite_par.username if r.traite_par else None,
        'date_traitement': r.date_traitement,
        'created_at':      r.created_at,
        **_user_info(r.wallet.user),
    }


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def retraits_list(request):
    """Toutes les demandes de retrait (filtre statut)."""
    qs = WalletRetrait.objects.select_related(
        'wallet__user', 'traite_par',
    ).order_by('-created_at')
    statut = request.query_params.get('statut', '')
    if statut:
        qs = qs.filter(statut=statut)
    return Response({'success': True,
                     'data': [_retrait_dict(request, r) for r in qs[:300]]})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def retrait_payer(request, pk):
    """
    Marque un retrait payé après le transfert MonCash/NatCash manuel.
    multipart : preuve_transfert (image, optionnelle) + note (optionnelle).
    """
    retrait = get_object_or_404(WalletRetrait, pk=pk)
    preuve = request.FILES.get('preuve_transfert')
    note = (request.data.get('note') or '').strip()

    if not WalletService.payer_retrait(
        retrait, traite_par=request.user, preuve_transfert=preuve, note=note,
    ):
        return Response(
            {'success': False, 'error': _("Ce retrait est déjà traité.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        from apps.wallet.tasks import task_notifier_retrait_paye
        task_notifier_retrait_paye.delay(retrait.pk)
    except Exception:
        pass
    retrait.refresh_from_db()
    return Response({'success': True, 'data': _retrait_dict(request, retrait)})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def retrait_rejeter(request, pk):
    """Rejette un retrait et re-crédite le wallet. Body : {motif}."""
    retrait = get_object_or_404(WalletRetrait, pk=pk)
    motif = (request.data.get('motif') or '').strip()
    try:
        traite = WalletService.rejeter_retrait(retrait, traite_par=request.user, motif=motif)
    except WalletError as e:
        return Response({'success': False, 'error': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    if not traite:
        return Response(
            {'success': False, 'error': _("Ce retrait est déjà traité.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        from apps.wallet.tasks import task_notifier_retrait_rejete
        task_notifier_retrait_rejete.delay(retrait.pk)
    except Exception:
        pass
    retrait.refresh_from_db()
    return Response({'success': True, 'data': _retrait_dict(request, retrait)})


# ── Bons cadeaux ─────────────────────────────────────────────────

def _bon_dict(b):
    return {
        'id':                 b.pk,
        'code':               b.code,
        'montant':            str(b.montant),
        'statut':             b.statut,
        'statut_label':       b.get_statut_display(),
        'achete_par':         b.achete_par.username if b.achete_par else None,
        'email_destinataire': b.email_destinataire,
        'encaisse_par':       b.encaisse_par.username if b.encaisse_par else None,
        'date_encaissement':  b.date_encaissement,
        'date_expiration':    b.date_expiration,
        'created_at':         b.created_at,
    }


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def bons_list(request):
    """Tous les bons cadeaux (filtre statut, recherche code/acheteur)."""
    qs = BonCadeau.objects.select_related('achete_par', 'encaisse_par').order_by('-created_at')
    statut = request.query_params.get('statut', '')
    if statut:
        qs = qs.filter(statut=statut)
    recherche = request.query_params.get('search', '').strip()
    if recherche:
        qs = qs.filter(
            Q(code__icontains=recherche)
            | Q(achete_par__username__icontains=recherche)
            | Q(email_destinataire__icontains=recherche)
        )
    return Response({'success': True, 'data': [_bon_dict(b) for b in qs[:300]]})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def bon_annuler(request, pk):
    """Annule un bon non utilisé (attente de paiement ou actif)."""
    bon = get_object_or_404(BonCadeau, pk=pk)
    if bon.statut not in (BonCadeau.Statut.ATTENTE_PAIEMENT, BonCadeau.Statut.ACTIF):
        return Response(
            {'success': False,
             'error': _("Seuls les bons en attente ou actifs peuvent être annulés.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    bon.statut = BonCadeau.Statut.ANNULE
    bon.save(update_fields=['statut', 'updated_at'])
    return Response({'success': True, 'data': _bon_dict(bon)})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def bon_renvoyer_email(request, pk):
    """Renvoie l'email du code (bons actifs uniquement)."""
    bon = get_object_or_404(BonCadeau, pk=pk)
    if bon.statut != BonCadeau.Statut.ACTIF:
        return Response(
            {'success': False, 'error': _("Ce bon n'est pas actif.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        from apps.wallet.tasks import task_envoyer_bon_cadeau
        task_envoyer_bon_cadeau.delay(bon.pk)
    except Exception as e:
        return Response({'success': False, 'error': str(e)},
                        status=status.HTTP_502_BAD_GATEWAY)
    return Response({'success': True, 'data': {'message': _("Email planifié.")}})
