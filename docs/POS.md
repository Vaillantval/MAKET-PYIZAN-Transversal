# Makèt Peyizan — Point de vente physique (POS)

> Caisse au comptoir pour les marchés physiques : sessions de caisse,
> ventes online/offline avec synchronisation idempotente, paiement wallet
> (online uniquement), décrément du stock par lots (FIFO) et rapports.

---

## Principes

- **Idempotence par vente** : chaque vente porte une `idempotency_key`
  (UUID généré côté terminal). Une resoumission — retry réseau, re-sync
  offline — renvoie la vente existante, jamais un doublon.
- **Le wallet est SYNCHRONE et ONLINE uniquement** : `/api/pos/sync/`
  rejette toute vente `methode_paiement=wallet` ou `montant_wallet > 0`
  (anti double-spending : impossible de vérifier le solde au moment d'une
  vente offline). Le débit wallet en ligne est dans la même transaction
  atomique que la création de la vente (type ledger `paiement_pos`,
  lié à la vente via `WalletTransaction.pos_sale`).
- **Consentement client obligatoire** : aucun débit wallet sans le **code
  de paiement** à usage unique (6 chiffres, 5 min) que le client génère
  depuis son portefeuille (`POST /api/wallet/code-paiement/`) et
  montre/dicte à l'opérateur. Un téléphone/email ne suffit JAMAIS à
  débiter un wallet.
- **La vente physique a eu lieu** : un stock serveur insuffisant ne rejette
  jamais une vente — elle est créée avec `stock_conflict=True` (badge dans
  l'admin, action « Lever le conflit » après arbitrage) et le lot est ramené
  à 0, jamais en négatif.
- **Vues minces** : toute la logique est dans `apps.pos.services.POSService`.

## Mise en route (obligatoire avant tout test)

Rien ne s'auto-enregistre — le superadmin crée dans l'admin :

1. **Le compte opérateur** : Utilisateurs → rôle « Opérateur de caisse »
   (`pos_operator`).
2. **Le terminal** : Terminaux POS → `device_uid` (identifiant matériel
   fourni par l'app), nom, opérateur, département/commune.
   `is_active` décoché = terminal révoqué (perte/vol).

L'opérateur s'authentifie ensuite en JWT (`/api/auth/login/`) et **toutes**
ses requêtes `/api/pos/` portent le header `X-POS-Device: <device_uid>` —
la permission vérifie que le terminal est actif et lui appartient.
Un superadmin passe sans header (supervision, rapports).

## Sessions de caisse

- `POST /api/pos/session/ouvrir/` `{device_uid, fonds_ouverture}` —
  une seule session OUVERTE par opérateur.
- `POST /api/pos/session/fermer/` `{fonds_fermeture}` — calcule
  `ecart_caisse = fonds_fermeture − (fonds_ouverture + ventes cash)` et
  retourne le récap (nb ventes, total, répartition par méthode). Dans la
  répartition, la part wallet des paiements hybrides est comptée dans le
  bucket `wallet` — le cash attendu en tiroir est donc exact.

### Sync tardive après clôture

Scénario couvert : vente offline à 16 h, caisse fermée à 17 h, réseau
retrouvé à 19 h. La vente synchronisée est **rattachée à la session qui
couvrait son `vendue_le`** (même FERMEE) et l'écart de caisse de cette
session est **recalculé** — l'argent était bien dans le tiroir au comptage.
À défaut de session couvrante : session ouverte courante, sinon dernière
session de l'opérateur. (L'écart n'est PAS recalculé à l'annulation d'une
vente : le comptage historique, lui, incluait cet argent.)

## Ventes

- `POST /api/pos/vente/` (online) —
  `{idempotency_key, items: [{produit_id, lot_id?, quantite, prix_unitaire}],
  methode_paiement, montant_wallet?, code_paiement?, client_telephone?,
  client_email?, vendue_le}`. Méthodes : `moncash | natcash | cash |
  voucher | wallet`. Montant total calculé côté serveur (Σ quantité × prix).
  `vendue_le` est l'horodatage réel de la vente (≠ `synced_le`).
  - Paiement wallet (total ou hybride `montant_wallet` + cash) : exige
    `code_paiement` (code de consentement du client — `client_telephone`/
    `client_email` sont refusés pour le wallet). Le code est consommé
    atomiquement dans la même transaction que le débit : solde insuffisant
    → 400 `SOLDE_INSUFFISANT`, rien n'est créé et le code est rendu au
    client ; deux caisses ne peuvent pas consommer le même code.
  - `POST /api/pos/client/verifier-code/` `{code}` : consultation avant
    encaissement (identité + solde du client) SANS consommer le code.
  - `client_telephone`/`client_email` : rattachement des ventes **sans**
    wallet à un compte client ; introuvable → vente anonyme.
- `POST /api/pos/sync/` `{ventes: [...]}` — batch offline, chaque vente
  traitée indépendamment :
  `{resultats: [{idempotency_key, status: created|duplicate|rejected,
  vente_id?, session_id?, stock_conflict?, erreur?}]}`.
- Annulation (admin, action « Annuler ») : re-crédit des lots et
  remboursement de la part wallet du client (idempotents).

## Stock (signal `apps.pos.signals`)

À la création d'une ligne : décrément du lot précisé, sinon du lot
DISPONIBLE le plus ancien (FIFO, en cascade si besoin — le premier lot
utilisé est retenu sur la ligne pour le re-crédit d'annulation). Quantités
manipulées sous `select_for_update`, lot passé EPUISE à 0, stock produit
resynchronisé.

## Catalogue et rapports

- `GET /api/pos/catalogue/` — catalogue allégé pour cache local (Hive) :
  produits actifs, prix détail/gros, lots disponibles (id, code-barres,
  quantité). **ETag** calculé sur le contenu (`Max(updated_at)`/`Max(id)`/
  count des produits actifs et lots disponibles) : toute modification de
  prix ou de stock produit un nouvel ETag ; renvoyer `If-None-Match` → 304
  si inchangé.
- `GET /api/pos/rapports/` — `?session_id=` ou `?date=YYYY-MM-DD` ou
  `?device_id=`. Totaux, répartition par méthode, top 10 produits, nb
  conflits de stock. Cloisonné : un opérateur ne voit que ses ventes
  (session d'un autre opérateur → 404), le superadmin voit tout.

## Admin Django

- **Terminaux POS** : filtres département/commune, actions révoquer/réactiver.
- **Sessions** : écart de caisse coloré (rouge = manque, orange = surplus),
  readonly une fois fermée (document comptable).
- **Ventes** : lignes en inline, badges statut/conflit, filtres méthode/
  statut/conflit/département, recherche par `numero_vente`, actions
  « Annuler » (stock + wallet) et « Lever le conflit de stock ».
