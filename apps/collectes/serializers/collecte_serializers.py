from rest_framework import serializers
from apps.collectes.models import Collecte, ParticipationCollecte
from django.utils.translation import gettext_lazy as _


class ZoneSerializer(serializers.Serializer):
    """Représentation minimale d'une zone de collecte."""
    id          = serializers.IntegerField(source='pk')
    nom         = serializers.CharField()
    departement = serializers.CharField()


class PointCollecteMinimalSerializer(serializers.Serializer):
    """Représentation minimale d'un point de collecte."""
    id      = serializers.IntegerField(source='pk')
    nom     = serializers.CharField()
    adresse = serializers.CharField()
    commune = serializers.CharField()


class CollecteMinimalSerializer(serializers.ModelSerializer):
    """Collecte vue par le producteur."""
    zone           = ZoneSerializer()
    point_collecte = PointCollecteMinimalSerializer(allow_null=True)
    statut_label   = serializers.CharField(source='get_statut_display')
    agent_nom      = serializers.SerializerMethodField()

    class Meta:
        model  = Collecte
        fields = [
            'reference',
            'zone', 'point_collecte',
            'date_planifiee', 'heure_debut', 'heure_fin',
            'statut', 'statut_label',
            'notes',
            'agent_nom',
        ]

    def get_agent_nom(self, obj):
        collecteur = getattr(obj, 'collecteur', None)
        if collecteur:
            return collecteur.get_full_name()
        return None


class ParticipationCollecteSerializer(serializers.ModelSerializer):
    """Participation d'un producteur à une collecte."""
    collecte      = CollecteMinimalSerializer()
    statut_label  = serializers.CharField(source='get_statut_display')

    class Meta:
        model  = ParticipationCollecte
        fields = [
            'id',
            'collecte',
            'statut',
            'statut_label',
            'quantite_prevue',
            'quantite_collectee',
            'notes',
            'created_at',
        ]


class ConfirmerParticipationSerializer(serializers.Serializer):
    """Données pour confirmer une participation."""
    quantite_prevue = serializers.IntegerField(
                        required=False, allow_null=True, min_value=0,
                        help_text="Quantité que le producteur prévoit d'apporter",
                      )
    notes           = serializers.CharField(
                        required=False, allow_blank=True,
                      )
