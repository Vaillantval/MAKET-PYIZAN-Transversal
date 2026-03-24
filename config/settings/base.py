from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.catalog',
    'apps.stock',
    'apps.orders',
    'apps.payments',
    'apps.collectes',
    'apps.analytics',
    'apps.emails',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
AUTH_USER_MODEL = 'accounts.CustomUser'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Port-au-Prince'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_URL = config('SITE_URL', default='https://maketpeyizan.ht')

# ── DRF ────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ── JWT ─────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ── CORS ────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL', default=True, cast=bool)

# ── SPECTACULAR (API Docs) ───────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Makèt Peyizan API',
    'DESCRIPTION': 'API REST — Marketplace agricole haïtienne',
    'VERSION': '1.0.0',
}

# ── JAZZMIN ─────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title":    "Makèt Peyizan",
    "site_brand":    "Makèt Peyizan",
    "site_header":   "Administration",
    "welcome_sign":  "Bienvenue sur Makèt Peyizan",
    "copyright":     "Makèt Peyizan Haiti",
    "search_model":  ["accounts.CustomUser", "catalog.Produit"],
    "show_sidebar":  True,
    "navigation_expanded": True,
    "icons": {
        "accounts.CustomUser":      "fas fa-users",
        "accounts.Producteur":      "fas fa-tractor",
        "accounts.Acheteur":        "fas fa-shopping-basket",
        "catalog.Produit":          "fas fa-box",
        "catalog.Categorie":        "fas fa-tags",
        "orders.Commande":          "fas fa-file-invoice",
        "stock.Lot":                "fas fa-warehouse",
        "stock.AlerteStock":        "fas fa-exclamation-triangle",
        "payments.Paiement":        "fas fa-credit-card",
        "payments.Voucher":         "fas fa-ticket-alt",
        "collectes.Collecte":       "fas fa-truck",
    },
    "topmenu_links": [
        {
            "name":        "Dashboard BI",
            "url":         "/analytics/dashboard/",
            "icon":        "fas fa-chart-line",
            "permissions": ["auth.view_user"],
        },
        {"name": "Swagger API", "url": "/api/schema/swagger-ui/", "icon": "fas fa-code"},
    ],
    "custom_links": {
        "analytics": [{
            "name":        "Dashboard BI",
            "url":         "/analytics/dashboard/",
            "icon":        "fas fa-chart-line",
            "permissions": ["auth.view_user"],
        }]
    },
    "order_with_respect_to": [
        "analytics", "accounts", "catalog",
        "orders", "payments", "stock", "collectes",
    ],
}

# ── JAZZMIN UI ──────────────────────────────────────────────────
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text":          False,
    "footer_small_text":          False,
    "body_small_text":            False,
    "brand_small_text":           False,
    "brand_colour":               "navbar-success",
    "accent":                     "accent-success",
    "navbar":                     "navbar-success navbar-dark",
    "no_navbar_border":           False,
    "navbar_fixed":               True,
    "layout_boxed":               False,
    "footer_fixed":               False,
    "sidebar_fixed":              True,
    "sidebar":                    "sidebar-dark-success",
    "sidebar_nav_small_text":     False,
    "sidebar_disable_expand":     False,
    "sidebar_nav_child_indent":   True,
    "sidebar_nav_compact_style":  False,
    "sidebar_nav_legacy_style":   False,
    "sidebar_nav_flat_style":     False,
    "theme":                      "default",
    "dark_mode_theme":            "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-outline-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
}

# ── EMAIL (Resend) ───────────────────────────────────────────────
RESEND_API_KEY      = config('RESEND_API_KEY', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL', default='Maket Peyizan <info@maketpeyizan.ht>')
ADMINS_NOTIFY       = config('ADMINS_NOTIFY', default='')

# ── MONCASH ─────────────────────────────────────────────────────
MONCASH_CLIENT_ID   = config('MONCASH_CLIENT_ID', default='')
MONCASH_SECRET_KEY  = config('MONCASH_SECRET_KEY', default='')
MONCASH_ENVIRONMENT = config('MONCASH_ENVIRONMENT', default='sandbox')
