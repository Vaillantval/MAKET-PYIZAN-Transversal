from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings, FAQCategorie, FAQItem, ContactMessage


# ── SiteSettings (Singleton) ─────────────────────────────────────────────────

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    save_on_top = True

    fieldsets = [
        ('🏷️ Identité du site', {
            'fields': ('nom_site', 'slogan', 'logo', 'favicon'),
        }),
        ('🏠 Page d\'accueil — Hero', {
            'fields': (
                'hero_badge_texte',
                'hero_titre_ligne1',
                'hero_titre_ligne2',
                'hero_sous_titre',
            ),
            'classes': ('collapse',),
        }),
        ('📖 Page À propos', {
            'fields': (
                'a_propos_titre',
                'a_propos_contenu',
                'a_propos_mission',
                'a_propos_vision',
                'a_propos_image',
                'annee_fondation',
            ),
            'classes': ('collapse',),
        }),
        ('📞 Coordonnées & Contact', {
            'fields': (
                'email_contact',
                'telephone',
                'whatsapp',
                'adresse',
                'horaires',
            ),
        }),
        ('🌐 Réseaux sociaux', {
            'fields': (
                'facebook_url',
                'instagram_url',
                'twitter_url',
                'youtube_url',
            ),
            'classes': ('collapse',),
        }),
        ('🔐 Pages Connexion & Inscription', {
            'fields': ('login_image', 'register_image'),
            'description': 'Images affichées dans le panneau gauche des pages de connexion et d\'inscription.',
        }),
        ('📄 Footer & SEO', {
            'fields': (
                'copyright_texte',
                'meta_description',
                'google_analytics_id',
            ),
            'classes': ('collapse',),
        }),
        ('🚧 Maintenance', {
            'fields': ('mode_maintenance', 'message_maintenance'),
            'classes': ('collapse',),
        }),
    ]

    def has_add_permission(self, request):
        """Empêche la création d'un deuxième enregistrement."""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Redirige directement vers la page d'édition."""
        obj = SiteSettings.get_solo()
        from django.shortcuts import redirect
        return redirect(
            f'/admin/core/sitesettings/{obj.pk}/change/'
        )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px; border-radius:4px">',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Aperçu logo'


# ── FAQ ──────────────────────────────────────────────────────────────────────

class FAQItemInline(admin.TabularInline):
    model   = FAQItem
    extra   = 1
    fields  = ('question', 'reponse', 'ordre', 'is_active')
    ordering = ('ordre',)


@admin.register(FAQCategorie)
class FAQCategorieAdmin(admin.ModelAdmin):
    list_display  = ('titre', 'icone', 'ordre', 'is_active', 'nb_questions')
    list_editable = ('ordre', 'is_active')
    inlines       = [FAQItemInline]

    def nb_questions(self, obj):
        n = obj.items.filter(is_active=True).count()
        return format_html(
            '<span style="background:#e8f8ee; color:#1a6b2f; '
            'padding:2px 10px; border-radius:12px; font-weight:600">'
            '{} question{}</span>',
            n, 's' if n > 1 else ''
        )
    nb_questions.short_description = 'Questions actives'


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display  = ('question_courte', 'categorie', 'ordre', 'is_active')
    list_filter   = ('categorie', 'is_active')
    list_editable = ('ordre', 'is_active')
    search_fields = ('question', 'reponse')
    ordering      = ('categorie__ordre', 'ordre')

    def question_courte(self, obj):
        return obj.question[:80] + ('…' if len(obj.question) > 80 else '')
    question_courte.short_description = 'Question'


# ── Messages de contact ──────────────────────────────────────────────────────

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'email', 'sujet_court', 'created_at', 'badge_lu')
    list_filter   = ('est_lu', 'created_at')
    search_fields = ('nom', 'email', 'sujet', 'message')
    readonly_fields = ('nom', 'email', 'telephone', 'sujet', 'message', 'created_at')
    ordering      = ('-created_at',)

    fieldsets = [
        ('Expéditeur', {
            'fields': ('nom', 'email', 'telephone', 'created_at'),
        }),
        ('Message', {
            'fields': ('sujet', 'message'),
        }),
        ('Traitement', {
            'fields': ('est_lu',),
        }),
    ]

    def sujet_court(self, obj):
        return obj.sujet[:60] + ('…' if len(obj.sujet) > 60 else '')
    sujet_court.short_description = 'Sujet'

    def badge_lu(self, obj):
        if obj.est_lu:
            return format_html(
                '<span style="background:#d5f5e3; color:#1e8449; '
                'padding:2px 10px; border-radius:12px; font-weight:600">Lu</span>'
            )
        return format_html(
            '<span style="background:#fef9e7; color:#e67e22; '
            'padding:2px 10px; border-radius:12px; font-weight:600">Non lu</span>'
        )
    badge_lu.short_description = 'Statut'

    def has_add_permission(self, request):
        return False
