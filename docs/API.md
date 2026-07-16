# Makèt Peyizan — Référence API

> Documentation complète de tous les endpoints REST.
> Schema OpenAPI interactif disponible sur `/api/schema/swagger-ui/` (Swagger) et `/api/schema/redoc/`.

---

## Authentification

Toutes les requêtes protégées nécessitent un header JWT :

```
Authorization: Bearer <access_token>
```

Les tokens sont retournés lors du login/register. L'access token expire après **1 jour**, le refresh token après **30 jours** (rotation automatique, blacklist activée).

---

## Format des réponses

Toutes les réponses suivent le format uniforme :

```json
{"success": true,  "data": ...}          // succès
{"success": false, "error": "...", "code": "..."}   // erreur (code optionnel)
```

Les endpoints **paginés** (`?page=`, `?page_size=` ≤ 100, 20 par défaut) —
`/api/wallet/transactions/`, `/api/wallet/retraits/`, `/api/wallet/bons/`,
`/api/wallet/bons/recus/`, `/api/products/` — enveloppent la pagination
dans `data` :

```json
{
  "success": true,
  "data": {
    "results":  [ ... ],
    "count":    57,
    "next":     "https://…?page=3",
    "previous": "https://…?page=1"
  }
}
```

Les montants sont toujours des **chaînes** (`"500.00"`), jamais des nombres.

---

## 1. Auth & Compte (`/api/auth/`)

### Inscription
```
POST /api/auth/register/
```
**Body JSON**
```json
{
  "username": "jean_dupont",
  "email": "jean@exemple.com",
  "password": "motdepasse123",
  "role": "acheteur",          // "acheteur" | "producteur" | "collecteur"
  "first_name": "Jean",
  "last_name": "Dupont",
  "telephone": "+50912345678"
}
```
**Réponse 201**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": 1, "username": "jean_dupont", "email": "jean@exemple.com",
    "role": "acheteur", "is_superuser": false
  }
}
```

---

### Connexion
```
POST /api/auth/login/
```
**Body JSON**
```json
{ "email": "jean@exemple.com", "password": "motdepasse123" }
```
**Réponse 200** — même format que `/register/`

---

### Déconnexion
```
POST /api/auth/logout/
Authorization: Bearer <token>
```
**Body JSON**
```json
{ "refresh": "<refresh_token>", "fcm_token": "<optionnel>" }
```

---

### Rafraîchir le token
```
POST /api/auth/token/refresh/
```
**Body JSON**
```json
{ "refresh": "<refresh_token>" }
```
**Réponse 200**
```json
{ "access": "<nouveau_access_token>", "refresh": "<nouveau_refresh_token>" }
```

---

### Profil utilisateur connecté
```
GET  /api/auth/me/         → retourne le profil
PATCH /api/auth/me/        → met à jour le profil
Authorization: Bearer <token>
```
**Body PATCH** (multipart/form-data pour la photo)
```
first_name, last_name, telephone, photo (fichier image)
```

---

### Changer le mot de passe
```
POST /api/auth/change-password/
Authorization: Bearer <token>
```
**Body JSON**
```json
{ "current_password": "ancienMDP", "new_password": "nouveauMDP" }
```

---

### Token FCM (Push notifications)
```
POST /api/auth/fcm-token/
Authorization: Bearer <token>
```
**Body JSON**
```json
{ "fcm_token": "<firebase_device_token>" }
```
**Réponse 200**
```json
{ "message": "Token enregistré.", "role": "acheteur", "topic_subscribed": "role_acheteur" }
```

---

## 2. Adresses (`/api/auth/adresses/`)

```
GET    /api/auth/adresses/              → liste des adresses de l'utilisateur
POST   /api/auth/adresses/              → créer une adresse
GET    /api/auth/adresses/<id>/         → détail
PUT    /api/auth/adresses/<id>/         → mise à jour complète
PATCH  /api/auth/adresses/<id>/         → mise à jour partielle
DELETE /api/auth/adresses/<id>/         → supprimer
PATCH  /api/auth/adresses/<id>/default/ → définir comme adresse par défaut
```

**Body POST/PUT**
```json
{
  "rue": "123 Rue des Mangues",
  "commune": "Pétion-Ville",
  "departement": "ouest",
  "section_communale": "1ère section",
  "telephone": "+50912345678",
  "instructions": "Près du marché"
}
```

---

## 3. Commandes acheteur (`/api/auth/commandes/`)

```
GET /api/auth/commandes/                → liste des commandes de l'acheteur
GET /api/auth/commandes/<numero>/       → détail d'une commande
Authorization: Bearer <token>
```

**Réponse liste**
```json
[
  {
    "numero_commande": "CMD-2026-001",
    "producteur": "Jean-Baptiste Pierre",
    "total": "1250.00",
    "statut": "confirmee",
    "statut_label": "Confirmée",
    "statut_paiement": "paye",
    "created_at": "2026-03-27T10:00:00Z"
  }
]
```

---

## 4. Dashboard Producteur (`/api/auth/producteur/`)

```
GET   /api/auth/producteur/stats/                        → statistiques dashboard
GET   /api/auth/producteur/profil/                       → profil boutique
PATCH /api/auth/producteur/profil/                       → modifier profil boutique
GET   /api/auth/producteur/commandes/?statut=            → commandes reçues
GET   /api/auth/producteur/commandes/<numero>/           → détail commande
PATCH /api/auth/producteur/commandes/<numero>/statut/    → changer statut commande
```

**PATCH statut commande — Body**
```json
{
  "action": "confirmer",    // "confirmer" | "preparer" | "prete" | "annuler"
  "motif": "Rupture de stock"   // requis pour "annuler"
}
```

---

## 5. Catalogue public (`/api/products/`)

### Listing avec filtres
```
GET /api/products/
```
**Query params**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Recherche dans nom, variété, description |
| `categorie` | slug | Filtrer par catégorie (ex: `legumes`) |
| `departement` | string | Département du producteur (ex: `ouest`) |
| `producteur_id` | int | ID du producteur |
| `prix_min` | decimal | Prix minimum |
| `prix_max` | decimal | Prix maximum |
| `featured` | `1` | Produits mis en avant seulement |
| `page` | int | Numéro de page (défaut: 1) |
| `page_size` | int | Résultats par page (défaut: 20, max: 100) |

**Réponse 200** (paginée)
```json
{
  "count": 84,
  "next": "/api/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "nom": "Banane Ti-Malice",
      "slug": "banane-ti-malice",
      "variete": "Gros Michel",
      "prix_unitaire": "150.00",
      "prix_gros": "120.00",
      "unite_vente": "regime",
      "unite_vente_label": "Régime",
      "quantite_min_commande": 1,
      "stock_reel": 42,
      "is_featured": true,
      "image_principale": "/media/produits/banane.jpg",
      "categorie": { "nom": "Fruits", "slug": "fruits" },
      "producteur": {
        "id": 3,
        "nom": "Marie Joseph",
        "commune": "Léogâne",
        "departement": "ouest"
      }
    }
  ]
}
```

---

### Détail produit
```
GET /api/products/public/<slug>/
```
Retourne tous les attributs + images galerie + produits similaires.

---

### Catégories
```
GET /api/products/categories/
```
```json
[{ "id": 1, "nom": "Légumes", "slug": "legumes", "icone": "🥦" }]
```

---

### Catalogue producteur connecté
```
GET    /api/products/mes-produits/           → mes produits
POST   /api/products/mes-produits/           → créer un produit (multipart/form-data)
GET    /api/products/mes-produits/<slug>/    → détail
PATCH  /api/products/mes-produits/<slug>/    → modifier (multipart)
DELETE /api/products/mes-produits/<slug>/    → supprimer
```

---

## 6. Panier (`/api/orders/`)

> Le panier est lié au **compte JWT** pour les utilisateurs connectés (Flutter/mobile).
> Pour les visiteurs anonymes (web), il est stocké en session.

```
GET    /api/orders/panier/                  → résumé du panier
POST   /api/orders/panier/ajouter/          → ajouter un article
PATCH  /api/orders/panier/modifier/<slug>/  → modifier la quantité
DELETE /api/orders/panier/retirer/<slug>/   → retirer un article
DELETE /api/orders/panier/vider/            → vider le panier
```

**POST ajouter — Body**
```json
{ "slug": "banane-ti-malice", "quantite": 2 }
```

**Réponse résumé**
```json
{
  "items": [
    {
      "slug": "banane-ti-malice",
      "nom": "Banane Ti-Malice",
      "quantite": 2,
      "prix_unitaire": "150.00",
      "sous_total": 300.0,
      "unite_vente": "regime",
      "producteur_id": 3,
      "producteur_nom": "Marie Joseph",
      "image": "/media/produits/banane.jpg"
    }
  ],
  "total": 300.0,
  "nb_articles": 2,
  "nb_items": 1,
  "producteurs": [{ "id": 3, "nom": "Marie Joseph" }]
}
```

---

## 7. Passer commande (`/api/orders/commander/`)

```
POST /api/orders/commander/
Authorization: Bearer <token>
```

> Requiert un utilisateur de rôle `acheteur`. Crée une commande par producteur présent dans le panier.

**Body JSON**
```json
{
  "methode_paiement": "cash",           // "cash" | "moncash" | "hors_ligne"
  "mode_livraison": "domicile",          // "domicile" | "collecte"
  "adresse_livraison_id": 2,             // ou adresse_livraison_text + ville_livraison + departement_livraison
  "notes": "Livrer le matin SVP"
}
```

**Réponse 201**
```json
{
  "message": "2 commande(s) créée(s) avec succès !",
  "commandes": [
    {
      "numero_commande": "CMD-2026-001",
      "producteur": "Marie Joseph",
      "total": "300.00",
      "statut": "En attente"
    }
  ]
}
```

> Pour **MonCash**, la réponse contient `redirect_url` vers la page de paiement MonCash.

---

## 8. Collectes (`/api/collectes/`)

```
GET   /api/collectes/mes-participations/               → participations du producteur
PATCH /api/collectes/participations/<id>/confirmer/    → confirmer participation
```

---

## 9. Géographie (`/api/geo/`)

> Endpoints publics, mis en cache 24h. Données géographiques d'Haïti.

```
GET /api/geo/departements/
GET /api/geo/communes/?dept=<slug>
GET /api/geo/arrondissements/?dept=<slug>
GET /api/geo/sections/?dept=<slug>&commune=<nom>
GET /api/geo/arbre/                         → arbre complet
GET /api/geo/recherche/?q=<terme>           → recherche (min 2 caractères)
```

---

## 10. API Superadmin (`/api/admin/`)

> Requiert `is_staff=True` ou `is_superuser=True` ou `role='superadmin'`.

### Statistiques globales
```
GET /api/admin/stats/
GET /api/admin/options/?type=categories|producteurs|produits|zones|points|collecteurs
```

### Utilisateurs
```
GET   /api/admin/users/?search=&role=&is_active=
POST  /api/admin/users/create/
GET   /api/admin/users/<id>/detail/
PATCH /api/admin/users/<id>/detail/
PATCH /api/admin/users/<id>/toggle/              → activer/désactiver
```

### Producteurs
```
GET   /api/admin/producteurs/?statut=&search=
POST  /api/admin/producteurs/create/
GET   /api/admin/producteurs/<id>/detail/
PATCH /api/admin/producteurs/<id>/statut/        → actif | suspendu | en_attente
```

### Commandes
```
GET   /api/admin/commandes/?statut=&search=
GET   /api/admin/commandes/<numero>/
PATCH /api/admin/commandes/<numero>/statut/
```

### Paiements
```
GET   /api/admin/paiements/?statut=
PATCH /api/admin/paiements/<id>/statut/
```

### Catalogue
```
GET   /api/admin/catalogue/?search=&statut=&producteur_id=
POST  /api/admin/catalogue/create/              (multipart)
GET   /api/admin/catalogue/<id>/detail/
PATCH /api/admin/catalogue/<id>/detail/         (multipart)
PATCH /api/admin/catalogue/<id>/statut/
PATCH /api/admin/catalogue/<id>/toggle/         → is_active | is_featured
```

### Stocks
```
GET   /api/admin/stocks/lots/?search=&statut=&producteur_id=
POST  /api/admin/stocks/lots/create/
GET   /api/admin/stocks/lots/<id>/
PATCH /api/admin/stocks/lots/<id>/
GET   /api/admin/stocks/alertes/?niveau=
GET   /api/admin/stocks/mouvements/
```

### Collectes terrain
```
GET   /api/admin/collectes/?statut=
POST  /api/admin/collectes/create/
GET   /api/admin/collectes/<id>/
PATCH /api/admin/collectes/<id>/statut/
PATCH /api/admin/collectes/<id>/edit/
POST  /api/admin/collectes/<id>/participations/
PATCH /api/admin/collectes/participations/<id>/statut/
DELETE /api/admin/collectes/participations/<id>/
```

### Configuration site
```
GET /api/admin/config/site/
GET /api/admin/config/faq/categories/
GET /api/admin/config/faq/categories/<id>/
GET /api/admin/config/faq/items/
GET /api/admin/config/faq/items/<id>/
GET /api/admin/config/contact/
GET /api/admin/config/contact/<id>/
```

### Autres
```
GET /api/admin/acheteurs/
GET /api/admin/acheteurs/<id>/
GET /api/admin/categories/
GET /api/admin/categories/<id>/
GET /api/admin/vouchers/
GET /api/admin/vouchers/<id>/
GET /api/admin/vouchers/programmes/
GET /api/admin/vouchers/programmes/<id>/
GET /api/admin/zones/
GET /api/admin/zones/<id>/
GET /api/admin/points/
GET /api/admin/points/<id>/
GET /api/admin/adresses/
```

---

## 11. Point de vente physique (POS) (`/api/pos/`)

Réservé au rôle `pos_operator` : header **`X-POS-Device: <device_uid>`**
obligatoire (terminal actif appartenant à l'opérateur, créé par le
superadmin dans l'admin). Le superadmin passe sans header.
Doc complète : `docs/POS.md`.

### Sessions de caisse
```
POST /api/pos/session/ouvrir/   {device_uid, fonds_ouverture}
POST /api/pos/session/fermer/   {fonds_fermeture}
     → {"session": {...POSSession...},
        "recap": {
          "nb_ventes": 12,
          "total_ventes": "5400.00",
          "total_cash": "3200.00",          ← part espèces réellement en tiroir
          "par_methode": {"cash": {"nb": 8, "montant": "3200.00"},
                          "wallet": {"nb": 4, "montant": "2200.00"}},
          "ecart_caisse": "-20.00"
        }}
```

### Paiement wallet — code de consentement (usage unique, 5 min)

Le débit wallet au comptoir exige un **code de paiement** généré par le
client — jamais un simple téléphone/email :

```
POST /api/wallet/code-paiement/          (client authentifié)
     → {"code": "483920", "expire_dans": 300, "solde": "150.00"}
     (en générer un nouveau invalide les précédents non utilisés)

POST /api/pos/client/verifier-code/      (opérateur) {code}
     → {"client": {"nom", "telephone"}, "solde"}   — SANS consommer le code
```

Le code est consommé atomiquement à la vente, dans la même transaction
que le débit (rollback = code rendu au client, double usage impossible).

### Ventes
```
POST /api/pos/vente/       (online)
     {idempotency_key, items: [{produit_id, lot_id?, quantite, prix_unitaire}],
      methode_paiement: moncash|natcash|cash|voucher|wallet,
      montant_wallet?, code_paiement?, client_telephone?, client_email?,
      vendue_le}
     — wallet ou montant_wallet > 0 → code_paiement OBLIGATOIRE
       (client_telephone/email refusés) ; solde insuffisant →
       400 {"code": "SOLDE_INSUFFISANT"}
     — client_telephone/email : rattachement des ventes SANS wallet
     — idempotency_key déjà connue → vente existante, pas de doublon

POST /api/pos/sync/        {ventes: [...]} — batch offline
     → {resultats: [{idempotency_key, status: created|duplicate|rejected,
        vente_id?, session_id?, stock_conflict?, erreur?}]}
     — toute vente wallet est REJETÉE (paiement wallet online uniquement)
     — stock insuffisant : vente créée avec stock_conflict=true (lot à 0 min.)
     — vente synchronisée après la clôture : rattachée à la session couvrant
       son vendue_le, écart de caisse recalculé
```

### Catalogue et rapports
```
GET /api/pos/catalogue/    → produits actifs : id, nom, categorie {id, nom},
                             prix_unitaire, prix_gros|null, unite_vente,
                             stock_disponible, photo_url|null (URL absolue),
                             lots [{id, numero_lot, code_barres, quantite_actuelle}]
                             (ETag contenu : If-None-Match → 304 si inchangé)
GET /api/pos/rapports/     ?session_id= | ?date=YYYY-MM-DD | ?device_id=
                             (opérateur : ses ventes ; superadmin : tout)
     → {
       "nb_ventes": 12,                  ← ventes confirmées
       "chiffre_affaires": "5400.00",
       "nb_annulees": 1,
       "nb_stock_conflict": 2,
       "par_methode": {"cash": {"nb": 8, "montant": "3400.00"}, ...},
       "top_produits": [{"produit_id", "produit", "quantite_vendue",
                         "montant"}, ...],              ← top 10
       "ventes": [                       ← réconciliation : 200 plus récentes
         {"id": 42, "idempotency_key": "9f1c...", "numero_vente": "POS-2026-00042",
          "statut": "confirmee|annulee", "montant_total": "450.00",
          "montant_wallet": "0.00", "methode_paiement": "cash",
          "stock_conflict": false, "vendue_le": "2026-07-13T09:30:00-04:00"},
         ...
       ]
     }
```

---

## 12. Endpoints système

```
GET /health/                    → {"status": "ok"} — healthcheck Railway
GET /api/schema/                → OpenAPI JSON schema
GET /api/schema/swagger-ui/     → Swagger UI interactif
GET /api/schema/redoc/          → ReDoc
GET /a-propos/                  → Page À propos
GET /faq/                       → FAQ publique
POST /contact/                  → Formulaire de contact
```

---

## Codes d'erreur communs

| Code | Signification |
|------|---------------|
| 400 | Données invalides ou manquantes |
| 401 | Token absent ou expiré |
| 403 | Permission insuffisante (rôle incorrect) |
| 404 | Ressource introuvable |
| 503 | Service tiers indisponible (MonCash, FCM) |

---

## Statuts métier

### Commande
| Valeur | Label |
|--------|-------|
| `en_attente` | En attente |
| `confirmee` | Confirmée |
| `en_preparation` | En préparation |
| `prete` | Prête |
| `en_collecte` | En collecte |
| `livree` | Livrée |
| `annulee` | Annulée |
| `litige` | En litige |

### Paiement
| Valeur | Label |
|--------|-------|
| `non_paye` | Non payé |
| `en_attente` | En attente |
| `preuve_soumise` | Preuve soumise |
| `verifie` | Vérifié |
| `paye` | Payé |
| `rembourse` | Remboursé |

### Producteur
| Valeur | Label |
|--------|-------|
| `en_attente` | En attente de validation |
| `actif` | Actif |
| `suspendu` | Suspendu |
| `inactif` | Inactif |
