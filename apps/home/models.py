from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SiteConfig(models.Model):
    """Configuration générale du site."""
    nom_site         = models.CharField(max_length=100, default='Makèt Peyizan')
    slogan           = models.TextField(blank=True)
    email_contact    = models.EmailField(blank=True)
    telephone        = models.CharField(max_length=20, blank=True)
    adresse          = models.TextField(blank=True)
    facebook_url     = models.URLField(blank=True)
    instagram_url    = models.URLField(blank=True)
    whatsapp_numero  = models.CharField(max_length=20, blank=True)
    is_active        = models.BooleanField(default=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Configuration site')
        verbose_name_plural = _('Configurations site')

    def __str__(self):
        return self.nom_site

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class FAQCategorie(models.Model):
    """Catégorie de questions fréquentes."""
    titre     = models.CharField(max_length=100)
    ordre     = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name        = _('Catégorie FAQ')
        verbose_name_plural = _('Catégories FAQ')
        ordering            = ['ordre', 'titre']

    def __str__(self):
        return self.titre


class FAQItem(models.Model):
    """Question/réponse fréquente."""
    categorie = models.ForeignKey(
                  FAQCategorie,
                  on_delete=models.CASCADE,
                  related_name='items'
                )
    question  = models.CharField(max_length=300)
    reponse   = models.TextField()
    ordre     = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name        = _('Item FAQ')
        verbose_name_plural = _('Items FAQ')
        ordering            = ['ordre']

    def __str__(self):
        return self.question


class SliderImage(models.Model):
    """Slide de la bannière principale de la page d'accueil."""
    titre        = models.CharField(max_length=120, blank=True)
    sous_titre   = models.CharField(max_length=220, blank=True)
    texte_bouton = models.CharField(max_length=50, blank=True, default='Découvrir')
    lien         = models.CharField(max_length=255, blank=True, help_text=_('URL ou ancre (#catalogue)'))
    image        = models.ImageField(upload_to='slider/', help_text=_('Résolution recommandée : 1600 × 700 px'))
    ordre        = models.PositiveSmallIntegerField(default=0)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Slide')
        verbose_name_plural = _('Slides')
        ordering            = ['ordre', 'created_at']

    def __str__(self):
        return self.titre or f'Slide #{self.pk}'


class ContactMessage(models.Model):
    """Message envoyé via le formulaire de contact."""
    class Statut(models.TextChoices):
        NOUVEAU  = 'nouveau',  _('Nouveau')
        LU       = 'lu',       _('Lu')
        REPONDU  = 'repondu',  _('Répondu')
        ARCHIVE  = 'archive',  _('Archivé')

    nom        = models.CharField(max_length=100)
    email      = models.EmailField()
    telephone  = models.CharField(max_length=20, blank=True)
    sujet      = models.CharField(max_length=200, blank=True)
    message    = models.TextField()
    statut     = models.CharField(
                   max_length=20,
                   choices=Statut.choices,
                   default=Statut.NOUVEAU
                 )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Message de contact')
        verbose_name_plural = _('Messages de contact')
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.sujet}"


class ContactReponse(models.Model):
    """Réponse d'un super-admin à un message de contact."""
    message    = models.ForeignKey(
                   ContactMessage,
                   on_delete=models.CASCADE,
                   related_name='reponses',
                 )
    contenu    = models.TextField(verbose_name=_('Contenu de la réponse'))
    envoye_par = models.ForeignKey(
                   settings.AUTH_USER_MODEL,
                   on_delete=models.SET_NULL,
                   null=True, blank=True,
                   related_name='reponses_contact',
                 )
    envoye_le  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Réponse contact')
        verbose_name_plural = _('Réponses contact')
        ordering            = ['envoye_le']

    def __str__(self):
        return f"Réponse à {self.message.nom} — {self.envoye_le.strftime('%d/%m/%Y')}"
