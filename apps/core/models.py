from django.db import models
from django.utils.translation import gettext_lazy as _


# ── Configuration globale du site (singleton) ────────────────────────────────

class SiteSettings(models.Model):

    # ── Identité ────────────────────────────────────────────────
    nom_site        = models.CharField(
        max_length=100, default='Makèt Peyizan',
        verbose_name=_('Nom du site'),
    )
    slogan          = models.CharField(
        max_length=200, default='Marketplace Agricole Haïtienne',
        verbose_name=_('Slogan / sous-titre'),
    )
    logo            = models.ImageField(
        upload_to='site/logo/', null=True, blank=True,
        verbose_name=_('Logo'),
        help_text=_('Recommandé : PNG transparent, 200×60 px minimum'),
    )
    favicon         = models.ImageField(
        upload_to='site/favicon/', null=True, blank=True,
        verbose_name=_('Favicon'),
        help_text=_('ICO ou PNG 32×32 px'),
    )

    # ── Textes page d'accueil ───────────────────────────────────
    hero_badge_texte  = models.CharField(
        max_length=100, default='Marketplace Agricole Haïtienne', blank=True,
        verbose_name=_('Texte du badge hero'),
    )
    hero_titre_ligne1 = models.CharField(
        max_length=200, default='Sòti nan jaden', blank=True,
        verbose_name=_('Hero — titre ligne 1'),
    )
    hero_titre_ligne2 = models.CharField(
        max_length=200, default='rive lakay ou', blank=True,
        verbose_name=_('Hero — titre ligne 2'),
    )
    hero_sous_titre   = models.TextField(
        default=(
            'Manje m se medikaman m — Achetez directement auprès '
            'des producteurs locaux. Produits frais, traçables, '
            'livrés depuis les champs d\'Haïti.'
        ),
        blank=True,
        verbose_name=_('Hero — sous-titre'),
    )

    # ── À propos ────────────────────────────────────────────────
    a_propos_titre   = models.CharField(
        max_length=200, default='À propos de Makèt Peyizan', blank=True,
        verbose_name=_('Titre de la page À propos'),
    )
    a_propos_contenu = models.TextField(
        blank=True,
        verbose_name=_('Présentation générale'),
        help_text=_('Texte principal de la page À propos'),
    )
    a_propos_mission = models.TextField(
        blank=True,
        verbose_name=_('Notre mission'),
    )
    a_propos_vision  = models.TextField(
        blank=True,
        verbose_name=_('Notre vision'),
    )
    a_propos_image   = models.ImageField(
        upload_to='site/apropos/', null=True, blank=True,
        verbose_name=_('Image À propos'),
    )
    annee_fondation  = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name=_('Année de fondation'),
    )

    # ── Contact ─────────────────────────────────────────────────
    email_contact    = models.EmailField(
        default='info@maketpeyizan.ht', blank=True,
        verbose_name=_('Email de contact'),
    )
    telephone        = models.CharField(
        max_length=30, blank=True,
        verbose_name=_('Téléphone'),
    )
    whatsapp         = models.CharField(
        max_length=30, blank=True,
        verbose_name=_('WhatsApp'),
        help_text=_('Numéro avec indicatif ex: +509 XXXX-XXXX'),
    )
    adresse          = models.TextField(
        blank=True,
        verbose_name=_('Adresse physique'),
    )
    horaires         = models.CharField(
        max_length=200, blank=True,
        verbose_name=_('Horaires d\'ouverture'),
        help_text=_('Ex: Lun–Ven 8h–17h'),
    )

    # ── Réseaux sociaux ─────────────────────────────────────────
    facebook_url     = models.URLField(
        blank=True, verbose_name=_('Facebook URL'),
    )
    instagram_url    = models.URLField(
        blank=True, verbose_name=_('Instagram URL'),
    )
    twitter_url      = models.URLField(
        blank=True, verbose_name=_('Twitter / X URL'),
    )
    youtube_url      = models.URLField(
        blank=True, verbose_name=_('YouTube URL'),
    )

    # ── Footer & SEO ─────────────────────────────────────────────
    copyright_texte  = models.CharField(
        max_length=300,
        default='Makèt Peyizan Haiti. Tous droits réservés.',
        blank=True,
        verbose_name=_('Texte copyright'),
    )
    meta_description = models.TextField(
        blank=True,
        verbose_name=_('Meta description (SEO)'),
        help_text=_('160 caractères max recommandé'),
    )
    google_analytics_id = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Google Analytics ID'),
        help_text=_('Format : G-XXXXXXXXXX'),
    )

    # ── Pages d'authentification ────────────────────────────────
    login_image     = models.ImageField(
        upload_to='site/auth/', null=True, blank=True,
        verbose_name=_('Image page Connexion'),
        help_text=_('Panneau gauche de la page de connexion. Recommandé : 800×1000 px'),
    )
    register_image  = models.ImageField(
        upload_to='site/auth/', null=True, blank=True,
        verbose_name=_('Image page Inscription'),
        help_text=_('Panneau gauche de la page d\'inscription. Recommandé : 800×1000 px'),
    )

    # ── Maintenance ─────────────────────────────────────────────
    mode_maintenance    = models.BooleanField(
        default=False,
        verbose_name=_('Mode maintenance'),
        help_text=_('Active une page de maintenance pour les visiteurs'),
    )
    message_maintenance = models.TextField(
        blank=True,
        verbose_name=_('Message de maintenance'),
        help_text=_('Message affiché pendant la maintenance'),
    )

    # ── Portefeuille (wallet) ───────────────────────────────────
    wallet_enabled  = models.BooleanField(
        default=False,
        verbose_name=_('Activer le portefeuille'),
        help_text=_('Active le wallet (recharges, paiements, retraits) pour les acheteurs et producteurs.'),
    )
    taux_commission = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Commission plateforme (%)'),
        help_text=_('Pourcentage prélevé sur les ventes créditées au wallet des producteurs. 0 = pas de commission.'),
    )
    cashback_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Activer le cashback'),
        help_text=_('Crédite un pourcentage de chaque commande payée sur le wallet de l\'acheteur.'),
    )
    taux_cashback   = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Taux de cashback (%)'),
    )
    parrainage_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Activer le parrainage'),
        help_text=_('Bonus wallet au parrain et au filleul à la première commande payée du filleul.'),
    )
    taux_bonus_parrainage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Bonus parrainage (%)'),
        help_text=_('Pourcentage du montant de la première commande, crédité au parrain ET au filleul.'),
    )
    numero_moncash_depot = models.CharField(
        max_length=30, blank=True,
        verbose_name=_('Numéro MonCash (dépôts hors ligne)'),
        help_text=_('Compte MonCash de la plateforme où les clients déposent pour recharger leur wallet.'),
    )
    numero_natcash_depot = models.CharField(
        max_length=30, blank=True,
        verbose_name=_('Numéro NatCash (dépôts hors ligne)'),
        help_text=_('Compte NatCash de la plateforme où les clients déposent pour recharger leur wallet.'),
    )

    # ── Application Android ─────────────────────────────────────
    android_apk = models.FileField(
        upload_to='android/',
        null=True,
        blank=True,
        verbose_name=_('Application Android (.apk)'),
        help_text=_('Fichier .apk de l\'application Android. Affiché comme bannière de téléchargement sur le site.'),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Configuration du site')
        verbose_name_plural = _('Configuration du site')

    def __str__(self):
        return f'Configuration — {self.nom_site}'

    @classmethod
    def get_solo(cls):
        """Retourne l'unique instance (singleton). La crée si elle n'existe pas."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1  # force singleton
        super().save(*args, **kwargs)


# ── FAQ ─────────────────────────────────────────────────────────────────────

class FAQCategorie(models.Model):
    titre     = models.CharField(max_length=100, verbose_name=_('Titre de la catégorie'))
    icone     = models.CharField(
        max_length=60, blank=True,
        verbose_name=_('Icône Font Awesome'),
        help_text=_('Ex: fas fa-question-circle'),
    )
    ordre     = models.PositiveSmallIntegerField(default=0, verbose_name=_('Ordre'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        verbose_name        = _('Catégorie FAQ')
        verbose_name_plural = _('Catégories FAQ')
        ordering            = ['ordre', 'titre']

    def __str__(self):
        return self.titre


class FAQItem(models.Model):
    categorie = models.ForeignKey(
        FAQCategorie, on_delete=models.CASCADE,
        related_name='items', verbose_name=_('Catégorie'),
    )
    question  = models.CharField(max_length=400, verbose_name=_('Question'))
    reponse   = models.TextField(verbose_name=_('Réponse'))
    ordre     = models.PositiveSmallIntegerField(default=0, verbose_name=_('Ordre'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        verbose_name        = _('Question FAQ')
        verbose_name_plural = _('Questions FAQ')
        ordering            = ['categorie__ordre', 'ordre']

    def __str__(self):
        return self.question[:80]


# ── Messages de contact ──────────────────────────────────────────────────────

class ContactMessage(models.Model):
    nom       = models.CharField(max_length=100, verbose_name=_('Nom complet'))
    email     = models.EmailField(verbose_name=_('Email'))
    telephone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    sujet     = models.CharField(max_length=200, verbose_name=_('Sujet'))
    message   = models.TextField(verbose_name=_('Message'))
    est_lu    = models.BooleanField(default=False, verbose_name=_('Lu'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Reçu le'))

    class Meta:
        verbose_name        = _('Message de contact')
        verbose_name_plural = _('Messages de contact')
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.nom} — {self.sujet} ({self.created_at.strftime("%d/%m/%Y")})'
