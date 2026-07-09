# Makèt Peyizan — Portefeuille (Wallet)

> Solde prépayé en HTG pour **acheteurs et producteurs** : recharges, paiement
> de commandes, ventes créditées, retraits, cashback, parrainage, bons cadeaux.
> Adapté du wallet MatStore, intégré aux modèles `Commande`/`Paiement` et à la
> passerelle Plopplop de Makèt Peyizan.

---

## Principes

- **Ledger immuable** : le solde n'est jamais modifié directement. Chaque
  mouvement crée une `WalletTransaction` (montant signé + solde résultant).
  Une erreur se corrige par une transaction d'ajustement inverse, jamais par
  modification/suppression.
- **Verrouillage** : chaque mouvement verrouille la ligne `Wallet`
  (`select_for_update`) — deux débits concurrents ne peuvent pas dépasser le solde.
- **Idempotence** : toutes les opérations liées à un objet métier (commande,
  recharge, retrait, bon) sont rejouables sans double effet.
- **Point d'entrée unique** : `apps.wallet.services.WalletService`. Ne jamais
  écrire `wallet.solde = ...` ailleurs.

## Activation (SiteSettings, admin → Configuration du site)

| Réglage | Rôle |
|---------|------|
| `wallet_enabled` | Active tout le module (API → 503 sinon) |
| `taux_commission` | % prélevé sur les ventes créditées aux producteurs (0 par défaut) |
| `cashback_enabled` / `taux_cashback` | Cashback fidélité acheteur (% du total, commandes non payées par wallet) |
| `parrainage_enabled` / `taux_bonus_parrainage` | Bonus parrain + filleul à la 1ère commande payée du filleul |
| `numero_moncash_depot` / `numero_natcash_depot` | Comptes de la plateforme pour les dépôts hors ligne |

## Cycle de vie automatique (signaux sur Commande)

| Événement | Effet wallet |
|-----------|--------------|
| `statut_paiement` → `paye` | Cashback acheteur + bonus parrainage (si activés) |
| `statut` → `livree` (payée) | Crédit producteur : `sous_total − commission` |
| Paiement confirmé après livraison (cash) | Crédit producteur au paiement |
| `statut` → `annulee` (payée) | Remboursement acheteur (total) + reprise vente/cashback/bonus |
| `statut` → `annulee` (réserve partielle) | Libération de la réserve wallet |

## Tâches Celery Beat (enregistrées par `init_site.py`)

- `wallet.liberer_reserves_expirees` (toutes les heures) : re-crédite les
  réserves de paiement partiel des commandes impayées depuis plus de 24 h.
- `wallet.expirer_bons_cadeaux` (03h00) : expire les bons actifs échus (validité 12 mois).
- `wallet.rappeler_bons_expirant` (09h00) : email de rappel pour les bons
  actifs expirant dans 30 jours (fenêtre de 24 h — un seul rappel par bon).
- `wallet.rappeler_soldes_dormants` (le 1er du mois, 10h00) : email aux
  wallets avec solde > 0 sans transaction depuis 30 jours.
- `wallet.relancer_parrainage` (le 15 du mois, 10h00) : email aux
  utilisateurs dont le code de parrainage n'a encore parrainé personne.

## Notifications automatiques (email Resend + push FCM)

Recharges (validée/rejetée), retraits (payé/rejeté + alerte admin), vente
créditée producteur, bon cadeau envoyé — et côté fidélité :

- **Cashback crédité** (`wallet.cashback_credite`) : email + push acheteur
  à chaque crédit, également mentionné dans l'email « paiement confirmé ».
- **Bonus parrainage** (`wallet.bonus_parrainage`) : email + push distincts
  pour le parrain (« votre filleul a commandé ») et le filleul (« bonus de
  bienvenue »).

## Marketing

- **Accueil** : section « Le portefeuille Makèt Peyizan » (cartes cashback /
  parrainage / paiement 1 clic / bons) — affichée si `wallet_enabled`, taux
  dynamiques depuis SiteSettings, CTA inscription (ou portefeuille si connecté).
- **Checkout** : encart « Vous gagnerez ≈ X HTG de cashback » calculé en
  direct (masqué si le wallet finance la commande — pas de cashback dans ce cas).
- **Inscription** : champ code de parrainage (pré-rempli via `?parrain=CODE`) ;
  la page wallet propose « Copier le lien » et le partage natif mobile.

---

## API — `/api/wallet/` (JWT requis)

### Solde et historique

```
GET /api/wallet/
```
```json
{
  "success": true,
  "data": {
    "solde": "1500.00",
    "devise": "HTG",
    "is_active": true,
    "cashback": {"actif": true, "taux": "5.00"},
    "parrainage": {"code": "K7XM2P9A", "taux_bonus": "2.00"},
    "depot_hors_ligne": {"numero_moncash": "…", "numero_natcash": "…"},
    "transactions_recentes": [ … ]
  }
}
```

```
GET /api/wallet/transactions/?page=1        # historique paginé (20/page)
```

### Recharges

```
POST /api/wallet/recharge/initier/          # {montant, methode: moncash|natcash}
→ {recharge_id, reference, redirect_url}    # ouvrir redirect_url, puis vérifier

POST /api/wallet/recharge/verifier/         # {recharge_id}
→ {confirmee, statut, solde}

POST /api/wallet/recharge/hors-ligne/       # multipart {montant, preuve_image}
→ crédité après validation admin (JPG/PNG ≤ 5 MB, max 3 en attente)
```
Bornes : 25 – 1 000 000 HTG.

### Paiement de commandes

```
POST /api/wallet/payer/                     # {commande_numero} — paiement total
→ {statut, statut_paiement, montant_paye, solde}
   (crée un Paiement type "wallet" confirmé + confirme la commande/stock)

POST /api/wallet/payer-partiel/             # {commande_numero}
→ réserve min(solde, total) ; le reste se paie via /api/payments/initier/
   (le Paiement/redirect Plopplop porte automatiquement sur total − réserve)

POST /api/wallet/liberer-partiel/           # {commande_numero} — re-crédit
```
Erreur solde : HTTP 400 + `"code": "SOLDE_INSUFFISANT"`.

### Retraits (producteurs et acheteurs)

```
POST /api/wallet/retrait/    # {montant, canal: moncash|natcash, numero_telephone}
GET  /api/wallet/retraits/   # mes demandes (statuts: demande | paye | rejete)
```
Le montant est **débité à la demande** (réservation). L'admin effectue le
transfert manuellement (preuve jointe) et marque payé, ou rejette (re-crédit
automatique). Bornes : 100 – 1 000 000 HTG.

### Bons cadeaux

```
POST /api/wallet/bon/acheter/    # {montant, methode: wallet|moncash|natcash,
                                 #  email_destinataire?, message?}
→ wallet : bon activé immédiatement ; Plopplop : {bon_id, redirect_url}

POST /api/wallet/bon/verifier/   # {bon_id} — active après paiement Plopplop
POST /api/wallet/bon/encaisser/  # {code} — crédite le wallet
                                 # anti-bruteforce : 10 essais/heure → 429
GET  /api/wallet/bons/           # mes bons achetés
GET  /api/wallet/bons/recus/     # bons reçus (code masqué tant que non encaissé)
```
Codes format `MKP-XXXX-XXXX-XXXX`, validité 12 mois, envoyés par email
(destinataire ou acheteur) à l'activation. Bornes : 100 – 100 000 HTG.

### Parrainage

- `POST /api/auth/register/` accepte `code_parrainage` (optionnel, validé).
- Le code de l'utilisateur est dans `GET /api/wallet/` → `parrainage.code`.
- Bonus versé une seule fois par filleul (parrain **et** filleul), à la
  première commande payée du filleul.

---

## Types de transactions (ledger)

| Type | Sens | Déclencheur |
|------|------|-------------|
| `recharge` | + | Plopplop confirmé ou preuve validée |
| `paiement` | − | Paiement total/partiel de commande |
| `remboursement` | + | Commande payée annulée |
| `liberation_reserve` | + | Réserve partielle libérée (annulation/24 h) |
| `vente` | + | Commande livrée → producteur (commission déduite) |
| `reprise_vente` | − | Annulation après livraison |
| `retrait` / `reprise_retrait` | − / + | Demande de retrait / rejet |
| `cashback` / `reprise_cashback` | + / − | Paiement / annulation |
| `bonus_parrainage` / `reprise_bonus_parrainage` | + / − | 1ère commande filleul / annulation |
| `bon_cadeau_achat` / `bon_cadeau_encaisse` | − / + | Achat / encaissement de bon |
| `ajustement` | ± | Ajustement manuel admin (via le service) |

## Interfaces

- **Web** : `/dashboard/acheteur/wallet/` (recharges, bons, parrainage,
  historique) et `/dashboard/producteur/wallet/` (retraits, ventes, historique).
- **Dashboard superadmin custom** : `/dashboard/superadmin/wallet/` — stats
  (encours, à traiter), 5 onglets (Recharges, Retraits, Portefeuilles,
  Transactions, Bons cadeaux) avec les mêmes actions que l'admin Django,
  servi par les endpoints `/api/admin/wallet/…` (permission `IsSuperAdmin`).
- **Admin Django** : Portefeuilles (solde en lecture seule), Transactions
  (ledger immuable, ajustements via formulaire dédié), Recharges (actions
  valider/rejeter avec lien preuve), Retraits (actions payer/rejeter,
  upload preuve de transfert), Bons cadeaux (annuler, renvoyer l'email).
- **Notifications** : emails Resend (`templates/emails/wallet_*.html`) +
  push FCM (`screen: "wallet"` pour le deep-linking Flutter).
