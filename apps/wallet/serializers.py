from decimal import Decimal

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.wallet.models import BonCadeau, WalletRecharge, WalletRetrait, WalletTransaction


# ── Sorties ─────────────────────────────────────────────────────

class WalletTransactionSerializer(serializers.ModelSerializer):
    type_display     = serializers.CharField(source='get_type_display', read_only=True)
    commande_numero  = serializers.CharField(source='commande.numero_commande', read_only=True, default=None)

    class Meta:
        model  = WalletTransaction
        fields = ['id', 'type', 'type_display', 'montant', 'solde_apres',
                  'commande_numero', 'description', 'reference', 'created_at']


class WalletRechargeSerializer(serializers.ModelSerializer):
    methode_display = serializers.CharField(source='get_methode_display', read_only=True)
    statut_display  = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model  = WalletRecharge
        fields = ['id', 'montant', 'methode', 'methode_display',
                  'statut', 'statut_display', 'reference_plopplop', 'created_at']


class WalletRetraitSerializer(serializers.ModelSerializer):
    canal_display  = serializers.CharField(source='get_canal_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model  = WalletRetrait
        fields = ['id', 'montant', 'canal', 'canal_display', 'numero_telephone',
                  'statut', 'statut_display', 'note_admin', 'date_traitement',
                  'created_at']


class BonCadeauSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    encaisse_par_username = serializers.CharField(
        source='encaisse_par.username', read_only=True, default=None,
    )

    class Meta:
        model  = BonCadeau
        fields = ['id', 'code', 'montant', 'statut', 'statut_display',
                  'email_destinataire', 'message_destinataire',
                  'encaisse_par_username', 'date_encaissement',
                  'date_expiration', 'created_at']


class BonCadeauRecuSerializer(serializers.ModelSerializer):
    """
    Bon reçu : le code est masqué tant que le bon n'est pas encaissé —
    l'email n'étant pas vérifié à l'inscription, on n'expose pas un code
    encaissable sur simple correspondance d'adresse.
    """
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    offert_par     = serializers.CharField(source='achete_par.username', read_only=True, default=None)
    code           = serializers.SerializerMethodField()

    class Meta:
        model  = BonCadeau
        fields = ['id', 'code', 'montant', 'statut', 'statut_display',
                  'message_destinataire', 'offert_par', 'date_expiration', 'created_at']

    def get_code(self, obj):
        if obj.statut == BonCadeau.Statut.UTILISE:
            return obj.code
        return f"{obj.code[:4]}••••••••"


# ── Entrées ─────────────────────────────────────────────────────

class RechargeInitierSerializer(serializers.Serializer):
    montant = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1'))
    methode = serializers.ChoiceField(choices=['moncash', 'natcash'])


class RechargeVerifierSerializer(serializers.Serializer):
    recharge_id = serializers.IntegerField()

    def validate_recharge_id(self, value):
        try:
            return WalletRecharge.objects.select_related('wallet__user').get(pk=value)
        except WalletRecharge.DoesNotExist:
            raise serializers.ValidationError(_("Recharge introuvable."))


class RechargeHorsLigneSerializer(serializers.Serializer):
    montant      = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1'))
    preuve_image = serializers.ImageField()

    def validate_preuve_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                _("Le fichier est trop volumineux. Taille maximale : 5 MB.")
            )
        if value.content_type not in ('image/jpeg', 'image/jpg', 'image/png'):
            raise serializers.ValidationError(
                _("Format non supporté. Utilisez JPG ou PNG.")
            )
        return value


class PayerCommandeSerializer(serializers.Serializer):
    commande_numero = serializers.CharField()


class RetraitSerializer(serializers.Serializer):
    montant          = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1'))
    canal            = serializers.ChoiceField(choices=['moncash', 'natcash'])
    numero_telephone = serializers.CharField(max_length=20)


class BonAcheterSerializer(serializers.Serializer):
    montant            = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1'))
    methode            = serializers.ChoiceField(choices=['wallet', 'moncash', 'natcash'])
    email_destinataire = serializers.EmailField(required=False, allow_blank=True, default='')
    message            = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class BonVerifierSerializer(serializers.Serializer):
    bon_id = serializers.IntegerField()

    def validate_bon_id(self, value):
        try:
            return BonCadeau.objects.get(pk=value)
        except BonCadeau.DoesNotExist:
            raise serializers.ValidationError(_("Bon cadeau introuvable."))


class BonEncaisserSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
