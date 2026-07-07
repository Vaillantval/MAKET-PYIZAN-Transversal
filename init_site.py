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


def register_wallet_periodic_tasks():
    """
    Enregistre les tâches Celery Beat du wallet (scheduler en base de données).
    Idempotent : get_or_create sur le nom de la tâche.
    """
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
    except ImportError:
        print('[init_site] django_celery_beat absent — tâches wallet non planifiées.')
        return

    # Tous les jours à 03h00 (heure de Port-au-Prince, cf. TIME_ZONE)
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0', hour='3', day_of_week='*', day_of_month='*', month_of_year='*',
        timezone='America/Port-au-Prince',
    )
    _, created = PeriodicTask.objects.get_or_create(
        name='Wallet — expirer les bons cadeaux',
        defaults={
            'task': 'wallet.expirer_bons_cadeaux',
            'crontab': schedule,
        },
    )
    print(f'[init_site] Tâche "wallet.expirer_bons_cadeaux" '
          f'{"créée" if created else "déjà planifiée"}.')

    # Toutes les heures : libérer les réserves de paiement partiel expirées
    horaire, _ = CrontabSchedule.objects.get_or_create(
        minute='15', hour='*', day_of_week='*', day_of_month='*', month_of_year='*',
        timezone='America/Port-au-Prince',
    )
    _, created = PeriodicTask.objects.get_or_create(
        name='Wallet — libérer les réserves expirées (24h)',
        defaults={
            'task': 'wallet.liberer_reserves_expirees',
            'crontab': horaire,
        },
    )
    print(f'[init_site] Tâche "wallet.liberer_reserves_expirees" '
          f'{"créée" if created else "déjà planifiée"}.')


if __name__ == '__main__':
    create_superadmin()
    register_wallet_periodic_tasks()
