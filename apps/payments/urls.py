from django.urls import path
from apps.payments import views

app_name = 'payments'

urlpatterns = [
    # Paiements
    path('initier/',          views.initier_paiement,  name='initier'),
    path('preuve/',           views.soumettre_preuve,  name='preuve'),
    path('verifier/',         views.verifier_paiement, name='verifier'),
    path('mes-paiements/',    views.mes_paiements,     name='mes_paiements'),

    path('plopplop-verify/', views.plopplop_verify, name='plopplop_verify'),

    # Vouchers
    path('voucher/valider/',       views.valider_voucher, name='voucher_valider'),
    path('voucher/mes-vouchers/',  views.mes_vouchers,    name='mes_vouchers'),
]
