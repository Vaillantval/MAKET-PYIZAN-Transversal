import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from apps.payments.models import Paiement
from apps.payments.serializers import (
    InitierPaiementSerializer,
    SoumettrePreuveSerializer,
    VerifierPaiementSerializer,
    PaiementSerializer,
)
from apps.payments.services.paiement_service import PaiementService
from apps.payments.services.plopplop_service import PlopplopService
from apps.orders.models import Commande
from django.utils.translation import gettext as _


# ── POST /api/payments/initier/ ─────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initier_paiement(request):
    """
    Initier un paiement pour une commande.
    Pour MonCash/NatCash : retourne redirect_url.
    Pour cash/virement  : crée l'enregistrement et retourne la référence.
    """
    serializer = InitierPaiementSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    commande      = serializer.validated_data['commande_numero']
    type_paiement = serializer.validated_data['type_paiement']
    numero_exp    = serializer.validated_data.get('numero_expediteur', '')
    notes         = serializer.validated_data.get('notes', '')

    # Vérifier que la commande appartient à l'utilisateur
    try:
        acheteur = request.user.profil_acheteur
        if commande.acheteur != acheteur:
            return Response(
                {'success': False, 'error': _("Commande non autorisée.")},
                status=status.HTTP_403_FORBIDDEN,
            )
    except Exception:
        return Response(
            {'success': False, 'error': _("Profil acheteur requis.")},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Vérifier que la commande n'est pas déjà payée
    if commande.statut_paiement == Commande.StatutPaiement.PAYE:
        return Response(
            {'success': False, 'error': _("Cette commande est déjà payée.")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    TYPE_MAP = {
        'moncash':  Paiement.TypePaiement.MONCASH,
        'natcash':  Paiement.TypePaiement.NATCASH,
        'virement': Paiement.TypePaiement.VIREMENT,
        'cash':     Paiement.TypePaiement.CASH,
    }
    type_django = TYPE_MAP.get(type_paiement, Paiement.TypePaiement.CASH)

    paiement = PaiementService.initier_paiement(
        commande=commande,
        type_paiement=type_django,
        numero_expediteur=numero_exp,
        notes=notes,
    )

    response_data = PaiementSerializer(paiement).data

    # Pour MonCash / NatCash — initier via Plopplop et retourner le redirect
    if type_paiement in ('moncash', 'natcash'):
        plopplop = PlopplopService()
        if not plopplop.is_configured():
            return Response(
                {'success': False, 'error': _('Passerelle de paiement non configurée.')},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            result = plopplop.initier_paiement(
                commande_ref=commande.numero_commande,
                montant=float(commande.total),
                payment_method=type_paiement,
            )
            response_data['redirect_url']   = result['redirect_url']
            response_data['transaction_id'] = result['transaction_id']
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f"Service de paiement indisponible : {str(e)}",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    return Response(
        {'success': True, 'data': response_data},
        status=status.HTTP_201_CREATED,
    )


# ── POST /api/payments/preuve/ ──────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def soumettre_preuve(request):
    """
    Soumettre une preuve de paiement (image JPG/PNG).
    Content-Type: multipart/form-data
    """
    serializer = SoumettrePreuveSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    paiement_id  = serializer.validated_data['paiement_id']
    preuve       = serializer.validated_data['preuve_image']
    id_trans     = serializer.validated_data.get('id_transaction', '')
    montant_recu = serializer.validated_data.get('montant_recu')

    try:
        paiement = Paiement.objects.select_related(
            'commande__acheteur__user'
        ).get(pk=paiement_id)
    except Paiement.DoesNotExist:
        return Response(
            {'success': False, 'error': _("Paiement introuvable.")},
            status=status.HTTP_404_NOT_FOUND,
        )

    if paiement.commande.acheteur.user != request.user:
        return Response(
            {'success': False, 'error': _("Paiement non autorisé.")},
            status=status.HTTP_403_FORBIDDEN,
        )

    if paiement.statut not in [Paiement.Statut.INITIE, Paiement.Statut.EN_ATTENTE]:
        return Response(
            {
                'success': False,
                'error': (
                    "Ce paiement ne peut plus recevoir de preuve "
                    f"(statut actuel : {paiement.get_statut_display()})."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    paiement = PaiementService.soumettre_preuve(
        paiement=paiement,
        preuve_image=preuve,
        id_transaction=id_trans,
        montant_recu=montant_recu,
    )

    return Response({
        'success': True,
        'data': {
            **PaiementSerializer(paiement).data,
            'message': (
                "Preuve de paiement reçue. "
                "L'admin va vérifier et confirmer votre commande."
            ),
        },
    })


# ── POST /api/payments/verifier/ ────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verifier_paiement(request):
    """Vérifier le statut d'un paiement."""
    serializer = VerifierPaiementSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    paiement_id    = serializer.validated_data.get('paiement_id')
    id_transaction = serializer.validated_data.get('id_transaction')

    if paiement_id:
        paiement = get_object_or_404(Paiement, pk=paiement_id)
    else:
        paiement = get_object_or_404(Paiement, id_transaction=id_transaction)

    if (
        paiement.commande.acheteur.user != request.user and
        not request.user.is_staff
    ):
        return Response(
            {'success': False, 'error': _("Paiement non autorisé.")},
            status=status.HTTP_403_FORBIDDEN,
        )

    response_data = dict(PaiementSerializer(paiement).data)

    return Response({'success': True, 'data': response_data})


# ── GET /api/payments/mes-paiements/ ────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mes_paiements(request):
    """Historique des paiements de l'utilisateur connecté."""
    try:
        acheteur  = request.user.profil_acheteur
        paiements = Paiement.objects.filter(
            commande__acheteur=acheteur
        ).select_related('commande').order_by('-created_at')
    except Exception:
        paiements = Paiement.objects.none()

    serializer = PaiementSerializer(paiements, many=True)
    return Response({'success': True, 'data': serializer.data})


# ── POST /api/payments/plopplop-verify/ ─────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plopplop_verify(request):
    """
    Vérifie le statut d'un paiement MonCash/NatCash via Plopplop.
    Body: { "commande_ref": _("CMD-XXXX-XXXXX") }
    Appelé depuis la page de retour (JS frontend).
    """
    commande_ref = request.data.get('commande_ref', '').strip()
    if not commande_ref:
        return Response(
            {'success': False, 'error': _('Référence de commande manquante.')},
            status=status.HTTP_400_BAD_REQUEST,
        )

    plopplop = PlopplopService()
    if not plopplop.is_configured():
        return Response(
            {'success': False, 'error': _('Passerelle de paiement non configurée.')},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        result = plopplop.verifier_paiement(commande_ref)
    except Exception as e:
        return Response(
            {'success': False, 'error': f'Erreur de vérification : {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    trans_status   = result.get('trans_status', 'no')
    id_transaction = result.get('id_transaction', commande_ref)
    methode        = result.get('method', '')
    commandes_qs   = Commande.objects.filter(numero_commande=commande_ref).select_related(
        'acheteur__user', 'producteur__user'
    )
    commandes_list = list(commandes_qs)

    if trans_status == 'ok':
        from apps.orders.services.commande_service import CommandeService

        paiements_a_confirmer = Paiement.objects.filter(
            commande__numero_commande=commande_ref,
            statut__in=[Paiement.Statut.INITIE, Paiement.Statut.EN_ATTENTE],
        ).select_related('commande')

        for paiement in paiements_a_confirmer:
            # 1. Enregistrer l'ID Plopplop avant confirmation
            paiement.id_transaction = id_transaction
            paiement.save(update_fields=['id_transaction'])

            # 2. Confirmer le paiement → statut_paiement = PAYE
            #    Déclenche le signal pre_save → task_paiement_confirme.delay()
            PaiementService.confirmer_paiement(
                paiement,
                verifie_par=None,
                note_verification=f"Confirmé automatiquement via Plopplop — {id_transaction}",
            )

            # 3. Confirmer la commande → statut = CONFIRMEE, stock débité
            try:
                CommandeService.confirmer_commande(paiement.commande)
            except Exception as e:
                logger.warning(
                    "plopplop_verify: confirmer_commande échoué pour %s : %s",
                    paiement.commande.numero_commande, e,
                )

        return Response({
            'success':     True,
            'confirme':    True,
            'montant':     result.get('montant', ''),
            'method':      methode,
            'transaction': id_transaction,
            'commandes':   list(commandes_qs.values('numero_commande', 'total')),
        })

    # Paiement non confirmé — notifier l'acheteur et les admins (async)
    if commandes_list:
        try:
            acheteur_user = commandes_list[0].acheteur.user
            from apps.emails.tasks import task_paiement_echec
            task_paiement_echec.delay(
                commande_ids=[c.pk for c in commandes_list],
                methode=commandes_list[0].methode_paiement,
                prenom=acheteur_user.first_name,
                email_dest=acheteur_user.email,
                acheteur_id=acheteur_user.pk,
                raison=f"Plopplop trans_status={trans_status!r} — ref={commande_ref}",
            )
        except Exception:
            logger.exception("Erreur queuing notification paiement non confirme — ref=%s", commande_ref)

    return Response({
        'success':  True,
        'confirme': False,
        'statut':   trans_status,
    })
