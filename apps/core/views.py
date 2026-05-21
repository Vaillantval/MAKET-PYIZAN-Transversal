from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Prefetch
from .models import FAQCategorie, FAQItem, SiteSettings
from apps.home.models import ContactMessage
from django.utils.translation import gettext as _


def apropos(request):
    """Page À propos."""
    site = SiteSettings.get_solo()
    return render(request, 'core/apropos.html', {'site': site})


def faq(request):
    """Page FAQ."""
    active_items_qs = FAQItem.objects.filter(is_active=True).order_by('ordre')
    categories = FAQCategorie.objects.filter(
        is_active=True,
        items__is_active=True,
    ).prefetch_related(
        Prefetch('items', queryset=active_items_qs)
    ).distinct()

    if not categories.exists():
        categories = FAQCategorie.objects.filter(is_active=True).prefetch_related(
            Prefetch('items', queryset=active_items_qs)
        )

    return render(request, 'core/faq.html', {
        'categories': categories,
    })


def contact(request):
    """Page Contact + traitement du formulaire."""
    if request.method == 'POST':
        nom       = request.POST.get('nom', '').strip()
        email     = request.POST.get('email', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        sujet     = request.POST.get('sujet', '').strip()
        msg       = request.POST.get('message', '').strip()

        erreurs = []
        if not nom:
            erreurs.append('Le nom est requis.')
        if not email:
            erreurs.append("L'email est requis.")
        if not sujet:
            erreurs.append('Le sujet est requis.')
        if not msg:
            erreurs.append('Le message est requis.')

        if not erreurs:
            ContactMessage.objects.create(
                nom=nom,
                email=email,
                telephone=telephone,
                sujet=sujet,
                message=msg,
            )
            messages.success(
                request,
                'Votre message a été envoyé. Nous vous répondrons dans les plus brefs délais !'
            )
            return redirect('core:contact')
        else:
            for e in erreurs:
                messages.error(request, e)

    return render(request, 'core/contact.html')
