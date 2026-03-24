from django.contrib import admin
from django.utils.html import format_html
from .models import Lot, MouvementStock, AlerteStock


class MouvementInline(admin.TabularInline):
    model           = MouvementStock
    extra           = 0
    readonly_fields = ('type_mouvement', 'quantite', 'stock_avant', 'stock_apres', 'motif', 'effectue_par', 'created_at')
    can_delete      = False
    ordering        = ('-created_at',)
    max_num         = 10


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display    = ('numero_lot', 'get_produit', 'get_producteur', 'quantite_initiale', 'stock_badge', 'taux_ecoulement_display', 'statut_badge', 'date_recolte', 'created_at')
    list_filter     = ('statut', 'produit__categorie', 'produit__producteur__departement')
    search_fields   = ('numero_lot', 'code_barres', 'produit__nom', 'produit__producteur__user__first_name')
    readonly_fields = ('numero_lot', 'taux_ecoulement', 'created_at', 'updated_at')
    inlines         = [MouvementInline]

    fieldsets = (
        ('Identification', {'fields': ('numero_lot', 'code_barres', 'produit')}),
        ('Quantites', {'fields': ('quantite_initiale', 'quantite_actuelle', 'quantite_vendue', 'taux_ecoulement')}),
        ('Tracabilite', {'fields': ('date_recolte', 'date_expiration', 'lieu_stockage', 'notes')}),
        ('Statut & Audit', {'fields': ('statut', 'cree_par', 'created_at', 'updated_at')}),
    )

    def get_produit(self, obj): return obj.produit.nom
    get_produit.short_description = 'Produit'

    def get_producteur(self, obj): return obj.produit.producteur.user.get_full_name()
    get_producteur.short_description = 'Producteur'

    def stock_badge(self, obj):
        q     = obj.quantite_actuelle
        seuil = obj.produit.seuil_alerte
        color = '#e74c3c' if q == 0 else '#f39c12' if q <= seuil else '#27ae60'
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, q)
    stock_badge.short_description = 'Stock actuel'

    def statut_badge(self, obj):
        colors = {'en_cours': '#3498db', 'disponible': '#27ae60', 'epuise': '#e74c3c', 'expire': '#7f8c8d', 'rappel': '#c0392b'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def taux_ecoulement_display(self, obj):
        taux  = obj.taux_ecoulement
        color = '#27ae60' if taux >= 70 else '#f39c12' if taux >= 30 else '#e74c3c'
        return format_html('<span style="color: {}; font-weight:bold">{}%</span>', color, taux)
    taux_ecoulement_display.short_description = 'Ecoulement'


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display    = ('created_at', 'get_produit', 'type_badge', 'quantite', 'stock_avant', 'stock_apres', 'effectue_par')
    list_filter     = ('type_mouvement', 'produit__categorie', 'created_at')
    search_fields   = ('produit__nom', 'lot__numero_lot', 'reference', 'motif')
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'

    def get_produit(self, obj): return obj.produit.nom
    get_produit.short_description = 'Produit'

    def type_badge(self, obj):
        colors = {'entree': '#27ae60', 'sortie_vente': '#e74c3c', 'sortie_collecte': '#e67e22', 'ajust_pos': '#3498db', 'ajust_neg': '#e74c3c', 'perte': '#c0392b', 'retour': '#9b59b6', 'transfert': '#1abc9c'}
        color  = colors.get(obj.type_mouvement, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_type_mouvement_display())
    type_badge.short_description = 'Type'


@admin.register(AlerteStock)
class AlerteStockAdmin(admin.ModelAdmin):
    list_display    = ('created_at', 'get_produit', 'get_producteur', 'niveau_badge', 'stock_actuel', 'seuil', 'statut_badge', 'traitee_par')
    list_filter     = ('niveau', 'statut', 'produit__producteur__departement')
    search_fields   = ('produit__nom', 'message')
    readonly_fields = ('created_at', 'message')
    date_hierarchy  = 'created_at'
    actions         = ['marquer_resolues', 'marquer_ignorees']

    def get_produit(self, obj): return obj.produit.nom
    get_produit.short_description = 'Produit'

    def get_producteur(self, obj): return obj.produit.producteur.user.get_full_name()
    get_producteur.short_description = 'Producteur'

    def niveau_badge(self, obj):
        colors = {'info': '#3498db', 'warning': '#f39c12', 'critique': '#e74c3c', 'epuise': '#c0392b'}
        color  = colors.get(obj.niveau, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_niveau_display())
    niveau_badge.short_description = 'Niveau'

    def statut_badge(self, obj):
        colors = {'nouvelle': '#e74c3c', 'vue': '#f39c12', 'en_cours': '#3498db', 'resolue': '#27ae60', 'ignoree': '#95a5a6'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    @admin.action(description='Marquer comme resolues')
    def marquer_resolues(self, request, queryset):
        queryset.update(statut=AlerteStock.Statut.RESOLUE)

    @admin.action(description='Marquer comme ignorees')
    def marquer_ignorees(self, request, queryset):
        queryset.update(statut=AlerteStock.Statut.IGNOREE)
