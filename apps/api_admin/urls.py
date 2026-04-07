from django.urls import path
from apps.api_admin import views

app_name = 'api_admin'

urlpatterns = [

    # ── Stats ───────────────────────────────────────────────────
    path('stats/',   views.global_stats,  name='stats'),
    path('options/', views.admin_options, name='options'),

    # ── Utilisateurs ────────────────────────────────────────────
    path('users/',                  views.users_list,   name='users_list'),
    path('users/create/',           views.user_create,  name='user_create'),
    path('users/carte/',            views.users_carte,  name='users_carte'),
    path('users/<int:pk>/detail/',  views.user_detail,  name='user_detail'),
    path('users/<int:pk>/toggle/',  views.user_toggle,  name='user_toggle'),

    # ── Producteurs ─────────────────────────────────────────────
    path('producteurs/',                   views.producteurs_list,  name='producteurs_list'),
    path('producteurs/create/',            views.producteur_create, name='producteur_create'),
    path('producteurs/<int:pk>/detail/',   views.producteur_detail, name='producteur_detail'),
    path('producteurs/<int:pk>/statut/',   views.producteur_statut, name='producteur_statut'),

    # ── Commandes ───────────────────────────────────────────────
    path('commandes/',                     views.commandes_list,  name='commandes_list'),
    path('commandes/<str:numero>/',        views.commande_detail, name='commande_detail'),
    path('commandes/<str:numero>/statut/', views.commande_statut, name='commande_statut'),

    # ── Paiements ───────────────────────────────────────────────
    path('paiements/',                  views.paiements_list,  name='paiements_list'),
    path('paiements/<int:pk>/statut/',  views.paiement_statut, name='paiement_statut'),

    # ── Catalogue ───────────────────────────────────────────────
    path('catalogue/',                  views.catalogue_list,   name='catalogue_list'),
    path('catalogue/create/',           views.catalogue_create, name='catalogue_create'),
    path('catalogue/<int:pk>/detail/',  views.catalogue_detail, name='catalogue_detail'),
    path('catalogue/<int:pk>/statut/',  views.catalogue_statut, name='catalogue_statut'),
    path('catalogue/<int:pk>/toggle/',  views.catalogue_toggle, name='catalogue_toggle'),
    path('categories/',                 views.categories_admin, name='categories_admin'),
    path('categories/<int:pk>/',        views.categorie_detail, name='categorie_detail'),

    # ── Stocks ──────────────────────────────────────────────────
    path('stocks/lots/',              views.lots_list,      name='lots_list'),
    path('stocks/lots/create/',       views.lot_create,     name='lot_create'),
    path('stocks/lots/<int:pk>/',     views.lot_detail,     name='lot_detail'),
    path('stocks/alertes/',           views.alertes_stock,  name='alertes_stock'),
    path('stocks/mouvements/',        views.mouvements_stock, name='mouvements_stock'),

    # ── Collectes ───────────────────────────────────────────────
    path('collectes/',                          views.collectes_list,             name='collectes_list'),
    path('collectes/create/',                   views.collecte_create,            name='collecte_create'),
    path('collectes/<int:pk>/',                 views.collecte_detail,            name='collecte_detail'),
    path('collectes/<int:pk>/statut/',          views.collecte_statut,            name='collecte_statut'),
    path('collectes/<int:pk>/participations/',  views.collecte_add_participation, name='add_participation'),
    path('collectes/participations/<int:pk>/statut/', views.participation_statut, name='participation_statut'),
    path('collectes/participations/<int:pk>/',  views.participation_delete,       name='participation_delete'),
    path('zones/',                              views.zones_list,                 name='zones_list'),
    path('zones/<int:pk>/',                     views.zone_detail,                name='zone_detail'),
    path('points/',                             views.points_list,                name='points_list'),
    path('points/<int:pk>/',                    views.point_detail,               name='point_detail'),

    # ── Config ──────────────────────────────────────────────────
    path('config/site/',                    views.site_config,            name='site_config'),
    path('config/site/apk/',               views.android_apk,            name='android_apk'),
    path('config/faq/categories/',          views.faq_categories,         name='faq_categories'),
    path('config/faq/categories/<int:pk>/', views.faq_categorie_detail,   name='faq_categorie_detail'),
    path('config/faq/items/',               views.faq_items,              name='faq_items'),
    path('config/faq/items/<int:pk>/',      views.faq_item_detail,        name='faq_item_detail'),
    path('config/contact/',                          views.contact_messages,       name='contact_messages'),
    path('config/contact/<int:pk>/',                 views.contact_message_detail, name='contact_detail'),
    path('config/contact/<int:pk>/repondre/',        views.repondre_contact,       name='contact_repondre'),
    path('config/slider/',                  views.slider_list,            name='slider_list'),
    path('config/slider/<int:pk>/',         views.slider_detail,          name='slider_detail'),

    # ── Acheteurs, Vouchers, Adresses ───────────────────────────
    path('acheteurs/',                  views.acheteurs_list,    name='acheteurs_list'),
    path('acheteurs/<int:pk>/',         views.acheteur_detail,   name='acheteur_detail'),
    path('vouchers/',                   views.vouchers_list,     name='vouchers_list'),
    path('vouchers/<int:pk>/',          views.voucher_detail,    name='voucher_detail'),
    path('vouchers/programmes/',        views.programmes_list,   name='programmes_list'),
    path('vouchers/programmes/<int:pk>/', views.programme_detail, name='programme_detail'),
    path('adresses/',                   views.adresses_list_admin, name='adresses_admin'),
]
