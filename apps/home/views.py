from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q
from apps.catalog.models import Produit, Categorie
from apps.accounts.models import Producteur


def home(request):
    """
    Page d'accueil publique.
    Visible par tous sans connexion.
    """
    from apps.orders.services.cart_service import CartService

    # ── Statistiques publiques ──────────────────────────────────
    stats = {
        'nb_producteurs': Producteur.objects.filter(statut='actif').count(),
        'nb_produits':    Produit.objects.filter(is_active=True).count(),
        'nb_categories':  Categorie.objects.filter(
                            is_active=True, parent=None
                          ).count(),
        'nb_communes':    Producteur.objects.filter(
                            statut='actif'
                          ).values('commune').distinct().count(),
    }

    # ── Catégories principales (sans parent) ────────────────────
    categories = Categorie.objects.filter(
        is_active=True,
        parent=None
    ).annotate(
        nb=Count('produits', filter=Q(produits__is_active=True))
    ).order_by('ordre')[:8]

    # ── Produits mis en avant ───────────────────────────────────
    produits_featured = Produit.objects.filter(
        is_active=True,
        is_featured=True,
        stock_disponible__gt=0
    ).select_related(
        'producteur__user',
        'categorie'
    ).order_by('-created_at')[:8]

    # ── Nouveaux produits ───────────────────────────────────────
    from django.utils import timezone
    from datetime import timedelta
    il_y_a_30j = timezone.now() - timedelta(days=30)

    nouveaux_produits = Produit.objects.filter(
        is_active=True,
        stock_disponible__gt=0,
        created_at__gte=il_y_a_30j
    ).select_related(
        'producteur__user',
        'categorie'
    ).order_by('-created_at')[:8]

    # ── Producteurs actifs récents ──────────────────────────────
    producteurs = Producteur.objects.filter(
        statut='actif'
    ).select_related('user').order_by('-created_at')[:6]

    # ── Produit sélectionné (si slug en paramètre) ──────────────
    slug    = request.GET.get('produit')
    produit = None
    if slug:
        produit = get_object_or_404(
            Produit, slug=slug, is_active=True
        )

    # ── Filtres catalogue ───────────────────────────────────────
    categorie_filtre = request.GET.get('categorie', '')
    recherche        = request.GET.get('q', '')

    produits_catalogue = Produit.objects.filter(
        is_active=True,
        stock_disponible__gt=0
    ).select_related('producteur__user', 'categorie')

    if categorie_filtre:
        produits_catalogue = produits_catalogue.filter(
            categorie__slug=categorie_filtre
        )
    if recherche:
        produits_catalogue = produits_catalogue.filter(
            Q(nom__icontains=recherche) |
            Q(description__icontains=recherche) |
            Q(variete__icontains=recherche) |
            Q(producteur__commune__icontains=recherche)
        )

    produits_catalogue = produits_catalogue.order_by('-created_at')[:24]

    return render(request, 'home/index.html', {
        'stats':              stats,
        'categories':         categories,
        'produits_featured':  produits_featured,
        'nouveaux_produits':  nouveaux_produits,
        'producteurs':        producteurs,
        'produits_catalogue': produits_catalogue,
        'produit_detail':     produit,
        'categorie_active':   categorie_filtre,
        'recherche':          recherche,
        'nb_panier':          CartService.nb_articles(request),
    })


def login_page(request):
    return render(request, 'accounts/login.html')


def register_page(request):
    return render(request, 'accounts/register.html')

def register_pending(request):
    return render(request, 'accounts/register_pending.html')


# ── Dashboards ──────────────────────────────────────────────────────────────

def dashboard_router(request):
    """Page de routage : redirige JS vers le bon dashboard selon le rôle."""
    return render(request, 'dashboard/router.html')


def dashboard_acheteur(request):
    return render(request, 'dashboard/acheteur.html')

def dashboard_acheteur_commandes(request):
    return render(request, 'dashboard/acheteur_commandes.html')

def dashboard_acheteur_adresses(request):
    return render(request, 'dashboard/acheteur_adresses.html')

def dashboard_acheteur_profil(request):
    return render(request, 'dashboard/acheteur_profil.html')


def dashboard_producteur(request):
    return render(request, 'dashboard/producteur.html')

def dashboard_producteur_commandes(request):
    return render(request, 'dashboard/producteur_commandes.html')

def dashboard_producteur_catalogue(request):
    return render(request, 'dashboard/producteur_catalogue.html')

def dashboard_producteur_profil(request):
    return render(request, 'dashboard/producteur_profil.html')

def dashboard_producteur_en_attente(request):
    return render(request, 'dashboard/producteur_en_attente.html')


def dashboard_admin(request):
    return render(request, 'dashboard/admin.html')


def dashboard_superadmin(request):
    return render(request, 'dashboard/superadmin.html')


# ── Pages catalogue public ──────────────────────────────────────────────────

def produit_detail(request, slug):
    """Page détail d'un produit — accessible sans connexion."""
    from apps.catalog.models import Produit
    from apps.orders.services.cart_service import CartService
    produit = get_object_or_404(Produit, slug=slug, is_active=True)

    similaires = Produit.objects.filter(
        categorie=produit.categorie, is_active=True
    ).exclude(pk=produit.pk).select_related('producteur__user')[:4]

    dans_panier = CartService.contient(request, slug)
    nb_panier   = CartService.nb_articles(request)

    return render(request, 'home/produit_detail.html', {
        'produit':     produit,
        'similaires':  similaires,
        'dans_panier': dans_panier,
        'nb_panier':   nb_panier,
    })


def panier_page(request):
    """Page panier — affiche le contenu du panier session."""
    from apps.orders.services.cart_service import CartService
    resume = CartService.resume(request)
    return render(request, 'home/panier.html', {'resume': resume})


def checkout_page(request):
    """Page de finalisation de commande."""
    from apps.orders.services.cart_service import CartService
    nb_panier = CartService.nb_articles(request)
    return render(request, 'home/checkout.html', {'nb_panier': nb_panier})


def moncash_retour(request):
    """
    Callback MonCash après paiement.
    GET /commander/moncash/retour/?transactionId=<id>
    """
    from apps.payments.services.moncash_service import MonCashService
    from apps.orders.models import Commande

    transaction_id = request.GET.get('transactionId', '')
    ctx = {'transaction_id': transaction_id, 'success': False, 'commandes': [], 'erreur': ''}

    if not transaction_id:
        ctx['erreur'] = 'Identifiant de transaction manquant.'
        return render(request, 'home/moncash_retour.html', ctx)

    mc = MonCashService()
    try:
        payment = mc.verifier_paiement(transaction_id)
    except Exception as e:
        ctx['erreur'] = f'Erreur de vérification MonCash : {e}'
        return render(request, 'home/moncash_retour.html', ctx)

    # reference = "MKT-CMD-XXXX-XXXXX"
    reference = payment.get('reference', '')
    if reference.startswith('MKT-'):
        numero = reference[4:]  # retire "MKT-"
        commandes = Commande.objects.filter(
            numero_commande=numero
        ) | Commande.objects.filter(
            reference_paiement=payment.get('transaction_id', transaction_id)
        )
    else:
        commandes = Commande.objects.filter(
            reference_paiement=transaction_id
        )

    commandes = commandes.distinct()

    message_mc = payment.get('message', '').lower()
    paiement_ok = message_mc in ('successful', 'success', 'approved') or payment.get('cost', 0) > 0

    if paiement_ok:
        commandes.update(
            statut_paiement=Commande.StatutPaiement.VERIFIE,
            reference_paiement=transaction_id,
        )
        ctx['success'] = True
    else:
        ctx['erreur'] = f"Paiement non confirmé. Statut : {payment.get('message', 'inconnu')}"

    ctx['commandes'] = list(commandes.values('numero_commande', 'total', 'producteur__user__first_name', 'producteur__user__last_name'))
    ctx['payer'] = payment.get('payer', '')
    ctx['montant'] = payment.get('cost', '')
    return render(request, 'home/moncash_retour.html', ctx)
