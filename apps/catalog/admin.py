from django.contrib import admin
from django.utils.html import format_html
from .models import Categorie, Produit, ImageProduit


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display        = ('apercu_image', 'nom', 'parent', 'nb_produits', 'ordre', 'is_active')
    list_filter         = ('is_active', 'parent')
    search_fields       = ('nom',)
    prepopulated_fields = {'slug': ('nom',)}
    list_editable       = ('ordre', 'is_active')
    ordering            = ('ordre', 'nom')

    def apercu_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px; height:40px; object-fit:cover; border-radius:4px"/>', obj.image.url)
        return format_html('<span style="color:#ccc; font-size:20px"><i class="{}"></i></span>', obj.icone or 'fas fa-leaf')
    apercu_image.short_description = ''


class ImageProduitInline(admin.TabularInline):
    model  = ImageProduit
    extra  = 1
    fields = ('image', 'legende', 'ordre')


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display    = ('apercu_image', 'nom', 'get_producteur', 'categorie', 'prix_unitaire', 'unite_vente', 'stock_badge', 'statut_badge', 'is_featured')
    list_filter     = ('statut', 'categorie', 'unite_vente', 'is_active', 'is_featured', 'producteur__departement')
    search_fields   = ('nom', 'variete', 'producteur__user__first_name', 'producteur__user__last_name', 'producteur__commune')
    readonly_fields = ('slug', 'qr_code_apercu', 'stock_reel', 'created_at', 'updated_at')
    list_editable   = ('is_featured',)
    inlines         = [ImageProduitInline]
    ordering        = ('-created_at',)

    fieldsets = (
        ('Informations de base', {'fields': ('producteur', 'categorie', 'nom', 'slug', 'variete', 'description')}),
        ('Prix & Vente', {'fields': ('prix_unitaire', 'prix_gros', 'unite_vente', 'quantite_min_commande')}),
        ('Stock', {'fields': ('stock_disponible', 'seuil_alerte', 'stock_reserve', 'stock_reel')}),
        ('Tracabilite', {'fields': ('origine', 'saison', 'certifications'), 'classes': ('collapse',)}),
        ('Medias', {'fields': ('image_principale', 'qr_code_apercu')}),
        ('Statut & Mise en avant', {'fields': ('statut', 'is_active', 'is_featured')}),
        ('Dates', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def apercu_image(self, obj):
        if obj.image_principale:
            return format_html('<img src="{}" style="width:45px; height:45px; object-fit:cover; border-radius:6px"/>', obj.image_principale.url)
        return '—'
    apercu_image.short_description = ''

    def get_producteur(self, obj): return obj.producteur.user.get_full_name()
    get_producteur.short_description = 'Producteur'

    def stock_badge(self, obj):
        stock = obj.stock_disponible
        if stock == 0:            color, label = '#e74c3c', 'Epuise'
        elif obj.est_en_alerte:   color, label = '#f39c12', f'(!) {stock}'
        else:                     color, label = '#27ae60', str(stock)
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, label)
    stock_badge.short_description = 'Stock'

    def statut_badge(self, obj):
        colors = {'brouillon': '#95a5a6', 'en_attente': '#f39c12', 'actif': '#27ae60', 'epuise': '#e74c3c', 'inactif': '#7f8c8d'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def qr_code_apercu(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" style="width:120px; height:120px;"/>', obj.qr_code.url)
        return 'QR code genere a la sauvegarde'
    qr_code_apercu.short_description = 'QR Code'
