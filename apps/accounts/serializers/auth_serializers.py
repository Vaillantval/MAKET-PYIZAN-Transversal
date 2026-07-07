from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import CustomUser, Producteur, Acheteur
from django.utils.translation import gettext_lazy as _


class RegisterSerializer(serializers.Serializer):
    """Inscription d'un nouvel utilisateur (Acheteur ou Producteur)."""

    # Champs communs
    username   = serializers.CharField(max_length=150)
    email      = serializers.EmailField()
    password   = serializers.CharField(write_only=True, validators=[validate_password])
    password2  = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    last_name  = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    telephone  = serializers.CharField(max_length=20, required=False, default='', allow_blank=True)
    role       = serializers.ChoiceField(
        choices=['acheteur', 'producteur', 'collecteur'],
        default='acheteur',
    )

    # Champs Producteur (requis si role=producteur)
    departement       = serializers.CharField(max_length=100, required=False, default='', allow_blank=True)
    commune           = serializers.CharField(max_length=100, required=False, default='', allow_blank=True)
    localite          = serializers.CharField(max_length=100, required=False, default='', allow_blank=True)
    superficie_ha     = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    description       = serializers.CharField(required=False, default='', allow_blank=True)
    num_identification = serializers.CharField(max_length=50, required=False, default='', allow_blank=True)

    # Champs Acheteur
    type_acheteur    = serializers.ChoiceField(
        choices=Acheteur.TypeAcheteur.choices,
        required=False,
        default=Acheteur.TypeAcheteur.PARTICULIER,
    )
    nom_organisation = serializers.CharField(max_length=200, required=False, default='', allow_blank=True)

    # Parrainage (optionnel) — code d'un utilisateur existant
    code_parrainage = serializers.CharField(max_length=12, required=False, default='', allow_blank=True)

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Ce nom d'utilisateur est déjà pris."))
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Un compte avec cet email existe déjà."))
        return value

    def validate_code_parrainage(self, value):
        value = (value or '').strip().upper()
        if value and not CustomUser.objects.filter(code_parrainage=value).exists():
            raise serializers.ValidationError(_("Code de parrainage invalide."))
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError(
                {'password2': "Les mots de passe ne correspondent pas."}
            )
        if data['role'] == 'producteur':
            if not data.get('departement'):
                raise serializers.ValidationError(
                    {'departement': _("Le département est requis pour un producteur.")}
                )
            if not data.get('commune'):
                raise serializers.ValidationError(
                    {'commune': _("La commune est requise pour un producteur.")}
                )
        return data

    def create(self, validated_data):
        profil_prod_data = {
            'departement':       validated_data.pop('departement', ''),
            'commune':           validated_data.pop('commune', ''),
            'localite':          validated_data.pop('localite', ''),
            'superficie_ha':     validated_data.pop('superficie_ha', None),
            'description':       validated_data.pop('description', ''),
            'num_identification': validated_data.pop('num_identification', ''),
        }
        profil_ach_data = {
            'type_acheteur':    validated_data.pop('type_acheteur', Acheteur.TypeAcheteur.PARTICULIER),
            'nom_organisation': validated_data.pop('nom_organisation', ''),
        }
        validated_data.pop('password2')
        code_parrain = validated_data.pop('code_parrainage', '')

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

        if code_parrain:
            parrain = CustomUser.objects.filter(code_parrainage=code_parrain).first()
            if parrain:
                user.parraine_par = parrain
                user.save(update_fields=['parraine_par'])

        if role == 'producteur':
            Producteur.objects.create(user=user, statut='en_attente', **profil_prod_data)
        elif role == 'acheteur':
            Acheteur.objects.create(user=user, **profil_ach_data)

        return user


class LoginSerializer(serializers.Serializer):
    """Connexion par email + mot de passe."""
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email    = data.get('email')
        password = data.get('password')

        try:
            user_obj = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(_("Email ou mot de passe incorrect."))

        user = authenticate(username=user_obj.username, password=password)
        if not user:
            raise serializers.ValidationError(_("Email ou mot de passe incorrect."))
        if not user.is_active:
            raise serializers.ValidationError(_("Ce compte est désactivé."))

        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Profil de l'utilisateur connecté (GET/PATCH /api/auth/me/)."""
    profil_producteur_statut = serializers.SerializerMethodField()
    photo_url                = serializers.SerializerMethodField()
    full_name                = serializers.SerializerMethodField()

    class Meta:
        model  = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'telephone', 'photo', 'photo_url', 'role',
            'is_active', 'is_superuser', 'is_staff', 'is_verified',
            'profil_producteur_statut', 'created_at', 'date_joined',
        ]
        read_only_fields = [
            'id', 'username', 'role', 'is_superuser', 'is_staff',
            'is_verified', 'created_at', 'date_joined', 'photo_url', 'full_name',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_profil_producteur_statut(self, obj):
        if obj.role == 'producteur':
            try:
                return obj.profil_producteur.statut
            except Exception:
                return None
        return None

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Changement de mot de passe."""
    current_password = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(
        write_only=True, validators=[validate_password]
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Mot de passe actuel incorrect."))
        return value


class FCMTokenSerializer(serializers.Serializer):
    """Enregistrement du token Firebase Cloud Messaging."""
    fcm_token = serializers.CharField()
