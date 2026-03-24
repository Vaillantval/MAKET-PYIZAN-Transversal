from django.db import models
from django.utils.text import slugify


class Categorie(models.Model):
    nom         = models.CharField(max_length=100)
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image       = models.ImageField(upload_to='categories/images/', null=True, blank=True)
    icone       = models.CharField(max_length=50, blank=True, help_text="Classe Font Awesome ex: fas fa-carrot")
    parent      = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sous_categories')
    ordre       = models.PositiveSmallIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Categorie'
        verbose_name_plural = 'Categories'
        ordering            = ['ordre', 'nom']

    def __str__(self):
        if self.parent:
            return f"{self.parent.nom} -> {self.nom}"
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nom)
            slug = base_slug
            n = 1
            while Categorie.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def nb_produits(self):
        return self.produits.filter(is_active=True).count()
