from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from apps.accounts.permissions import IsSuperAdmin
from apps.payments.models import Paiement
from apps.payments.serializers import PaiementSerializer
from apps.payments.services.paiement_service import PaiementService
from django.utils.translation import gettext as _


# ── GET /api/admin/paiements/ ────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def paiements_list(request):
    """Tous les paiements avec filtre par statut."""
    statut = request.query_params.get('statut', '')

    qs = Paiement.objects.select_related(
        'commande__acheteur__user'
    ).order_by('-created_at')

    if statut:
        qs = qs.filter(statut=statut)

    serializer = PaiementSerializer(qs, many=True)
    return Response({'success': True, 'data': serializer.data})


# ── PATCH /api/admin/paiements/<id>/statut/ ─────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def paiement_statut(request, pk):
    """
    Mettre à jour le statut d'un paiement.
    Body : { "statut": "verifie"|"confirme"|"echoue"|"annule", "note": "...", "montant_recu": ... }
    """
    paiement = get_object_or_404(Paiement, pk=pk)
    nouveau_statut = request.data.get('statut')
    note           = request.data.get('note', '')
    montant_recu   = request.data.get('montant_recu')

    STATUTS_VALIDES = ['verifie', 'confirme', 'echoue', 'annule']
    if nouveau_statut not in STATUTS_VALIDES:
        return Response(
            {'success': False, 'error': _("Statut invalide. Valeurs acceptées : verifie, confirme, echoue, annule.")},
            status=status.HTTP_400_BAD_REQUEST
        )

    if nouveau_statut == 'confirme':
        paiement = PaiementService.confirmer_paiement(
            paiement=paiement,
            verifie_par=request.user,
            note_verification=note,
        )
    elif nouveau_statut == 'echoue':
        paiement = PaiementService.rejeter_paiement(
            paiement=paiement,
            verifie_par=request.user,
            motif=note,
        )
    elif nouveau_statut == 'annule':
        with transaction.atomic():
            paiement.statut             = Paiement.Statut.ANNULE
            paiement.verifie_par        = request.user
            paiement.date_verification  = timezone.now()
            paiement.note_verification  = note
            paiement.save()
            paiement.commande.statut_paiement = 'non_paye'
            paiement.commande.save(update_fields=['statut_paiement'])
    else:  # 'verifie'
        paiement.statut            = Paiement.Statut.VERIFIE
        paiement.verifie_par       = request.user
        paiement.date_verification = timezone.now()
        paiement.note_verification = note
        paiement.save()

    if montant_recu:
        try:
            paiement.montant_recu = float(montant_recu)
            paiement.save(update_fields=['montant_recu'])
        except (ValueError, TypeError):
            pass

    return Response({
        'success': True,
        'data': PaiementSerializer(paiement).data
    })
