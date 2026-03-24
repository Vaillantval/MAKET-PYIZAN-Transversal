from django.contrib import admin
from django.utils.html import format_html
from .models import Commande, CommandeDetail, HistoriqueStatutCommande


class CommandeDetailInline(admin.TabularInline):
    model           = CommandeDetail
    extra           = 0
    readonly_fields = ('produit', 'lot', 'prix_unitaire', 'quantite', 'unite_vente', 'sous_total')
    can_delete      = False


class HistoriqueStatutInline(admin.TabularInline):
    model           = HistoriqueStatutCommande
    extra           = 0
    readonly_fields = ('statut_avant', 'statut_apres', 'commentaire', 'effectue_par', 'created_at')
    can_delete      = False
    ordering        = ('created_at',)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display    = ('numero_commande', 'get_acheteur', 'get_producteur', 'nb_articles', 'total', 'methode_paiement', 'statut_badge', 'paiement_badge', 'created_at')
    list_filter     = ('statut', 'statut_paiement', 'methode_paiement', 'mode_livraison', 'producteur__departement', 'created_at')
    search_fields   = ('numero_commande', 'acheteur__user__first_name', 'acheteur__user__last_name', 'producteur__user__first_name', 'reference_paiement')
    readonly_fields = ('numero_commande', 'sous_total', 'total', 'created_at', 'updated_at', 'apercu_preuve_paiement')
    inlines         = [CommandeDetailInline, HistoriqueStatutInline]
    date_hierarchy  = 'created_at'
    ordering        = ('-created_at',)
    actions         = ['confirmer_commandes', 'marquer_livrees', 'annuler_commandes']

    fieldsets = (
        ('Identification', {'fields': ('numero_commande', 'acheteur', 'producteur', 'collecte')}),
        ('Statuts', {'fields': ('statut', 'statut_paiement')}),
        ('Paiement', {'fields': ('methode_paiement', 'reference_paiement', 'voucher', 'apercu_preuve_paiement', 'preuve_paiement')}),
        ('Montants', {'fields': ('sous_total', 'frais_livraison', 'remise', 'total')}),
        ('Livraison', {'fields': ('mode_livraison', 'adresse_livraison', 'ville_livraison', 'departement_livraison', 'date_livraison_prevue', 'date_livraison_reelle')}),
        ('Notes', {'fields': ('notes_acheteur', 'notes_admin'), 'classes': ('collapse',)}),
        ('Dates', {'fields': ('date_confirmation', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_acheteur(self, obj): return obj.acheteur.user.get_full_name()
    get_acheteur.short_description = 'Acheteur'

    def get_producteur(self, obj): return obj.producteur.user.get_full_name()
    get_producteur.short_description = 'Producteur'

    def statut_badge(self, obj):
        colors = {'en_attente': '#f39c12', 'confirmee': '#3498db', 'en_preparation': '#9b59b6', 'prete': '#1abc9c', 'en_collecte': '#e67e22', 'livree': '#27ae60', 'annulee': '#e74c3c', 'litige': '#c0392b'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def paiement_badge(self, obj):
        colors = {'non_paye': '#e74c3c', 'en_attente': '#f39c12', 'preuve_soumise': '#e67e22', 'verifie': '#3498db', 'paye': '#27ae60', 'rembourse': '#9b59b6'}
        color  = colors.get(obj.statut_paiement, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_paiement_display())
    paiement_badge.short_description = 'Paiement'

    def apercu_preuve_paiement(self, obj):
        if obj.preuve_paiement:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:200px; border-radius:6px; cursor:pointer"/></a>', obj.preuve_paiement.url, obj.preuve_paiement.url)
        return '—'
    apercu_preuve_paiement.short_description = 'Preuve de paiement'

    @admin.action(description='Confirmer les commandes selectionnees')
    def confirmer_commandes(self, request, queryset):
        from apps.orders.services.commande_service import CommandeService
        count = 0
        for commande in queryset.filter(statut=Commande.Statut.EN_ATTENTE):
            try:
                CommandeService.confirmer_commande(commande, request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} commande(s) confirmee(s).")

    @admin.action(description='Marquer comme livrees')
    def marquer_livrees(self, request, queryset):
        from apps.orders.services.commande_service import CommandeService
        count = 0
        for commande in queryset.exclude(statut__in=[Commande.Statut.LIVREE, Commande.Statut.ANNULEE]):
            CommandeService.changer_statut(commande, Commande.Statut.LIVREE, effectue_par=request.user, commentaire="Marquee livree par l'admin.")
            count += 1
        self.message_user(request, f"{count} commande(s) marquee(s) livree(s).")

    @admin.action(description='Annuler les commandes selectionnees')
    def annuler_commandes(self, request, queryset):
        from apps.orders.services.commande_service import CommandeService
        count = 0
        for commande in queryset:
            try:
                CommandeService.annuler_commande(commande, effectue_par=request.user, motif="Annulation groupee par l'admin.")
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} commande(s) annulee(s).")
