from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission

from apps.pos.models import POSDevice


class IsPOSOperator(BasePermission):
    """
    Autorise les opérateurs de caisse (role pos_operator) dont le header
    X-POS-Device correspond à un terminal actif qui leur appartient.
    Un superadmin passe sans header (supervision / rapports).
    """

    message = _('Accès réservé aux opérateurs de caisse.')

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if (
            user.is_superuser or user.is_staff
            or getattr(user, 'role', '') == 'superadmin'
        ):
            return True

        if getattr(user, 'role', '') != 'pos_operator':
            return False

        device_uid = (request.headers.get('X-POS-Device') or '').strip()
        if not device_uid:
            self.message = _('Header X-POS-Device manquant.')
            return False

        device = POSDevice.objects.filter(
            device_uid=device_uid, operateur=user, is_active=True,
        ).first()
        if device is None:
            self.message = _('Terminal inconnu, révoqué ou appartenant à un autre opérateur.')
            return False

        # Mis à disposition des vues/services (évite une seconde requête).
        request.pos_device = device
        return True
