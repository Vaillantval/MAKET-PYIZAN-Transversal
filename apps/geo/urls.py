from django.urls import path
from . import views

app_name = 'geo'

urlpatterns = [
    path('departements/',    views.departements,        name='departements'),
    path('arrondissements/', views.arrondissements,     name='arrondissements'),
    path('communes/',        views.communes,            name='communes'),
    path('sections/',        views.sections_communales, name='sections'),
    path('arbre/',           views.arbre_complet,       name='arbre'),
    path('recherche/',       views.recherche,           name='recherche'),
]
