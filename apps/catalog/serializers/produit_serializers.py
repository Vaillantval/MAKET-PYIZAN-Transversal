from rest_framework import serializers
from apps.catalog.models import Produit, Categorie, ImageProduit
from django.utils.translation import gettext_lazy as _


class ImageProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ImageProduit
        fields = ['id', 'image', 'legende', 'ordre']


class ProduitListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour la liste du catalogue."""
    categorie         = serializers.SerializerMethodField()
    producteur        = serializers.SerializerMethodField()
    unite_vente_label = serializers.CharField(source='get_unite_vente_display')
    statut_label      = serializers.CharField(source='get_statut_display')
    est_en_alerte     = serializers.SerializerMethodField()

    class Meta:
        model  = Produit
        fields = [
            'id', 'nom', 'slug', 'variete',
            'prix_unitaire', 'prix_gros',
            'unite_vente', 'unite_vente_label',
            'quantite_min_commande',
            'stock_disponible', 'seuil_alerte', 'stock_reel',
            'statut', 'statut_label', 'est_en_alerte',
            'is_active', 'is_featured', 'image_principale',
            'categorie', 'producteur', 'created_at',
        ]

    def get_categorie(self, obj):
        return {'id': obj.categorie.pk, 'nom': obj.categorie.nom, 'slug': obj.categorie.slug}

    def get_producteur(self, obj):
        return {
            'id':              obj.producteur.pk,
            'nom':             obj.producteur.user.get_full_name(),
            'code_producteur': obj.producteur.code_producteur,
            'commune':         obj.producteur.commune,
            'departement':     obj.producteur.departement,
        }

    def get_est_en_alerte(self, obj):
        return obj.stock_disponible <= obj.seuil_alerte


class ProduitDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un produit."""
    categorie         = serializers.SerializerMethodField()
    producteur        = serializers.SerializerMethodField()
    images            = ImageProduitSerializer(many=True, read_only=True)
    unite_vente_label = serializers.CharField(
                          source='get_unite_vente_display'
                        )
    similaires        = serializers.SerializerMethodField()
    qr_code_url       = serializers.SerializerMethodField()

    class Meta:
        model  = Produit
        fields = [
            'id', 'nom', 'slug', 'variete', 'description',
            'prix_unitaire', 'prix_gros',
            'unite_vente', 'unite_vente_label',
            'quantite_min_commande', 'stock_disponible', 'stock_reel',
            'seuil_alerte', 'statut', 'is_active', 'is_featured',
            'image_principale', 'qr_code_url',
            'origine', 'saison', 'certifications',
            'categorie', 'producteur', 'images',
            'similaires', 'created_at',
        ]

    def get_categorie(self, obj):
        return {
            'id':   obj.categorie.pk,
            'nom':  obj.categorie.nom,
            'slug': obj.categorie.slug,
        }

    def get_producteur(self, obj):
        p = obj.producteur
        return {
            'id':              p.pk,
            'nom':             p.user.get_full_name(),
            'commune':         p.commune,
            'departement':     p.departement,
            'code_producteur': p.code_producteur,
            'telephone':       p.user.telephone,
            'nb_produits':     p.nb_produits_actifs,
        }

    def get_similaires(self, obj):
        similaires = Produit.objects.filter(
            categorie=obj.categorie,
            is_active=True,
            stock_disponible__gt=0,
        ).exclude(pk=obj.pk)[:4]
        return ProduitListSerializer(
            similaires, many=True,
            context=self.context,
        ).data

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
        return None


class ProduitCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier un produit (producteur)."""

    class Meta:
        model  = Produit
        fields = [
            'nom', 'categorie', 'variete', 'description',
            'prix_unitaire', 'prix_gros',
            'unite_vente', 'quantite_min_commande',
            'stock_disponible', 'seuil_alerte',
            'image_principale',
            'origine', 'saison', 'certifications',
            'statut', 'is_active',
        ]

    def validate_prix_unitaire(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Le prix doit être supérieur à 0.")
            )
        return value

    def validate_stock_disponible(self, value):
        if value < 0:
            raise serializers.ValidationError(
                _("Le stock ne peut pas être négatif.")
            )
        return value
