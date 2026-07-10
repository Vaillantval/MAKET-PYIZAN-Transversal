from django.urls import path

from apps.pos import views

app_name = 'pos'

urlpatterns = [
    path('session/ouvrir/', views.session_ouvrir, name='session_ouvrir'),
    path('session/fermer/', views.session_fermer, name='session_fermer'),
    path('vente/',          views.vente_creer,    name='vente'),
    path('sync/',           views.sync_ventes,    name='sync'),
    path('catalogue/',      views.catalogue,      name='catalogue'),
    path('rapports/',       views.rapports,       name='rapports'),
]
