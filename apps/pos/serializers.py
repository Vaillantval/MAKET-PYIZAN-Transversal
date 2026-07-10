from decimal import Decimal

from rest_framework import serializers

from apps.pos.models import POSItem, POSSale, POSSession


# ── Sorties ─────────────────────────────────────────────────────

class POSItemSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    lot_numero  = serializers.CharField(source='lot.numero_lot', read_only=True, default=None)

    class Meta:
        model  = POSItem
        fields = ['id', 'produit_id', 'produit_nom', 'lot_id', 'lot_numero',
                  'quantite', 'prix_unitaire', 'sous_total']


class POSSaleSerializer(serializers.ModelSerializer):
    methode_display = serializers.CharField(source='get_methode_paiement_display', read_only=True)
    statut_display  = serializers.CharField(source='get_statut_display', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True, default=None)
    items           = POSItemSerializer(many=True, read_only=True)

    class Meta:
        model  = POSSale
        fields = ['id', 'numero_vente', 'idempotency_key', 'session_id',
                  'client_username', 'montant_total', 'methode_paiement',
                  'methode_display', 'montant_wallet', 'statut', 'statut_display',
                  'stock_conflict', 'vendue_le', 'synced_le', 'items']


class POSSessionSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    device_nom     = serializers.CharField(source='device.nom', read_only=True)
    device_uid     = serializers.CharField(source='device.device_uid', read_only=True)

    class Meta:
        model  = POSSession
        fields = ['id', 'device_id', 'device_nom', 'device_uid', 'fonds_ouverture',
                  'fonds_fermeture', 'ecart_caisse', 'ouverte_le', 'fermee_le',
                  'statut', 'statut_display']


# ── Entrées ─────────────────────────────────────────────────────

class SessionOuvrirSerializer(serializers.Serializer):
    device_uid      = serializers.CharField(max_length=64)
    fonds_ouverture = serializers.DecimalField(max_digits=12, decimal_places=2,
                                               min_value=Decimal('0'))


class SessionFermerSerializer(serializers.Serializer):
    fonds_fermeture = serializers.DecimalField(max_digits=12, decimal_places=2,
                                               min_value=Decimal('0'))


class POSItemInputSerializer(serializers.Serializer):
    produit_id    = serializers.IntegerField(min_value=1)
    lot_id        = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    quantite      = serializers.IntegerField(min_value=1)
    prix_unitaire = serializers.DecimalField(max_digits=12, decimal_places=2,
                                             min_value=Decimal('0.01'))


class VenteInputSerializer(serializers.Serializer):
    idempotency_key  = serializers.UUIDField()
    items            = POSItemInputSerializer(many=True, allow_empty=False)
    methode_paiement = serializers.ChoiceField(choices=POSSale.MethodePaiement.choices)
    montant_wallet   = serializers.DecimalField(max_digits=12, decimal_places=2,
                                                min_value=Decimal('0'),
                                                required=False, default=Decimal('0'))
    client_telephone = serializers.CharField(max_length=20, required=False,
                                             allow_blank=True, default='')
    client_email     = serializers.EmailField(required=False, allow_blank=True, default='')
    vendue_le        = serializers.DateTimeField()


class SyncSerializer(serializers.Serializer):
    ventes = VenteInputSerializer(many=True, allow_empty=False)
