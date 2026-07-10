from django.urls import path

from apps.wallet import views

app_name = 'wallet'

urlpatterns = [
    path('',                      views.wallet_detail,       name='detail'),
    path('transactions/',         views.wallet_transactions, name='transactions'),
    path('code-paiement/',        views.code_paiement_generer, name='code_paiement'),

    # Recharges
    path('recharge/initier/',     views.recharge_initier,    name='recharge_initier'),
    path('recharge/verifier/',    views.recharge_verifier,   name='recharge_verifier'),
    path('recharge/hors-ligne/',  views.recharge_hors_ligne, name='recharge_hors_ligne'),

    # Paiement de commandes
    path('payer/',                views.payer_commande,      name='payer'),
    path('payer-partiel/',        views.payer_partiel,       name='payer_partiel'),
    path('liberer-partiel/',      views.liberer_partiel,     name='liberer_partiel'),

    # Retraits
    path('retrait/',              views.retrait_demander,    name='retrait'),
    path('retraits/',             views.retraits_liste,      name='retraits'),

    # Bons cadeaux
    path('bon/acheter/',          views.bon_acheter,         name='bon_acheter'),
    path('bon/verifier/',         views.bon_verifier,        name='bon_verifier'),
    path('bon/encaisser/',        views.bon_encaisser,       name='bon_encaisser'),
    path('bons/',                 views.bons_achetes,        name='bons_achetes'),
    path('bons/recus/',           views.bons_recus,          name='bons_recus'),
]
