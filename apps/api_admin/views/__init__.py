from .stats_views      import global_stats, admin_options
from .user_views       import users_list, user_create, user_detail, user_toggle, users_carte
from .producteur_views import (
    producteurs_list, producteur_create,
    producteur_detail, producteur_statut,
)
from .commande_views   import commandes_list, commande_detail, commande_statut
from .paiement_views   import paiements_list, paiement_statut
from .catalogue_views  import (
    catalogue_list, catalogue_create,
    catalogue_detail, catalogue_statut, catalogue_toggle,
    categories_admin, categorie_detail,
)
from .stock_views      import (
    lots_list, lot_create, lot_detail,
    alertes_stock, mouvements_stock,
)
from .collecte_views   import (
    collectes_list, collecte_create, collecte_detail,
    collecte_statut, collecte_add_participation,
    participation_statut, participation_delete,
    zones_list, zone_detail, points_list, point_detail,
)
from .config_views     import (
    site_config,
    android_apk,
    faq_categories, faq_categorie_detail,
    faq_items, faq_item_detail,
    contact_messages, contact_message_detail, repondre_contact,
    slider_list, slider_detail,
)
from .acheteur_views   import (
    acheteurs_list, acheteur_detail,
    vouchers_list, voucher_detail,
    programmes_list, programme_detail,
    adresses_list_admin,
)
