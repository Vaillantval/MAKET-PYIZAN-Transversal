from django.urls import path
from apps.accounts.views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    TokenRefreshView,
    AdresseListCreateView,
    AdresseDetailView,
    AdresseSetDefaultView,
    MesCommandesView,
    CommandeDetailView,
    ChangePasswordView,
    ProducteurStatsView,
    ProducteurCommandesView,
    ProducteurCommandeDetailView,
    ProducteurCommandeStatutView,
    ProducteurProfilUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/',       RegisterView.as_view(),     name='register'),
    path('login/',          LoginView.as_view(),         name='login'),
    path('logout/',         LogoutView.as_view(),        name='logout'),
    path('token/refresh/',  TokenRefreshView.as_view(),  name='token_refresh'),
    path('me/',             MeView.as_view(),             name='me'),

    # Adresses
    path('adresses/',                    AdresseListCreateView.as_view(), name='adresses'),
    path('adresses/<int:pk>/',           AdresseDetailView.as_view(),     name='adresse_detail'),
    path('adresses/<int:pk>/default/',   AdresseSetDefaultView.as_view(), name='adresse_default'),

    # Commandes acheteur
    path('commandes/',                   MesCommandesView.as_view(),   name='mes_commandes'),
    path('commandes/<str:numero>/',      CommandeDetailView.as_view(), name='commande_detail'),

    # Changement de mot de passe
    path('change-password/',             ChangePasswordView.as_view(), name='change_password'),

    # Dashboard Producteur
    path('producteur/stats/',                              ProducteurStatsView.as_view(),           name='producteur_stats'),
    path('producteur/profil/',                             ProducteurProfilUpdateView.as_view(),     name='producteur_profil'),
    path('producteur/commandes/',                          ProducteurCommandesView.as_view(),        name='producteur_commandes'),
    path('producteur/commandes/<str:numero>/',             ProducteurCommandeDetailView.as_view(),   name='producteur_commande_detail'),
    path('producteur/commandes/<str:numero>/statut/',      ProducteurCommandeStatutView.as_view(),   name='producteur_commande_statut'),
]
