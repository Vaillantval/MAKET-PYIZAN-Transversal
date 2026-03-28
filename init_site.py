"""
init_site.py — Script d'initialisation au démarrage Railway.

Exécuté une fois après `migrate`, avant gunicorn.
Crée le superadmin si il n'existe pas déjà.

Variables d'environnement requises :
  SUPERADMIN_USERNAME  (ex: superadmin)
  SUPERADMIN_EMAIL     (ex: admin@maketpeyizan.ht)
  SUPERADMIN_PASSWORD  (mot de passe fort)

Usage :
  python init_site.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def create_superadmin():
    username = os.environ.get('SUPERADMIN_USERNAME', '').strip()
    email    = os.environ.get('SUPERADMIN_EMAIL', '').strip()
    password = os.environ.get('SUPERADMIN_PASSWORD', '').strip()

    if not username or not email or not password:
        print('[init_site] SUPERADMIN_USERNAME / SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD '
              'non définis — superadmin non créé.')
        return

    if User.objects.filter(email=email).exists():
        print(f'[init_site] Superadmin "{email}" existe déjà — aucune action.')
        return

    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
    )
    user.role        = 'superadmin'
    user.is_staff    = True
    user.is_superuser = True
    user.save(update_fields=['role', 'is_staff', 'is_superuser'])

    print(f'[init_site] Superadmin "{email}" créé avec succès.')


if __name__ == '__main__':
    create_superadmin()
