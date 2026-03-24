from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import ZoneCollecte, PointCollecte, Collecte, ParticipationCollecte


class PointCollecteInline(admin.TabularInline):
    model  = PointCollecte
    extra  = 0
    fields = ('nom', 'commune', 'adresse', 'responsable', 'telephone', 'is_active')


@admin.register(ZoneCollecte)
class ZoneCollecteAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'departement', 'get_nb_points', 'get_nb_collectes', 'is_active')
    list_filter   = ('departement', 'is_active')
    search_fields = ('nom', 'description')
    list_editable = ('is_active',)
    inlines       = [PointCollecteInline]

    def get_nb_points(self, obj): return obj.points.filter(is_active=True).count()
    get_nb_points.short_description = 'Points actifs'

    def get_nb_collectes(self, obj): return obj.collectes.count()
    get_nb_collectes.short_description = 'Total collectes'


@admin.register(PointCollecte)
class PointCollecteAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'zone', 'commune', 'responsable', 'telephone', 'is_active')
    list_filter   = ('zone__departement', 'zone', 'is_active')
    search_fields = ('nom', 'commune', 'adresse', 'responsable')
    list_editable = ('is_active',)


class ParticipationInline(admin.TabularInline):
    model           = ParticipationCollecte
    extra           = 0
    readonly_fields = ('taux_realisation',)
    fields          = ('producteur', 'statut', 'quantite_prevue', 'quantite_collectee', 'taux_realisation', 'notes')


@admin.register(Collecte)
class CollecteAdmin(admin.ModelAdmin):
    list_display    = ('reference', 'zone', 'point_collecte', 'date_planifiee', 'heure_debut', 'collecteur', 'statut_badge', 'nb_producteurs', 'nb_commandes', 'retard_badge', 'created_at')
    list_filter     = ('statut', 'zone__departement', 'zone', 'date_planifiee')
    search_fields   = ('reference', 'zone__nom', 'collecteur__first_name', 'collecteur__last_name')
    readonly_fields = ('reference', 'nb_producteurs', 'nb_commandes', 'montant_total', 'created_at', 'updated_at')
    inlines         = [ParticipationInline]
    date_hierarchy  = 'date_planifiee'
    ordering        = ('-date_planifiee',)
    actions         = ['demarrer_collectes', 'terminer_collectes', 'annuler_collectes']

    fieldsets = (
        ('Identification', {'fields': ('reference', 'zone', 'point_collecte', 'collecteur')}),
        ('Planification', {'fields': ('date_planifiee', 'heure_debut', 'heure_fin')}),
        ('Realisation', {'fields': ('statut', 'date_debut_reel', 'date_fin_reel', 'rapport')}),
        ('Stats', {'fields': ('nb_producteurs', 'nb_commandes', 'montant_total'), 'classes': ('collapse',)}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
        ('Dates', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def statut_badge(self, obj):
        colors = {'planifiee': '#3498db', 'en_cours': '#f39c12', 'terminee': '#27ae60', 'annulee': '#e74c3c', 'reportee': '#95a5a6'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def retard_badge(self, obj):
        if obj.est_en_retard:
            return format_html('<span style="background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:11px">En retard</span>')
        return '—'
    retard_badge.short_description = 'Retard'

    @admin.action(description='Demarrer les collectes selectionnees')
    def demarrer_collectes(self, request, queryset):
        from apps.collectes.services.collecte_service import CollecteService
        count = 0
        for c in queryset.filter(statut=Collecte.Statut.PLANIFIEE):
            try:
                CollecteService.demarrer_collecte(c)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} collecte(s) demarree(s).")

    @admin.action(description='Terminer les collectes selectionnees')
    def terminer_collectes(self, request, queryset):
        from apps.collectes.services.collecte_service import CollecteService
        count = 0
        for c in queryset.filter(statut=Collecte.Statut.EN_COURS):
            try:
                CollecteService.terminer_collecte(c)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} collecte(s) terminee(s).")

    @admin.action(description='Annuler les collectes selectionnees')
    def annuler_collectes(self, request, queryset):
        count = queryset.exclude(statut__in=[Collecte.Statut.TERMINEE, Collecte.Statut.ANNULEE]).update(statut=Collecte.Statut.ANNULEE)
        self.message_user(request, f"{count} collecte(s) annulee(s).")


@admin.register(ParticipationCollecte)
class ParticipationCollecteAdmin(admin.ModelAdmin):
    list_display    = ('collecte', 'get_producteur', 'get_zone', 'statut_badge', 'quantite_prevue', 'quantite_collectee', 'taux_realisation_display', 'created_at')
    list_filter     = ('statut', 'collecte__zone__departement', 'collecte__statut')
    search_fields   = ('producteur__user__first_name', 'producteur__user__last_name', 'collecte__reference')
    readonly_fields = ('taux_realisation', 'created_at', 'updated_at')

    def get_producteur(self, obj): return obj.producteur.user.get_full_name()
    get_producteur.short_description = 'Producteur'

    def get_zone(self, obj): return obj.collecte.zone.nom
    get_zone.short_description = 'Zone'

    def statut_badge(self, obj):
        colors = {'inscrit': '#3498db', 'confirme': '#9b59b6', 'present': '#27ae60', 'absent': '#e74c3c', 'annule': '#95a5a6'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def taux_realisation_display(self, obj):
        taux  = obj.taux_realisation
        color = '#27ae60' if taux >= 80 else '#f39c12' if taux >= 50 else '#e74c3c'
        return format_html('<span style="color:{}; font-weight:bold">{}%</span>', color, taux)
    taux_realisation_display.short_description = 'Realisation'
