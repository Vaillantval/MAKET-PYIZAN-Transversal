from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Producteur, Acheteur, Adresse


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'get_full_name', 'email', 'role_badge', 'telephone', 'is_verified', 'created_at')
    list_filter   = ('role', 'is_verified', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telephone')
    ordering      = ('-created_at',)
    fieldsets     = UserAdmin.fieldsets + (
        ('Informations supplementaires', {
            'fields': ('role', 'telephone', 'photo', 'is_verified', 'fcm_token')
        }),
    )

    def role_badge(self, obj):
        colors = {
            'superadmin': '#e74c3c',
            'producteur': '#27ae60', 'acheteur': '#2980b9', 'collecteur': '#8e44ad',
        }
        color = colors.get(obj.role, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'


@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display    = ('code_producteur', 'get_nom', 'commune', 'departement', 'statut_badge', 'nb_produits_actifs', 'nb_commandes_total', 'created_at')
    list_filter     = ('statut', 'departement')
    search_fields   = ('user__first_name', 'user__last_name', 'code_producteur', 'commune')
    readonly_fields = ('code_producteur', 'created_at', 'updated_at', 'nb_produits_actifs', 'nb_commandes_total')
    ordering        = ('-created_at',)

    fieldsets = (
        ('Identite', {'fields': ('user', 'code_producteur', 'num_identification', 'photo_identite')}),
        ('Localisation', {'fields': ('departement', 'commune', 'localite', 'adresse_complete')}),
        ('Informations agricoles', {'fields': ('superficie_ha', 'description')}),
        ('Validation', {'fields': ('statut', 'note_admin', 'valide_par', 'date_validation')}),
        ('Stats', {'fields': ('nb_produits_actifs', 'nb_commandes_total'), 'classes': ('collapse',)}),
    )

    def get_nom(self, obj): return obj.user.get_full_name()
    get_nom.short_description = 'Nom complet'

    def statut_badge(self, obj):
        colors = {'en_attente': '#f39c12', 'actif': '#27ae60', 'suspendu': '#e74c3c', 'inactif': '#95a5a6'}
        color  = colors.get(obj.statut, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'


@admin.register(Acheteur)
class AcheteurAdmin(admin.ModelAdmin):
    list_display    = ('get_nom', 'type_acheteur', 'departement', 'nom_organisation', 'total_commandes', 'total_depense', 'created_at')
    list_filter     = ('type_acheteur', 'departement')
    search_fields   = ('user__first_name', 'user__last_name', 'nom_organisation')
    readonly_fields = ('total_commandes', 'total_depense', 'created_at', 'updated_at')
    ordering        = ('-created_at',)

    fieldsets = (
        ('Compte',       {'fields': ('user',)}),
        ('Profil',       {'fields': ('type_acheteur', 'nom_organisation')}),
        ('Localisation', {'fields': ('departement',)}),
        ('Stats',        {'fields': ('total_commandes', 'total_depense'), 'classes': ('collapse',)}),
    )

    def get_nom(self, obj): return str(obj)
    get_nom.short_description = 'Acheteur'


@admin.register(Adresse)
class AdresseAdmin(admin.ModelAdmin):
    list_display    = ('libelle', 'get_user', 'nom_complet', 'commune', 'section_communale', 'departement', 'type_adresse', 'is_default')
    list_filter     = ('type_adresse', 'departement', 'is_default')
    search_fields   = ('user__username', 'user__first_name', 'user__last_name', 'nom_complet', 'commune')
    ordering        = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Identification', {'fields': ('user', 'libelle', 'type_adresse', 'is_default')}),
        ('Destinataire',   {'fields': ('nom_complet', 'telephone')}),
        ('Adresse',        {'fields': ('rue', 'departement', 'commune', 'section_communale')}),
        ('Détails',        {'fields': ('details',)}),
    )

    def get_user(self, obj): return obj.user.get_full_name() or obj.user.username
    get_user.short_description = 'Utilisateur'
