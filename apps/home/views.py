from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Count, Q
from apps.catalog.models import Produit, Categorie
from apps.accounts.models import Producteur


def health_check(request):
    """GET /health/ — utilisé par Railway pour vérifier que l'app est vivante."""
    return JsonResponse({'status': 'ok'})


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

def dashboard_producteur_collectes(request):
    return render(request, 'dashboard/producteur_collectes.html')

def dashboard_producteur_catalogue(request):
    return render(request, 'dashboard/producteur_catalogue.html')

def dashboard_producteur_profil(request):
    return render(request, 'dashboard/producteur_profil.html')

def dashboard_producteur_en_attente(request):
    return render(request, 'dashboard/producteur_en_attente.html')


def dashboard_admin(request):
    from django.shortcuts import redirect
    return redirect('/dashboard/superadmin/')


def dashboard_superadmin(request):
    return render(request, 'dashboard/superadmin.html')

def dashboard_superadmin_utilisateurs(request):
    return render(request, 'dashboard/superadmin_utilisateurs.html')

def dashboard_superadmin_producteurs(request):
    return render(request, 'dashboard/superadmin_producteurs.html')

def dashboard_superadmin_commandes(request):
    return render(request, 'dashboard/superadmin_commandes.html')

def dashboard_superadmin_paiements(request):
    return render(request, 'dashboard/superadmin_paiements.html')

def dashboard_superadmin_catalogue(request):
    return render(request, 'dashboard/superadmin_catalogue.html')

def dashboard_superadmin_stocks(request):
    return render(request, 'dashboard/superadmin_stocks.html')

def dashboard_superadmin_collectes(request):
    return render(request, 'dashboard/superadmin_collectes.html')

def dashboard_superadmin_acheteurs(request):
    return render(request, 'dashboard/superadmin_acheteurs.html')

def dashboard_superadmin_adresses(request):
    return render(request, 'dashboard/superadmin_adresses.html')

def dashboard_superadmin_categories(request):
    return render(request, 'dashboard/superadmin_categories.html')

def dashboard_superadmin_vouchers(request):
    return render(request, 'dashboard/superadmin_vouchers.html')

def dashboard_superadmin_zones(request):
    return render(request, 'dashboard/superadmin_zones.html')

def dashboard_superadmin_config(request):
    return render(request, 'dashboard/superadmin_config.html')

def dashboard_superadmin_profil(request):
    return render(request, 'dashboard/superadmin_profil.html')

def dashboard_superadmin_rapport(request):
    if request.method == 'POST':
        return _handle_superadmin_export(request)
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    return render(request, 'dashboard/superadmin_rapport.html', {
        'default_start': today - timedelta(days=30),
        'default_end': today,
        'today': today,
    })

def _handle_superadmin_export(request):
    """Handle export POST from superadmin dashboard — requires valid JWT for superadmin role."""
    from django.http import HttpResponse, HttpResponseForbidden
    from datetime import datetime
    from django.utils import timezone

    user = _jwt_user_from_post(request)
    if user is None or not (user.is_staff or getattr(user, 'role', '') == 'superadmin'):
        return HttpResponseForbidden('Accès refusé.')

    export_format = request.POST.get('format', 'pdf')
    start_date_str = request.POST.get('start_date')
    end_date_str   = request.POST.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date   = datetime.strptime(end_date_str,   '%Y-%m-%d').date()
    except (ValueError, TypeError):
        today = timezone.now().date()
        from datetime import timedelta
        start_date = today - timedelta(days=30)
        end_date   = today

    from apps.analytics.report_generators import ReportDataGenerator
    gen = ReportDataGenerator(start_date, end_date)
    report_data = {
        'kpis':              gen.get_kpis(),
        'daily_sales':       gen.get_daily_sales(),
        'monthly_sales':     gen.get_monthly_sales(),
        'orders_by_status':  gen.get_orders_by_status(),
        'payments_by_type':  gen.get_payments_by_type(),
        'top_products':      gen.get_top_products(),
        'top_producers':     gen.get_top_producers(),
        'top_buyers':        gen.get_top_buyers(),
        'sales_by_category': list(gen.get_sales_by_category()),
    }

    fname_base = f"rapport_maket_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

    if export_format == 'csv':
        from apps.analytics.views import ExportDashboardView
        view = ExportDashboardView()
        return view._export_csv(report_data, start_date, end_date)
    elif export_format == 'xlsx':
        from apps.analytics.views import ExportDashboardView
        view = ExportDashboardView()
        return view._export_xlsx(report_data, start_date, end_date)
    else:
        from apps.analytics.report_generators import PDFReportGenerator
        try:
            pdf_gen = PDFReportGenerator(report_data)
            buf = pdf_gen.generate()
            response = HttpResponse(buf.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{fname_base}.pdf"'
            return response
        except Exception as e:
            from django.http import HttpResponseServerError
            return HttpResponseServerError(f'Erreur PDF: {e}')


def dashboard_producteur_rapport(request):
    if request.method == 'POST':
        return _handle_producteur_export(request)
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    return render(request, 'dashboard/producteur_rapport.html', {
        'default_start': today - timedelta(days=30),
        'default_end': today,
        'today': today,
    })

def _handle_producteur_export(request):
    """Handle export POST from producteur dashboard — requires valid JWT for producteur role."""
    from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
    from datetime import datetime
    from django.utils import timezone

    user = _jwt_user_from_post(request)
    if user is None:
        return HttpResponseForbidden('Accès refusé.')

    try:
        from apps.accounts.models import Producteur
        producteur = Producteur.objects.get(user=user)
    except Exception:
        return HttpResponseForbidden('Compte producteur introuvable.')

    export_format = request.POST.get('format', 'pdf')
    start_date_str = request.POST.get('start_date')
    end_date_str   = request.POST.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date   = datetime.strptime(end_date_str,   '%Y-%m-%d').date()
    except (ValueError, TypeError):
        today = timezone.now().date()
        from datetime import timedelta
        start_date = today - timedelta(days=30)
        end_date   = today

    from apps.analytics.report_generators import ProducteurReportDataGenerator
    gen = ProducteurReportDataGenerator(producteur, start_date, end_date)
    report_data = {
        'kpis':           gen.get_kpis(),
        'monthly_sales':  gen.get_revenue_by_month(),
        'orders_by_status': gen.get_orders_by_status(),
        'top_products':   gen.get_top_products(),
        'stock_actuel':   gen.get_stock_actuel(),
        'recent_orders':  gen.get_recent_orders(),
        'producteur':     producteur,
    }

    fname_base = f"rapport_producteur_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

    if export_format == 'csv':
        from io import StringIO
        import csv
        buf = StringIO()
        w = csv.writer(buf)
        kpis = report_data['kpis']
        w.writerow(['RAPPORT MAKÈT PEYIZAN — PRODUCTEUR'])
        w.writerow([f"Producteur: {producteur.user.get_full_name()}"])
        w.writerow([f"Période: {kpis.get('periode_debut','')} au {kpis.get('periode_fin','')}"])
        w.writerow([])
        w.writerow(['KPIs'])
        for k, v in kpis.items():
            w.writerow([k, v])
        w.writerow([])
        w.writerow(['CA Mensuel', 'Date', 'CA (HTG)'])
        for row in report_data['monthly_sales']:
            w.writerow([row.get('mois',''), row.get('ca', 0)])
        w.writerow([])
        w.writerow(['Top Produits', 'Produit', 'Quantité', 'CA'])
        for row in report_data['top_products']:
            w.writerow([row.get('produit__nom',''), row.get('total_vendu',0), row.get('ca',0)])
        from django.http import HttpResponse
        response = HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{fname_base}.csv"'
        return response
    else:
        from apps.analytics.report_generators import ProducteurPDFReportGenerator
        try:
            pdf_gen = ProducteurPDFReportGenerator(report_data)
            buf = pdf_gen.generate()
            response = HttpResponse(buf.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{fname_base}.pdf"'
            return response
        except Exception as e:
            return HttpResponseServerError(f'Erreur PDF: {e}')


def _jwt_user_from_post(request):
    """Decode JWT token from POST field '_jwt' and return the corresponding user, or None."""
    token_str = request.POST.get('_jwt', '').strip()
    if not token_str:
        return None
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_str)
        user_id = token['user_id']
        from apps.accounts.models import CustomUser
        return CustomUser.objects.get(pk=user_id, is_active=True)
    except Exception:
        return None


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
