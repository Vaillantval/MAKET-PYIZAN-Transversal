from collections import defaultdict

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.catalog.models import Produit
from apps.orders.services.cart_service import CartService


class PanierView(APIView):
    """
    GET  /api/orders/panier/  — résumé du panier courant
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(CartService.resume(request))


class PanierAjouterView(APIView):
    """
    POST /api/orders/panier/ajouter/
    Body: { "slug": "<slug>", "quantite": <int> }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        slug     = request.data.get('slug', '').strip()
        quantite = int(request.data.get('quantite', 1))

        if not slug:
            return Response({'detail': "Le champ 'slug' est requis."}, status=status.HTTP_400_BAD_REQUEST)
        if quantite < 1:
            return Response({'detail': "La quantité doit être au moins 1."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            produit = Produit.objects.select_related('producteur__user').get(slug=slug, is_active=True)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable ou indisponible.'}, status=status.HTTP_404_NOT_FOUND)

        if produit.stock_reel < quantite:
            return Response(
                {'detail': f"Stock insuffisant. Disponible : {produit.stock_reel} {produit.get_unite_vente_display()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        panier = CartService.ajouter(request, produit, quantite)
        return Response({'message': 'Produit ajouté au panier.', 'panier': panier}, status=status.HTTP_200_OK)


class PanierRetirerView(APIView):
    """
    DELETE /api/orders/panier/retirer/<slug>/
    """
    permission_classes = [AllowAny]

    def delete(self, request, slug):
        panier = CartService.retirer(request, slug)
        return Response({'message': 'Article retiré.', 'panier': panier})


class PanierModifierView(APIView):
    """
    PATCH /api/orders/panier/modifier/<slug>/
    Body: { "quantite": <int> }
    """
    permission_classes = [AllowAny]

    def patch(self, request, slug):
        quantite = request.data.get('quantite')
        if quantite is None:
            return Response({'detail': "Le champ 'quantite' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        # Vérifier le stock si augmentation
        try:
            quantite = int(quantite)
        except (ValueError, TypeError):
            return Response({'detail': "Quantité invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if quantite > 0:
            try:
                produit = Produit.objects.get(slug=slug, is_active=True)
                if produit.stock_reel < quantite:
                    return Response(
                        {'detail': f"Stock insuffisant. Disponible : {produit.stock_reel}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Produit.DoesNotExist:
                pass  # L'article sera supprimé si quantite <= 0 de toute façon

        panier = CartService.modifier_quantite(request, slug, quantite)
        return Response({'panier': panier})


class PanierViderView(APIView):
    """
    DELETE /api/orders/panier/vider/
    """
    permission_classes = [AllowAny]

    def delete(self, request):
        CartService.vider(request)
        return Response({'message': 'Panier vidé.'})


class CommanderView(APIView):
    """
    POST /api/orders/commander/
    Crée une ou plusieurs commandes à partir du panier session.
    Requiert un JWT valide (acheteur ou collecteur).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.orders.services.commande_service import CommandeService
        from apps.accounts.models import Adresse

        # ── 1. Profil acheteur ───────────────────────────────────────
        try:
            acheteur = request.user.profil_acheteur
        except Exception:
            return Response(
                {'detail': 'Seuls les acheteurs peuvent passer commande.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── 2. Panier ────────────────────────────────────────────────
        resume = CartService.resume(request)
        if not resume['items']:
            return Response({'detail': 'Le panier est vide.'}, status=status.HTTP_400_BAD_REQUEST)

        # ── 3. Paramètres ────────────────────────────────────────────
        methode_paiement = request.data.get('methode_paiement', 'cash')
        mode_livraison   = request.data.get('mode_livraison', 'domicile')
        notes            = request.data.get('notes', '')
        adresse_id       = request.data.get('adresse_livraison_id')
        adresse_text     = request.data.get('adresse_livraison_text', '')
        ville            = request.data.get('ville_livraison', '')
        departement      = request.data.get('departement_livraison', '')

        # ── 4. Résoudre l'adresse ─────────────────────────────────────
        if adresse_id:
            try:
                adresse_obj = Adresse.objects.get(pk=adresse_id, user=request.user)
                adresse_livraison = f"{adresse_obj.rue}, {adresse_obj.commune}"
                ville_livraison   = adresse_obj.commune
                dept_livraison    = adresse_obj.get_departement_display()
            except Adresse.DoesNotExist:
                return Response({'detail': 'Adresse introuvable.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not adresse_text:
                return Response(
                    {'detail': 'Une adresse de livraison est requise.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            adresse_livraison = adresse_text
            ville_livraison   = ville
            dept_livraison    = departement

        # ── 5. Regrouper par producteur ───────────────────────────────
        slugs = [item['slug'] for item in resume['items']]
        produits_map = {
            p.slug: p
            for p in Produit.objects.filter(
                slug__in=slugs, is_active=True
            ).select_related('producteur__user')
        }

        items_by_producteur = defaultdict(list)
        for item in resume['items']:
            produit = produits_map.get(item['slug'])
            if not produit:
                return Response(
                    {'detail': f"Produit '{item['slug']}' introuvable ou indisponible."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items_by_producteur[produit.producteur_id].append({
                'produit':  produit,
                'quantite': item['quantite'],
            })

        # ── 6. Créer une commande par producteur ──────────────────────
        commandes_creees = []
        try:
            for pid, items in items_by_producteur.items():
                producteur = items[0]['produit'].producteur
                commande = CommandeService.creer_commande(
                    acheteur=acheteur,
                    producteur=producteur,
                    items=items,
                    methode_paiement=methode_paiement,
                    mode_livraison=mode_livraison,
                    adresse_livraison=adresse_livraison,
                    notes=notes,
                )
                commande.ville_livraison       = ville_livraison
                commande.departement_livraison = dept_livraison
                commande.save(update_fields=['ville_livraison', 'departement_livraison'])
                commandes_creees.append(commande)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── 7. Post-traitement selon méthode de paiement ─────────────
        if methode_paiement == 'moncash':
            from apps.payments.services.moncash_service import MonCashService
            mc = MonCashService()
            if not mc.is_configured():
                return Response({'detail': 'MonCash non configuré.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Montant total toutes commandes
            montant_total = sum(c.total for c in commandes_creees)
            # Référence principale = première commande
            ref_principale = commandes_creees[0].numero_commande

            try:
                mc_data = mc.initier_paiement(ref_principale, float(montant_total))
            except Exception as e:
                # Annuler les commandes créées
                for c in commandes_creees:
                    c.statut = c.Statut.ANNULEE
                    c.save(update_fields=['statut'])
                return Response({'detail': f'Erreur MonCash : {e}'}, status=status.HTTP_502_BAD_GATEWAY)

            # Stocker le token dans la référence de chaque commande
            for c in commandes_creees:
                c.reference_paiement = mc_data['token']
                c.statut_paiement    = c.StatutPaiement.EN_ATTENTE
                c.save(update_fields=['reference_paiement', 'statut_paiement'])

            CartService.vider(request)
            return Response({
                'redirect_url': mc_data['redirect_url'],
                'commandes': [
                    {
                        'numero_commande': c.numero_commande,
                        'producteur':      c.producteur.user.get_full_name(),
                        'total':           str(c.total),
                    }
                    for c in commandes_creees
                ],
            }, status=status.HTTP_200_OK)

        elif methode_paiement == 'hors_ligne':
            preuve = request.FILES.get('preuve_paiement')
            if preuve:
                for c in commandes_creees:
                    c.preuve_paiement = preuve
                    c.statut_paiement = c.StatutPaiement.PREUVE_SOUMISE
                    c.save(update_fields=['preuve_paiement', 'statut_paiement'])

        # ── 8. Vider le panier ────────────────────────────────────────
        CartService.vider(request)

        return Response({
            'message': f"{len(commandes_creees)} commande(s) créée(s) avec succès !",
            'commandes': [
                {
                    'numero_commande': c.numero_commande,
                    'producteur':      c.producteur.user.get_full_name(),
                    'total':           str(c.total),
                    'statut':          c.get_statut_display(),
                }
                for c in commandes_creees
            ],
        }, status=status.HTTP_201_CREATED)
