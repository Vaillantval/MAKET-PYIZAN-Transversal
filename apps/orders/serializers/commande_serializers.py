from rest_framework import serializers
from apps.accounts.models import Adresse
from django.utils.translation import gettext_lazy as _


class PasserCommandeSerializer(serializers.Serializer):
    """Données pour passer une commande depuis le panier."""

    METHODES = ['cash', 'moncash', 'natcash', 'hors_ligne']
    MODES    = ['domicile', 'collecte', 'retrait']

    methode_paiement      = serializers.ChoiceField(choices=METHODES)
    mode_livraison        = serializers.ChoiceField(choices=MODES)

    # Adresse — soit un ID soit du texte libre
    adresse_livraison_id   = serializers.IntegerField(
                               required=False, allow_null=True
                             )
    adresse_livraison_text = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )
    ville_livraison        = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )
    departement_livraison  = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )

    # Preuve de paiement (hors ligne) — JPG, PNG ou PDF acceptés
    preuve_paiement        = serializers.FileField(
                               required=False, allow_null=True
                             )

    def validate_preuve_paiement(self, value):
        if value is None:
            return value
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.pdf'):
            raise serializers.ValidationError(
                "Format non supporté. Utilisez JPG, PNG ou PDF."
            )
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Fichier trop volumineux (max 5 Mo)."
            )
        return value

    notes                  = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )

    # Voucher (optionnel)
    code_voucher           = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )

    # Paiement hybride : utiliser le solde du portefeuille, le reste part
    # vers MonCash/NatCash (Plopplop)
    utiliser_wallet        = serializers.BooleanField(
                               required=False, default=False,
                             )

    def validate(self, data):
        mode = data.get('mode_livraison')
        if mode == 'domicile':
            addr_id   = data.get('adresse_livraison_id')
            addr_text = data.get('adresse_livraison_text', '')
            if not addr_id and not addr_text:
                raise serializers.ValidationError(
                    _("Une adresse de livraison est requise pour la livraison à domicile.")
                )
        # Le complément d'un paiement wallet doit être immédiat (Plopplop) :
        # avec cash/virement la réserve serait libérée (24 h) avant l'encaissement.
        if data.get('utiliser_wallet') and data.get('methode_paiement') not in ('moncash', 'natcash'):
            raise serializers.ValidationError(
                _("Le portefeuille est combinable uniquement avec MonCash ou NatCash.")
            )
        return data
