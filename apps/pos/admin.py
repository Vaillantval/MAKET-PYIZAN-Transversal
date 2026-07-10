from django.contrib import admin, messages
from django.utils.html import format_html

from apps.pos.models import POSDevice, POSItem, POSSale, POSSession
from apps.pos.services import POSService


@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'device_uid_court', 'operateur', 'departement',
                    'commune', 'badge_actif', 'created_at')
    list_display_links = ('nom',)
    list_filter = ('is_active', 'departement', 'commune')
    search_fields = ('nom', 'device_uid', 'operateur__username',
                     'operateur__email', 'commune')
    actions = ['desactiver_terminaux', 'reactiver_terminaux']

    @admin.display(description='UID')
    def device_uid_court(self, obj):
        return f"{obj.device_uid[:16]}…" if len(obj.device_uid) > 16 else obj.device_uid

    @admin.display(description='Statut')
    def badge_actif(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">Actif</span>')
        return format_html('<span class="badge badge-danger">Révoqué</span>')

    @admin.action(description='Désactiver (révoquer) les terminaux sélectionnés')
    def desactiver_terminaux(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} terminal(aux) révoqué(s).", level=messages.SUCCESS)

    @admin.action(description='Réactiver les terminaux sélectionnés')
    def reactiver_terminaux(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} terminal(aux) réactivé(s).", level=messages.SUCCESS)


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'operateur', 'device', 'fonds_ouverture',
                    'fonds_fermeture', 'ecart_colore', 'badge_statut',
                    'ouverte_le', 'fermee_le')
    list_filter = ('statut', 'device__departement', 'ouverte_le')
    search_fields = ('operateur__username', 'operateur__email', 'device__nom')
    date_hierarchy = 'ouverte_le'

    @admin.display(description='Écart de caisse')
    def ecart_colore(self, obj):
        if obj.ecart_caisse is None:
            return '—'
        if obj.ecart_caisse == 0:
            return format_html('<span style="color:#2e7d32;font-weight:600;">0.00</span>')
        couleur = '#c62828' if obj.ecart_caisse < 0 else '#e65100'
        return format_html('<span style="color:{};font-weight:700;">{} HTG</span>',
                           couleur, obj.ecart_caisse)

    @admin.display(description='Statut')
    def badge_statut(self, obj):
        if obj.statut == POSSession.Statut.OUVERTE:
            return format_html('<span class="badge badge-success">Ouverte</span>')
        return format_html('<span class="badge badge-secondary">Fermée</span>')

    def get_readonly_fields(self, request, obj=None):
        # Une session fermée est un document comptable : plus rien n'est éditable.
        if obj and obj.statut == POSSession.Statut.FERMEE:
            return [f.name for f in self.model._meta.fields]
        return ('ecart_caisse', 'ouverte_le', 'fermee_le')

    def has_add_permission(self, request):
        # Les sessions s'ouvrent depuis le terminal (le service garantit
        # l'unicité de la session ouverte), jamais à la main.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class POSItemInline(admin.TabularInline):
    model = POSItem
    extra = 0
    can_delete = False
    readonly_fields = ('produit', 'lot', 'quantite', 'prix_unitaire', 'sous_total')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(POSSale)
class POSSaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_vente', 'operateur', 'client', 'montant_total',
                    'methode_paiement', 'montant_wallet', 'badge_statut',
                    'badge_conflit', 'vendue_le')
    list_display_links = ('numero_vente',)
    list_filter = ('methode_paiement', 'statut', 'stock_conflict', 'vendue_le',
                   'session__device__departement')
    search_fields = ('numero_vente', 'operateur__username', 'client__username',
                     'client__email', 'client__telephone')
    date_hierarchy = 'vendue_le'
    readonly_fields = ('idempotency_key', 'session', 'operateur', 'client',
                       'numero_vente', 'montant_total', 'methode_paiement',
                       'montant_wallet', 'statut', 'vendue_le', 'synced_le')
    inlines = [POSItemInline]
    actions = ['annuler_ventes', 'lever_conflit_stock']

    @admin.display(description='Statut')
    def badge_statut(self, obj):
        if obj.statut == POSSale.Statut.CONFIRMEE:
            return format_html('<span class="badge badge-success">Confirmée</span>')
        return format_html('<span class="badge badge-danger">Annulée</span>')

    @admin.display(description='Stock')
    def badge_conflit(self, obj):
        if obj.stock_conflict:
            return format_html('<span class="badge badge-warning">'
                               '<i class="fas fa-exclamation-triangle"></i> Conflit</span>')
        return format_html('<span class="badge badge-light">OK</span>')

    @admin.action(description='Annuler les ventes (re-crédit stock + wallet)')
    def annuler_ventes(self, request, queryset):
        annulees, ignorees = 0, 0
        for vente in queryset:
            if POSService.annuler_vente(vente):
                annulees += 1
            else:
                ignorees += 1
        if annulees:
            self.message_user(request, f"{annulees} vente(s) annulée(s).", level=messages.SUCCESS)
        if ignorees:
            self.message_user(request, f"{ignorees} vente(s) déjà annulée(s).", level=messages.WARNING)

    @admin.action(description='Lever le conflit de stock (arbitré)')
    def lever_conflit_stock(self, request, queryset):
        n = queryset.filter(stock_conflict=True).update(stock_conflict=False)
        self.message_user(request, f"{n} conflit(s) levé(s).", level=messages.SUCCESS)

    def has_add_permission(self, request):
        # Les ventes se créent au terminal (idempotence + wallet + stock),
        # jamais à la main.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
