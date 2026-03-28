from .base import *
from decouple import config as env
import dj_database_url

DEBUG = False

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# Domaines autorisés — mettre l'URL Railway + domaine custom si applicable
# Ex : ALLOWED_HOSTS=maket-peyizan.up.railway.app,maketpeyizan.ht
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='localhost').split(',')

# Nécessaire pour les requêtes POST (admin Django, formulaires dashboard)
_raw_origins = env('CSRF_TRUSTED_ORIGINS', default='')
if _raw_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _raw_origins.split(',')]

# CORS : en prod mettre les origines Flutter + web
# Ex : CORS_ALLOW_ALL=False  +  CORS_ALLOWED_ORIGINS=https://maketpeyizan.ht
CORS_ALLOW_ALL_ORIGINS = env('CORS_ALLOW_ALL', default=False, cast=bool)
_cors_origins = env('CORS_ALLOWED_ORIGINS', default='')
if _cors_origins and not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',')]

# Fichiers media — monter un Railway Volume sur /app/media
MEDIA_ROOT = '/app/media'
