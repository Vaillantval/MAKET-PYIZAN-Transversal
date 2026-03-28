from django.urls import path
from apps.catalog.views import (
    CategorieListView,
    CataloguePublicListView,
    MonCatalogueView,
    MonProduitDetailView,
    ProduitPublicDetailView,
)

app_name = 'catalog'

urlpatterns = [
    # Public
    path('',                             CataloguePublicListView.as_view(), name='catalogue_public'),
    path('categories/',                  CategorieListView.as_view(),       name='categories'),
    path('public/<slug:slug>/',          ProduitPublicDetailView.as_view(), name='produit_public_detail'),
    # Producteur connecté
    path('mes-produits/',                MonCatalogueView.as_view(),        name='mes_produits'),
    path('mes-produits/<slug:slug>/',    MonProduitDetailView.as_view(),    name='mon_produit_detail'),
]
