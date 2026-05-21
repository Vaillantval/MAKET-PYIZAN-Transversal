from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from apps.accounts.permissions import IsSuperAdmin
from apps.accounts.models import CustomUser
from apps.accounts.serializers import RegisterSerializer, UserProfileSerializer
from django.utils.translation import gettext as _


# ── GET /api/admin/users/ ────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def users_list(request):
    """Liste des utilisateurs avec filtres."""
    search    = request.query_params.get('search', '')
    role      = request.query_params.get('role', '')
    is_active = request.query_params.get('is_active', '')

    qs = CustomUser.objects.order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)      |
            Q(username__icontains=search)   |
            Q(telephone__icontains=search)
        )
    if role:
        qs = qs.filter(role=role)
    if is_active:
        qs = qs.filter(is_active=(is_active.lower() == 'true'))

    data = UserProfileSerializer(
        qs, many=True, context={'request': request}
    ).data
    return Response({'success': True, 'data': data})


# ── POST /api/admin/users/create/ ───────────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def user_create(request):
    """Créer un utilisateur."""
    data = request.data.copy()
    # Dupliquer password2 si absent (l'admin n'a qu'un champ de confirmation)
    if 'password2' not in data and 'password' in data:
        data['password2'] = data['password']

    serializer = RegisterSerializer(data=data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    user = serializer.save()

    # Appliquer is_active si fourni (RegisterSerializer ne le gère pas)
    is_active = request.data.get('is_active')
    if is_active is not None:
        user.is_active = bool(is_active)
        user.save(update_fields=['is_active'])

    return Response(
        {
            'success': True,
            'data': UserProfileSerializer(
                user, context={'request': request}
            ).data
        },
        status=status.HTTP_201_CREATED
    )


# ── GET/PATCH /api/admin/users/<id>/detail/ ─────────────────────
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def user_detail(request, pk):
    """Détail ou mise à jour d'un utilisateur."""
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': UserProfileSerializer(
                user, context={'request': request}
            ).data
        })

    serializer = UserProfileSerializer(
        user, data=request.data,
        partial=True,
        context={'request': request}
    )
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer.save()
    return Response({'success': True, 'data': serializer.data})


# ── PATCH /api/admin/users/<id>/toggle/ ─────────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def user_toggle(request, pk):
    """Activer ou désactiver un utilisateur."""
    user           = get_object_or_404(CustomUser, pk=pk)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return Response({
        'success': True,
        'data': {
            'id':        user.pk,
            'is_active': user.is_active,
            'message':   f"Compte {'activé' if user.is_active else 'désactivé'}."
        }
    })


# ── GET /api/admin/users/carte/ ─────────────────────────────────
import json
import os
import random

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication


@extend_schema(tags=['Admin — Carte'])
@api_view(['GET'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsSuperAdmin])
def users_carte(request):
    """
    Données des utilisateurs pour la carte interactive.
    Retourne lat/lng déduites de la commune ou du département.
    Filtres : ?role=&statut=&date_debut=&date_fin=
    """
    role       = request.query_params.get('role', '')
    statut     = request.query_params.get('statut', '')
    date_debut = request.query_params.get('date_debut', '')
    date_fin   = request.query_params.get('date_fin', '')

    # Charger les coordonnées géographiques
    geo_path = os.path.join(
        os.path.dirname(__file__),
        '../../../apps/geo/data/haiti_geo.json'
    )
    with open(geo_path, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)

    # Construire des index de lookup lat/lng
    dept_coords    = {}
    commune_coords = {}
    for dept in geo_data['departements']:
        dept_coords[dept['nom'].lower()] = {'lat': dept['lat'], 'lng': dept['lng']}
        dept_coords[dept['slug']]        = {'lat': dept['lat'], 'lng': dept['lng']}
        for arrond in dept['arrondissements']:
            for commune in arrond['communes']:
                commune_coords[commune['nom'].lower()] = {
                    'lat': commune['lat'],
                    'lng': commune['lng'],
                    'departement': dept['nom'],
                }

    def get_coords(user):
        # 1. Adresse enregistrée avec commune
        try:
            adresse = user.adresses.filter(is_default=True).first() or user.adresses.first()
            if adresse and adresse.commune:
                coords = commune_coords.get(adresse.commune.lower())
                if coords:
                    return (
                        coords['lat'] + random.uniform(-0.02, 0.02),
                        coords['lng'] + random.uniform(-0.02, 0.02),
                        'commune',
                    )
        except Exception:
            pass

        # 2. Profil producteur
        if user.role == 'producteur':
            try:
                p = user.profil_producteur
                if p.commune:
                    coords = commune_coords.get(p.commune.lower())
                    if coords:
                        return (coords['lat'], coords['lng'], 'commune')
                if p.departement:
                    coords = dept_coords.get(p.departement.lower())
                    if coords:
                        return (coords['lat'], coords['lng'], 'departement')
            except Exception:
                pass

        # 3. Profil acheteur
        if user.role == 'acheteur':
            try:
                a = user.profil_acheteur
                if a.ville:
                    coords = commune_coords.get(a.ville.lower())
                    if coords:
                        return (coords['lat'], coords['lng'], 'commune')
                if a.departement:
                    coords = dept_coords.get(a.departement.lower())
                    if coords:
                        return (coords['lat'], coords['lng'], 'departement')
            except Exception:
                pass

        return (None, None, None)

    qs = CustomUser.objects.filter(
        is_active=True
    ).select_related(
        'profil_producteur',
        'profil_acheteur',
    ).prefetch_related('adresses').order_by('-created_at')

    if role:
        qs = qs.filter(role=role)
    if date_debut:
        qs = qs.filter(created_at__date__gte=date_debut)
    if date_fin:
        qs = qs.filter(created_at__date__lte=date_fin)
    if statut:
        if statut in ['en_attente', 'actif', 'suspendu', 'inactif']:
            qs = qs.filter(role='producteur', profil_producteur__statut=statut)
        elif statut == 'is_active':
            qs = qs.filter(is_active=True)

    users_data = []
    stats = {'acheteur': 0, 'producteur': 0, 'collecteur': 0, 'superadmin': 0, 'admin': 0, 'total': 0}

    for user in qs:
        lat, lng, precision = get_coords(user)

        extra = {}
        if user.role == 'producteur':
            try:
                p = user.profil_producteur
                extra = {
                    'code_producteur': p.code_producteur,
                    'commune':         p.commune,
                    'departement':     p.get_departement_display(),
                    'statut':          p.statut,
                    'nb_produits':     p.nb_produits_actifs,
                }
            except Exception:
                pass
        elif user.role == 'acheteur':
            try:
                a = user.profil_acheteur
                extra = {
                    'type_acheteur': a.get_type_acheteur_display(),
                    'ville':         a.ville,
                    'departement':   a.departement,
                }
            except Exception:
                pass

        adresse_str = ''
        try:
            adresse = user.adresses.filter(is_default=True).first()
            if adresse:
                adresse_str = f"{adresse.rue}, {adresse.commune}"
        except Exception:
            pass

        user_dict = {
            'id':          user.pk,
            'nom':         user.get_full_name(),
            'email':       user.email,
            'telephone':   user.telephone,
            'role':        user.role,
            'is_verified': user.is_verified,
            'adresse':     adresse_str,
            'created_at':  user.created_at.strftime('%d/%m/%Y'),
            'lat':         lat,
            'lng':         lng,
            'precision':   precision,
            **extra,
        }
        users_data.append(user_dict)

        role_key = user.role if user.role in stats else 'admin'
        stats[role_key] = stats.get(role_key, 0) + 1
        stats['total'] += 1

    return Response({
        'success': True,
        'data': {
            'users': users_data,
            'stats': stats,
            'total': len(users_data),
        }
    })
