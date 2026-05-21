import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('maket_peyizan')

# Lit tous les paramètres CELERY_* depuis settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tasks.py dans chaque app Django
app.autodiscover_tasks()
