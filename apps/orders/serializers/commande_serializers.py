from rest_framework import serializers
from apps.accounts.models import Adresse


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

    # Preuve de paiement (hors ligne)
    preuve_paiement        = serializers.ImageField(
                               required=False, allow_null=True
                             )

    notes                  = serializers.CharField(
                               required=False, allow_blank=True,
                               default='',
                             )

    def validate(self, data):
        mode = data.get('mode_livraison')
        if mode == 'domicile':
            addr_id   = data.get('adresse_livraison_id')
            addr_text = data.get('adresse_livraison_text', '')
            if not addr_id and not addr_text:
                raise serializers.ValidationError(
                    "Une adresse de livraison est requise "
                    "pour la livraison à domicile."
                )
        return data
