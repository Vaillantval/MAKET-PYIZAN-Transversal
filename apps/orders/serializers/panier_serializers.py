from rest_framework import serializers
from apps.orders.models import Panier, LignePanier


class LignePanierSerializer(serializers.ModelSerializer):
    """Ligne de panier enrichie avec les infos produit."""
    slug              = serializers.CharField(source='produit.slug')
    nom               = serializers.CharField(source='produit.nom')
    prix_unitaire     = serializers.DecimalField(
                          source='produit.prix_unitaire',
                          max_digits=10, decimal_places=2,
                        )
    unite_vente       = serializers.CharField(source='produit.unite_vente')
    unite_vente_label = serializers.SerializerMethodField()
    producteur_id     = serializers.IntegerField(source='produit.producteur.pk')
    producteur_nom    = serializers.SerializerMethodField()
    image             = serializers.SerializerMethodField()
    stock_reel        = serializers.IntegerField(source='produit.stock_reel')

    class Meta:
        model  = LignePanier
        fields = [
            'id', 'slug', 'nom', 'quantite',
            'prix_unitaire', 'sous_total',
            'unite_vente', 'unite_vente_label',
            'producteur_id', 'producteur_nom',
            'image', 'stock_reel',
        ]

    def get_unite_vente_label(self, obj):
        return obj.produit.get_unite_vente_display()

    def get_producteur_nom(self, obj):
        return obj.produit.producteur.user.get_full_name()

    def get_image(self, obj):
        if obj.produit.image_principale:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(
                    obj.produit.image_principale.url
                )
        return None


class PanierSerializer(serializers.ModelSerializer):
    """Résumé complet du panier."""
    items       = LignePanierSerializer(many=True, read_only=True)
    producteurs = serializers.SerializerMethodField()

    class Meta:
        model  = Panier
        fields = [
            'items', 'total', 'nb_articles',
            'nb_items', 'producteurs',
        ]

    def get_producteurs(self, obj):
        seen = {}
        for item in obj.items.select_related(
            'produit__producteur__user'
        ).all():
            p = item.produit.producteur
            if p.pk not in seen:
                seen[p.pk] = {
                    'id':  p.pk,
                    'nom': p.user.get_full_name(),
                }
        return list(seen.values())
