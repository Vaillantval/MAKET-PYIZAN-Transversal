from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Produit, Categorie


# ── API publique : détail d'un produit ───────────────────────────────────────

class ProduitPublicDetailView(APIView):
    """
    GET /api/products/public/<slug>/
    Accessible sans authentification.
    Retourne tous les attributs du produit + producteur + images + produits similaires.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            p = Produit.objects.select_related(
                'producteur__user', 'categorie'
            ).prefetch_related('images').get(slug=slug, is_active=True)
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        images = [
            {'url': img.image.url, 'legende': img.legende, 'ordre': img.ordre}
            for img in p.images.all()
        ]

        similaires = Produit.objects.filter(
            categorie=p.categorie, is_active=True
        ).exclude(pk=p.pk).select_related('producteur__user').order_by('-created_at')[:4]

        return Response({
            'id':                    p.pk,
            'nom':                   p.nom,
            'slug':                  p.slug,
            'description':           p.description,
            'variete':               p.variete,
            'prix_unitaire':         str(p.prix_unitaire),
            'prix_gros':             str(p.prix_gros) if p.prix_gros else '',
            'unite_vente':           p.unite_vente,
            'unite_vente_label':     p.get_unite_vente_display(),
            'quantite_min_commande': p.quantite_min_commande,
            'stock_reel':            p.stock_reel,
            'est_en_alerte':         p.est_en_alerte,
            'categorie': {
                'nom':  p.categorie.nom,
                'slug': p.categorie.slug,
            },
            'origine':        p.origine,
            'saison':         p.saison,
            'certifications': p.certifications,
            'image_principale': p.image_principale.url if p.image_principale else None,
            'images':         images,
            'qr_code':        p.qr_code.url if p.qr_code else None,
            'producteur': {
                'id':          p.producteur.pk,
                'nom':         p.producteur.user.get_full_name(),
                'commune':     p.producteur.commune,
                'departement': p.producteur.departement,
                'code':        p.producteur.code_producteur,
                'description': p.producteur.description,
            },
            'similaires': [
                {
                    'nom':            s.nom,
                    'slug':           s.slug,
                    'prix_unitaire':  str(s.prix_unitaire),
                    'unite_vente_label': s.get_unite_vente_display(),
                    'image':          s.image_principale.url if s.image_principale else None,
                    'producteur_nom': s.producteur.user.get_full_name(),
                }
                for s in similaires
            ],
        })


# ── API publique : catégories ─────────────────────────────────────────────────

class CategorieListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cats = Categorie.objects.filter(is_active=True, parent=None).order_by('ordre')
        data = [{'id': c.pk, 'nom': c.nom, 'slug': c.slug, 'icone': c.icone} for c in cats]
        return Response(data)


# ── API Producteur : gestion de son catalogue ─────────────────────────────────

def _get_producteur(user):
    try:
        return user.profil_producteur
    except Exception:
        return None


class MonCatalogueView(APIView):
    """
    GET  /api/products/mes-produits/  — liste les produits du producteur connecté
    POST /api/products/mes-produits/  — crée un nouveau produit
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_403_FORBIDDEN)

        qs = Produit.objects.filter(producteur=prod).select_related('categorie').order_by('-created_at')
        return Response([_serialize_produit(p) for p in qs])

    def post(self, request):
        prod = _get_producteur(request.user)
        if not prod:
            return Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        required = ['nom', 'prix_unitaire', 'unite_vente', 'stock_disponible', 'categorie_id']
        for f in required:
            if not data.get(f):
                return Response({'detail': f'Le champ {f} est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            categorie = Categorie.objects.get(pk=data['categorie_id'])
        except Categorie.DoesNotExist:
            return Response({'detail': 'Catégorie introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        p = Produit(
            producteur=prod,
            categorie=categorie,
            nom=data['nom'],
            description=data.get('description', ''),
            variete=data.get('variete', ''),
            prix_unitaire=data['prix_unitaire'],
            prix_gros=data.get('prix_gros') or None,
            unite_vente=data['unite_vente'],
            quantite_min_commande=data.get('quantite_min_commande', 1),
            stock_disponible=int(data['stock_disponible']),
            seuil_alerte=data.get('seuil_alerte', 10),
            origine=data.get('origine', ''),
            saison=data.get('saison', ''),
            certifications=data.get('certifications', ''),
            statut='en_attente',
            is_active=False,
        )
        if 'image_principale' in request.FILES:
            p.image_principale = request.FILES['image_principale']
        p.save()

        return Response(_serialize_produit(p), status=status.HTTP_201_CREATED)


class MonProduitDetailView(APIView):
    """
    GET    /api/products/mes-produits/<slug>/
    PATCH  /api/products/mes-produits/<slug>/
    DELETE /api/products/mes-produits/<slug>/
    """
    permission_classes = [IsAuthenticated]

    def _get_obj(self, request, slug):
        prod = _get_producteur(request.user)
        if not prod:
            return None, Response({'detail': 'Profil producteur introuvable.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            p = Produit.objects.select_related('categorie').get(slug=slug, producteur=prod)
            return p, None
        except Produit.DoesNotExist:
            return None, Response({'detail': 'Produit introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, slug):
        p, err = self._get_obj(request, slug)
        if err:
            return err
        return Response(_serialize_produit(p))

    def patch(self, request, slug):
        p, err = self._get_obj(request, slug)
        if err:
            return err

        data = request.data
        editable = [
            'nom', 'description', 'variete', 'prix_unitaire', 'prix_gros',
            'unite_vente', 'quantite_min_commande', 'stock_disponible',
            'seuil_alerte', 'origine', 'saison', 'certifications',
        ]
        for field in editable:
            if field in data:
                setattr(p, field, data[field])

        if 'categorie_id' in data:
            try:
                p.categorie = Categorie.objects.get(pk=data['categorie_id'])
            except Categorie.DoesNotExist:
                return Response({'detail': 'Catégorie introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        if 'image_principale' in request.FILES:
            p.image_principale = request.FILES['image_principale']

        p.save()
        return Response(_serialize_produit(p))

    def delete(self, request, slug):
        p, err = self._get_obj(request, slug)
        if err:
            return err
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _serialize_produit(p):
    return {
        'id':                   p.pk,
        'nom':                  p.nom,
        'slug':                 p.slug,
        'description':          p.description,
        'variete':              p.variete,
        'prix_unitaire':        str(p.prix_unitaire),
        'prix_gros':            str(p.prix_gros) if p.prix_gros else '',
        'unite_vente':          p.unite_vente,
        'unite_vente_label':    p.get_unite_vente_display(),
        'quantite_min_commande': p.quantite_min_commande,
        'stock_disponible':     p.stock_disponible,
        'seuil_alerte':         p.seuil_alerte,
        'stock_reel':           p.stock_reel,
        'est_en_alerte':        p.est_en_alerte,
        'categorie_id':         p.categorie_id,
        'categorie_nom':        p.categorie.nom,
        'origine':              p.origine,
        'saison':               p.saison,
        'certifications':       p.certifications,
        'statut':               p.statut,
        'statut_label':         p.get_statut_display(),
        'is_active':            p.is_active,
        'is_featured':          p.is_featured,
        'image_principale':     p.image_principale.url if p.image_principale else None,
        'created_at':           p.created_at.isoformat(),
    }
