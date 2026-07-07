from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', _('Super Administrateur')
        PRODUCTEUR = 'producteur', _('Producteur')
        ACHETEUR   = 'acheteur',   _('Acheteur')
        COLLECTEUR = 'collecteur', _('Agent de Collecte')

    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.ACHETEUR)
    telephone   = models.CharField(max_length=20, blank=True)
    photo       = models.ImageField(upload_to='users/photos/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    fcm_token   = models.TextField(blank=True, help_text=_("Firebase token pour notifications push"))
    code_parrainage = models.CharField(
        max_length=12, unique=True, null=True, blank=True,
        verbose_name=_('Code de parrainage'),
        help_text=_("Code à partager — généré à la demande (wallet)."),
    )
    parraine_par = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='filleuls', verbose_name=_('Parrainé par'),
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email', 'role']

    class Meta:
        verbose_name        = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def get_or_create_code_parrainage(self):
        """Retourne le code de parrainage de l'utilisateur, le génère au besoin."""
        if self.code_parrainage:
            return self.code_parrainage
        import secrets
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not type(self).objects.filter(code_parrainage=code).exists():
                break
        self.code_parrainage = code
        self.save(update_fields=['code_parrainage'])
        return code

    @property
    def is_producteur(self):
        return self.role == self.Role.PRODUCTEUR

    @property
    def is_acheteur(self):
        return self.role == self.Role.ACHETEUR
