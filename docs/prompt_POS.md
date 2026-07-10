Tu travailles sur le projet Django "Makèt Peyizan" (marketplace agricole haïtienne).
Backend : Django 5.1 + DRF + Jazzmin, réponses API au format uniforme
{"success": true, "data": ...} / {"success": false, "error": ...}, auth JWT existante.

OBJECTIF : créer l'app "pos" (point de vente physique) — modèles, services,
endpoints, signal stock, admin — avec intégration du wallet existant.

AVANT DE COMMENCER, lis ces fichiers pour comprendre les conventions :
- apps/wallet/ (structure de référence : models/ en package, services.py,
  signals.py, urls.py, admin.py)
- apps/wallet/services.py (WalletService : debiter, encaisser_bon_cadeau,
  appliquer_cashback)
- apps/wallet/models/transaction.py (WalletTransaction et ses Type)
- apps/accounts/models/user.py (CustomUser.Role)
- apps/stock/models/lot.py (Lot : quantite_actuelle, quantite_vendue, statut)
- apps/orders/models/commande.py (MethodePaiement)
- config/settings/base.py (INSTALLED_APPS)

═══════════════════════════════════════════
ÉTAPE A — Rôle pos_operator
═══════════════════════════════════════════
Dans CustomUser.Role, ajouter :
    POS_OPERATOR = 'pos_operator', _('Opérateur de caisse')
Ajouter une propriété is_pos_operator sur le modèle, comme les existantes.
Migration accounts.

═══════════════════════════════════════════
ÉTAPE B — App apps.pos : 4 modèles
═══════════════════════════════════════════
Créer apps/pos/ avec la même structure que apps/wallet/ (models/ en package).
Ajouter 'apps.pos' dans INSTALLED_APPS.

1. POSDevice
   - device_uid : CharField(64) unique (identifiant matériel du terminal)
   - nom : CharField(100)
   - operateur : FK settings.AUTH_USER_MODEL, related_name='pos_devices'
   - departement : CharField(max_length=20, choices=Departement.choices,
     verbose_name=_('Département')) — importer Departement depuis
     apps.accounts.models.producteur, EXACTEMENT comme le fait
     apps/accounts/models/adresse.py
   - commune : CharField(max_length=100, verbose_name=_('Commune'))
   - section_communale : CharField(max_length=150, blank=True,
     verbose_name=_('Section communale'))
   - adresse_detail : CharField(max_length=255, blank=True,
     verbose_name=_('Précision du lieu'),
     help_text=_('Ex : Marché Croix-des-Bossales, stand 12'))
   - is_active : BooleanField(default=True) — pour révoquer un terminal volé
   - created_at / updated_at
2. POSSession
   - device : FK POSDevice, related_name='sessions'
   - operateur : FK settings.AUTH_USER_MODEL, related_name='pos_sessions'
   - fonds_ouverture : DecimalField(12,2) — fonds de caisse initial
   - fonds_fermeture : DecimalField(12,2) null blank — comptage à la clôture
   - ecart_caisse : DecimalField(12,2) null blank — calculé à la clôture :
     fonds_fermeture - (fonds_ouverture + total ventes cash de la session)
   - ouverte_le : DateTimeField(auto_now_add=True)
   - fermee_le : DateTimeField(null=True, blank=True)
   - statut : TextChoices OUVERTE/FERMEE, default OUVERTE
   - Contrainte : un opérateur ne peut avoir qu'une seule session OUVERTE
     à la fois (valider dans le service, pas en contrainte DB).

3. POSSale
   - idempotency_key : UUIDField unique — TOUJOURS généré côté client
   - session : FK POSSession, related_name='ventes', on_delete=PROTECT
   - operateur : FK settings.AUTH_USER_MODEL
   - client : FK settings.AUTH_USER_MODEL null blank, related_name='achats_pos'
     (acheteur identifié par téléphone/email, ou null = vente anonyme)
   - numero_vente : CharField(30) unique blank — auto-généré au save() :
     format POS-{annee}-{compteur:05d} (même pattern que Lot.numero_lot)
   - montant_total : DecimalField(12,2)
   - methode_paiement : TextChoices reprenant les valeurs de
     Commande.MethodePaiement : moncash, natcash, cash, voucher, wallet
     (pas de virement ni hors_ligne au comptoir)
   - montant_wallet : DecimalField(12,2) default 0 — part payée par wallet
     (paiement hybride wallet + cash)
   - statut : TextChoices CONFIRMEE / ANNULEE, default CONFIRMEE
   - stock_conflict : BooleanField(default=False) — vente synchronisée alors
     que le stock serveur était insuffisant ; à arbitrer par le superadmin
   - vendue_le : DateTimeField — horodatage RÉEL de la vente fourni par le
     client (important pour les ventes offline synchronisées plus tard)
   - synced_le : DateTimeField(auto_now_add=True)

4. POSItem
   - vente : FK POSSale, related_name='items', on_delete=CASCADE
   - produit : FK 'catalog.Produit', on_delete=PROTECT
   - lot : FK 'stock.Lot', null blank, on_delete=PROTECT
   - quantite : PositiveIntegerField
   - prix_unitaire : DecimalField(12,2) — prix appliqué (détail ou gros)
   - sous_total : DecimalField(12,2)

Verbose names FR avec gettext_lazy, __str__ soignés, Meta.ordering,
comme dans le reste du projet. Migrations.

═══════════════════════════════════════════
ÉTAPE C — Intégration wallet
═══════════════════════════════════════════
1. Dans WalletTransaction.Type, ajouter :
       PAIEMENT_POS = 'paiement_pos', _('Paiement vente POS')
2. Sur WalletTransaction, ajouter un FK nullable :
       pos_sale = FK('pos.POSSale', on_delete=SET_NULL, null=True, blank=True,
                     related_name='wallet_transactions')
3. Dans WalletService, ajouter une méthode payer_vente_pos(cls, user, pos_sale,
   montant) qui réutilise _appliquer() avec type PAIEMENT_POS, lie pos_sale,
   lève SoldeInsuffisant si besoin. NE PAS dupliquer la logique du ledger.
4. RÈGLE MÉTIER STRICTE : le paiement wallet POS est SYNCHRONE et ONLINE
   UNIQUEMENT. L'endpoint de sync batch (étape D) doit REJETER toute vente
   avec methode_paiement='wallet' ou montant_wallet > 0, avec une erreur
   explicite par vente. Raison : empêcher le double-spending offline.
Migration wallet.

═══════════════════════════════════════════
ÉTAPE D — POSService + 5 endpoints /api/pos/
═══════════════════════════════════════════
Créer apps/pos/services.py (class POSService) portant TOUTE la logique
métier (les vues restent minces), et apps/pos/serializers.py.

Permission : classe IsPOSOperator (role == pos_operator) + vérification que
le device_uid transmis dans le header 'X-POS-Device' correspond à un
POSDevice actif appartenant à l'opérateur. Superadmin passe aussi.

1. POST /api/pos/session/ouvrir/
   body: {device_uid, fonds_ouverture}
   Refuse si une session OUVERTE existe déjà pour cet opérateur.

2. POST /api/pos/session/fermer/
   body: {fonds_fermeture}
   Calcule ecart_caisse, passe en FERMEE, retourne le récap
   (total ventes, par méthode de paiement, écart).

3. POST /api/pos/vente/
   Vente unitaire ONLINE.
   body: {idempotency_key, items: [{produit_id, lot_id?, quantite,
   prix_unitaire}], methode_paiement, montant_wallet?, client_telephone?,
   client_email?, vendue_le}
   - Si idempotency_key déjà connue → retourner la vente existante avec
     succès (pas d'erreur, pas de doublon).
   - Si client_telephone/email fourni → retrouver le CustomUser acheteur ;
     introuvable = erreur claire si paiement wallet, sinon vente anonyme.
   - Si wallet : appeler WalletService.payer_vente_pos dans la même
     transaction atomique que la création de la vente.
   - Tout est atomique (transaction.atomic).

4. POST /api/pos/sync/
   body: {ventes: [...]} — batch de ventes offline, même schéma que /vente/.
   - Traiter chaque vente indépendamment ; réponse :
     {"success": true, "data": {"resultats": [{idempotency_key,
     status: "created"|"duplicate"|"rejected", vente_id?, erreur?}]}}
   - REJETER les ventes wallet (cf. étape C).
   - Stock insuffisant à la sync : NE PAS rejeter (la vente physique a eu
     lieu) → créer la vente avec stock_conflict=True et décrémenter le lot
     à 0 minimum (jamais de quantité négative).

5. GET /api/pos/catalogue/
   Catalogue allégé pour cache Hive : produits actifs avec prix détail/gros,
   lots disponibles (id, code_barres, quantite_actuelle), catégorie.
   Support ETag : si le catalogue n'a pas changé → 304.

6. GET /api/pos/rapports/
   Params: ?session_id= ou ?date=YYYY-MM-DD ou ?device_id=
   Totaux : nb ventes, CA, répartition par méthode de paiement,
   top produits. Accessible pos_operator (ses données) et superadmin (tout).

Routes dans apps/pos/urls.py, incluses dans la conf d'URLs principale
sous /api/pos/. Format de réponse uniforme du projet partout.

═══════════════════════════════════════════
ÉTAPE E — Signal stock
═══════════════════════════════════════════
apps/pos/signals.py (branché dans apps.py.ready(), comme wallet) :
- post_save sur POSItem (created=True, vente CONFIRMEE) : décrémenter
  lot.quantite_actuelle, incrémenter lot.quantite_vendue, passer le lot
  en EPUISE si quantite_actuelle atteint 0. Si pas de lot précisé,
  décrémenter le lot DISPONIBLE le plus ancien du produit (FIFO).
- Annulation d'une POSSale (statut → ANNULEE) : re-créditer les lots.
Utiliser select_for_update pour éviter les races sur les quantités.

═══════════════════════════════════════════
ÉTAPE F — Admin Jazzmin
═══════════════════════════════════════════
apps/pos/admin.py : admin riche comme apps/wallet/admin.py —
POSDevice (list + action désactiver), POSSession (readonly après fermeture,
écart en couleur si non nul), POSSale (inline POSItem, filtres par méthode/
statut/stock_conflict, recherche par numero_vente), badges colorés de statut.
POSDevice : list_filter par departement et commune, pour que le 
superadmin filtre les terminaux par zone géographique.

═══════════════════════════════════════════
CONTRAINTES GÉNÉRALES
═══════════════════════════════════════════
- Ne modifier AUCUN comportement existant (wallet, orders, stock) en dehors
  des ajouts explicitement listés.
- Toutes les chaînes visibles avec gettext_lazy (projet multilingue fr/en/es/ht).
- Après implémentation : python manage.py makemigrations && migrate,
  puis vérifier avec python manage.py check.
- Fournir en fin de tâche un résumé des fichiers créés/modifiés et des
  exemples curl pour chacun des 6 endpoints.