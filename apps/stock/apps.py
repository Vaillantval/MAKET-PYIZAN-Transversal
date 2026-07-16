from django.apps import AppConfig

class StockConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stock'
    verbose_name = 'Gestion des Stocks'

    def ready(self):
        from apps.stock import signals  # noqa: F401
