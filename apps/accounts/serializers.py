from django.contrib.auth import authenticate
from django.core.validators import MinLengthValidator
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser, Producteur, Acheteur


# ── Profils imbriqués ────────────────────────────────────────────────────────

class ProducteurProfilSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Producteur
        fields = [
            'code_producteur', 'departement', 'commune', 'localite',
            'adresse_complete', 'superficie_ha', 'description',
            'num_identification', 'statut',
        ]
        read_only_fields = ['code_producteur', 'statut']


class AcheteurProfilSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Acheteur
        fields = [
            'type_acheteur', 'nom_organisation', 'adresse',
            'ville', 'departement', 'total_commandes', 'total_depense',
        ]
        read_only_fields = ['total_commandes', 'total_depense']


# ── Inscription ──────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    # Champs communs
    username   = serializers.CharField(max_length=150)
    email      = serializers.EmailField()
    password   = serializers.CharField(write_only=True, min_length=8)
    password2  = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name  = serializers.CharField(max_length=150, required=False, default='')
    telephone  = serializers.CharField(max_length=20, required=False, default='')
    role       = serializers.ChoiceField(
        choices=[CustomUser.Role.PRODUCTEUR, CustomUser.Role.ACHETEUR],
        default=CustomUser.Role.ACHETEUR,
    )

    # Champs Producteur (optionnels selon le rôle)
    departement      = serializers.ChoiceField(choices=[], required=False)
    commune          = serializers.CharField(max_length=100, required=False, default='')
    localite         = serializers.CharField(max_length=100, required=False, default='')
    superficie_ha    = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    description      = serializers.CharField(required=False, default='')
    num_identification = serializers.CharField(max_length=50, required=False, default='')

    # Champs Acheteur (optionnels)
    type_acheteur    = serializers.ChoiceField(
        choices=Acheteur.TypeAcheteur.choices,
        required=False,
        default=Acheteur.TypeAcheteur.PARTICULIER,
    )
    nom_organisation = serializers.CharField(max_length=200, required=False, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models.producteur import Departement
        self.fields['departement'].choices = Departement.choices

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': "Les mots de passe ne correspondent pas."})
        if data['role'] == CustomUser.Role.PRODUCTEUR and not data.get('departement'):
            raise serializers.ValidationError({'departement': "Le département est requis pour un producteur."})
        if data['role'] == CustomUser.Role.PRODUCTEUR and not data.get('commune'):
            raise serializers.ValidationError({'commune': "La commune est requise pour un producteur."})
        return data

    def create(self, validated_data):
        # Extraire les données de profil
        profil_producteur_data = {
            'departement':       validated_data.pop('departement', ''),
            'commune':           validated_data.pop('commune', ''),
            'localite':          validated_data.pop('localite', ''),
            'superficie_ha':     validated_data.pop('superficie_ha', None),
            'description':       validated_data.pop('description', ''),
            'num_identification': validated_data.pop('num_identification', ''),
        }
        profil_acheteur_data = {
            'type_acheteur':    validated_data.pop('type_acheteur', Acheteur.TypeAcheteur.PARTICULIER),
            'nom_organisation': validated_data.pop('nom_organisation', ''),
            'departement':      profil_producteur_data.get('departement', ''),
        }
        validated_data.pop('password2')

        role = validated_data['role']
        user = CustomUser.objects.create_user(
            username   = validated_data['username'],
            email      = validated_data['email'],
            password   = validated_data['password'],
            first_name = validated_data.get('first_name', ''),
            last_name  = validated_data.get('last_name', ''),
            telephone  = validated_data.get('telephone', ''),
            role       = role,
        )

        if role == CustomUser.Role.PRODUCTEUR:
            Producteur.objects.create(user=user, **profil_producteur_data)
        else:
            Acheteur.objects.create(user=user, **profil_acheteur_data)

        return user


# ── Adresse ──────────────────────────────────────────────────────────────────

class AdresseSerializer(serializers.ModelSerializer):
    departement_display  = serializers.CharField(source='get_departement_display',  read_only=True)
    type_adresse_display = serializers.CharField(source='get_type_adresse_display', read_only=True)

    class Meta:
        from apps.accounts.models import Adresse
        model  = Adresse
        fields = [
            'id', 'libelle', 'nom_complet', 'telephone',
            'rue', 'commune', 'departement', 'departement_display',
            'section_communale', 'details', 'type_adresse', 'type_adresse_display',
            'is_default', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'departement_display', 'type_adresse_display']


# ── Connexion ────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Identifiants incorrects.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        data['user'] = user
        return data


# ── Profil utilisateur connecté ──────────────────────────────────────────────

class MeSerializer(serializers.ModelSerializer):
    profil_producteur = ProducteurProfilSerializer(read_only=True)
    profil_acheteur   = AcheteurProfilSerializer(read_only=True)

    class Meta:
        model  = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_superuser', 'telephone', 'photo', 'is_verified',
            'profil_producteur', 'profil_acheteur',
            'date_joined', 'created_at',
        ]
        read_only_fields = ['id', 'role', 'is_superuser', 'is_verified', 'date_joined', 'created_at']
