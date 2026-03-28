from django.urls import path
from apps.accounts.views_superadmin import (
    AdminStatsView,
    AdminUsersView, AdminUserToggleView, AdminUserCreateView, AdminUserDetailView,
    AdminProducteursView, AdminProducteurStatutView, AdminProducteurCreateView, AdminProducteurDetailView,
    AdminCommandesView, AdminCommandeDetailView, AdminCommandeStatutView,
    AdminPaiementsView, AdminPaiementStatutView,
    AdminCatalogueView, AdminCatalogueToggleView, AdminCatalogueStatutView,
    AdminCatalogueCreateView, AdminCatalogueDetailView,
    AdminStocksLotsView, AdminStocksAlertesView, AdminStockLotCreateView, AdminStockLotDetailView,
    AdminStocksMouvementsView,
    AdminCollectesView, AdminCollecteDetailView, AdminCollecteStatutView,
    AdminCollecteCreateView, AdminCollecteEditView,
    AdminCollecteAddParticipationView,
    AdminParticipationStatutView, AdminParticipationDeleteView,
    AdminOptionsView,
    # Nouveaux
    AdminAcheteursView, AdminAcheteurDetailView,
    AdminAdressesView,
    AdminCategoriesView, AdminCategorieDetailView,
    AdminVoucherProgrammesView, AdminVoucherProgrammeDetailView,
    AdminVouchersView, AdminVoucherDetailView,
    AdminZonesCollecteView, AdminZoneCollecteDetailView,
    AdminPointsCollecteView, AdminPointCollecteDetailView,
    AdminSiteSettingsView,
    AdminFAQCategoriesView, AdminFAQCategorieDetailView,
    AdminFAQItemsView, AdminFAQItemDetailView,
    AdminContactMessagesView, AdminContactMessageDetailView,
)

urlpatterns = [
    path('stats/',                                            AdminStatsView.as_view(),                    name='admin_stats'),
    path('options/',                                          AdminOptionsView.as_view(),                  name='admin_options'),

    # Utilisateurs
    path('users/',                                            AdminUsersView.as_view(),                    name='admin_users'),
    path('users/create/',                                     AdminUserCreateView.as_view(),               name='admin_user_create'),
    path('users/<int:pk>/toggle/',                            AdminUserToggleView.as_view(),               name='admin_user_toggle'),
    path('users/<int:pk>/detail/',                            AdminUserDetailView.as_view(),               name='admin_user_detail'),

    # Producteurs
    path('producteurs/',                                      AdminProducteursView.as_view(),              name='admin_producteurs'),
    path('producteurs/create/',                               AdminProducteurCreateView.as_view(),         name='admin_producteur_create'),
    path('producteurs/<int:pk>/statut/',                      AdminProducteurStatutView.as_view(),         name='admin_producteur_statut'),
    path('producteurs/<int:pk>/detail/',                      AdminProducteurDetailView.as_view(),         name='admin_producteur_detail'),

    # Commandes
    path('commandes/',                                        AdminCommandesView.as_view(),                name='admin_commandes'),
    path('commandes/<str:numero>/',                           AdminCommandeDetailView.as_view(),           name='admin_commande_detail'),
    path('commandes/<str:numero>/statut/',                    AdminCommandeStatutView.as_view(),           name='admin_commande_statut'),

    # Paiements
    path('paiements/',                                        AdminPaiementsView.as_view(),                name='admin_paiements'),
    path('paiements/<int:pk>/statut/',                        AdminPaiementStatutView.as_view(),           name='admin_paiement_statut'),

    # Catalogue
    path('catalogue/',                                        AdminCatalogueView.as_view(),                name='admin_catalogue'),
    path('catalogue/create/',                                 AdminCatalogueCreateView.as_view(),          name='admin_catalogue_create'),
    path('catalogue/<int:pk>/toggle/',                        AdminCatalogueToggleView.as_view(),          name='admin_catalogue_toggle'),
    path('catalogue/<int:pk>/statut/',                        AdminCatalogueStatutView.as_view(),          name='admin_catalogue_statut'),
    path('catalogue/<int:pk>/detail/',                        AdminCatalogueDetailView.as_view(),          name='admin_catalogue_detail'),

    # Stocks
    path('stocks/lots/',                                      AdminStocksLotsView.as_view(),               name='admin_stocks_lots'),
    path('stocks/lots/create/',                               AdminStockLotCreateView.as_view(),           name='admin_stock_lot_create'),
    path('stocks/lots/<int:pk>/',                             AdminStockLotDetailView.as_view(),           name='admin_stock_lot_detail'),
    path('stocks/alertes/',                                   AdminStocksAlertesView.as_view(),            name='admin_stocks_alertes'),

    # Stocks — mouvements
    path('stocks/mouvements/',                                AdminStocksMouvementsView.as_view(),         name='admin_stocks_mouvements'),

    # Collectes
    path('collectes/',                                        AdminCollectesView.as_view(),                name='admin_collectes'),
    path('collectes/create/',                                 AdminCollecteCreateView.as_view(),           name='admin_collecte_create'),
    path('collectes/participations/<int:pk>/statut/',         AdminParticipationStatutView.as_view(),      name='admin_participation_statut'),
    path('collectes/participations/<int:pk>/',                AdminParticipationDeleteView.as_view(),      name='admin_participation_delete'),
    path('collectes/<int:pk>/',                               AdminCollecteDetailView.as_view(),           name='admin_collecte_detail'),
    path('collectes/<int:pk>/statut/',                        AdminCollecteStatutView.as_view(),           name='admin_collecte_statut'),
    path('collectes/<int:pk>/edit/',                          AdminCollecteEditView.as_view(),             name='admin_collecte_edit'),
    path('collectes/<int:pk>/participations/',                AdminCollecteAddParticipationView.as_view(), name='admin_collecte_add_participation'),

    # Acheteurs
    path('acheteurs/',                                        AdminAcheteursView.as_view(),                name='admin_acheteurs'),
    path('acheteurs/<int:pk>/',                               AdminAcheteurDetailView.as_view(),           name='admin_acheteur_detail'),

    # Adresses
    path('adresses/',                                         AdminAdressesView.as_view(),                 name='admin_adresses'),

    # Catégories catalogue
    path('categories/',                                       AdminCategoriesView.as_view(),               name='admin_categories'),
    path('categories/<int:pk>/',                              AdminCategorieDetailView.as_view(),          name='admin_categorie_detail'),

    # Vouchers
    path('vouchers/programmes/',                              AdminVoucherProgrammesView.as_view(),        name='admin_voucher_programmes'),
    path('vouchers/programmes/<int:pk>/',                     AdminVoucherProgrammeDetailView.as_view(),   name='admin_voucher_programme_detail'),
    path('vouchers/',                                         AdminVouchersView.as_view(),                 name='admin_vouchers'),
    path('vouchers/<int:pk>/',                                AdminVoucherDetailView.as_view(),            name='admin_voucher_detail'),

    # Zones & Points de collecte
    path('zones/',                                            AdminZonesCollecteView.as_view(),            name='admin_zones'),
    path('zones/<int:pk>/',                                   AdminZoneCollecteDetailView.as_view(),       name='admin_zone_detail'),
    path('points/',                                           AdminPointsCollecteView.as_view(),           name='admin_points'),
    path('points/<int:pk>/',                                  AdminPointCollecteDetailView.as_view(),      name='admin_point_detail'),

    # Configuration du site
    path('config/site/',                                      AdminSiteSettingsView.as_view(),             name='admin_config_site'),
    path('config/faq/categories/',                            AdminFAQCategoriesView.as_view(),            name='admin_faq_categories'),
    path('config/faq/categories/<int:pk>/',                   AdminFAQCategorieDetailView.as_view(),       name='admin_faq_categorie_detail'),
    path('config/faq/items/',                                 AdminFAQItemsView.as_view(),                 name='admin_faq_items'),
    path('config/faq/items/<int:pk>/',                        AdminFAQItemDetailView.as_view(),            name='admin_faq_item_detail'),
    path('config/contact/',                                   AdminContactMessagesView.as_view(),          name='admin_contact_messages'),
    path('config/contact/<int:pk>/',                          AdminContactMessageDetailView.as_view(),     name='admin_contact_message_detail'),
]
