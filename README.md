# Makèt Peyizan 🌱

**Platfòm komès agrikòl ayisyen** — La marketplace agricole haïtienne qui connecte producteurs et acheteurs directement.

> *"Sòti nan jaden, rive lakay ou"*

---

## À propos

**Makèt Peyizan** est une plateforme web full-stack conçue pour digitaliser et structurer la filière agricole haïtienne. Elle met en relation les producteurs locaux, les acheteurs (particuliers, grossistes, restaurants, institutions) et les collecteurs logistiques, avec un accent sur la traçabilité des produits et la flexibilité des paiements.

### Utilisateurs cibles

| Rôle | Description |
|------|-------------|
| **Producteur** | Agriculteur gérant son catalogue, ses stocks et ses commandes |
| **Acheteur** | Particulier, grossiste, coopérative ou institution achetant des produits frais |
| **Collecteur** | Agent logistique coordonnant les collectes sur le terrain |
| **Super-Admin** | Gestionnaire de la plateforme avec accès BI complet |

---

## Fonctionnalités

### Pour les producteurs
- Gestion du catalogue produits avec photos, QR codes générés automatiquement
- Tarification unitaire et en gros (prix de détail / prix grossiste)
- Gestion des stocks par lot (date de récolte, date d'expiration, alertes)
- Suivi des commandes reçues et mise à jour des statuts
- Participation aux collectes planifiées
- Tableau de bord avec statistiques de ventes et revenus

### Pour les acheteurs
- Navigation dans le catalogue (filtres par catégorie, localisation, disponibilité)
- Panier persistant multi-vendeurs
- Checkout avec choix du mode de livraison (domicile / retrait / collecte)
- Paiement via MonCash, NatCash, virement bancaire, cash, e-voucher ou wallet
- Suivi des commandes en temps réel
- Gestion des adresses de livraison multiples
- Système de vouchers et bons de réduction

### Portefeuille (wallet) — acheteurs & producteurs
- Solde prépayé HTG avec ledger immuable (voir `docs/WALLET.md`)
- Recharges MonCash/NatCash (Plopplop) ou dépôt hors ligne avec preuve
- Paiement de commande total ou partiel (complément Plopplop, réserve libérée après 24 h)
- Ventes créditées automatiquement au producteur à la livraison (commission configurable)
- Retraits MonCash/NatCash validés par l'admin (preuve de transfert)
- Cashback fidélité, parrainage (bonus parrain + filleul) et bons cadeaux — le tout activable dans la configuration du site

### Pour les administrateurs
- Interface d'administration Jazzmin (Django Admin stylisé)
- Gestion complète des utilisateurs, produits, commandes, paiements
- Tableau de bord analytique (KPIs, ventes, top produits/producteurs)
- Export des données en PDF et Excel
- Configuration du site (logo, textes, réseaux sociaux, mode maintenance)
- Gestion des FAQ et messages de contact

### Système
- Notifications push Firebase (FCM) pour Android et iOS
- Emails transactionnels via Resend
- API REST documentée (Swagger UI / ReDoc)
- Support multilingue : Français, Kreyòl ayisyen, English, Español
- Fuseau horaire : America/Port-au-Prince

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Framework | Django 5.2, Django REST Framework 3.15 |
| Langage | Python 3.13 |
| Base de données | PostgreSQL (production), SQLite (développement) |
| Authentification | JWT via SimpleJWT |
| Admin UI | Jazzmin |
| Fichiers statiques | WhiteNoise (compression + serving) |
| Notifications push | Firebase Admin SDK (FCM) |
| Emails | Resend API |
| Paiements | Plopplop Gateway (MonCash, NatCash) |
| PDF / Excel | ReportLab, openpyxl |
| QR Codes | qrcode[pil] |
| Serveur WSGI | Gunicorn (3 workers, 4 threads gthread) |
| Déploiement | Docker + Railway |
| Documentation API | drf-spectacular (OpenAPI 3) |

---

## Architecture

```
maket_peyizan/
├── config/                  # Configuration Django (settings base/dev/prod, urls, wsgi)
├── apps/
│   ├── accounts/            # Utilisateurs, profils Producteur & Acheteur, adresses
│   ├── catalog/             # Produits, catégories, images, QR codes
│   ├── orders/              # Panier, commandes, lignes de commande
│   ├── payments/            # Paiements, vouchers, intégration Plopplop/MonCash
│   ├── stock/               # Lots, mouvements de stock, alertes
│   ├── collectes/           # Zones, points, événements de collecte, participations
│   ├── analytics/           # Tableau de bord BI super-admin
│   ├── core/                # Configuration site, FAQ, messages de contact
│   ├── emails/              # Service email (Resend) + notifications FCM
│   ├── home/                # Pages publiques et tableaux de bord utilisateurs
│   ├── geo/                 # Données géographiques (départements, communes)
│   ├── api_admin/           # Endpoints API réservés aux administrateurs
│   └── wallet/              # Portefeuille : soldes, recharges, retraits, bons cadeaux
├── templates/               # Templates HTML (Jinja2 / DTL)
├── static/                  # CSS, JS, images statiques
├── media/                   # Fichiers uploadés (images produits, QR codes, preuves)
├── locale/                  # Fichiers de traduction (.po / .mo)
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── Dockerfile
├── railway.toml             # Configuration déploiement Railway
└── init_site.py             # Création automatique du super-admin au démarrage
```

---

## Déploiement (Railway)

L'application est déployée sur [Railway](https://railway.app) avec :
- **URL de production :** https://maketpeyizan.ht
- **Base de données :** PostgreSQL (service Railway dédié)
- **Volume persistant :** monté sur `/app/media` pour les fichiers uploadés
- **Build :** Dockerfile (Python 3.13 slim)

### Séquence de démarrage automatique

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py compilemessages
python init_site.py
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 4 --worker-class gthread --timeout 120
```

### Variables d'environnement Railway

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète Django |
| `DEBUG` | `False` en production |
| `ALLOWED_HOSTS` | Domaines autorisés |
| `DATABASE_URL` | URL connexion PostgreSQL (auto Railway) |
| `CSRF_TRUSTED_ORIGIN` | Origine CSRF de confiance (ex: `https://maketpeyizan.ht`) |
| `CORS_ALLOW_ALL` | `True` / `False` |
| `SITE_URL` | URL publique du site |
| `DEFAULT_FROM_EMAIL` | Email expéditeur |
| `RESEND_API_KEY` | Clé API Resend pour les emails |
| `ADMINS_NOTIFY` | Email(s) de notification admin |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | JSON des credentials Firebase (FCM) |
| `MONCASH_ENVIRONMENT` | `sandbox` ou `production` |
| `PLOPPLOP_CLIENT_ID` | Client ID gateway Plopplop |
| `SUPERADMIN_USERNAME` | Username du super-admin initial |
| `SUPERADMIN_EMAIL` | Email du super-admin initial |
| `SUPERADMIN_PASSWORD` | Mot de passe du super-admin initial |

> Les variables sont gérées directement dans le dashboard Railway — ne jamais les committer dans le code.

---

## Installation locale

### Prérequis
- Python 3.13+
- pip
- (Optionnel) PostgreSQL si vous ne souhaitez pas utiliser SQLite

### Étapes

```bash
# Cloner le dépôt
git clone https://github.com/Vaillantval/MAKET-PYIZAN-Transversal.git
cd MAKET-PYIZAN-Transversal

# Créer et activer un environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows.

# Installer les dépendances
pip install -r requirements/development.txt

# Configurer les variables d'environnement
cp .env.example .env            # adapter selon votre config locale

# Appliquer les migrations
python manage.py migrate

# Compiler les messages i18n
python manage.py compilemessages

# Lancer le serveur de développement
python manage.py runserver
```

L'application sera accessible sur [http://localhost:8000](http://localhost:8000).

---

## Endpoints API principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/auth/register/` | Inscription (Producteur ou Acheteur) |
| `POST` | `/api/auth/login/` | Connexion (retourne JWT) |
| `GET` | `/api/auth/me/` | Profil utilisateur connecté |
| `GET` | `/api/products/` | Liste des produits (filtres, pagination) |
| `GET` | `/api/products/categories/` | Catégories du catalogue |
| `GET` | `/api/orders/panier/` | Contenu du panier |
| `POST` | `/api/orders/panier/ajouter/` | Ajouter au panier |
| `POST` | `/api/orders/commander/` | Passer une commande |
| `POST` | `/api/payments/initier/` | Initier un paiement (retourne redirect_url) |
| `POST` | `/api/payments/preuve/` | Soumettre une preuve de paiement |
| `GET` | `/api/wallet/` | Solde et dernières transactions du portefeuille |
| `POST` | `/api/wallet/recharge/initier/` | Recharger le wallet (MonCash/NatCash) |
| `POST` | `/api/wallet/payer/` | Payer une commande avec le solde wallet |
| `POST` | `/api/wallet/retrait/` | Demander un retrait (producteur) |
| `GET` | `/api/schema/swagger-ui/` | Documentation Swagger |
| `GET` | `/health/` | Health check |

---

## Paiements supportés

- **MonCash** (Digicel) — paiement mobile haïtien
- **NatCash** — paiement mobile haïtien
- **Virement bancaire** — avec soumission de preuve
- **Cash** — paiement à la livraison
- **E-Voucher** — crédit interne / bons de réduction
- **Plopplop** — passerelle unifiée (MonCash, NatCash, etc.)

---

## Licence

Projet propriétaire — Tous droits réservés © Makèt Peyizan 2026.
