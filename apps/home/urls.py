from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('',                        views.home,                name='index'),
    path('connexion/',              views.login_page,          name='login'),
    path('inscription/',            views.register_page,       name='register'),
    path('inscription/en-attente/', views.register_pending,    name='register_pending'),
    path('dashboard/',              views.dashboard_router,    name='dashboard'),
    path('dashboard/acheteur/',              views.dashboard_acheteur,           name='dashboard_acheteur'),
    path('dashboard/acheteur/commandes/',    views.dashboard_acheteur_commandes, name='dashboard_acheteur_commandes'),
    path('dashboard/acheteur/adresses/',     views.dashboard_acheteur_adresses,  name='dashboard_acheteur_adresses'),
    path('dashboard/acheteur/profil/',       views.dashboard_acheteur_profil,    name='dashboard_acheteur_profil'),
    path('dashboard/producteur/',                 views.dashboard_producteur,             name='dashboard_producteur'),
    path('dashboard/producteur/commandes/',       views.dashboard_producteur_commandes,   name='dashboard_producteur_commandes'),
    path('dashboard/producteur/catalogue/',       views.dashboard_producteur_catalogue,   name='dashboard_producteur_catalogue'),
    path('dashboard/producteur/profil/',          views.dashboard_producteur_profil,      name='dashboard_producteur_profil'),
    path('dashboard/producteur/en-attente/',     views.dashboard_producteur_en_attente,  name='dashboard_producteur_en_attente'),
    path('dashboard/admin/',        views.dashboard_admin,     name='dashboard_admin'),
    path('dashboard/superadmin/',   views.dashboard_superadmin,name='dashboard_superadmin'),
    # Catalogue public
    path('produits/<slug:slug>/',   views.produit_detail,      name='produit_detail'),
    path('panier/',                 views.panier_page,         name='panier'),
    path('commander/',                   views.checkout_page,   name='checkout'),
    path('commander/moncash/retour/',    views.moncash_retour,  name='moncash_retour'),
]
