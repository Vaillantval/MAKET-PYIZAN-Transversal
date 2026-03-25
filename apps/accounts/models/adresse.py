from django.db import models
from django.conf import settings
from .producteur import Departement


class Adresse(models.Model):
    class TypeAdresse(models.TextChoices):
        LIVRAISON   = 'livraison',   'Livraison'
        FACTURATION = 'facturation', 'Facturation'

    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='adresses',
    )
    libelle      = models.CharField(max_length=100, verbose_name='Libellé',
                                     help_text='Ex : Domicile, Bureau…')
    nom_complet  = models.CharField(max_length=150, verbose_name='Nom complet du destinataire')
    telephone    = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    rue          = models.CharField(max_length=255, verbose_name='Rue / Adresse')
    commune      = models.CharField(max_length=100, verbose_name='Commune')
    departement  = models.CharField(max_length=20, choices=Departement.choices,
                                     verbose_name='Département')
    section_communale = models.CharField(max_length=150, blank=True, verbose_name='Section communale')
    details      = models.TextField(blank=True, verbose_name='Instructions de livraison')
    type_adresse = models.CharField(max_length=20, choices=TypeAdresse.choices,
                                     default=TypeAdresse.LIVRAISON, verbose_name='Type')
    is_default   = models.BooleanField(default=False, verbose_name='Adresse par défaut')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Adresse'
        verbose_name_plural = 'Adresses'
        ordering            = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.libelle} — {self.nom_complet} ({self.commune})"

    def save(self, *args, **kwargs):
        # Si on marque cette adresse comme défaut, retirer le défaut des autres du même type
        if self.is_default:
            Adresse.objects.filter(
                user=self.user,
                type_adresse=self.type_adresse,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
