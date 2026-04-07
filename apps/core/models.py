from django.db import models


# ── Configuration globale du site (singleton) ────────────────────────────────

class SiteSettings(models.Model):

    # ── Identité ────────────────────────────────────────────────
    nom_site        = models.CharField(
        max_length=100, default='Makèt Peyizan',
        verbose_name='Nom du site',
    )
    slogan          = models.CharField(
        max_length=200, default='Marketplace Agricole Haïtienne',
        verbose_name='Slogan / sous-titre',
    )
    logo            = models.ImageField(
        upload_to='site/logo/', null=True, blank=True,
        verbose_name='Logo',
        help_text='Recommandé : PNG transparent, 200×60 px minimum',
    )
    favicon         = models.ImageField(
        upload_to='site/favicon/', null=True, blank=True,
        verbose_name='Favicon',
        help_text='ICO ou PNG 32×32 px',
    )

    # ── Textes page d'accueil ───────────────────────────────────
    hero_badge_texte  = models.CharField(
        max_length=100, default='Marketplace Agricole Haïtienne', blank=True,
        verbose_name='Texte du badge hero',
    )
    hero_titre_ligne1 = models.CharField(
        max_length=200, default='Sòti nan jaden', blank=True,
        verbose_name='Hero — titre ligne 1',
    )
    hero_titre_ligne2 = models.CharField(
        max_length=200, default='rive lakay ou', blank=True,
        verbose_name='Hero — titre ligne 2',
    )
    hero_sous_titre   = models.TextField(
        default=(
            'Manje m se medikaman m — Achetez directement auprès '
            'des producteurs locaux. Produits frais, traçables, '
            'livrés depuis les champs d\'Haïti.'
        ),
        blank=True,
        verbose_name='Hero — sous-titre',
    )

    # ── À propos ────────────────────────────────────────────────
    a_propos_titre   = models.CharField(
        max_length=200, default='À propos de Makèt Peyizan', blank=True,
        verbose_name='Titre de la page À propos',
    )
    a_propos_contenu = models.TextField(
        blank=True,
        verbose_name='Présentation générale',
        help_text='Texte principal de la page À propos',
    )
    a_propos_mission = models.TextField(
        blank=True,
        verbose_name='Notre mission',
    )
    a_propos_vision  = models.TextField(
        blank=True,
        verbose_name='Notre vision',
    )
    a_propos_image   = models.ImageField(
        upload_to='site/apropos/', null=True, blank=True,
        verbose_name='Image À propos',
    )
    annee_fondation  = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Année de fondation',
    )

    # ── Contact ─────────────────────────────────────────────────
    email_contact    = models.EmailField(
        default='info@maketpeyizan.ht', blank=True,
        verbose_name='Email de contact',
    )
    telephone        = models.CharField(
        max_length=30, blank=True,
        verbose_name='Téléphone',
    )
    whatsapp         = models.CharField(
        max_length=30, blank=True,
        verbose_name='WhatsApp',
        help_text='Numéro avec indicatif ex: +509 XXXX-XXXX',
    )
    adresse          = models.TextField(
        blank=True,
        verbose_name='Adresse physique',
    )
    horaires         = models.CharField(
        max_length=200, blank=True,
        verbose_name='Horaires d\'ouverture',
        help_text='Ex: Lun–Ven 8h–17h',
    )

    # ── Réseaux sociaux ─────────────────────────────────────────
    facebook_url     = models.URLField(
        blank=True, verbose_name='Facebook URL',
    )
    instagram_url    = models.URLField(
        blank=True, verbose_name='Instagram URL',
    )
    twitter_url      = models.URLField(
        blank=True, verbose_name='Twitter / X URL',
    )
    youtube_url      = models.URLField(
        blank=True, verbose_name='YouTube URL',
    )

    # ── Footer & SEO ─────────────────────────────────────────────
    copyright_texte  = models.CharField(
        max_length=300,
        default='Makèt Peyizan Haiti. Tous droits réservés.',
        blank=True,
        verbose_name='Texte copyright',
    )
    meta_description = models.TextField(
        blank=True,
        verbose_name='Meta description (SEO)',
        help_text='160 caractères max recommandé',
    )
    google_analytics_id = models.CharField(
        max_length=50, blank=True,
        verbose_name='Google Analytics ID',
        help_text='Format : G-XXXXXXXXXX',
    )

    # ── Pages d'authentification ────────────────────────────────
    login_image     = models.ImageField(
        upload_to='site/auth/', null=True, blank=True,
        verbose_name='Image page Connexion',
        help_text='Panneau gauche de la page de connexion. Recommandé : 800×1000 px',
    )
    register_image  = models.ImageField(
        upload_to='site/auth/', null=True, blank=True,
        verbose_name='Image page Inscription',
        help_text='Panneau gauche de la page d\'inscription. Recommandé : 800×1000 px',
    )

    # ── Maintenance ─────────────────────────────────────────────
    mode_maintenance    = models.BooleanField(
        default=False,
        verbose_name='Mode maintenance',
        help_text='Active une page de maintenance pour les visiteurs',
    )
    message_maintenance = models.TextField(
        blank=True,
        verbose_name='Message de maintenance',
        help_text='Message affiché pendant la maintenance',
    )

    # ── Application Android ─────────────────────────────────────
    android_apk = models.FileField(
        upload_to='android/',
        null=True,
        blank=True,
        verbose_name='Application Android (.apk)',
        help_text='Fichier .apk de l\'application Android. Affiché comme bannière de téléchargement sur le site.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Configuration du site'
        verbose_name_plural = 'Configuration du site'

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
    titre     = models.CharField(max_length=100, verbose_name='Titre de la catégorie')
    icone     = models.CharField(
        max_length=60, blank=True,
        verbose_name='Icône Font Awesome',
        help_text='Ex: fas fa-question-circle',
    )
    ordre     = models.PositiveSmallIntegerField(default=0, verbose_name='Ordre')
    is_active = models.BooleanField(default=True, verbose_name='Active')

    class Meta:
        verbose_name        = 'Catégorie FAQ'
        verbose_name_plural = 'Catégories FAQ'
        ordering            = ['ordre', 'titre']

    def __str__(self):
        return self.titre


class FAQItem(models.Model):
    categorie = models.ForeignKey(
        FAQCategorie, on_delete=models.CASCADE,
        related_name='items', verbose_name='Catégorie',
    )
    question  = models.CharField(max_length=400, verbose_name='Question')
    reponse   = models.TextField(verbose_name='Réponse')
    ordre     = models.PositiveSmallIntegerField(default=0, verbose_name='Ordre')
    is_active = models.BooleanField(default=True, verbose_name='Active')

    class Meta:
        verbose_name        = 'Question FAQ'
        verbose_name_plural = 'Questions FAQ'
        ordering            = ['categorie__ordre', 'ordre']

    def __str__(self):
        return self.question[:80]


# ── Messages de contact ──────────────────────────────────────────────────────

class ContactMessage(models.Model):
    nom       = models.CharField(max_length=100, verbose_name='Nom complet')
    email     = models.EmailField(verbose_name='Email')
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    sujet     = models.CharField(max_length=200, verbose_name='Sujet')
    message   = models.TextField(verbose_name='Message')
    est_lu    = models.BooleanField(default=False, verbose_name='Lu')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Reçu le')

    class Meta:
        verbose_name        = 'Message de contact'
        verbose_name_plural = 'Messages de contact'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.nom} — {self.sujet} ({self.created_at.strftime("%d/%m/%Y")})'
