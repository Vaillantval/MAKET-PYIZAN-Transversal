from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.serializers import LoginSerializer, RegisterSerializer, MeSerializer, AdresseSerializer
from apps.accounts.models import Adresse


def _tokens_for_user(user):
    """Retourne access + refresh tokens pour un utilisateur."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Inscription d'un Producteur ou d'un Acheteur.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _tokens_for_user(user)
        return Response({
            'message': "Inscription réussie.",
            'user': {
                'id':           user.id,
                'username':     user.username,
                'email':        user.email,
                'role':         user.role,
                'full_name':    user.get_full_name(),
                'is_superuser': user.is_superuser,
            },
            **tokens,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Retourne access + refresh tokens JWT.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = _tokens_for_user(user)
        return Response({
            'message': "Connexion réussie.",
            'user': {
                'id':           user.id,
                'username':     user.username,
                'email':        user.email,
                'role':         user.role,
                'full_name':    user.get_full_name(),
                'is_superuser': user.is_superuser,
            },
            **tokens,
        })


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blackliste le refresh token (révoque la session).
    Body: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': "Le champ 'refresh' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': "Token invalide ou déjà révoqué."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'message': "Déconnexion réussie."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET  /api/auth/me/  — lire son profil
    PATCH /api/auth/me/ — modifier first_name, last_name, telephone, photo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True,
                                  context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TokenRefreshView(BaseTokenRefreshView):
    """
    POST /api/auth/token/refresh/
    Échange un refresh token contre un nouvel access token.
    """
    pass


# ── Adresses ─────────────────────────────────────────────────────────────────

class AdresseListCreateView(APIView):
    """
    GET  /api/auth/adresses/  — liste des adresses de l'utilisateur
    POST /api/auth/adresses/  — créer une nouvelle adresse
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Adresse.objects.filter(user=request.user)
        return Response(AdresseSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AdresseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdresseDetailView(APIView):
    """
    GET    /api/auth/adresses/<pk>/  — détail
    PUT    /api/auth/adresses/<pk>/  — mise à jour complète
    PATCH  /api/auth/adresses/<pk>/  — mise à jour partielle
    DELETE /api/auth/adresses/<pk>/  — suppression
    """
    permission_classes = [IsAuthenticated]

    def _get_adresse(self, pk, user):
        try:
            return Adresse.objects.get(pk=pk, user=user)
        except Adresse.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_adresse(pk, request.user)
        if not obj:
            return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdresseSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get_adresse(pk, request.user)
        if not obj:
            return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdresseSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get_adresse(pk, request.user)
        if not obj:
            return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdresseSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_adresse(pk, request.user)
        if not obj:
            return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdresseSetDefaultView(APIView):
    """
    PATCH /api/auth/adresses/<pk>/default/  — définir comme adresse par défaut
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            obj = Adresse.objects.get(pk=pk, user=request.user)
        except Adresse.DoesNotExist:
            return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        obj.is_default = True
        obj.save()
        return Response(AdresseSerializer(obj).data)


# ── Commandes acheteur ────────────────────────────────────────────────────────

class MesCommandesView(APIView):
    """
    GET /api/auth/commandes/  — liste des commandes de l'acheteur connecté
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models.commande import Commande
        try:
            acheteur = request.user.profil_acheteur
        except Exception:
            return Response({'detail': 'Profil acheteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        commandes = Commande.objects.filter(acheteur=acheteur).select_related(
            'producteur__user'
        ).prefetch_related('details').order_by('-created_at')

        data = []
        for c in commandes:
            data.append({
                'id':               c.pk,
                'numero':           c.numero_commande,
                'statut':           c.statut,
                'statut_label':     c.get_statut_display(),
                'statut_paiement':  c.statut_paiement,
                'statut_paiement_label': c.get_statut_paiement_display(),
                'total':            str(c.total),
                'nb_articles':      c.nb_articles,
                'producteur_nom':   c.producteur.user.get_full_name(),
                'producteur_commune': c.producteur.commune,
                'mode_livraison':   c.get_mode_livraison_display(),
                'created_at':       c.created_at.isoformat(),
                'est_annulable':    c.est_annulable,
            })
        return Response(data)


class CommandeDetailView(APIView):
    """
    GET /api/auth/commandes/<numero>/  — détail d'une commande
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, numero):
        from apps.orders.models.commande import Commande
        try:
            acheteur = request.user.profil_acheteur
        except Exception:
            return Response({'detail': 'Profil acheteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            c = Commande.objects.select_related(
                'producteur__user', 'acheteur__user'
            ).prefetch_related('details__produit').get(
                numero_commande=numero, acheteur=acheteur
            )
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        details = []
        for d in c.details.all():
            details.append({
                'produit_nom':   d.produit.nom,
                'produit_slug':  d.produit.slug,
                'quantite':      d.quantite,
                'unite_vente':   d.unite_vente,
                'prix_unitaire': str(d.prix_unitaire),
                'sous_total':    str(d.sous_total),
            })

        return Response({
            'id':                     c.pk,
            'numero':                 c.numero_commande,
            'statut':                 c.statut,
            'statut_label':           c.get_statut_display(),
            'statut_paiement':        c.statut_paiement,
            'statut_paiement_label':  c.get_statut_paiement_display(),
            'methode_paiement_label': c.get_methode_paiement_display(),
            'sous_total':             str(c.sous_total),
            'frais_livraison':        str(c.frais_livraison),
            'remise':                 str(c.remise),
            'total':                  str(c.total),
            'mode_livraison':         c.get_mode_livraison_display(),
            'adresse_livraison':      c.adresse_livraison,
            'ville_livraison':        c.ville_livraison,
            'departement_livraison':  c.departement_livraison,
            'notes_acheteur':         c.notes_acheteur,
            'date_livraison_prevue':  c.date_livraison_prevue.isoformat() if c.date_livraison_prevue else None,
            'producteur_nom':         c.producteur.user.get_full_name(),
            'producteur_commune':     c.producteur.commune,
            'details':                details,
            'created_at':             c.created_at.isoformat(),
            'est_annulable':          c.est_annulable,
        })


# ── Changement de mot de passe ────────────────────────────────────────────────

class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Body: { current_password, new_password }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current  = request.data.get('current_password', '')
        new_pwd  = request.data.get('new_password', '')

        if not request.user.check_password(current):
            return Response(
                {'detail': 'Mot de passe actuel incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_pwd) < 8:
            return Response(
                {'detail': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_pwd)
        request.user.save()
        return Response({'message': 'Mot de passe mis à jour avec succès.'})


# ── Dashboard Producteur ───────────────────────────────────────────────────────

def _get_producteur(user):
    try:
        return user.profil_producteur
    except Exception:
        return None


class ProducteurStatsView(APIView):
    """GET /api/auth/producteur/stats/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum
        from apps.orders.models.commande import Commande

        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        qs = Commande.objects.filter(producteur=prod)
        now = timezone.now()
        debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        revenus_mois = qs.filter(
            statut='livree', created_at__gte=debut_mois
        ).aggregate(total=Sum('total'))['total'] or 0

        en_attente = qs.filter(statut='en_attente').count()
        en_cours   = qs.filter(statut__in=['confirmee', 'en_preparation', 'prete', 'en_collecte']).count()

        produits_actifs = prod.produits.filter(is_active=True).count()
        stock_faible    = prod.produits.filter(
            is_active=True,
            stock_disponible__lte=prod.produits.model._meta.get_field('seuil_alerte').default
        ).count()
        # Calcul correct : produits dont stock <= leur propre seuil
        from apps.catalog.models import Produit
        stock_faible = Produit.objects.filter(
            producteur=prod, is_active=True
        ).extra(where=['stock_disponible <= seuil_alerte']).count()

        return Response({
            'revenus_mois':     float(revenus_mois),
            'total_commandes':  qs.count(),
            'en_attente':       en_attente,
            'en_cours':         en_cours,
            'produits_actifs':  produits_actifs,
            'stock_faible':     stock_faible,
            'statut':           prod.statut,
            'statut_label':     prod.get_statut_display(),
            'code_producteur':  prod.code_producteur,
        })


class ProducteurCommandesView(APIView):
    """GET /api/auth/producteur/commandes/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models.commande import Commande

        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        statut_filtre = request.GET.get('statut', '')
        qs = Commande.objects.filter(producteur=prod).select_related(
            'acheteur__user'
        ).prefetch_related('details').order_by('-created_at')

        if statut_filtre:
            qs = qs.filter(statut=statut_filtre)

        data = []
        for c in qs:
            data.append({
                'id':               c.pk,
                'numero':           c.numero_commande,
                'statut':           c.statut,
                'statut_label':     c.get_statut_display(),
                'statut_paiement':  c.statut_paiement,
                'statut_paiement_label': c.get_statut_paiement_display(),
                'total':            str(c.total),
                'nb_articles':      c.nb_articles,
                'acheteur_nom':     c.acheteur.user.get_full_name() or c.acheteur.user.username,
                'acheteur_tel':     c.acheteur.user.telephone or '',
                'mode_livraison':   c.get_mode_livraison_display(),
                'created_at':       c.created_at.isoformat(),
                'est_annulable':    c.est_annulable,
                'actions_possibles': _actions_possibles(c.statut),
            })
        return Response(data)


def _actions_possibles(statut):
    mapping = {
        'en_attente':     ['confirmer', 'annuler'],
        'confirmee':      ['preparer', 'annuler'],
        'en_preparation': ['prete'],
        'prete':          [],
        'en_collecte':    [],
        'livree':         [],
        'annulee':        [],
        'litige':         [],
    }
    return mapping.get(statut, [])


class ProducteurCommandeDetailView(APIView):
    """GET /api/auth/producteur/commandes/<numero>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, numero):
        from apps.orders.models.commande import Commande

        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            c = Commande.objects.select_related(
                'acheteur__user'
            ).prefetch_related('details__produit').get(
                numero_commande=numero, producteur=prod
            )
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        details = [{
            'produit_nom':   d.produit.nom,
            'produit_slug':  d.produit.slug,
            'quantite':      d.quantite,
            'unite_vente':   d.unite_vente,
            'prix_unitaire': str(d.prix_unitaire),
            'sous_total':    str(d.sous_total),
        } for d in c.details.all()]

        return Response({
            'id':                     c.pk,
            'numero':                 c.numero_commande,
            'statut':                 c.statut,
            'statut_label':           c.get_statut_display(),
            'statut_paiement':        c.statut_paiement,
            'statut_paiement_label':  c.get_statut_paiement_display(),
            'methode_paiement_label': c.get_methode_paiement_display(),
            'sous_total':             str(c.sous_total),
            'frais_livraison':        str(c.frais_livraison),
            'remise':                 str(c.remise),
            'total':                  str(c.total),
            'mode_livraison':         c.get_mode_livraison_display(),
            'adresse_livraison':      c.adresse_livraison,
            'ville_livraison':        c.ville_livraison,
            'departement_livraison':  c.departement_livraison,
            'notes_acheteur':         c.notes_acheteur,
            'acheteur_nom':           c.acheteur.user.get_full_name() or c.acheteur.user.username,
            'acheteur_tel':           c.acheteur.user.telephone or '',
            'acheteur_email':         c.acheteur.user.email or '',
            'date_livraison_prevue':  c.date_livraison_prevue.isoformat() if c.date_livraison_prevue else None,
            'details':                details,
            'created_at':             c.created_at.isoformat(),
            'est_annulable':          c.est_annulable,
            'actions_possibles':      _actions_possibles(c.statut),
        })


TRANSITION_MAP = {
    'confirmer': ('en_attente',     'confirmee'),
    'preparer':  ('confirmee',      'en_preparation'),
    'prete':     ('en_preparation', 'prete'),
    'annuler':   (None,             'annulee'),  # annulable depuis en_attente ou confirmee
}


class ProducteurCommandeStatutView(APIView):
    """PATCH /api/auth/producteur/commandes/<numero>/statut/"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, numero):
        from django.utils import timezone
        from apps.orders.models.commande import Commande

        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            c = Commande.objects.get(numero_commande=numero, producteur=prod)
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', '')
        if action not in TRANSITION_MAP:
            return Response({'detail': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        statut_requis, nouveau_statut = TRANSITION_MAP[action]
        if action == 'annuler':
            if c.statut not in ['en_attente', 'confirmee']:
                return Response({'detail': 'Cette commande ne peut plus être annulée.'}, status=status.HTTP_400_BAD_REQUEST)
        elif c.statut != statut_requis:
            return Response(
                {'detail': f"Action impossible depuis le statut '{c.get_statut_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        c.statut = nouveau_statut
        if nouveau_statut == 'confirmee':
            c.date_confirmation = timezone.now()
        c.save()

        return Response({
            'statut':       c.statut,
            'statut_label': c.get_statut_display(),
        })


class ProducteurProfilUpdateView(APIView):
    """
    GET   /api/auth/producteur/profil/  — lire infos boutique
    PATCH /api/auth/producteur/profil/  — modifier infos boutique
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._serialize(prod))

    def patch(self, request):
        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Champs modifiables sur le profil producteur
        prod_fields = ['commune', 'departement', 'localite', 'adresse_complete', 'superficie_ha', 'description']
        for field in prod_fields:
            if field in request.data:
                setattr(prod, field, request.data[field])
        prod.save()

        return Response(self._serialize(prod))

    def _serialize(self, prod):
        return {
            'code_producteur':  prod.code_producteur,
            'statut':           prod.statut,
            'statut_label':     prod.get_statut_display(),
            'commune':          prod.commune,
            'departement':      prod.departement,
            'departement_label': prod.get_departement_display(),
            'localite':         prod.localite,
            'adresse_complete': prod.adresse_complete,
            'superficie_ha':    str(prod.superficie_ha) if prod.superficie_ha else '',
            'description':      prod.description,
            'nb_produits_actifs': prod.nb_produits_actifs,
            'nb_commandes_total': prod.nb_commandes_total,
        }
