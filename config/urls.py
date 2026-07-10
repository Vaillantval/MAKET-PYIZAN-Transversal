from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.conf.urls.i18n import i18n_patterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.home.views import health_check, faq_publique, contact_public

urlpatterns = [
    # Endpoint de changement de langue — en dehors de i18n_patterns
    path('i18n/', include('django.conf.urls.i18n')),
    # Fichiers media — servis directement par Django (DEBUG=True et False)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

urlpatterns += i18n_patterns(
    path('health/',  health_check,   name='health'),
    path('faq/',     faq_publique,   name='faq'),
    path('contact/', contact_public, name='contact'),
    path('',            include('apps.home.urls')),
    path('admin/',                   admin.site.urls),
    path('api/auth/',                include('apps.accounts.urls')),
    path('api/admin/',               include('apps.api_admin.urls')),
    path('api/products/',            include('apps.catalog.urls')),
    path('api/stock/',               include('apps.stock.urls')),
    path('api/orders/',              include('apps.orders.urls')),
    path('api/payments/',            include('apps.payments.urls')),
    path('api/wallet/',              include('apps.wallet.urls')),
    path('api/pos/',                 include('apps.pos.urls')),
    path('api/collectes/',           include('apps.collectes.urls')),
    path('api/geo/',                 include('apps.geo.urls')),
    path('',            include('apps.core.urls')),
    path('analytics/',               include('apps.analytics.urls')),
    path('api/schema/',              SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/',        SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    prefix_default_language=False,
)
