from django.urls import path
from apps.orders.views import (
    PanierView,
    PanierAjouterView,
    PanierRetirerView,
    PanierModifierView,
    PanierViderView,
    CommanderView,
)

app_name = 'orders'

urlpatterns = [
    path('panier/',                       PanierView.as_view(),        name='panier'),
    path('panier/ajouter/',               PanierAjouterView.as_view(), name='panier_ajouter'),
    path('panier/retirer/<slug:slug>/',   PanierRetirerView.as_view(), name='panier_retirer'),
    path('panier/modifier/<slug:slug>/',  PanierModifierView.as_view(),name='panier_modifier'),
    path('panier/vider/',                 PanierViderView.as_view(),   name='panier_vider'),
    path('commander/',                    CommanderView.as_view(),      name='commander'),
]
