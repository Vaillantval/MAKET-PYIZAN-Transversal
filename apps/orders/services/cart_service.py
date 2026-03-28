"""
CartService — Panier hybride pour Makèt Peyizan

Backend selon le contexte :
  - Utilisateur authentifié (JWT) → base de données (PanierItem)
  - Visiteur anonyme (web)        → session Django (comportement inchangé)

Structure session (inchangée, rétrocompatible) :
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
      "quantite_min": int,
      "stock_reel": int,
    },
    ...
  }
"""

from decimal import Decimal

CART_SESSION_KEY = 'mp_cart'


class CartService:

    # ── Dispatch ─────────────────────────────────────────────────────────────

    @staticmethod
    def _use_db(request) -> bool:
        return request.user.is_authenticated

    # ── Session backend ───────────────────────────────────────────────────────

    @staticmethod
    def _session_get(request) -> dict:
        return request.session.get(CART_SESSION_KEY, {})

    @staticmethod
    def _session_save(request, cart: dict) -> None:
        request.session[CART_SESSION_KEY] = cart
        request.session.modified = True

    # ── DB backend helpers ────────────────────────────────────────────────────

    @staticmethod
    def _db_qs(request):
        from apps.orders.models.panier import PanierItem
        return PanierItem.objects.filter(user=request.user).select_related(
            'produit__producteur__user', 'produit__categorie'
        ).prefetch_related('produit__images')

    # ── resume ────────────────────────────────────────────────────────────────

    @classmethod
    def resume(cls, request) -> dict:
        if cls._use_db(request):
            return cls._db_resume(request)
        return cls._session_resume(request)

    @classmethod
    def _session_resume(cls, request) -> dict:
        cart = cls._session_get(request)
        items = []
        total = 0.0
        producteurs = {}

        for slug, item in cart.items():
            prix      = float(item['prix_unitaire'])
            qte       = item['quantite']
            sous_total = round(prix * qte, 2)
            total     += sous_total

            items.append({**item, 'sous_total': sous_total})

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
    def _db_resume(cls, request) -> dict:
        items = []
        total = Decimal('0')
        producteurs = {}

        for pi in cls._db_qs(request):
            p          = pi.produit
            prix       = p.prix_unitaire
            qte        = pi.quantite
            sous_total = qte * prix
            total     += sous_total

            image = None
            if p.image_principale:
                try:
                    image = request.build_absolute_uri(p.image_principale.url)
                except Exception:
                    image = p.image_principale.url

            pid = p.producteur_id
            producteur_nom = p.producteur.user.get_full_name()

            items.append({
                'slug':              p.slug,
                'nom':               p.nom,
                'quantite':          float(qte),
                'prix_unitaire':     str(prix),
                'unite_vente':       p.unite_vente,
                'unite_vente_label': p.get_unite_vente_display(),
                'image':             image,
                'producteur_id':     pid,
                'producteur_nom':    producteur_nom,
                'quantite_min':      p.quantite_min_commande,
                'stock_reel':        p.stock_reel,
                'sous_total':        float(sous_total),
            })

            if pid not in producteurs:
                producteurs[pid] = producteur_nom

        return {
            'items':       items,
            'total':       float(round(total, 2)),
            'nb_articles': sum(i['quantite'] for i in items),
            'nb_items':    len(items),
            'producteurs': [{'id': k, 'nom': v} for k, v in producteurs.items()],
        }

    # ── ajouter ───────────────────────────────────────────────────────────────

    @classmethod
    def ajouter(cls, request, produit, quantite=1) -> dict:
        if cls._use_db(request):
            return cls._db_ajouter(request, produit, quantite)
        return cls._session_ajouter(request, produit, quantite)

    @classmethod
    def _session_ajouter(cls, request, produit, quantite) -> dict:
        cart = cls._session_get(request)
        slug = produit.slug

        if slug in cart:
            cart[slug]['quantite'] += quantite
        else:
            cart[slug] = {
                'slug':              produit.slug,
                'nom':               produit.nom,
                'quantite':          quantite,
                'prix_unitaire':     str(produit.prix_unitaire),
                'unite_vente':       produit.unite_vente,
                'unite_vente_label': produit.get_unite_vente_display(),
                'image':             produit.image_principale.url if produit.image_principale else None,
                'producteur_id':     produit.producteur_id,
                'producteur_nom':    produit.producteur.user.get_full_name(),
                'quantite_min':      produit.quantite_min_commande,
                'stock_reel':        produit.stock_reel,
            }

        cls._session_save(request, cart)
        return cls._session_resume(request)

    @classmethod
    def _db_ajouter(cls, request, produit, quantite) -> dict:
        from apps.orders.models.panier import PanierItem
        quantite = Decimal(str(quantite))
        pi, created = PanierItem.objects.get_or_create(
            user=request.user,
            produit=produit,
            defaults={'quantite': quantite},
        )
        if not created:
            pi.quantite += quantite
            pi.save(update_fields=['quantite', 'updated_at'])
        return cls._db_resume(request)

    # ── retirer ───────────────────────────────────────────────────────────────

    @classmethod
    def retirer(cls, request, slug: str) -> dict:
        if cls._use_db(request):
            from apps.orders.models.panier import PanierItem
            PanierItem.objects.filter(user=request.user, produit__slug=slug).delete()
            return cls._db_resume(request)

        cart = cls._session_get(request)
        cart.pop(slug, None)
        cls._session_save(request, cart)
        return cls._session_resume(request)

    # ── modifier_quantite ─────────────────────────────────────────────────────

    @classmethod
    def modifier_quantite(cls, request, slug: str, quantite) -> dict:
        if cls._use_db(request):
            from apps.orders.models.panier import PanierItem
            quantite = Decimal(str(quantite))
            if quantite <= 0:
                PanierItem.objects.filter(user=request.user, produit__slug=slug).delete()
            else:
                PanierItem.objects.filter(
                    user=request.user, produit__slug=slug
                ).update(quantite=quantite)
            return cls._db_resume(request)

        cart = cls._session_get(request)
        if slug in cart:
            if quantite <= 0:
                del cart[slug]
            else:
                cart[slug]['quantite'] = quantite
        cls._session_save(request, cart)
        return cls._session_resume(request)

    # ── vider ─────────────────────────────────────────────────────────────────

    @classmethod
    def vider(cls, request) -> None:
        if cls._use_db(request):
            from apps.orders.models.panier import PanierItem
            PanierItem.objects.filter(user=request.user).delete()
        else:
            request.session.pop(CART_SESSION_KEY, None)
            request.session.modified = True

    # ── utilitaires ───────────────────────────────────────────────────────────

    @classmethod
    def nb_articles(cls, request) -> int:
        if cls._use_db(request):
            from apps.orders.models.panier import PanierItem
            from django.db.models import Sum
            result = PanierItem.objects.filter(user=request.user).aggregate(total=Sum('quantite'))
            return float(result['total'] or 0)
        cart = cls._session_get(request)
        return sum(i['quantite'] for i in cart.values())

    @classmethod
    def contient(cls, request, slug: str) -> bool:
        if cls._use_db(request):
            from apps.orders.models.panier import PanierItem
            return PanierItem.objects.filter(user=request.user, produit__slug=slug).exists()
        return slug in cls._session_get(request)
