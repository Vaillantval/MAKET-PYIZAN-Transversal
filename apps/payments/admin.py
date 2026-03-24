from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Paiement, ProgrammeVoucher, Voucher


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display    = ('reference', 'get_commande', 'get_acheteur', 'type_badge', 'montant', 'montant_recu', 'statut_badge', 'verifie_par', 'created_at')
    list_filter     = ('statut', 'type_paiement', 'created_at')
    search_fields   = ('reference', 'commande__numero_commande', 'commande__acheteur__user__first_name', 'id_transaction', 'numero_expediteur')
    readonly_fields = ('reference', 'created_at', 'updated_at', 'apercu_preuve', 'difference_montant')
    date_hierarchy  = 'created_at'
    ordering        = ('-created_at',)
    actions         = ['confirmer_paiements', 'rejeter_paiements']

    fieldsets = (
        ('Identification', {'fields': ('reference', 'commande', 'effectue_par')}),
        ('Type & Statut', {'fields': ('type_paiement', 'statut')}),
        ('Montants', {'fields': ('montant', 'montant_recu', 'difference_montant')}),
        ('Details transaction', {'fields': ('numero_expediteur', 'id_transaction', 'notes')}),
        ('Preuve', {'fields': ('apercu_preuve', 'preuve_image')}),
        ('Verification', {'fields': ('verifie_par', 'note_verification', 'date_verification')}),
        ('Dates', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_commande(self, obj): return obj.commande.numero_commande
    get_commande.short_description = 'Commande'

    def get_acheteur(self, obj): return obj.commande.acheteur.user.get_full_name()
    get_acheteur.short_description = 'Acheteur'

    def type_badge(self, obj):
        colors = {'moncash': '#e74c3c', 'natcash': '#e67e22', 'virement': '#3498db', 'cash': '#27ae60', 'voucher': '#9b59b6'}
        color  = colors.get(obj.type_paiement, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_type_paiement_display())
    type_badge.short_description = 'Type'

    def statut_badge(self, obj):
        colors = {'initie': '#95a5a6', 'en_attente': '#f39c12', 'soumis': '#e67e22', 'verifie': '#3498db', 'confirme': '#27ae60', 'echoue': '#e74c3c', 'annule': '#7f8c8d', 'rembourse': '#9b59b6'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    def apercu_preuve(self, obj):
        if obj.preuve_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:250px; border-radius:6px;"/></a>', obj.preuve_image.url, obj.preuve_image.url)
        return '—'
    apercu_preuve.short_description = 'Apercu preuve'

    @admin.action(description='Confirmer les paiements selectionnes')
    def confirmer_paiements(self, request, queryset):
        from apps.payments.services.paiement_service import PaiementService
        count = 0
        for paiement in queryset.filter(statut__in=[Paiement.Statut.SOUMIS, Paiement.Statut.VERIFIE]):
            try:
                PaiementService.confirmer_paiement(paiement, request.user, note_verification="Confirme en masse par l'admin.")
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} paiement(s) confirme(s).")

    @admin.action(description='Rejeter les paiements selectionnes')
    def rejeter_paiements(self, request, queryset):
        from apps.payments.services.paiement_service import PaiementService
        count = 0
        for paiement in queryset.exclude(statut__in=[Paiement.Statut.CONFIRME, Paiement.Statut.ECHOUE]):
            try:
                PaiementService.rejeter_paiement(paiement, request.user, motif="Rejete par l'admin.")
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} paiement(s) rejete(s).")


class VoucherInline(admin.TabularInline):
    model           = Voucher
    extra           = 0
    readonly_fields = ('code', 'statut', 'date_utilisation', 'created_at')
    fields          = ('code', 'beneficiaire', 'type_valeur', 'valeur', 'date_expiration', 'statut')
    show_change_link = True


@admin.register(ProgrammeVoucher)
class ProgrammeVoucherAdmin(admin.ModelAdmin):
    list_display    = ('nom', 'code_programme', 'type_programme', 'budget_total', 'budget_utilise', 'budget_restant', 'est_en_cours', 'is_active', 'date_debut', 'date_fin')
    list_filter     = ('type_programme', 'is_active')
    search_fields   = ('nom', 'code_programme', 'contact_nom', 'contact_email')
    readonly_fields = ('budget_utilise', 'created_at')
    inlines         = [VoucherInline]

    fieldsets = (
        ('Identification', {'fields': ('nom', 'code_programme', 'type_programme', 'description', 'logo')}),
        ('Contact', {'fields': ('contact_nom', 'contact_email', 'contact_tel')}),
        ('Budget & Periode', {'fields': ('budget_total', 'budget_utilise', 'date_debut', 'date_fin', 'is_active')}),
    )


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display    = ('code', 'programme', 'get_beneficiaire', 'type_valeur', 'valeur', 'montant_commande_min', 'statut_badge', 'date_expiration', 'date_utilisation')
    list_filter     = ('statut', 'type_valeur', 'programme')
    search_fields   = ('code', 'beneficiaire__user__first_name', 'beneficiaire__user__last_name', 'programme__nom')
    readonly_fields = ('code', 'date_utilisation', 'created_at')
    ordering        = ('-created_at',)
    actions         = ['suspendre_vouchers', 'annuler_vouchers']

    fieldsets = (
        ('Identification', {'fields': ('code', 'programme', 'beneficiaire', 'cree_par')}),
        ('Valeur', {'fields': ('type_valeur', 'valeur', 'montant_max', 'montant_commande_min')}),
        ('Categories autorisees', {'fields': ('categories_autorisees',)}),
        ('Statut & Validite', {'fields': ('statut', 'date_expiration', 'date_utilisation')}),
    )

    def get_beneficiaire(self, obj):
        if obj.beneficiaire: return str(obj.beneficiaire)
        return 'Ouvert'
    get_beneficiaire.short_description = 'Beneficiaire'

    def statut_badge(self, obj):
        colors = {'actif': '#27ae60', 'utilise': '#3498db', 'expire': '#95a5a6', 'annule': '#e74c3c', 'suspendu': '#f39c12'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html('<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>', color, obj.get_statut_display())
    statut_badge.short_description = 'Statut'

    @admin.action(description='Suspendre les vouchers selectionnes')
    def suspendre_vouchers(self, request, queryset):
        updated = queryset.filter(statut=Voucher.Statut.ACTIF).update(statut=Voucher.Statut.SUSPENDU)
        self.message_user(request, f"{updated} voucher(s) suspendu(s).")

    @admin.action(description='Annuler les vouchers selectionnes')
    def annuler_vouchers(self, request, queryset):
        updated = queryset.exclude(statut__in=[Voucher.Statut.UTILISE, Voucher.Statut.ANNULE]).update(statut=Voucher.Statut.ANNULE)
        self.message_user(request, f"{updated} voucher(s) annule(s).")
