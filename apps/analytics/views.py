from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from datetime import timedelta, date


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'kpis':                    self._get_kpis(),
            'ventes_par_jour':         self._get_ventes_par_jour(),
            'ventes_par_mois':         self._get_ventes_par_mois(),
            'commandes_par_statut':    self._get_commandes_par_statut(),
            'paiements_par_type':      self._get_paiements_par_type(),
            'top_produits':            self._get_top_produits(),
            'top_producteurs':         self._get_top_producteurs(),
            'top_acheteurs':           self._get_top_acheteurs(),
            'producteurs_par_dept':    self._get_producteurs_par_departement(),
            'ventes_par_categorie':    self._get_ventes_par_categorie(),
            'alertes_stock':           self._get_alertes_stock(),
            'collectes_a_venir':       self._get_collectes_a_venir(),
            'collectes_en_retard':     self._get_collectes_en_retard(),
            'dernieres_commandes':     self._get_dernieres_commandes(),
            'derniers_producteurs':    self._get_derniers_producteurs(),
            'paiements_en_attente':    self._get_paiements_en_attente(),
            'today':                   timezone.now(),
        })
        return ctx

    def _get_kpis(self):
        from apps.accounts.models import CustomUser, Producteur, Acheteur
        from apps.catalog.models import Produit
        from apps.orders.models import Commande
        from apps.payments.models import Paiement
        from apps.stock.models import AlerteStock

        today = timezone.now().date()
        debut_mois = today.replace(day=1)

        total_commandes = Commande.objects.count()
        commandes_mois  = Commande.objects.filter(created_at__date__gte=debut_mois).count()

        ca_total = Commande.objects.filter(statut_paiement='paye').aggregate(total=Sum('total'))['total'] or 0
        ca_mois  = Commande.objects.filter(statut_paiement='paye', created_at__date__gte=debut_mois).aggregate(total=Sum('total'))['total'] or 0

        return {
            'total_utilisateurs':   CustomUser.objects.filter(is_active=True).count(),
            'total_producteurs':    Producteur.objects.filter(statut='actif').count(),
            'total_acheteurs':      Acheteur.objects.count(),
            'total_produits':       Produit.objects.filter(is_active=True).count(),
            'total_commandes':      total_commandes,
            'commandes_mois':       commandes_mois,
            'ca_total':             ca_total,
            'ca_mois':              ca_mois,
            'alertes_nouvelles':    AlerteStock.objects.filter(statut='nouvelle').count(),
            'paiements_en_attente': Paiement.objects.filter(statut__in=['initie', 'en_attente', 'soumis']).count(),
        }

    def _get_ventes_par_jour(self):
        from apps.orders.models import Commande
        today = timezone.now().date()
        data  = []
        for i in range(29, -1, -1):
            jour = today - timedelta(days=i)
            ca   = Commande.objects.filter(created_at__date=jour, statut_paiement='paye').aggregate(total=Sum('total'))['total'] or 0
            data.append({'date': jour.strftime('%d/%m'), 'ca': float(ca)})
        return data

    def _get_ventes_par_mois(self):
        from apps.orders.models import Commande
        today = timezone.now().date()
        data  = []
        for i in range(11, -1, -1):
            mois = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            ca   = Commande.objects.filter(
                created_at__year=mois.year,
                created_at__month=mois.month,
                statut_paiement='paye'
            ).aggregate(total=Sum('total'))['total'] or 0
            data.append({'mois': mois.strftime('%b %Y'), 'ca': float(ca)})
        return data

    def _get_commandes_par_statut(self):
        from apps.orders.models import Commande
        statuts = Commande.objects.values('statut').annotate(count=Count('id')).order_by()
        return [{'statut': s['statut'], 'count': s['count']} for s in statuts]

    def _get_paiements_par_type(self):
        from apps.payments.models import Paiement
        types = Paiement.objects.filter(statut='confirme').values('type_paiement').annotate(
            count=Count('id'), total=Sum('montant')
        ).order_by('-total')
        return list(types)

    def _get_top_produits(self):
        from apps.orders.models import CommandeDetail
        return CommandeDetail.objects.values(
            'produit__nom', 'produit__slug'
        ).annotate(
            total_vendu=Sum('quantite'),
            ca=Sum('sous_total')
        ).order_by('-ca')[:10]

    def _get_top_producteurs(self):
        from apps.accounts.models import Producteur
        return Producteur.objects.annotate(
            nb_cmd=Count('commandes_recues'),
            ca=Sum('commandes_recues__total', filter=Q(commandes_recues__statut_paiement='paye'))
        ).order_by('-ca')[:10]

    def _get_top_acheteurs(self):
        from apps.accounts.models import Acheteur
        return Acheteur.objects.annotate(
            nb_cmd=Count('commandes'),
            depense=Sum('commandes__total', filter=Q(commandes__statut_paiement='paye'))
        ).order_by('-depense')[:10]

    def _get_producteurs_par_departement(self):
        from apps.accounts.models import Producteur
        return list(Producteur.objects.filter(statut='actif').values('departement').annotate(count=Count('id')).order_by('-count'))

    def _get_ventes_par_categorie(self):
        from apps.orders.models import CommandeDetail
        return list(CommandeDetail.objects.values('produit__categorie__nom').annotate(
            ca=Sum('sous_total'), nb=Count('id')
        ).order_by('-ca')[:8])

    def _get_alertes_stock(self):
        from apps.stock.models import AlerteStock
        return AlerteStock.objects.filter(
            statut__in=['nouvelle', 'vue']
        ).select_related('produit', 'produit__producteur__user').order_by('-created_at')[:15]

    def _get_collectes_a_venir(self):
        from apps.collectes.models import Collecte
        today = timezone.now().date()
        limit = today + timedelta(days=14)
        return Collecte.objects.filter(
            statut='planifiee',
            date_planifiee__range=[today, limit]
        ).select_related('zone', 'point_collecte', 'collecteur').order_by('date_planifiee')[:10]

    def _get_collectes_en_retard(self):
        from apps.collectes.models import Collecte
        today = timezone.now().date()
        return Collecte.objects.filter(
            statut__in=['planifiee', 'en_cours'],
            date_planifiee__lt=today
        ).select_related('zone', 'collecteur').order_by('date_planifiee')

    def _get_dernieres_commandes(self):
        from apps.orders.models import Commande
        return Commande.objects.select_related(
            'acheteur__user', 'producteur__user'
        ).order_by('-created_at')[:15]

    def _get_derniers_producteurs(self):
        from apps.accounts.models import Producteur
        return Producteur.objects.filter(
            statut='en_attente'
        ).select_related('user').order_by('-created_at')[:10]

    def _get_paiements_en_attente(self):
        from apps.payments.models import Paiement
        return Paiement.objects.filter(
            statut__in=['soumis', 'en_attente']
        ).select_related(
            'commande__acheteur__user', 'effectue_par'
        ).order_by('-created_at')[:15]
