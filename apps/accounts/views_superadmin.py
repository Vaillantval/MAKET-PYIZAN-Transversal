"""
API Superadmin — Makèt Peyizan
Toutes les vues sont protégées : utilisateur authentifié + is_staff ou is_superuser.
Préfixe : /api/admin/
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


def _require_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'superadmin')


class IsAdminOrSuperuser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and _require_admin(request.user)


# ── Stats globales ────────────────────────────────────────────────────────────

class AdminStatsView(APIView):
    """GET /api/admin/stats/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.accounts.models import CustomUser
        from apps.accounts.models.producteur import Producteur
        from apps.orders.models.commande import Commande
        from apps.payments.models import Paiement
        from apps.catalog.models import Produit
        from apps.stock.models import AlerteStock

        now = timezone.now()
        debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        revenus_mois = Commande.objects.filter(
            statut='livree', created_at__gte=debut_mois
        ).aggregate(t=Sum('total'))['t'] or 0

        return Response({
            'total_users':         CustomUser.objects.count(),
            'users_actifs':        CustomUser.objects.filter(is_active=True).count(),
            'producteurs_attente': Producteur.objects.filter(statut='en_attente').count(),
            'producteurs_actifs':  Producteur.objects.filter(statut='actif').count(),
            'commandes_attente':   Commande.objects.filter(statut='en_attente').count(),
            'commandes_jour':      Commande.objects.filter(created_at__date=now.date()).count(),
            'commandes_mois':      Commande.objects.filter(created_at__gte=debut_mois).count(),
            'revenus_mois':        float(revenus_mois),
            'paiements_a_verifier': Paiement.objects.filter(statut='soumis').count(),
            'alertes_stock':       AlerteStock.objects.filter(
                niveau__in=['critique', 'epuise'], resolue=False
            ).count() if hasattr(AlerteStock, 'resolue') else AlerteStock.objects.filter(
                niveau__in=['critique', 'epuise']
            ).count(),
            'produits_actifs':     Produit.objects.filter(is_active=True).count(),
        })


# ── Utilisateurs ──────────────────────────────────────────────────────────────

class AdminUsersView(APIView):
    """GET /api/admin/users/?search=&role=&is_active="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.accounts.models import CustomUser

        qs = CustomUser.objects.all().order_by('-created_at')
        search = request.GET.get('search', '').strip()
        role   = request.GET.get('role', '').strip()
        active = request.GET.get('is_active', '').strip()

        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(telephone__icontains=search)
            )
        if role:
            qs = qs.filter(role=role)
        if active in ('true', 'false'):
            qs = qs.filter(is_active=(active == 'true'))

        data = []
        for u in qs[:200]:
            data.append({
                'id':          u.pk,
                'username':    u.username,
                'email':       u.email,
                'full_name':   u.get_full_name() or u.username,
                'role':        u.role,
                'role_label':  u.get_role_display(),
                'telephone':   u.telephone,
                'is_active':   u.is_active,
                'is_staff':    u.is_staff,
                'is_superuser': u.is_superuser,
                'is_verified': u.is_verified,
                'date_joined': u.date_joined.isoformat(),
                'created_at':  u.created_at.isoformat(),
                'photo':       request.build_absolute_uri(u.photo.url) if u.photo else None,
            })
        return Response(data)


class AdminUserToggleView(APIView):
    """PATCH /api/admin/users/<pk>/toggle/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.accounts.models import CustomUser
        try:
            u = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=404)
        if u.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Impossible de modifier un superadmin.'}, status=403)
        u.is_active = not u.is_active
        u.save(update_fields=['is_active'])
        return Response({'is_active': u.is_active, 'username': u.username})


# ── Producteurs ───────────────────────────────────────────────────────────────

class AdminProducteursView(APIView):
    """GET /api/admin/producteurs/?statut="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.accounts.models.producteur import Producteur

        statut = request.GET.get('statut', '').strip()
        search = request.GET.get('search', '').strip()
        qs = Producteur.objects.select_related('user').order_by('-created_at')

        if statut:
            qs = qs.filter(statut=statut)
        if search:
            qs = qs.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(code_producteur__icontains=search) |
                Q(commune__icontains=search)
            )

        data = []
        for p in qs[:200]:
            data.append({
                'id':               p.pk,
                'code_producteur':  p.code_producteur,
                'user_id':          p.user.pk,
                'nom':              p.user.get_full_name() or p.user.username,
                'email':            p.user.email,
                'telephone':        p.user.telephone,
                'departement':      p.get_departement_display(),
                'commune':          p.commune,
                'localite':         p.localite,
                'superficie_ha':    str(p.superficie_ha) if p.superficie_ha else None,
                'statut':           p.statut,
                'statut_label':     p.get_statut_display(),
                'note_admin':       p.note_admin,
                'date_validation':  p.date_validation.isoformat() if p.date_validation else None,
                'created_at':       p.created_at.isoformat(),
                'nb_produits':      p.produits.count(),
                'photo':            request.build_absolute_uri(p.user.photo.url) if p.user.photo else None,
            })
        return Response(data)


class AdminProducteurStatutView(APIView):
    """PATCH /api/admin/producteurs/<pk>/statut/  body: {statut, note}"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.accounts.models.producteur import Producteur

        try:
            p = Producteur.objects.select_related('user').get(pk=pk)
        except Producteur.DoesNotExist:
            return Response({'detail': 'Producteur introuvable.'}, status=404)

        nouveau_statut = request.data.get('statut', '').strip()
        note           = request.data.get('note', '').strip()

        statuts_valides = [s[0] for s in Producteur.Statut.choices]
        if nouveau_statut not in statuts_valides:
            return Response({'detail': 'Statut invalide.'}, status=400)

        if note:
            p.note_admin = note
        if nouveau_statut == Producteur.Statut.ACTIF:
            p.date_validation = timezone.now()
            p.valide_par      = request.user
        p.statut = nouveau_statut
        p.save()

        return Response({
            'statut':       p.statut,
            'statut_label': p.get_statut_display(),
            'note_admin':   p.note_admin,
        })


# ── Commandes ─────────────────────────────────────────────────────────────────

class AdminCommandesView(APIView):
    """GET /api/admin/commandes/?statut=&search="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.orders.models.commande import Commande

        qs = Commande.objects.select_related(
            'acheteur__user', 'producteur__user'
        ).prefetch_related('details').order_by('-created_at')

        statut = request.GET.get('statut', '').strip()
        search = request.GET.get('search', '').strip()

        if statut:
            qs = qs.filter(statut=statut)
        if search:
            qs = qs.filter(
                Q(numero_commande__icontains=search) |
                Q(acheteur__user__first_name__icontains=search) |
                Q(acheteur__user__last_name__icontains=search) |
                Q(acheteur__user__telephone__icontains=search)
            )

        data = []
        for c in qs[:300]:
            data.append({
                'id':                    c.pk,
                'numero':                c.numero_commande,
                'statut':                c.statut,
                'statut_label':          c.get_statut_display(),
                'statut_paiement':       c.statut_paiement,
                'statut_paiement_label': c.get_statut_paiement_display(),
                'methode_paiement':      c.methode_paiement,
                'methode_paiement_label': c.get_methode_paiement_display(),
                'total':                 str(c.total),
                'nb_articles':           c.nb_articles,
                'acheteur_nom':          c.acheteur.user.get_full_name() or c.acheteur.user.username,
                'acheteur_tel':          c.acheteur.user.telephone,
                'producteur_nom':        c.producteur.user.get_full_name() or c.producteur.user.username,
                'mode_livraison':        c.get_mode_livraison_display(),
                'est_annulable':         c.est_annulable,
                'created_at':            c.created_at.isoformat(),
            })
        return Response(data)


class AdminCommandeDetailView(APIView):
    """GET /api/admin/commandes/<numero>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, numero):
        from apps.orders.models.commande import Commande
        try:
            c = Commande.objects.select_related(
                'acheteur__user', 'producteur__user'
            ).prefetch_related('details__produit').get(numero_commande=numero)
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=404)

        from apps.accounts.views import _actions_possibles
        details = [{
            'produit_nom':   d.produit.nom,
            'quantite':      d.quantite,
            'unite_vente':   d.unite_vente,
            'prix_unitaire': str(d.prix_unitaire),
            'sous_total':    str(d.sous_total),
        } for d in c.details.all()]

        historique = [{
            'statut_avant':  h.statut_avant,
            'statut_apres':  h.statut_apres,
            'commentaire':   h.commentaire,
            'created_at':    h.created_at.isoformat(),
            'effectue_par':  h.effectue_par.get_full_name() if h.effectue_par else 'Système',
        } for h in c.historique_statuts.all().order_by('created_at')]

        return Response({
            'id':                    c.pk,
            'numero':                c.numero_commande,
            'statut':                c.statut,
            'statut_label':          c.get_statut_display(),
            'statut_paiement':       c.statut_paiement,
            'statut_paiement_label': c.get_statut_paiement_display(),
            'methode_paiement_label': c.get_methode_paiement_display(),
            'sous_total':            str(c.sous_total),
            'frais_livraison':       str(c.frais_livraison),
            'remise':                str(c.remise),
            'total':                 str(c.total),
            'mode_livraison':        c.get_mode_livraison_display(),
            'adresse_livraison':     c.adresse_livraison,
            'ville_livraison':       c.ville_livraison,
            'notes_acheteur':        c.notes_acheteur,
            'notes_admin':           c.notes_admin,
            'acheteur_nom':          c.acheteur.user.get_full_name() or c.acheteur.user.username,
            'acheteur_email':        c.acheteur.user.email,
            'acheteur_tel':          c.acheteur.user.telephone,
            'producteur_nom':        c.producteur.user.get_full_name() or c.producteur.user.username,
            'producteur_code':       c.producteur.code_producteur,
            'preuve_paiement':       request.build_absolute_uri(c.preuve_paiement.url) if c.preuve_paiement else None,
            'date_confirmation':     c.date_confirmation.isoformat() if c.date_confirmation else None,
            'created_at':            c.created_at.isoformat(),
            'est_annulable':         c.est_annulable,
            'actions_possibles':     _actions_possibles(c.statut),
            'details':               details,
            'historique':            historique,
        })


ADMIN_TRANSITION_MAP = {
    'confirmer':   'confirmee',
    'preparer':    'en_preparation',
    'prete':       'prete',
    'en_collecte': 'en_collecte',
    'livrer':      'livree',
    'litige':      'litige',
    'annuler':     'annulee',
}

ADMIN_ACTIONS_POSSIBLES = {
    'en_attente':     ['confirmer', 'annuler'],
    'confirmee':      ['preparer', 'annuler'],
    'en_preparation': ['prete'],
    'prete':          ['en_collecte'],
    'en_collecte':    ['livrer', 'litige'],
    'livree':         [],
    'annulee':        [],
    'litige':         ['livrer', 'annuler'],
}


class AdminCommandeStatutView(APIView):
    """PATCH /api/admin/commandes/<numero>/statut/  body: {action, commentaire}"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, numero):
        from apps.orders.models.commande import Commande
        from apps.orders.services.commande_service import CommandeService

        try:
            c = Commande.objects.get(numero_commande=numero)
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=404)

        action      = request.data.get('action', '').strip()
        commentaire = request.data.get('commentaire', '').strip()

        if action not in ADMIN_ACTIONS_POSSIBLES.get(c.statut, []):
            return Response({'detail': f"Action '{action}' non disponible depuis '{c.statut}'."}, status=400)

        try:
            if action == 'confirmer':
                CommandeService.confirmer_commande(c, effectue_par=request.user)
            elif action == 'annuler':
                CommandeService.annuler_commande(c, effectue_par=request.user, motif=commentaire)
            else:
                nouveau = ADMIN_TRANSITION_MAP[action]
                CommandeService.changer_statut(c, nouveau, effectue_par=request.user, commentaire=commentaire)
        except ValueError as e:
            return Response({'detail': str(e)}, status=400)

        return Response({
            'statut':       c.statut,
            'statut_label': c.get_statut_display(),
            'actions_possibles': ADMIN_ACTIONS_POSSIBLES.get(c.statut, []),
        })


# ── Paiements ─────────────────────────────────────────────────────────────────

class AdminPaiementsView(APIView):
    """GET /api/admin/paiements/?statut="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.payments.models import Paiement

        qs = Paiement.objects.select_related(
            'commande__acheteur__user', 'commande__producteur__user', 'effectue_par'
        ).order_by('-created_at')

        statut = request.GET.get('statut', '').strip()
        if statut:
            qs = qs.filter(statut=statut)

        data = []
        for p in qs[:200]:
            data.append({
                'id':               p.pk,
                'reference':        p.reference,
                'statut':           p.statut,
                'statut_label':     p.get_statut_display(),
                'type_paiement':    p.type_paiement,
                'type_label':       p.get_type_paiement_display(),
                'montant':          str(p.montant),
                'montant_recu':     str(p.montant_recu) if p.montant_recu else None,
                'numero_expediteur': p.numero_expediteur,
                'id_transaction':   p.id_transaction,
                'preuve_image':     request.build_absolute_uri(p.preuve_image.url) if p.preuve_image else None,
                'notes':            p.notes,
                'note_verification': p.note_verification,
                'commande_numero':  p.commande.numero_commande,
                'commande_id':      p.commande.pk,
                'acheteur':         p.commande.acheteur.user.get_full_name() or p.commande.acheteur.user.username,
                'acheteur_tel':     p.commande.acheteur.user.telephone,
                'created_at':       p.created_at.isoformat(),
                'date_verification': p.date_verification.isoformat() if p.date_verification else None,
            })
        return Response(data)


class AdminPaiementStatutView(APIView):
    """PATCH /api/admin/paiements/<pk>/statut/  body: {statut, note, montant_recu}"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.payments.models import Paiement

        try:
            p = Paiement.objects.select_related('commande').get(pk=pk)
        except Paiement.DoesNotExist:
            return Response({'detail': 'Paiement introuvable.'}, status=404)

        nouveau_statut = request.data.get('statut', '').strip()
        statuts_valides = [s[0] for s in Paiement.Statut.choices]
        if nouveau_statut not in statuts_valides:
            return Response({'detail': 'Statut invalide.'}, status=400)

        note        = request.data.get('note', '').strip()
        montant_recu = request.data.get('montant_recu')

        p.statut         = nouveau_statut
        p.verifie_par    = request.user
        p.date_verification = timezone.now()
        if note:
            p.note_verification = note
        if montant_recu:
            try:
                p.montant_recu = float(montant_recu)
            except (ValueError, TypeError):
                pass

        # Mettre à jour statut_paiement de la commande si confirmé
        if nouveau_statut == Paiement.Statut.CONFIRME:
            from apps.orders.models.commande import Commande
            p.commande.statut_paiement = Commande.StatutPaiement.PAYE
            p.commande.save(update_fields=['statut_paiement'])

        p.save()

        return Response({
            'statut':       p.statut,
            'statut_label': p.get_statut_display(),
        })


# ── Catalogue ─────────────────────────────────────────────────────────────────

class AdminCatalogueView(APIView):
    """GET /api/admin/catalogue/?search=&statut=&producteur_id="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.catalog.models import Produit

        qs = Produit.objects.select_related(
            'producteur__user', 'categorie'
        ).order_by('-created_at')

        search       = request.GET.get('search', '').strip()
        statut       = request.GET.get('statut', '').strip()
        producteur   = request.GET.get('producteur_id', '').strip()

        if search:
            qs = qs.filter(Q(nom__icontains=search) | Q(categorie__nom__icontains=search))
        if statut:
            qs = qs.filter(statut=statut)
        if producteur:
            qs = qs.filter(producteur_id=producteur)

        data = []
        for p in qs[:300]:
            data.append({
                'id':               p.pk,
                'nom':              p.nom,
                'slug':             p.slug,
                'categorie':        p.categorie.nom,
                'prix_unitaire':    str(p.prix_unitaire),
                'unite_vente':      p.get_unite_vente_display(),
                'stock_disponible': p.stock_disponible,
                'stock_reel':       p.stock_reel,
                'statut':           p.statut,
                'statut_label':     p.get_statut_display(),
                'is_active':        p.is_active,
                'is_featured':      p.is_featured,
                'producteur_nom':   p.producteur.user.get_full_name() or p.producteur.user.username,
                'producteur_code':  p.producteur.code_producteur,
                'producteur_id':    p.producteur.pk,
                'image':            request.build_absolute_uri(p.image_principale.url) if p.image_principale else None,
                'created_at':       p.created_at.isoformat(),
            })
        return Response(data)


class AdminCatalogueToggleView(APIView):
    """PATCH /api/admin/catalogue/<pk>/toggle/  body: {champ: 'is_active'|'is_featured'}"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.catalog.models import Produit
        try:
            p = Produit.objects.get(pk=pk)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)

        champ = request.data.get('champ', 'is_active')
        if champ == 'is_active':
            p.is_active = not p.is_active
            p.save(update_fields=['is_active'])
            return Response({'is_active': p.is_active})
        elif champ == 'is_featured':
            p.is_featured = not p.is_featured
            p.save(update_fields=['is_featured'])
            return Response({'is_featured': p.is_featured})
        return Response({'detail': 'Champ invalide.'}, status=400)


class AdminCatalogueStatutView(APIView):
    """PATCH /api/admin/catalogue/<pk>/statut/  body: {statut}"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.catalog.models import Produit
        try:
            p = Produit.objects.get(pk=pk)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)

        nouveau = request.data.get('statut', '').strip()
        statuts = [s[0] for s in Produit.Statut.choices]
        if nouveau not in statuts:
            return Response({'detail': 'Statut invalide.'}, status=400)

        p.statut = nouveau
        if nouveau == Produit.Statut.ACTIF:
            p.is_active = True
        elif nouveau in (Produit.Statut.INACTIF, Produit.Statut.BROUILLON):
            p.is_active = False
        p.save(update_fields=['statut', 'is_active'])
        return Response({'statut': p.statut, 'statut_label': p.get_statut_display(), 'is_active': p.is_active})


# ── Stocks ────────────────────────────────────────────────────────────────────

class AdminStocksLotsView(APIView):
    """GET /api/admin/stocks/lots/?search=&statut=&producteur_id="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.stock.models import Lot

        qs = Lot.objects.select_related('produit__producteur__user', 'produit__categorie').order_by('-created_at')

        search     = request.GET.get('search', '').strip()
        statut     = request.GET.get('statut', '').strip()
        producteur = request.GET.get('producteur_id', '').strip()

        if search:
            qs = qs.filter(Q(numero_lot__icontains=search) | Q(produit__nom__icontains=search))
        if statut:
            qs = qs.filter(statut=statut)
        if producteur:
            qs = qs.filter(produit__producteur_id=producteur)

        data = []
        for lot in qs[:300]:
            data.append({
                'id':               lot.pk,
                'numero_lot':       lot.numero_lot,
                'produit_nom':      lot.produit.nom,
                'produit_id':       lot.produit.pk,
                'producteur_nom':   lot.produit.producteur.user.get_full_name() or lot.produit.producteur.user.username,
                'producteur_code':  lot.produit.producteur.code_producteur,
                'categorie':        lot.produit.categorie.nom,
                'quantite_initiale': lot.quantite_initiale,
                'quantite_actuelle': lot.quantite_actuelle,
                'quantite_vendue':   lot.quantite_vendue,
                'taux_ecoulement':   lot.taux_ecoulement,
                'statut':            lot.statut,
                'statut_label':      lot.get_statut_display(),
                'date_recolte':      str(lot.date_recolte) if lot.date_recolte else None,
                'date_expiration':   str(lot.date_expiration) if lot.date_expiration else None,
                'lieu_stockage':     lot.lieu_stockage,
                'created_at':        lot.created_at.isoformat(),
            })
        return Response(data)


class AdminStocksAlertesView(APIView):
    """GET /api/admin/stocks/alertes/?niveau="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.stock.models import AlerteStock

        qs = AlerteStock.objects.select_related(
            'produit__producteur__user', 'produit__categorie'
        ).order_by('-created_at')

        niveau = request.GET.get('niveau', '').strip()
        if niveau:
            qs = qs.filter(niveau=niveau)

        data = []
        for a in qs[:200]:
            data.append({
                'id':               a.pk,
                'niveau':           a.niveau,
                'niveau_label':     a.get_niveau_display(),
                'produit_nom':      a.produit.nom,
                'produit_id':       a.produit.pk,
                'producteur_nom':   a.produit.producteur.user.get_full_name() or a.produit.producteur.user.username,
                'producteur_tel':   a.produit.producteur.user.telephone,
                'quantite_actuelle': a.quantite_actuelle,
                'seuil_alerte':     a.seuil_alerte,
                'unite_vente':      a.produit.get_unite_vente_display(),
                'created_at':       a.created_at.isoformat(),
            })
        return Response(data)


# ── Collectes ─────────────────────────────────────────────────────────────────

class AdminCollectesView(APIView):
    """GET /api/admin/collectes/?statut="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.collectes.models import Collecte

        qs = Collecte.objects.select_related('zone', 'point_collecte', 'collecteur').order_by('-date_planifiee')

        statut = request.GET.get('statut', '').strip()
        if statut:
            qs = qs.filter(statut=statut)

        data = []
        for c in qs[:200]:
            data.append({
                'id':               c.pk,
                'reference':        c.reference,
                'statut':           c.statut,
                'statut_label':     c.get_statut_display(),
                'zone':             c.zone.nom,
                'departement':      c.zone.get_departement_display(),
                'point':            c.point_collecte.nom if c.point_collecte else None,
                'commune':          c.point_collecte.commune if c.point_collecte else None,
                'collecteur':       c.collecteur.get_full_name() if c.collecteur else None,
                'date_planifiee':   str(c.date_planifiee),
                'heure_debut':      str(c.heure_debut) if c.heure_debut else None,
                'nb_producteurs':   c.nb_producteurs,
                'nb_commandes':     c.nb_commandes,
                'montant_total':    float(c.montant_total),
                'est_en_retard':    c.est_en_retard,
                'notes':            c.notes,
                'created_at':       c.created_at.isoformat(),
            })
        return Response(data)


class AdminCollecteDetailView(APIView):
    """GET /api/admin/collectes/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.collectes.models import Collecte

        try:
            c = Collecte.objects.select_related('zone', 'point_collecte', 'collecteur').get(pk=pk)
        except Collecte.DoesNotExist:
            return Response({'detail': 'Collecte introuvable.'}, status=404)

        participations = []
        for p in c.participations.select_related('producteur__user').all():
            participations.append({
                'id':               p.pk,
                'statut':           p.statut,
                'statut_label':     p.get_statut_display(),
                'producteur_nom':   p.producteur.user.get_full_name() or p.producteur.user.username,
                'producteur_code':  p.producteur.code_producteur,
                'producteur_tel':   p.producteur.user.telephone,
                'producteur_commune': p.producteur.commune,
                'quantite_prevue':  p.quantite_prevue,
                'quantite_collectee': p.quantite_collectee,
                'taux_realisation': p.taux_realisation,
                'notes':            p.notes,
                'created_at':       p.created_at.isoformat(),
            })

        return Response({
            'id':             c.pk,
            'reference':      c.reference,
            'statut':         c.statut,
            'statut_label':   c.get_statut_display(),
            'zone':           c.zone.nom,
            'zone_id':        c.zone.pk,
            'departement':    c.zone.get_departement_display(),
            'point':          c.point_collecte.nom if c.point_collecte else None,
            'point_id':       c.point_collecte.pk if c.point_collecte else None,
            'collecteur':     c.collecteur.get_full_name() if c.collecteur else None,
            'collecteur_id':  c.collecteur.pk if c.collecteur else None,
            'date_planifiee': str(c.date_planifiee),
            'heure_debut':    str(c.heure_debut) if c.heure_debut else None,
            'heure_fin':      str(c.heure_fin) if c.heure_fin else None,
            'notes':          c.notes,
            'rapport':        c.rapport,
            'nb_producteurs': c.nb_producteurs,
            'montant_total':  float(c.montant_total),
            'participations': participations,
        })


class AdminCollecteStatutView(APIView):
    """PATCH /api/admin/collectes/<pk>/statut/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.collectes.models import Collecte

        try:
            c = Collecte.objects.get(pk=pk)
        except Collecte.DoesNotExist:
            return Response({'detail': 'Collecte introuvable.'}, status=404)

        nouveau = request.data.get('statut', '').strip()
        statuts = [s[0] for s in Collecte.Statut.choices]
        if nouveau not in statuts:
            return Response({'detail': 'Statut invalide.'}, status=400)

        c.statut = nouveau
        if nouveau == Collecte.Statut.EN_COURS and not c.date_debut_reel:
            c.date_debut_reel = timezone.now()
        if nouveau == Collecte.Statut.TERMINEE and not c.date_fin_reel:
            c.date_fin_reel = timezone.now()
        c.save()
        return Response({'statut': c.statut, 'statut_label': c.get_statut_display()})


class AdminParticipationStatutView(APIView):
    """PATCH /api/admin/collectes/participations/<pk>/statut/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.collectes.models import ParticipationCollecte

        try:
            p = ParticipationCollecte.objects.get(pk=pk)
        except ParticipationCollecte.DoesNotExist:
            return Response({'detail': 'Participation introuvable.'}, status=404)

        nouveau = request.data.get('statut', '').strip()
        statuts = [s[0] for s in ParticipationCollecte.Statut.choices]
        if nouveau not in statuts:
            return Response({'detail': 'Statut invalide.'}, status=400)

        quantite = request.data.get('quantite_collectee')
        if quantite is not None:
            try:
                p.quantite_collectee = int(quantite)
            except (ValueError, TypeError):
                pass

        p.statut = nouveau
        p.save(update_fields=['statut', 'quantite_collectee', 'updated_at'])
        return Response({'statut': p.statut, 'statut_label': p.get_statut_display()})


# ── Options (données pour les selects des formulaires) ────────────────────────

class AdminOptionsView(APIView):
    """GET /api/admin/options/?type=categories|producteurs|produits|zones|points|collecteurs&zone_id="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        type_ = request.GET.get('type', '').strip()

        if type_ == 'categories':
            from apps.catalog.models import Categorie
            data = [{'id': c.pk, 'label': str(c)} for c in Categorie.objects.filter(is_active=True).order_by('ordre', 'nom')]

        elif type_ == 'producteurs':
            from apps.accounts.models.producteur import Producteur
            data = [{'id': p.pk, 'label': f"{p.user.get_full_name() or p.user.username} ({p.code_producteur})"} for p in Producteur.objects.filter(statut='actif').select_related('user').order_by('user__last_name')]

        elif type_ == 'produits':
            from apps.catalog.models import Produit
            producteur_id = request.GET.get('producteur_id', '').strip()
            qs = Produit.objects.select_related('producteur__user').order_by('nom')
            if producteur_id:
                qs = qs.filter(producteur_id=producteur_id)
            data = [{'id': p.pk, 'label': f"{p.nom} ({p.get_unite_vente_display()})"} for p in qs]

        elif type_ == 'zones':
            from apps.collectes.models import ZoneCollecte
            data = [{'id': z.pk, 'label': str(z)} for z in ZoneCollecte.objects.filter(is_active=True)]

        elif type_ == 'points':
            from apps.collectes.models import PointCollecte
            zone_id = request.GET.get('zone_id', '').strip()
            qs = PointCollecte.objects.filter(is_active=True).order_by('nom')
            if zone_id:
                qs = qs.filter(zone_id=zone_id)
            data = [{'id': p.pk, 'label': f"{p.nom} — {p.commune}"} for p in qs]

        elif type_ == 'collecteurs':
            from apps.accounts.models import CustomUser
            data = [{'id': u.pk, 'label': u.get_full_name() or u.username} for u in CustomUser.objects.filter(role='collecteur', is_active=True).order_by('last_name')]

        elif type_ == 'producteurs_all':
            from apps.accounts.models.producteur import Producteur
            data = [{'id': p.pk, 'label': f"{p.user.get_full_name() or p.user.username} ({p.code_producteur})", 'departement': p.departement, 'commune': p.commune} for p in Producteur.objects.select_related('user').order_by('-created_at')]

        else:
            return Response({'detail': 'type invalide.'}, status=400)

        return Response(data)


# ── Catalogue — CREATE + DETAIL EDIT ─────────────────────────────────────────

class AdminCatalogueCreateView(APIView):
    """POST /api/admin/catalogue/create/  multipart/form-data"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        from apps.catalog.models import Produit, Categorie
        from apps.accounts.models.producteur import Producteur

        data = request.data
        errors = {}
        for f in ('nom', 'producteur_id', 'categorie_id', 'prix_unitaire', 'unite_vente'):
            if not data.get(f):
                errors[f] = 'Champ requis.'
        if errors:
            return Response(errors, status=400)

        try:
            producteur = Producteur.objects.get(pk=data['producteur_id'])
        except Producteur.DoesNotExist:
            return Response({'producteur_id': 'Producteur introuvable.'}, status=400)
        try:
            categorie = Categorie.objects.get(pk=data['categorie_id'])
        except Categorie.DoesNotExist:
            return Response({'categorie_id': 'Categorie introuvable.'}, status=400)

        produit = Produit(
            producteur=producteur,
            categorie=categorie,
            nom=data['nom'],
            description=data.get('description', ''),
            variete=data.get('variete', ''),
            prix_unitaire=data['prix_unitaire'],
            prix_gros=data.get('prix_gros') or None,
            unite_vente=data['unite_vente'],
            quantite_min_commande=int(data.get('quantite_min_commande') or 1),
            seuil_alerte=int(data.get('seuil_alerte') or 10),
            origine=data.get('origine', ''),
            saison=data.get('saison', ''),
            certifications=data.get('certifications', ''),
            statut=data.get('statut', Produit.Statut.EN_ATTENTE),
            is_active=data.get('is_active') in ('true', '1', True),
            is_featured=data.get('is_featured') in ('true', '1', True),
        )
        if 'image_principale' in request.FILES:
            produit.image_principale = request.FILES['image_principale']
        produit.save()

        return Response({
            'id':           produit.pk,
            'nom':          produit.nom,
            'statut':       produit.statut,
            'statut_label': produit.get_statut_display(),
        }, status=201)


class AdminCatalogueDetailView(APIView):
    """GET /api/admin/catalogue/<pk>/detail/   PATCH /api/admin/catalogue/<pk>/detail/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.catalog.models import Produit
        try:
            p = Produit.objects.select_related('producteur__user', 'categorie').get(pk=pk)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)
        return Response({
            'id':                   p.pk,
            'nom':                  p.nom,
            'description':          p.description,
            'variete':              p.variete,
            'prix_unitaire':        str(p.prix_unitaire),
            'prix_gros':            str(p.prix_gros) if p.prix_gros else '',
            'unite_vente':          p.unite_vente,
            'quantite_min_commande': p.quantite_min_commande,
            'seuil_alerte':         p.seuil_alerte,
            'origine':              p.origine,
            'saison':               p.saison,
            'certifications':       p.certifications,
            'statut':               p.statut,
            'is_active':            p.is_active,
            'is_featured':          p.is_featured,
            'categorie_id':         p.categorie.pk,
            'producteur_id':        p.producteur.pk,
            'producteur_nom':       p.producteur.user.get_full_name() or p.producteur.user.username,
            'image':                request.build_absolute_uri(p.image_principale.url) if p.image_principale else None,
        })

    def patch(self, request, pk):
        from apps.catalog.models import Produit, Categorie
        try:
            p = Produit.objects.get(pk=pk)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)

        data = request.data
        if data.get('nom'):            p.nom = data['nom']
        if 'description' in data:      p.description = data['description']
        if 'variete' in data:          p.variete = data['variete']
        if data.get('prix_unitaire'):  p.prix_unitaire = data['prix_unitaire']
        if 'prix_gros' in data:        p.prix_gros = data['prix_gros'] or None
        if data.get('unite_vente'):    p.unite_vente = data['unite_vente']
        if data.get('quantite_min_commande'): p.quantite_min_commande = int(data['quantite_min_commande'])
        if data.get('seuil_alerte'):   p.seuil_alerte = int(data['seuil_alerte'])
        if 'origine' in data:          p.origine = data['origine']
        if 'saison' in data:           p.saison = data['saison']
        if 'certifications' in data:   p.certifications = data['certifications']
        if data.get('statut'):         p.statut = data['statut']
        if 'is_active' in data:        p.is_active = data['is_active'] in ('true', '1', True)
        if 'is_featured' in data:      p.is_featured = data['is_featured'] in ('true', '1', True)
        if data.get('categorie_id'):
            try:
                p.categorie = Categorie.objects.get(pk=data['categorie_id'])
            except Categorie.DoesNotExist:
                pass
        if 'image_principale' in request.FILES:
            p.image_principale = request.FILES['image_principale']
        p.save()
        return Response({'id': p.pk, 'nom': p.nom, 'statut': p.statut, 'statut_label': p.get_statut_display(), 'is_active': p.is_active})


# ── Stocks Lots — CREATE + DETAIL EDIT ───────────────────────────────────────

class AdminStockLotCreateView(APIView):
    """POST /api/admin/stocks/lots/create/"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        from apps.stock.models import Lot
        from apps.catalog.models import Produit

        data = request.data
        if not data.get('produit_id') or not data.get('quantite_initiale'):
            return Response({'detail': 'produit_id et quantite_initiale sont requis.'}, status=400)

        try:
            produit = Produit.objects.get(pk=data['produit_id'])
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=400)

        qte = int(data['quantite_initiale'])
        lot = Lot(
            produit=produit,
            quantite_initiale=qte,
            quantite_actuelle=qte,
            date_recolte=data.get('date_recolte') or None,
            date_expiration=data.get('date_expiration') or None,
            lieu_stockage=data.get('lieu_stockage', ''),
            notes=data.get('notes', ''),
            statut=data.get('statut', Lot.Statut.DISPONIBLE),
            cree_par=request.user,
        )
        lot.save()

        from apps.stock.models import MouvementStock
        MouvementStock.objects.create(
            lot=lot,
            produit=produit,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE,
            quantite=qte,
            stock_avant=0,
            stock_apres=qte,
            effectue_par=request.user,
            motif=data.get('notes', 'Création de lot'),
        )

        return Response({
            'id':           lot.pk,
            'numero_lot':   lot.numero_lot,
            'statut':       lot.statut,
            'statut_label': lot.get_statut_display(),
        }, status=201)


class AdminStockLotDetailView(APIView):
    """GET /api/admin/stocks/lots/<pk>/   PATCH /api/admin/stocks/lots/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.stock.models import Lot
        try:
            lot = Lot.objects.select_related('produit__producteur__user').get(pk=pk)
        except Lot.DoesNotExist:
            return Response({'detail': 'Lot introuvable.'}, status=404)
        return Response({
            'id':               lot.pk,
            'numero_lot':       lot.numero_lot,
            'produit_id':       lot.produit.pk,
            'produit_nom':      lot.produit.nom,
            'quantite_initiale': lot.quantite_initiale,
            'quantite_actuelle': lot.quantite_actuelle,
            'date_recolte':     str(lot.date_recolte) if lot.date_recolte else '',
            'date_expiration':  str(lot.date_expiration) if lot.date_expiration else '',
            'lieu_stockage':    lot.lieu_stockage,
            'notes':            lot.notes,
            'statut':           lot.statut,
        })

    def patch(self, request, pk):
        from apps.stock.models import Lot
        try:
            lot = Lot.objects.get(pk=pk)
        except Lot.DoesNotExist:
            return Response({'detail': 'Lot introuvable.'}, status=404)

        data = request.data
        if 'date_recolte' in data:    lot.date_recolte    = data['date_recolte'] or None
        if 'date_expiration' in data: lot.date_expiration = data['date_expiration'] or None
        if 'lieu_stockage' in data:   lot.lieu_stockage   = data['lieu_stockage']
        if 'notes' in data:           lot.notes           = data['notes']
        if data.get('statut'):        lot.statut          = data['statut']

        # Ajustement de stock si quantite_actuelle modifiée
        if data.get('quantite_actuelle') is not None:
            from apps.stock.models import MouvementStock
            nouvelle_qte = int(data['quantite_actuelle'])
            stock_avant  = lot.quantite_actuelle
            diff         = nouvelle_qte - stock_avant
            lot.quantite_actuelle = nouvelle_qte
            type_mvt = (MouvementStock.TypeMouvement.AJUSTEMENT_POS if diff >= 0
                        else MouvementStock.TypeMouvement.AJUSTEMENT_NEG)
            MouvementStock.objects.create(
                lot=lot, produit=lot.produit,
                type_mouvement=type_mvt,
                quantite=abs(diff),
                stock_avant=stock_avant,
                stock_apres=nouvelle_qte,
                effectue_par=request.user,
                motif='Ajustement manuel via dashboard',
            )

        lot.save()
        return Response({'id': lot.pk, 'numero_lot': lot.numero_lot, 'statut': lot.statut, 'statut_label': lot.get_statut_display()})


# ── Utilisateurs — CREATE + DETAIL EDIT ──────────────────────────────────────

class AdminUserCreateView(APIView):
    """POST /api/admin/users/create/"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        from apps.accounts.models import CustomUser

        data = request.data
        errors = {}
        for f in ('username', 'email', 'role', 'password'):
            if not data.get(f):
                errors[f] = 'Champ requis.'
        if errors:
            return Response(errors, status=400)

        if CustomUser.objects.filter(username=data['username']).exists():
            return Response({'username': 'Ce nom d\'utilisateur est déjà pris.'}, status=400)
        if CustomUser.objects.filter(email=data['email']).exists():
            return Response({'email': 'Cet email est déjà utilisé.'}, status=400)

        role = data['role']
        u = CustomUser(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            telephone=data.get('telephone', ''),
            role=role,
            is_active=data.get('is_active') in ('true', '1', True, 'on') or data.get('is_active', True) is True,
        )
        # Un superadmin doit avoir is_staff et is_superuser pour accéder aux APIs
        if role == 'superadmin':
            u.is_staff = True
            u.is_superuser = True
        u.set_password(data['password'])
        u.save()

        # Créer automatiquement le profil Producteur si rôle = producteur
        if u.role == 'producteur' and data.get('departement') and data.get('commune'):
            from apps.accounts.models.producteur import Producteur
            Producteur.objects.create(
                user=u,
                departement=data.get('departement', ''),
                commune=data.get('commune', ''),
                localite=data.get('localite', ''),
            )

        return Response({
            'id':       u.pk,
            'username': u.username,
            'role':     u.role,
        }, status=201)


class AdminUserDetailView(APIView):
    """GET /api/admin/users/<pk>/detail/   PATCH /api/admin/users/<pk>/detail/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.accounts.models import CustomUser
        try:
            u = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=404)
        return Response({
            'id':         u.pk,
            'username':   u.username,
            'email':      u.email,
            'first_name': u.first_name,
            'last_name':  u.last_name,
            'telephone':  u.telephone,
            'role':       u.role,
            'is_active':  u.is_active,
            'is_verified': u.is_verified,
        })

    def patch(self, request, pk):
        from apps.accounts.models import CustomUser
        try:
            u = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=404)

        if u.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Impossible de modifier un superadmin.'}, status=403)

        data = request.data
        if data.get('email'):      u.email      = data['email']
        if 'first_name' in data:   u.first_name = data['first_name']
        if 'last_name' in data:    u.last_name  = data['last_name']
        if 'telephone' in data:    u.telephone  = data['telephone']
        if data.get('role'):       u.role       = data['role']
        if 'is_active' in data:    u.is_active  = data['is_active'] in ('true', '1', True)
        if 'is_verified' in data:  u.is_verified = data['is_verified'] in ('true', '1', True)
        if data.get('password'):
            u.set_password(data['password'])
        u.save()
        return Response({'id': u.pk, 'username': u.username, 'role': u.role})


# ── Producteurs — CREATE + DETAIL EDIT ───────────────────────────────────────

class AdminProducteurCreateView(APIView):
    """POST /api/admin/producteurs/create/  — crée user + profil producteur"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        from apps.accounts.models import CustomUser
        from apps.accounts.models.producteur import Producteur

        data = request.data
        errors = {}
        for f in ('username', 'email', 'first_name', 'last_name', 'password', 'departement', 'commune'):
            if not data.get(f):
                errors[f] = 'Champ requis.'
        if errors:
            return Response(errors, status=400)

        if CustomUser.objects.filter(username=data['username']).exists():
            return Response({'username': 'Ce nom d\'utilisateur est déjà pris.'}, status=400)

        from django.db import transaction
        with transaction.atomic():
            u = CustomUser(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                telephone=data.get('telephone', ''),
                role='producteur',
                is_active=True,
            )
            u.set_password(data['password'])
            u.save()

            p = Producteur(
                user=u,
                departement=data['departement'],
                commune=data['commune'],
                localite=data.get('localite', ''),
                adresse_complete=data.get('adresse_complete', ''),
                superficie_ha=data.get('superficie_ha') or None,
                description=data.get('description', ''),
                num_identification=data.get('num_identification', ''),
                statut=data.get('statut', Producteur.Statut.EN_ATTENTE),
            )
            if 'photo_identite' in request.FILES:
                p.photo_identite = request.FILES['photo_identite']
            p.save()

        return Response({
            'id':              p.pk,
            'code_producteur': p.code_producteur,
            'nom':             u.get_full_name(),
        }, status=201)


class AdminProducteurDetailView(APIView):
    """GET /api/admin/producteurs/<pk>/detail/   PATCH /api/admin/producteurs/<pk>/detail/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.accounts.models.producteur import Producteur
        try:
            p = Producteur.objects.select_related('user').get(pk=pk)
        except Producteur.DoesNotExist:
            return Response({'detail': 'Producteur introuvable.'}, status=404)
        return Response({
            'id':               p.pk,
            'code_producteur':  p.code_producteur,
            'user_id':          p.user.pk,
            'username':         p.user.username,
            'email':            p.user.email,
            'first_name':       p.user.first_name,
            'last_name':        p.user.last_name,
            'telephone':        p.user.telephone,
            'departement':      p.departement,
            'commune':          p.commune,
            'localite':         p.localite,
            'adresse_complete': p.adresse_complete,
            'superficie_ha':    str(p.superficie_ha) if p.superficie_ha else '',
            'description':      p.description,
            'num_identification': p.num_identification,
            'statut':           p.statut,
            'note_admin':       p.note_admin,
        })

    def patch(self, request, pk):
        from apps.accounts.models.producteur import Producteur
        try:
            p = Producteur.objects.select_related('user').get(pk=pk)
        except Producteur.DoesNotExist:
            return Response({'detail': 'Producteur introuvable.'}, status=404)

        data = request.data
        u = p.user
        if 'first_name' in data:     u.first_name = data['first_name']
        if 'last_name' in data:      u.last_name  = data['last_name']
        if data.get('email'):        u.email      = data['email']
        if 'telephone' in data:      u.telephone  = data['telephone']
        if data.get('password'):     u.set_password(data['password'])
        u.save()

        if data.get('departement'):        p.departement       = data['departement']
        if data.get('commune'):            p.commune           = data['commune']
        if 'localite' in data:             p.localite          = data['localite']
        if 'adresse_complete' in data:     p.adresse_complete  = data['adresse_complete']
        if 'superficie_ha' in data:        p.superficie_ha     = data['superficie_ha'] or None
        if 'description' in data:          p.description       = data['description']
        if 'num_identification' in data:   p.num_identification = data['num_identification']
        if 'note_admin' in data:           p.note_admin        = data['note_admin']
        if 'photo_identite' in request.FILES:
            p.photo_identite = request.FILES['photo_identite']
        p.save()
        return Response({'id': p.pk, 'code_producteur': p.code_producteur})


# ── Collectes — CREATE + FULL EDIT + PARTICIPATIONS ──────────────────────────

class AdminCollecteCreateView(APIView):
    """POST /api/admin/collectes/create/"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        from apps.collectes.models import Collecte, ZoneCollecte, PointCollecte
        from apps.accounts.models import CustomUser

        data = request.data
        if not data.get('zone_id') or not data.get('date_planifiee'):
            return Response({'detail': 'zone_id et date_planifiee sont requis.'}, status=400)

        try:
            zone = ZoneCollecte.objects.get(pk=data['zone_id'])
        except ZoneCollecte.DoesNotExist:
            return Response({'zone_id': 'Zone introuvable.'}, status=400)

        point = None
        if data.get('point_collecte_id'):
            try:
                point = PointCollecte.objects.get(pk=data['point_collecte_id'])
            except PointCollecte.DoesNotExist:
                pass

        collecteur = None
        if data.get('collecteur_id'):
            try:
                collecteur = CustomUser.objects.get(pk=data['collecteur_id'])
            except CustomUser.DoesNotExist:
                pass

        c = Collecte(
            zone=zone,
            point_collecte=point,
            collecteur=collecteur,
            date_planifiee=data['date_planifiee'],
            heure_debut=data.get('heure_debut') or None,
            heure_fin=data.get('heure_fin') or None,
            notes=data.get('notes', ''),
            statut=Collecte.Statut.PLANIFIEE,
        )
        c.save()
        return Response({'id': c.pk, 'reference': c.reference, 'statut': c.statut}, status=201)


class AdminCollecteEditView(APIView):
    """PATCH /api/admin/collectes/<pk>/edit/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.collectes.models import Collecte, ZoneCollecte, PointCollecte
        from apps.accounts.models import CustomUser

        try:
            c = Collecte.objects.get(pk=pk)
        except Collecte.DoesNotExist:
            return Response({'detail': 'Collecte introuvable.'}, status=404)

        data = request.data
        if data.get('zone_id'):
            try:
                c.zone = ZoneCollecte.objects.get(pk=data['zone_id'])
            except ZoneCollecte.DoesNotExist:
                pass
        if 'point_collecte_id' in data:
            c.point_collecte = PointCollecte.objects.filter(pk=data['point_collecte_id']).first() if data['point_collecte_id'] else None
        if 'collecteur_id' in data:
            c.collecteur = CustomUser.objects.filter(pk=data['collecteur_id']).first() if data['collecteur_id'] else None
        if data.get('date_planifiee'): c.date_planifiee = data['date_planifiee']
        if 'heure_debut' in data:      c.heure_debut    = data['heure_debut'] or None
        if 'heure_fin' in data:        c.heure_fin      = data['heure_fin'] or None
        if 'notes' in data:            c.notes          = data['notes']
        if 'rapport' in data:          c.rapport        = data['rapport']
        c.save()
        return Response({'id': c.pk, 'reference': c.reference})


class AdminCollecteAddParticipationView(APIView):
    """POST /api/admin/collectes/<pk>/participations/"""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request, pk):
        from apps.collectes.models import Collecte, ParticipationCollecte
        from apps.accounts.models.producteur import Producteur

        try:
            c = Collecte.objects.get(pk=pk)
        except Collecte.DoesNotExist:
            return Response({'detail': 'Collecte introuvable.'}, status=404)

        producteur_id = request.data.get('producteur_id')
        if not producteur_id:
            return Response({'detail': 'producteur_id requis.'}, status=400)

        try:
            prod = Producteur.objects.get(pk=producteur_id)
        except Producteur.DoesNotExist:
            return Response({'detail': 'Producteur introuvable.'}, status=400)

        if ParticipationCollecte.objects.filter(collecte=c, producteur=prod).exists():
            return Response({'detail': 'Ce producteur est déjà inscrit à cette collecte.'}, status=400)

        p = ParticipationCollecte.objects.create(
            collecte=c,
            producteur=prod,
            quantite_prevue=int(request.data.get('quantite_prevue') or 0),
            notes=request.data.get('notes', ''),
            statut=ParticipationCollecte.Statut.INSCRIT,
        )
        return Response({
            'id':             p.pk,
            'producteur_nom': prod.user.get_full_name() or prod.user.username,
            'statut':         p.statut,
            'statut_label':   p.get_statut_display(),
        }, status=201)


class AdminParticipationDeleteView(APIView):
    """DELETE /api/admin/collectes/participations/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def delete(self, request, pk):
        from apps.collectes.models import ParticipationCollecte
        try:
            p = ParticipationCollecte.objects.get(pk=pk)
        except ParticipationCollecte.DoesNotExist:
            return Response({'detail': 'Participation introuvable.'}, status=404)
        p.delete()
        return Response(status=204)


# ── Acheteurs ─────────────────────────────────────────────────────────────────

class AdminAcheteursView(APIView):
    """GET /api/admin/acheteurs/?search=&type="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.accounts.models.acheteur import Acheteur
        qs = Acheteur.objects.select_related('user').order_by('-created_at')
        search = request.GET.get('search', '').strip()
        type_  = request.GET.get('type', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(nom_organisation__icontains=search)
            )
        if type_:
            qs = qs.filter(type_acheteur=type_)
        data = []
        for a in qs[:200]:
            data.append({
                'id':               a.pk,
                'user_id':          a.user.pk,
                'full_name':        a.user.get_full_name() or a.user.username,
                'email':            a.user.email,
                'telephone':        a.user.telephone,
                'type_acheteur':    a.type_acheteur,
                'type_label':       a.get_type_acheteur_display(),
                'nom_organisation': a.nom_organisation,
                'departement':      a.departement,
                'total_commandes':  a.total_commandes,
                'total_depense':    float(a.total_depense),
                'is_active':        a.user.is_active,
                'created_at':       a.created_at.isoformat(),
            })
        return Response(data)


class AdminAcheteurDetailView(APIView):
    """GET /PATCH /api/admin/acheteurs/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.accounts.models.acheteur import Acheteur
        try:
            a = Acheteur.objects.select_related('user').get(pk=pk)
        except Acheteur.DoesNotExist:
            return Response({'detail': 'Acheteur introuvable.'}, status=404)
        return Response({
            'id':               a.pk,
            'user_id':          a.user.pk,
            'full_name':        a.user.get_full_name() or a.user.username,
            'email':            a.user.email,
            'telephone':        a.user.telephone,
            'type_acheteur':    a.type_acheteur,
            'nom_organisation': a.nom_organisation,
            'adresse':          a.adresse,
            'ville':            a.ville,
            'departement':      a.departement,
            'total_commandes':  a.total_commandes,
            'total_depense':    float(a.total_depense),
            'is_active':        a.user.is_active,
        })

    def patch(self, request, pk):
        from apps.accounts.models.acheteur import Acheteur
        try:
            a = Acheteur.objects.select_related('user').get(pk=pk)
        except Acheteur.DoesNotExist:
            return Response({'detail': 'Acheteur introuvable.'}, status=404)
        data = request.data
        if data.get('type_acheteur'):    a.type_acheteur    = data['type_acheteur']
        if 'nom_organisation' in data:   a.nom_organisation = data['nom_organisation']
        if 'departement' in data:        a.departement      = data['departement']
        if 'is_active' in data:
            a.user.is_active = data['is_active'] in ('true', '1', True)
            a.user.save(update_fields=['is_active'])
        a.save()
        return Response({'id': a.pk, 'type_acheteur': a.type_acheteur})


# ── Adresses ──────────────────────────────────────────────────────────────────

class AdminAdressesView(APIView):
    """GET /api/admin/adresses/?user_id=&search=&type="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.accounts.models.adresse import Adresse
        qs = Adresse.objects.select_related('user').order_by('-created_at')
        search  = request.GET.get('search', '').strip()
        user_id = request.GET.get('user_id', '').strip()
        type_   = request.GET.get('type', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(nom_complet__icontains=search) |
                Q(commune__icontains=search)
            )
        if user_id:
            qs = qs.filter(user_id=user_id)
        if type_:
            qs = qs.filter(type_adresse=type_)
        data = []
        for ad in qs[:200]:
            data.append({
                'id':               ad.pk,
                'user_id':          ad.user.pk,
                'user_nom':         ad.user.get_full_name() or ad.user.username,
                'libelle':          ad.libelle,
                'nom_complet':      ad.nom_complet,
                'telephone':        ad.telephone,
                'rue':              ad.rue,
                'commune':          ad.commune,
                'departement':      ad.departement,
                'section_communale': ad.section_communale,
                'type_adresse':     ad.type_adresse,
                'type_label':       ad.get_type_adresse_display(),
                'is_default':       ad.is_default,
                'created_at':       ad.created_at.isoformat(),
            })
        return Response(data)


# ── Catégories du catalogue ───────────────────────────────────────────────────

class AdminCategoriesView(APIView):
    """GET /api/admin/categories/   POST create"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.catalog.models import Categorie
        qs = Categorie.objects.all().order_by('ordre', 'nom')
        data = []
        for c in qs:
            data.append({
                'id':         c.pk,
                'nom':        c.nom,
                'slug':       c.slug,
                'parent_id':  c.parent_id,
                'parent_nom': c.parent.nom if c.parent else None,
                'icone':      c.icone,
                'ordre':      c.ordre,
                'is_active':  c.is_active,
                'nb_produits': c.nb_produits,
            })
        return Response(data)

    def post(self, request):
        from apps.catalog.models import Categorie
        from django.utils.text import slugify
        data = request.data
        if not data.get('nom'):
            return Response({'nom': 'Champ requis.'}, status=400)
        nom  = data['nom'].strip()
        slug = slugify(nom)
        # S'assurer de l'unicité du slug
        base, i = slug, 1
        while Categorie.objects.filter(slug=slug).exists():
            slug = f'{base}-{i}'; i += 1
        c = Categorie(
            nom=nom,
            slug=slug,
            icone=data.get('icone', 'fas fa-leaf'),
            ordre=int(data.get('ordre', 0)),
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        if data.get('parent_id'):
            try:
                c.parent = Categorie.objects.get(pk=data['parent_id'])
            except Categorie.DoesNotExist:
                pass
        c.save()
        return Response({'id': c.pk, 'nom': c.nom, 'slug': c.slug}, status=201)


class AdminCategorieDetailView(APIView):
    """GET /PATCH /DELETE /api/admin/categories/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.catalog.models import Categorie
        try:
            c = Categorie.objects.get(pk=pk)
        except Categorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=404)
        return Response({
            'id':        c.pk,
            'nom':       c.nom,
            'slug':      c.slug,
            'parent_id': c.parent_id,
            'icone':     c.icone,
            'ordre':     c.ordre,
            'is_active': c.is_active,
        })

    def patch(self, request, pk):
        from apps.catalog.models import Categorie
        try:
            c = Categorie.objects.get(pk=pk)
        except Categorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=404)
        data = request.data
        if data.get('nom'):       c.nom      = data['nom']
        if 'icone' in data:       c.icone    = data['icone']
        if 'ordre' in data:       c.ordre    = int(data['ordre'])
        if 'is_active' in data:   c.is_active = data['is_active'] not in ('false', '0', False)
        if 'parent_id' in data:
            c.parent = Categorie.objects.filter(pk=data['parent_id']).first() if data['parent_id'] else None
        c.save()
        return Response({'id': c.pk, 'nom': c.nom})

    def delete(self, request, pk):
        from apps.catalog.models import Categorie
        try:
            c = Categorie.objects.get(pk=pk)
        except Categorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=404)
        if c.produits.exists():
            return Response({'detail': 'Impossible de supprimer une catégorie avec des produits.'}, status=400)
        c.delete()
        return Response(status=204)


# ── Programmes Voucher ────────────────────────────────────────────────────────

class AdminVoucherProgrammesView(APIView):
    """GET /api/admin/vouchers/programmes/   POST create"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.payments.models import ProgrammeVoucher
        qs = ProgrammeVoucher.objects.order_by('-created_at')
        data = []
        for p in qs:
            data.append({
                'id':             p.pk,
                'nom':            p.nom,
                'code_programme': p.code_programme,
                'type_programme': p.type_programme,
                'type_label':     p.get_type_programme_display(),
                'budget_total':   float(p.budget_total),
                'budget_utilise': float(p.budget_utilise),
                'budget_restant': float(p.budget_restant),
                'nb_vouchers':    p.vouchers.count(),
                'is_active':      p.is_active,
                'est_en_cours':   p.est_en_cours,
                'date_debut':     str(p.date_debut) if p.date_debut else None,
                'date_fin':       str(p.date_fin) if p.date_fin else None,
                'contact_nom':    p.contact_nom,
                'contact_email':  p.contact_email,
            })
        return Response(data)

    def post(self, request):
        from apps.payments.models import ProgrammeVoucher
        data = request.data
        if not data.get('nom') or not data.get('type_programme'):
            return Response({'detail': 'nom et type_programme requis.'}, status=400)
        p = ProgrammeVoucher(
            nom=data['nom'],
            type_programme=data['type_programme'],
            description=data.get('description', ''),
            budget_total=float(data.get('budget_total', 0)),
            contact_nom=data.get('contact_nom', ''),
            contact_email=data.get('contact_email', ''),
            contact_tel=data.get('contact_tel', ''),
            date_debut=data.get('date_debut') or None,
            date_fin=data.get('date_fin') or None,
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        p.save()
        return Response({'id': p.pk, 'nom': p.nom, 'code_programme': p.code_programme}, status=201)


class AdminVoucherProgrammeDetailView(APIView):
    """GET /PATCH /api/admin/vouchers/programmes/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.payments.models import ProgrammeVoucher
        try:
            p = ProgrammeVoucher.objects.get(pk=pk)
        except ProgrammeVoucher.DoesNotExist:
            return Response({'detail': 'Programme introuvable.'}, status=404)
        return Response({
            'id':             p.pk,
            'nom':            p.nom,
            'code_programme': p.code_programme,
            'type_programme': p.type_programme,
            'description':    p.description,
            'budget_total':   float(p.budget_total),
            'budget_utilise': float(p.budget_utilise),
            'contact_nom':    p.contact_nom,
            'contact_email':  p.contact_email,
            'contact_tel':    p.contact_tel,
            'date_debut':     str(p.date_debut) if p.date_debut else '',
            'date_fin':       str(p.date_fin) if p.date_fin else '',
            'is_active':      p.is_active,
        })

    def patch(self, request, pk):
        from apps.payments.models import ProgrammeVoucher
        try:
            p = ProgrammeVoucher.objects.get(pk=pk)
        except ProgrammeVoucher.DoesNotExist:
            return Response({'detail': 'Programme introuvable.'}, status=404)
        data = request.data
        if data.get('nom'):           p.nom            = data['nom']
        if 'description' in data:     p.description    = data['description']
        if 'budget_total' in data:    p.budget_total   = float(data['budget_total'])
        if 'contact_nom' in data:     p.contact_nom    = data['contact_nom']
        if 'contact_email' in data:   p.contact_email  = data['contact_email']
        if 'contact_tel' in data:     p.contact_tel    = data['contact_tel']
        if 'date_debut' in data:      p.date_debut     = data['date_debut'] or None
        if 'date_fin' in data:        p.date_fin       = data['date_fin'] or None
        if 'is_active' in data:       p.is_active      = data['is_active'] not in ('false', '0', False)
        p.save()
        return Response({'id': p.pk, 'nom': p.nom, 'is_active': p.is_active})


class AdminVouchersView(APIView):
    """GET /api/admin/vouchers/?statut=&programme_id=&search=    POST create"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.payments.models import Voucher
        qs = Voucher.objects.select_related('programme', 'beneficiaire__user').order_by('-created_at')
        statut       = request.GET.get('statut', '').strip()
        programme_id = request.GET.get('programme_id', '').strip()
        search       = request.GET.get('search', '').strip()
        if statut:       qs = qs.filter(statut=statut)
        if programme_id: qs = qs.filter(programme_id=programme_id)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(code__icontains=search) |
                Q(beneficiaire__user__first_name__icontains=search) |
                Q(beneficiaire__user__last_name__icontains=search)
            )
        data = []
        for v in qs[:200]:
            data.append({
                'id':               v.pk,
                'code':             v.code,
                'programme_nom':    v.programme.nom,
                'programme_id':     v.programme.pk,
                'beneficiaire_nom': str(v.beneficiaire) if v.beneficiaire else 'Ouvert',
                'type_valeur':      v.type_valeur,
                'valeur':           float(v.valeur),
                'statut':           v.statut,
                'statut_label':     v.get_statut_display(),
                'date_expiration':  str(v.date_expiration) if v.date_expiration else None,
                'date_utilisation': v.date_utilisation.isoformat() if v.date_utilisation else None,
                'created_at':       v.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        from apps.payments.models import ProgrammeVoucher, Voucher
        data = request.data
        if not data.get('programme_id') or not data.get('type_valeur') or not data.get('valeur'):
            return Response({'detail': 'programme_id, type_valeur et valeur requis.'}, status=400)
        try:
            prog = ProgrammeVoucher.objects.get(pk=data['programme_id'])
        except ProgrammeVoucher.DoesNotExist:
            return Response({'detail': 'Programme introuvable.'}, status=400)
        beneficiaire = None
        if data.get('beneficiaire_id'):
            from apps.accounts.models.acheteur import Acheteur
            beneficiaire = Acheteur.objects.filter(pk=data['beneficiaire_id']).first()
        v = Voucher(
            programme=prog,
            beneficiaire=beneficiaire,
            type_valeur=data['type_valeur'],
            valeur=float(data['valeur']),
            montant_commande_min=float(data.get('montant_commande_min', 0)),
            date_expiration=data.get('date_expiration') or None,
            cree_par=request.user,
        )
        v.save()
        return Response({'id': v.pk, 'code': v.code, 'statut': v.statut}, status=201)


class AdminVoucherDetailView(APIView):
    """PATCH /api/admin/vouchers/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.payments.models import Voucher
        try:
            v = Voucher.objects.get(pk=pk)
        except Voucher.DoesNotExist:
            return Response({'detail': 'Voucher introuvable.'}, status=404)
        data = request.data
        if data.get('statut'): v.statut = data['statut']
        if 'date_expiration' in data: v.date_expiration = data['date_expiration'] or None
        v.save()
        return Response({'id': v.pk, 'code': v.code, 'statut': v.statut})


# ── Zones & Points de collecte ────────────────────────────────────────────────

class AdminZonesCollecteView(APIView):
    """GET /api/admin/zones/   POST create"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.collectes.models import ZoneCollecte
        qs = ZoneCollecte.objects.order_by('departement', 'nom')
        data = []
        for z in qs:
            data.append({
                'id':          z.pk,
                'nom':         z.nom,
                'departement': z.departement,
                'description': z.description,
                'nb_points':   z.points.filter(is_active=True).count(),
                'nb_collectes': z.collectes.count(),
                'is_active':   z.is_active,
            })
        return Response(data)

    def post(self, request):
        from apps.collectes.models import ZoneCollecte
        data = request.data
        if not data.get('nom') or not data.get('departement'):
            return Response({'detail': 'nom et departement requis.'}, status=400)
        z = ZoneCollecte(
            nom=data['nom'],
            departement=data['departement'],
            description=data.get('description', ''),
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        z.save()
        return Response({'id': z.pk, 'nom': z.nom}, status=201)


class AdminZoneCollecteDetailView(APIView):
    """GET /PATCH /DELETE /api/admin/zones/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request, pk):
        from apps.collectes.models import ZoneCollecte, PointCollecte
        try:
            z = ZoneCollecte.objects.get(pk=pk)
        except ZoneCollecte.DoesNotExist:
            return Response({'detail': 'Zone introuvable.'}, status=404)
        points = PointCollecte.objects.filter(zone=z).order_by('nom')
        return Response({
            'id':          z.pk,
            'nom':         z.nom,
            'departement': z.departement,
            'description': z.description,
            'is_active':   z.is_active,
            'points': [{
                'id': p.pk, 'nom': p.nom, 'commune': p.commune,
                'responsable': p.responsable, 'telephone': p.telephone,
                'adresse': p.adresse, 'is_active': p.is_active,
            } for p in points],
        })

    def patch(self, request, pk):
        from apps.collectes.models import ZoneCollecte
        try:
            z = ZoneCollecte.objects.get(pk=pk)
        except ZoneCollecte.DoesNotExist:
            return Response({'detail': 'Zone introuvable.'}, status=404)
        data = request.data
        if data.get('nom'):         z.nom         = data['nom']
        if 'departement' in data:   z.departement = data['departement']
        if 'description' in data:   z.description = data['description']
        if 'is_active' in data:     z.is_active   = data['is_active'] not in ('false', '0', False)
        z.save()
        return Response({'id': z.pk, 'nom': z.nom})

    def delete(self, request, pk):
        from apps.collectes.models import ZoneCollecte
        try:
            z = ZoneCollecte.objects.get(pk=pk)
        except ZoneCollecte.DoesNotExist:
            return Response({'detail': 'Zone introuvable.'}, status=404)
        if z.collectes.exists():
            return Response({'detail': 'Impossible de supprimer une zone avec des collectes.'}, status=400)
        z.delete()
        return Response(status=204)


class AdminPointsCollecteView(APIView):
    """GET /api/admin/points/?zone_id=   POST create"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.collectes.models import PointCollecte
        qs = PointCollecte.objects.select_related('zone').order_by('zone__nom', 'nom')
        zone_id = request.GET.get('zone_id', '').strip()
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        data = []
        for p in qs:
            data.append({
                'id':          p.pk,
                'nom':         p.nom,
                'zone_id':     p.zone.pk,
                'zone_nom':    p.zone.nom,
                'commune':     p.commune,
                'adresse':     p.adresse,
                'responsable': p.responsable,
                'telephone':   p.telephone,
                'is_active':   p.is_active,
            })
        return Response(data)

    def post(self, request):
        from apps.collectes.models import ZoneCollecte, PointCollecte
        data = request.data
        if not data.get('zone_id') or not data.get('nom') or not data.get('commune'):
            return Response({'detail': 'zone_id, nom et commune requis.'}, status=400)
        try:
            zone = ZoneCollecte.objects.get(pk=data['zone_id'])
        except ZoneCollecte.DoesNotExist:
            return Response({'detail': 'Zone introuvable.'}, status=400)
        p = PointCollecte(
            zone=zone,
            nom=data['nom'],
            commune=data['commune'],
            adresse=data.get('adresse', ''),
            responsable=data.get('responsable', ''),
            telephone=data.get('telephone', ''),
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        p.save()
        return Response({'id': p.pk, 'nom': p.nom}, status=201)


class AdminPointCollecteDetailView(APIView):
    """PATCH /DELETE /api/admin/points/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.collectes.models import PointCollecte
        try:
            p = PointCollecte.objects.get(pk=pk)
        except PointCollecte.DoesNotExist:
            return Response({'detail': 'Point introuvable.'}, status=404)
        data = request.data
        if data.get('nom'):        p.nom        = data['nom']
        if 'commune' in data:      p.commune    = data['commune']
        if 'adresse' in data:      p.adresse    = data['adresse']
        if 'responsable' in data:  p.responsable = data['responsable']
        if 'telephone' in data:    p.telephone  = data['telephone']
        if 'is_active' in data:    p.is_active  = data['is_active'] not in ('false', '0', False)
        p.save()
        return Response({'id': p.pk, 'nom': p.nom})

    def delete(self, request, pk):
        from apps.collectes.models import PointCollecte
        try:
            p = PointCollecte.objects.get(pk=pk)
        except PointCollecte.DoesNotExist:
            return Response({'detail': 'Point introuvable.'}, status=404)
        p.delete()
        return Response(status=204)


# ── Mouvements de stock ───────────────────────────────────────────────────────

class AdminStocksMouvementsView(APIView):
    """GET /api/admin/stocks/mouvements/?type=&produit_id="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.stock.models import MouvementStock
        qs = MouvementStock.objects.select_related(
            'produit__producteur__user', 'lot', 'effectue_par'
        ).order_by('-created_at')
        type_      = request.GET.get('type', '').strip()
        produit_id = request.GET.get('produit_id', '').strip()
        search     = request.GET.get('search', '').strip()
        if type_:       qs = qs.filter(type_mouvement=type_)
        if produit_id:  qs = qs.filter(produit_id=produit_id)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(produit__nom__icontains=search) |
                Q(lot__numero_lot__icontains=search) |
                Q(motif__icontains=search)
            )
        data = []
        for m in qs[:200]:
            data.append({
                'id':              m.pk,
                'produit_nom':     m.produit.nom,
                'lot_numero':      m.lot.numero_lot if m.lot else '—',
                'type_mouvement':  m.type_mouvement,
                'type_label':      m.get_type_mouvement_display(),
                'quantite':        m.quantite,
                'stock_avant':     m.stock_avant,
                'stock_apres':     m.stock_apres,
                'motif':           m.motif,
                'effectue_par':    m.effectue_par.get_full_name() if m.effectue_par else '—',
                'created_at':      m.created_at.isoformat(),
            })
        return Response(data)


# ── Configuration du site ─────────────────────────────────────────────────────

class AdminSiteSettingsView(APIView):
    """GET /api/admin/config/site/   PATCH"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.core.models import SiteSettings
        s = SiteSettings.get_solo()
        return Response({
            'nom_site':          s.nom_site,
            'slogan':            s.slogan,
            'logo':              request.build_absolute_uri(s.logo.url) if s.logo else None,
            'favicon':           request.build_absolute_uri(s.favicon.url) if s.favicon else None,
            # Hero
            'hero_badge_texte':  s.hero_badge_texte,
            'hero_titre_ligne1': s.hero_titre_ligne1,
            'hero_titre_ligne2': s.hero_titre_ligne2,
            'hero_sous_titre':   s.hero_sous_titre,
            # À propos
            'a_propos_titre':    s.a_propos_titre,
            'a_propos_contenu':  s.a_propos_contenu,
            'a_propos_mission':  s.a_propos_mission,
            'a_propos_vision':   s.a_propos_vision,
            'annee_fondation':   s.annee_fondation,
            # Contact
            'email_contact':     s.email_contact,
            'telephone':         s.telephone,
            'whatsapp':          s.whatsapp,
            'adresse':           s.adresse,
            'horaires':          s.horaires,
            # Réseaux sociaux
            'facebook_url':      s.facebook_url,
            'instagram_url':     s.instagram_url,
            'twitter_url':       s.twitter_url,
            'youtube_url':       s.youtube_url,
            # Footer & SEO
            'copyright_texte':   s.copyright_texte,
            'meta_description':  s.meta_description,
            'google_analytics_id': s.google_analytics_id,
            # Maintenance
            'mode_maintenance':      s.mode_maintenance,
            'message_maintenance':   s.message_maintenance,
        })

    def patch(self, request):
        from apps.core.models import SiteSettings
        s    = SiteSettings.get_solo()
        data = request.data
        text_fields = [
            'nom_site', 'slogan', 'hero_badge_texte', 'hero_titre_ligne1',
            'hero_titre_ligne2', 'hero_sous_titre', 'a_propos_titre',
            'a_propos_contenu', 'a_propos_mission', 'a_propos_vision',
            'email_contact', 'telephone', 'whatsapp', 'adresse', 'horaires',
            'facebook_url', 'instagram_url', 'twitter_url', 'youtube_url',
            'copyright_texte', 'meta_description', 'google_analytics_id',
            'message_maintenance',
        ]
        for f in text_fields:
            if f in data:
                setattr(s, f, data[f])
        if 'annee_fondation' in data:
            s.annee_fondation = int(data['annee_fondation']) if data['annee_fondation'] else None
        if 'mode_maintenance' in data:
            s.mode_maintenance = data['mode_maintenance'] not in ('false', '0', False)
        # Fichiers images
        for img_field in ('logo', 'favicon', 'login_image', 'register_image', 'a_propos_image'):
            if img_field in request.FILES:
                setattr(s, img_field, request.FILES[img_field])
        s.save()
        return Response({'detail': 'Paramètres mis à jour.'})


class AdminFAQCategoriesView(APIView):
    """GET /api/admin/config/faq/categories/   POST"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.core.models import FAQCategorie
        data = []
        for c in FAQCategorie.objects.all().order_by('ordre'):
            data.append({
                'id':        c.pk,
                'titre':     c.titre,
                'icone':     c.icone,
                'ordre':     c.ordre,
                'is_active': c.is_active,
                'nb_items':  c.items.filter(is_active=True).count(),
            })
        return Response(data)

    def post(self, request):
        from apps.core.models import FAQCategorie
        data = request.data
        if not data.get('titre'):
            return Response({'titre': 'Champ requis.'}, status=400)
        c = FAQCategorie(
            titre=data['titre'],
            icone=data.get('icone', 'fas fa-question-circle'),
            ordre=int(data.get('ordre', 0)),
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        c.save()
        return Response({'id': c.pk, 'titre': c.titre}, status=201)


class AdminFAQCategorieDetailView(APIView):
    """PATCH /DELETE /api/admin/config/faq/categories/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.core.models import FAQCategorie
        try:
            c = FAQCategorie.objects.get(pk=pk)
        except FAQCategorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=404)
        data = request.data
        if data.get('titre'):   c.titre    = data['titre']
        if 'icone' in data:     c.icone    = data['icone']
        if 'ordre' in data:     c.ordre    = int(data['ordre'])
        if 'is_active' in data: c.is_active = data['is_active'] not in ('false', '0', False)
        c.save()
        return Response({'id': c.pk, 'titre': c.titre})

    def delete(self, request, pk):
        from apps.core.models import FAQCategorie
        try:
            c = FAQCategorie.objects.get(pk=pk)
        except FAQCategorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=404)
        c.delete()
        return Response(status=204)


class AdminFAQItemsView(APIView):
    """GET /api/admin/config/faq/items/?categorie_id=   POST"""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.core.models import FAQItem
        qs = FAQItem.objects.select_related('categorie').order_by('categorie__ordre', 'ordre')
        cat_id = request.GET.get('categorie_id', '').strip()
        if cat_id:
            qs = qs.filter(categorie_id=cat_id)
        data = []
        for item in qs:
            data.append({
                'id':           item.pk,
                'categorie_id': item.categorie.pk,
                'categorie':    item.categorie.titre,
                'question':     item.question,
                'reponse':      item.reponse,
                'ordre':        item.ordre,
                'is_active':    item.is_active,
            })
        return Response(data)

    def post(self, request):
        from apps.core.models import FAQItem, FAQCategorie
        data = request.data
        if not data.get('question') or not data.get('reponse') or not data.get('categorie_id'):
            return Response({'detail': 'question, reponse et categorie_id requis.'}, status=400)
        try:
            cat = FAQCategorie.objects.get(pk=data['categorie_id'])
        except FAQCategorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=400)
        item = FAQItem(
            categorie=cat,
            question=data['question'],
            reponse=data['reponse'],
            ordre=int(data.get('ordre', 0)),
            is_active=data.get('is_active', True) not in ('false', '0', False),
        )
        item.save()
        return Response({'id': item.pk, 'question': item.question[:60]}, status=201)


class AdminFAQItemDetailView(APIView):
    """PATCH /DELETE /api/admin/config/faq/items/<pk>/"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.core.models import FAQItem, FAQCategorie
        try:
            item = FAQItem.objects.get(pk=pk)
        except FAQItem.DoesNotExist:
            return Response({'detail': 'Question introuvable.'}, status=404)
        data = request.data
        if data.get('question'):    item.question  = data['question']
        if 'reponse' in data:       item.reponse   = data['reponse']
        if 'ordre' in data:         item.ordre     = int(data['ordre'])
        if 'is_active' in data:     item.is_active = data['is_active'] not in ('false', '0', False)
        if data.get('categorie_id'):
            item.categorie = FAQCategorie.objects.filter(pk=data['categorie_id']).first() or item.categorie
        item.save()
        return Response({'id': item.pk})

    def delete(self, request, pk):
        from apps.core.models import FAQItem
        try:
            item = FAQItem.objects.get(pk=pk)
        except FAQItem.DoesNotExist:
            return Response({'detail': 'Question introuvable.'}, status=404)
        item.delete()
        return Response(status=204)


class AdminContactMessagesView(APIView):
    """GET /api/admin/config/contact/?est_lu="""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        from apps.core.models import ContactMessage
        qs = ContactMessage.objects.order_by('-created_at')
        est_lu = request.GET.get('est_lu', '').strip()
        if est_lu in ('true', 'false'):
            qs = qs.filter(est_lu=(est_lu == 'true'))
        data = []
        for m in qs[:200]:
            data.append({
                'id':        m.pk,
                'nom':       m.nom,
                'email':     m.email,
                'telephone': m.telephone,
                'sujet':     m.sujet,
                'message':   m.message,
                'est_lu':    m.est_lu,
                'created_at': m.created_at.isoformat(),
            })
        return Response(data)


class AdminContactMessageDetailView(APIView):
    """PATCH /api/admin/config/contact/<pk>/  — marquer lu/non-lu"""
    permission_classes = [IsAdminOrSuperuser]

    def patch(self, request, pk):
        from apps.core.models import ContactMessage
        try:
            m = ContactMessage.objects.get(pk=pk)
        except ContactMessage.DoesNotExist:
            return Response({'detail': 'Message introuvable.'}, status=404)
        if 'est_lu' in request.data:
            m.est_lu = request.data['est_lu'] not in ('false', '0', False)
            m.save(update_fields=['est_lu'])
        return Response({'id': m.pk, 'est_lu': m.est_lu})
