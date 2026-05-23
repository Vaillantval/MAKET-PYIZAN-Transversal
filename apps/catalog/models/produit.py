from django.db import models
from django.conf import settings
from django.utils.text import slugify
import qrcode
import io
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _


class UniteVente(models.TextChoices):
    KG       = 'kg',     _('Kilogramme (kg)')
    TONNE    = 'tonne',  _('Tonne')
    SAC_50KG = 'sac_50', _('Sac 50 kg')
    SAC_25KG = 'sac_25', _('Sac 25 kg')
    BOTTE    = 'botte',  _('Botte')
    PIECE    = 'piece',  _('Piece')
    LITRE    = 'litre',  _('Litre')
    CARTON   = 'carton', _('Carton')
    DOUZ     = 'douz',   _('Douzaine')


class Produit(models.Model):
    class Statut(models.TextChoices):
        BROUILLON  = 'brouillon',  _('Brouillon')
        EN_ATTENTE = 'en_attente', _('En attente de validation')
        ACTIF      = 'actif',      _('Actif')
        EPUISE     = 'epuise',     _('Epuise')
        INACTIF    = 'inactif',    _('Inactif')

    producteur            = models.ForeignKey('accounts.Producteur', on_delete=models.CASCADE, related_name='produits')
    categorie             = models.ForeignKey('catalog.Categorie', on_delete=models.PROTECT, related_name='produits')
    nom                   = models.CharField(max_length=200)
    slug                  = models.SlugField(max_length=220, unique=True, blank=True)
    description           = models.TextField(blank=True)
    variete               = models.CharField(max_length=100, blank=True)
    prix_unitaire         = models.DecimalField(max_digits=10, decimal_places=2)
    prix_gros             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unite_vente           = models.CharField(max_length=20, choices=UniteVente.choices, default=UniteVente.KG)
    quantite_min_commande = models.PositiveIntegerField(default=1)
    stock_disponible      = models.PositiveIntegerField(default=0)
    seuil_alerte          = models.PositiveIntegerField(default=10)
    stock_reserve         = models.PositiveIntegerField(default=0)
    image_principale      = models.ImageField(upload_to='produits/images/', null=True, blank=True)
    qr_code               = models.ImageField(upload_to='produits/qrcodes/', null=True, blank=True)
    origine               = models.CharField(max_length=200, blank=True)
    saison                = models.CharField(max_length=100, blank=True)
    certifications        = models.CharField(max_length=200, blank=True)
    statut                = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    is_active             = models.BooleanField(default=False)
    is_featured           = models.BooleanField(default=False)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Produit')
        verbose_name_plural = _('Produits')
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.producteur.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.nom}-{self.producteur.code_producteur}")
            slug = base
            n = 1
            while Produit.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if self.stock_disponible == 0 and self.statut == self.Statut.ACTIF:
            self.statut    = self.Statut.EPUISE
            self.is_active = False
        super().save(*args, **kwargs)
        if not self.qr_code:
            self._generer_qr_code()

    def _generer_qr_code(self):
        site_url = getattr(settings, 'SITE_URL', 'https://maketpeyizan.ht')
        data = (
            f"{site_url}/produits/{self.slug}/\n"
            f"Produit : {self.nom}\n"
            f"Producteur : {self.producteur.user.get_full_name()}\n"
            f"Commune : {self.producteur.commune}\n"
            f"Prix : {self.prix_unitaire} HTG / {self.get_unite_vente_display()}"
        )
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img      = qr.make_image(fill_color="black", back_color="white")
        buffer   = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.slug}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)

    @property
    def stock_reel(self):
        return max(0, self.stock_disponible - self.stock_reserve)

    @property
    def est_en_alerte(self):
        return self.stock_disponible <= self.seuil_alerte

    @property
    def prix_affiche(self):
        return self.prix_unitaire

    def recalculer_stock_reserve(self):
        from django.db.models import Sum
        from apps.orders.models import Commande
        total = Commande.objects.filter(
            details__produit=self,
            statut__in=[Commande.Statut.EN_ATTENTE, Commande.Statut.CONFIRMEE],
        ).aggregate(total=Sum('details__quantite'))['total'] or 0
        self.stock_reserve = total
        self.save(update_fields=['stock_reserve'])
        return self.stock_reserve


class ImageProduit(models.Model):
    produit    = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='produits/galerie/')
    legende    = models.CharField(max_length=200, blank=True)
    ordre      = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Image produit')
        verbose_name_plural = _('Images produit')
        ordering            = ['ordre']

    def __str__(self):
        return f"Image {self.ordre} — {self.produit.nom}"
