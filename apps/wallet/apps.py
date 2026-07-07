from django.apps import AppConfig


class WalletConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.wallet'
    verbose_name = 'Portefeuille'

    def ready(self):
        from apps.wallet import signals  # noqa: F401
