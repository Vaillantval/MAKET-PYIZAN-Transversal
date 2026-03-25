"""
CartService — Panier session-based pour Makèt Peyizan

Structure session :
  mp_cart = {
    "<slug>": {
      "slug": str,
      "nom": str,
      "quantite": int,
      "prix_unitaire": str,   # Decimal sérialisé en str
      "unite_vente": str,
      "unite_vente_label": str,
      "image": str | None,
      "producteur_id": int,
      "producteur_nom": str,
    },
    ...
  }

Note : chaque commande est liée à UN producteur.
       Si le panier contient des produits de producteurs différents,
       le checkout devra créer plusieurs commandes.
"""

CART_SESSION_KEY = 'mp_cart'


class CartService:

    # ── Accès interne ──────────────────────────────────────────────────────────

    @staticmethod
    def _get(request) -> dict:
        return request.session.get(CART_SESSION_KEY, {})

    @staticmethod
    def _save(request, cart: dict) -> None:
        request.session[CART_SESSION_KEY] = cart
        request.session.modified = True

    # ── API publique ───────────────────────────────────────────────────────────

    @classmethod
    def ajouter(cls, request, produit, quantite: int = 1) -> dict:
        """
        Ajoute `quantite` unités du produit au panier.
        `produit` est une instance de apps.catalog.models.Produit.
        Retourne le résumé du panier.
        """
        cart = cls._get(request)
        slug = produit.slug

        if slug in cart:
            cart[slug]['quantite'] += quantite
        else:
            cart[slug] = {
                'slug':            produit.slug,
                'nom':             produit.nom,
                'quantite':        quantite,
                'prix_unitaire':   str(produit.prix_unitaire),
                'unite_vente':     produit.unite_vente,
                'unite_vente_label': produit.get_unite_vente_display(),
                'image':           produit.image_principale.url if produit.image_principale else None,
                'producteur_id':   produit.producteur_id,
                'producteur_nom':  produit.producteur.user.get_full_name(),
                'quantite_min':    produit.quantite_min_commande,
                'stock_reel':      produit.stock_reel,
            }

        cls._save(request, cart)
        return cls.resume(request)

    @classmethod
    def retirer(cls, request, slug: str) -> dict:
        """Supprime complètement un article du panier."""
        cart = cls._get(request)
        cart.pop(slug, None)
        cls._save(request, cart)
        return cls.resume(request)

    @classmethod
    def modifier_quantite(cls, request, slug: str, quantite: int) -> dict:
        """Met à jour la quantité d'un article. Supprime l'article si quantite <= 0."""
        cart = cls._get(request)
        if slug in cart:
            if quantite <= 0:
                del cart[slug]
            else:
                cart[slug]['quantite'] = quantite
        cls._save(request, cart)
        return cls.resume(request)

    @classmethod
    def vider(cls, request) -> None:
        """Vide complètement le panier."""
        request.session.pop(CART_SESSION_KEY, None)
        request.session.modified = True

    @classmethod
    def resume(cls, request) -> dict:
        """
        Retourne un résumé complet du panier :
          - items     : liste des articles avec sous-totaux
          - total     : total HTG
          - nb_articles : nombre total d'unités
          - nb_items  : nombre de lignes distinctes
          - producteurs : liste des producteurs présents
        """
        cart = cls._get(request)
        items = []
        total = 0.0
        producteurs = {}

        for slug, item in cart.items():
            prix = float(item['prix_unitaire'])
            qte  = item['quantite']
            sous_total = round(prix * qte, 2)
            total += sous_total

            items.append({
                **item,
                'sous_total': sous_total,
            })

            pid = item['producteur_id']
            if pid not in producteurs:
                producteurs[pid] = item['producteur_nom']

        return {
            'items':       items,
            'total':       round(total, 2),
            'nb_articles': sum(i['quantite'] for i in cart.values()),
            'nb_items':    len(cart),
            'producteurs': [{'id': k, 'nom': v} for k, v in producteurs.items()],
        }

    @classmethod
    def nb_articles(cls, request) -> int:
        """Nombre total d'unités dans le panier (pour le badge navbar)."""
        cart = cls._get(request)
        return sum(i['quantite'] for i in cart.values())

    @classmethod
    def contient(cls, request, slug: str) -> bool:
        return slug in cls._get(request)
