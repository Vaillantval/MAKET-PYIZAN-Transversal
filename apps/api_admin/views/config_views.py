from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.home.models import ContactMessage, ContactReponse, SliderImage
from apps.core.models import FAQCategorie, FAQItem
from django.utils.translation import gettext as _


# ── GET/POST/DELETE /api/admin/config/site/apk/ ─────────────────
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsSuperAdmin])
def android_apk(request):
    """Gestion du fichier APK Android affiché sur le site."""
    from apps.core.models import SiteSettings
    settings = SiteSettings.get_solo()

    if request.method == 'GET':
        apk_url = request.build_absolute_uri(settings.android_apk.url) if settings.android_apk else None
        return Response({'success': True, 'data': {
            'has_apk': bool(settings.android_apk),
            'apk_url': apk_url,
            'apk_name': settings.android_apk.name.split('/')[-1] if settings.android_apk else None,
        }})

    if request.method == 'DELETE':
        if settings.android_apk:
            settings.android_apk.delete(save=False)
            settings.android_apk = None
            settings.save(update_fields=['android_apk'])
        return Response({'success': True, 'data': {'has_apk': False, 'apk_url': None}})

    # POST — upload du fichier .apk
    apk_file = request.FILES.get('android_apk')
    if not apk_file:
        return Response({'success': False, 'error': _('Aucun fichier fourni.')}, status=400)

    # Validation extension
    filename = apk_file.name.lower()
    if not filename.endswith('.apk'):
        return Response(
            {'success': False, 'error': _('Format invalide. Seuls les fichiers .apk sont acceptés.')},
            status=400,
        )

    # Supprime l'ancien APK s'il existe
    if settings.android_apk:
        settings.android_apk.delete(save=False)

    settings.android_apk = apk_file
    settings.save(update_fields=['android_apk'])

    apk_url = request.build_absolute_uri(settings.android_apk.url)
    return Response({'success': True, 'data': {
        'has_apk': True,
        'apk_url': apk_url,
        'apk_name': apk_file.name,
    }}, status=201)


def _config_data(s, request=None):
    def img_url(f):
        if not f:
            return None
        return request.build_absolute_uri(f.url) if request else f.url

    return {
        'nom_site':            s.nom_site,
        'slogan':              s.slogan,
        'logo':                img_url(s.logo),
        'favicon':             img_url(s.favicon),
        # Hero
        'hero_badge_texte':    s.hero_badge_texte,
        'hero_titre_ligne1':   s.hero_titre_ligne1,
        'hero_titre_ligne2':   s.hero_titre_ligne2,
        'hero_sous_titre':     s.hero_sous_titre,
        # À propos
        'a_propos_titre':      s.a_propos_titre,
        'a_propos_contenu':    s.a_propos_contenu,
        'a_propos_mission':    s.a_propos_mission,
        'a_propos_vision':     s.a_propos_vision,
        'annee_fondation':     s.annee_fondation,
        # Contact
        'email_contact':       s.email_contact,
        'telephone':           s.telephone,
        'whatsapp':            s.whatsapp,
        'horaires':            s.horaires,
        'adresse':             s.adresse,
        # Réseaux sociaux
        'facebook_url':        s.facebook_url,
        'instagram_url':       s.instagram_url,
        'twitter_url':         s.twitter_url,
        'youtube_url':         s.youtube_url,
        # Footer & SEO
        'copyright_texte':     s.copyright_texte,
        'meta_description':    s.meta_description,
        'google_analytics_id': s.google_analytics_id,
        # Maintenance
        'mode_maintenance':    s.mode_maintenance,
        'message_maintenance': s.message_maintenance,
        # Applications mobiles
        'android_apk_url':     s.android_apk_url,
        'ios_app_url':         s.ios_app_url,
        # Portefeuille (wallet)
        'wallet_enabled':        s.wallet_enabled,
        'taux_commission':       str(s.taux_commission),
        'numero_moncash_depot':  s.numero_moncash_depot,
        'numero_natcash_depot':  s.numero_natcash_depot,
        'cashback_enabled':      s.cashback_enabled,
        'taux_cashback':         str(s.taux_cashback),
        'cashback_montant_max':  str(s.cashback_montant_max),
        'parrainage_enabled':    s.parrainage_enabled,
        'taux_bonus_parrainage': str(s.taux_bonus_parrainage),
        'parrainage_bonus_montant_max': str(s.parrainage_bonus_montant_max),
    }


# ── GET/PATCH /api/admin/config/site/ ───────────────────────────
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def site_config(request):
    from apps.core.models import SiteSettings
    s = SiteSettings.get_solo()

    if request.method == 'GET':
        return Response({'success': True, 'data': _config_data(s, request)})

    text_fields = [
        'nom_site', 'slogan', 'hero_badge_texte', 'hero_titre_ligne1',
        'hero_titre_ligne2', 'hero_sous_titre', 'a_propos_titre',
        'a_propos_contenu', 'a_propos_mission', 'a_propos_vision',
        'email_contact', 'telephone', 'whatsapp', 'adresse', 'horaires',
        'facebook_url', 'instagram_url', 'twitter_url', 'youtube_url',
        'copyright_texte', 'meta_description', 'google_analytics_id',
        'message_maintenance', 'android_apk_url', 'ios_app_url',
    ]
    for field in text_fields:
        if field in request.data:
            setattr(s, field, request.data[field])
    if 'annee_fondation' in request.data:
        raw = request.data['annee_fondation']
        s.annee_fondation = int(raw) if raw else None
    if 'mode_maintenance' in request.data:
        val = request.data['mode_maintenance']
        s.mode_maintenance = val not in ('false', '0', False, 'False')

    # Portefeuille (wallet) — booléens
    for f in ('wallet_enabled', 'cashback_enabled', 'parrainage_enabled'):
        if f in request.data:
            setattr(s, f, request.data[f] not in ('false', '0', False, 'False', ''))
    # Portefeuille (wallet) — taux et plafonds décimaux
    decimal_fields = [
        'taux_commission', 'taux_cashback', 'cashback_montant_max',
        'taux_bonus_parrainage', 'parrainage_bonus_montant_max',
    ]
    for f in decimal_fields:
        if f in request.data and request.data[f] not in (None, ''):
            try:
                setattr(s, f, Decimal(str(request.data[f])))
            except (InvalidOperation, ValueError):
                pass
    # Portefeuille (wallet) — numéros de dépôt hors ligne
    for f in ('numero_moncash_depot', 'numero_natcash_depot'):
        if f in request.data:
            setattr(s, f, request.data[f])

    for img_field in ('logo', 'favicon', 'login_image', 'register_image', 'a_propos_image'):
        if img_field in request.FILES:
            setattr(s, img_field, request.FILES[img_field])
    s.save()
    return Response({'success': True, 'data': _config_data(s, request)})


# ── GET/POST /api/admin/config/faq/categories/ ──────────────────
@extend_schema(operation_id='admin_faq_categories_list', tags=['Admin — Config'])
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def faq_categories(request):
    if request.method == 'POST':
        titre = request.data.get('titre', '').strip()
        if not titre:
            return Response({'success': False, 'error': _('Le titre est requis.')}, status=400)
        cat = FAQCategorie.objects.create(
            titre     = titre,
            icone     = request.data.get('icone', ''),
            ordre     = int(request.data.get('ordre', 0)),
            is_active = request.data.get('is_active', True),
        )
        return Response({'success': True, 'data': _faq_cat_data(cat)}, status=201)

    cats = FAQCategorie.objects.all().order_by('ordre')
    return Response({'success': True, 'data': [_faq_cat_data(c) for c in cats]})


def _faq_cat_data(c):
    return {
        'id':        c.pk,
        'titre':     c.titre,
        'ordre':     c.ordre,
        'is_active': c.is_active,
        'icone':     c.icone,
        'nb_items':  c.items.count(),
    }


@extend_schema(operation_id='admin_faq_categorie_detail', tags=['Admin — Config'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def faq_categorie_detail(request, pk):
    cat = get_object_or_404(FAQCategorie, pk=pk)

    if request.method == 'DELETE':
        nb = cat.items.count()
        if nb > 0:
            cat.items.all().delete()
        cat.delete()
        return Response({'success': True, 'data': {'id': pk}})

    if request.method == 'PATCH':
        if 'titre' in request.data:
            cat.titre = request.data['titre']
        if 'icone' in request.data:
            cat.icone = request.data['icone']
        if 'ordre' in request.data:
            cat.ordre = int(request.data['ordre'])
        if 'is_active' in request.data:
            val = request.data['is_active']
            cat.is_active = val if isinstance(val, bool) else str(val).lower() != 'false'
        cat.save()
        return Response({'success': True, 'data': _faq_cat_data(cat)})

    # GET — return category with its items
    items = FAQItem.objects.filter(categorie=cat, is_active=True)
    return Response({
        'success': True,
        'data': {
            **_faq_cat_data(cat),
            'items': [
                {'id': i.pk, 'question': i.question, 'reponse': i.reponse}
                for i in items
            ]
        }
    })


# ── GET/POST /api/admin/config/faq/items/ ───────────────────────
@extend_schema(operation_id='admin_faq_items_list', tags=['Admin — Config'])
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def faq_items(request):
    if request.method == 'POST':
        cat_id = request.data.get('categorie_id')
        cat    = get_object_or_404(FAQCategorie, pk=cat_id) if cat_id else None
        if not cat:
            return Response({'success': False, 'error': _('Catégorie requise.')}, status=400)
        question = request.data.get('question', '').strip()
        reponse  = request.data.get('reponse', '').strip()
        if not question or not reponse:
            return Response({'success': False, 'error': _('Question et réponse requises.')}, status=400)
        item = FAQItem.objects.create(
            categorie = cat,
            question  = question,
            reponse   = reponse,
            ordre     = int(request.data.get('ordre', 0)),
            is_active = request.data.get('is_active', True),
        )
        return Response({'success': True, 'data': _faq_item_data(item)}, status=201)

    qs = FAQItem.objects.select_related('categorie').order_by('categorie__ordre', 'ordre')
    cat_id = request.query_params.get('categorie_id')
    if cat_id:
        qs = qs.filter(categorie_id=cat_id)
    return Response({'success': True, 'data': [_faq_item_data(i) for i in qs]})


def _faq_item_data(i):
    return {
        'id':           i.pk,
        'categorie_id': i.categorie_id,
        'categorie':    i.categorie.titre,
        'question':     i.question,
        'reponse':      i.reponse,
        'ordre':        i.ordre,
        'is_active':    i.is_active,
    }


@extend_schema(operation_id='admin_faq_item_detail', tags=['Admin — Config'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def faq_item_detail(request, pk):
    i = get_object_or_404(FAQItem, pk=pk)

    if request.method == 'DELETE':
        i.delete()
        return Response({'success': True, 'data': {'id': pk}})

    if request.method == 'PATCH':
        for field in ('question', 'reponse'):
            if field in request.data:
                setattr(i, field, request.data[field])
        if 'is_active' in request.data:
            val = request.data['is_active']
            i.is_active = val if isinstance(val, bool) else str(val).lower() != 'false'
        if 'ordre' in request.data:
            i.ordre = int(request.data['ordre'])
        i.save()
        return Response({'success': True, 'data': _faq_item_data(i)})

    return Response({'success': True, 'data': _faq_item_data(i)})


# ── GET /api/admin/config/contact/ ──────────────────────────────
@extend_schema(operation_id='admin_contact_messages_list', tags=['Admin — Config'])
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def contact_messages(request):
    est_lu_param = request.query_params.get('est_lu', '')
    qs = ContactMessage.objects.prefetch_related(
        'reponses__envoye_par'
    ).order_by('-created_at')

    if est_lu_param != '':
        if est_lu_param.lower() in ('true', '1'):
            qs = qs.exclude(statut='nouveau')
        else:
            qs = qs.filter(statut='nouveau')

    qs = qs[:100]
    return Response({'success': True, 'data': [_contact_msg_data(m) for m in qs]})


def _contact_msg_data(m):
    reponses = [
        {
            'id':         r.pk,
            'contenu':    r.contenu,
            'envoye_par': r.envoye_par.get_full_name() if r.envoye_par else 'Admin',
            'envoye_le':  r.envoye_le.isoformat(),
        }
        for r in m.reponses.all()
    ]
    return {
        'id':         m.pk,
        'nom':        m.nom,
        'email':      m.email,
        'telephone':  getattr(m, 'telephone', ''),
        'sujet':      m.sujet,
        'message':    m.message,
        'statut':     m.statut,
        'est_lu':     m.statut != 'nouveau',
        'created_at': m.created_at.isoformat(),
        'reponses':   reponses,
    }


@extend_schema(operation_id='admin_contact_message_detail', tags=['Admin — Config'])
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def contact_message_detail(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': {
                'id':      msg.pk,
                'nom':     msg.nom,
                'email':   msg.email,
                'sujet':   msg.sujet,
                'message': msg.message,
                'statut':  msg.statut,
            }
        })

    STATUTS = ['nouveau', 'lu', 'repondu', 'archive']
    # Accept either {est_lu: true/false} or {statut: 'lu'} from the frontend
    if 'est_lu' in request.data:
        msg.statut = 'lu' if request.data['est_lu'] else 'nouveau'
        msg.save()
    elif 'statut' in request.data and request.data['statut'] in STATUTS:
        msg.statut = request.data['statut']
        msg.save()

    return Response({'success': True, 'data': _contact_msg_data(msg)})


# ── POST /api/admin/config/contact/<pk>/repondre/ ───────────────
@extend_schema(operation_id='admin_contact_repondre', tags=['Admin — Config'])
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def repondre_contact(request, pk):
    """Envoyer une réponse par email à un message de contact."""
    msg = get_object_or_404(ContactMessage, pk=pk)

    contenu = request.data.get('reponse', '').strip()
    if not contenu:
        return Response(
            {'success': False, 'error': _('Le contenu de la réponse est requis.')},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Créer l'enregistrement de réponse
    reponse = ContactReponse.objects.create(
        message    = msg,
        contenu    = contenu,
        envoye_par = request.user,
    )

    # Envoyer l'email via Resend (synchrone — rollback si échec)
    from apps.emails.utils import email_reponse_contact
    sent = email_reponse_contact(msg, contenu, admin=request.user)

    if not sent:
        reponse.delete()
        return Response(
            {'success': False, 'error': _("Échec de l'envoi de l'email. Réessayez.")},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Push FCM en arrière-plan (silencieux si user sans token)
    from apps.emails.tasks import task_push_reponse_contact
    task_push_reponse_contact.delay(reponse.pk)

    # Mettre le statut du message à "repondu"
    msg.statut = ContactMessage.Statut.REPONDU
    msg.save(update_fields=['statut'])

    return Response({
        'success': True,
        'data': _contact_msg_data(msg),
    }, status=status.HTTP_201_CREATED)


# ── GET/POST /api/admin/config/slider/ ──────────────────────────
def _slide_data(s, request=None):
    image_url = None
    if s.image:
        image_url = request.build_absolute_uri(s.image.url) if request else s.image.url
    return {
        'id':           s.pk,
        'titre':        s.titre,
        'sous_titre':   s.sous_titre,
        'texte_bouton': s.texte_bouton,
        'lien':         s.lien,
        'image':        image_url,
        'ordre':        s.ordre,
        'is_active':    s.is_active,
        'created_at':   s.created_at.isoformat(),
    }


@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def slider_list(request):
    if request.method == 'GET':
        slides = SliderImage.objects.all().order_by('ordre')
        return Response({'success': True, 'data': [_slide_data(s, request) for s in slides]})

    # POST — multipart (image upload)
    image = request.FILES.get('image')
    if not image:
        return Response({'success': False, 'error': _('Image requise.')}, status=400)

    slide = SliderImage.objects.create(
        image        = image,
        titre        = request.data.get('titre', ''),
        sous_titre   = request.data.get('sous_titre', ''),
        texte_bouton = request.data.get('texte_bouton', 'Découvrir'),
        lien         = request.data.get('lien', ''),
        ordre        = int(request.data.get('ordre', 0)),
        is_active    = request.data.get('is_active', 'true').lower() != 'false',
    )
    return Response({'success': True, 'data': _slide_data(slide, request)}, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def slider_detail(request, pk):
    slide = get_object_or_404(SliderImage, pk=pk)

    if request.method == 'GET':
        return Response({'success': True, 'data': _slide_data(slide, request)})

    if request.method == 'DELETE':
        slide.image.delete(save=False)
        slide.delete()
        return Response({'success': True, 'data': {'id': pk}})

    # PATCH
    for field in ('titre', 'sous_titre', 'texte_bouton', 'lien'):
        if field in request.data:
            setattr(slide, field, request.data[field])
    if 'ordre' in request.data:
        slide.ordre = int(request.data['ordre'])
    if 'is_active' in request.data:
        val = request.data['is_active']
        slide.is_active = val if isinstance(val, bool) else str(val).lower() != 'false'
    if 'image' in request.FILES:
        slide.image.delete(save=False)
        slide.image = request.FILES['image']
    slide.save()
    return Response({'success': True, 'data': _slide_data(slide, request)})
