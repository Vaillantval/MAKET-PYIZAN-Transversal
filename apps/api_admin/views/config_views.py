from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.home.models import SiteConfig, FAQCategorie, FAQItem, ContactMessage, ContactReponse, SliderImage


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
        return Response({'success': False, 'error': 'Aucun fichier fourni.'}, status=400)

    # Validation extension
    filename = apk_file.name.lower()
    if not filename.endswith('.apk'):
        return Response(
            {'success': False, 'error': 'Format invalide. Seuls les fichiers .apk sont acceptés.'},
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


def _config_data(c):
    return {
        'nom_site':        c.nom_site,
        'slogan':          c.slogan,
        'email_contact':   c.email_contact,
        'telephone':       c.telephone,
        'adresse':         c.adresse,
        'facebook_url':    c.facebook_url,
        'instagram_url':   c.instagram_url,
        'whatsapp_numero': c.whatsapp_numero,
    }


# ── GET/PATCH /api/admin/config/site/ ───────────────────────────
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def site_config(request):
    config = SiteConfig.get_config()

    if request.method == 'GET':
        return Response({'success': True, 'data': _config_data(config)})

    for field in [
        'nom_site', 'slogan', 'email_contact', 'telephone',
        'adresse', 'facebook_url', 'instagram_url', 'whatsapp_numero'
    ]:
        if field in request.data:
            setattr(config, field, request.data[field])
    config.save()
    return Response({'success': True, 'data': _config_data(config)})


# ── GET/POST /api/admin/config/faq/categories/ ──────────────────
@extend_schema(operation_id='admin_faq_categories_list', tags=['Admin — Config'])
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def faq_categories(request):
    if request.method == 'POST':
        titre = request.data.get('titre', '').strip()
        if not titre:
            return Response({'success': False, 'error': 'Le titre est requis.'}, status=400)
        cat = FAQCategorie.objects.create(
            titre     = titre,
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
        'icone':     '',
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
            return Response({'success': False, 'error': 'Catégorie requise.'}, status=400)
        question = request.data.get('question', '').strip()
        reponse  = request.data.get('reponse', '').strip()
        if not question or not reponse:
            return Response({'success': False, 'error': 'Question et réponse requises.'}, status=400)
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
    qs = ContactMessage.objects.order_by('-created_at')[:100]
    data = [_contact_msg_data(m) for m in qs]
    if est_lu_param != '':
        want_lu = est_lu_param.lower() in ('true', '1')
        data = [m for m in data if m['est_lu'] == want_lu]
    return Response({'success': True, 'data': data})


def _contact_msg_data(m):
    reponses = [
        {
            'id':         r.pk,
            'contenu':    r.contenu,
            'envoye_par': r.envoye_par.get_full_name() if r.envoye_par else 'Admin',
            'envoye_le':  r.envoye_le.isoformat(),
        }
        for r in m.reponses.select_related('envoye_par').all()
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
            {'success': False, 'error': 'Le contenu de la réponse est requis.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Créer l'enregistrement de réponse
    reponse = ContactReponse.objects.create(
        message    = msg,
        contenu    = contenu,
        envoye_par = request.user,
    )

    # Envoyer l'email via Resend
    from apps.emails.utils import email_reponse_contact
    from apps.emails.fcm_notifications import push_reponse_contact
    sent = email_reponse_contact(msg, contenu, admin=request.user)

    if not sent:
        reponse.delete()
        return Response(
            {'success': False, 'error': "Échec de l'envoi de l'email. Réessayez."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Notification FCM (silencieuse si user introuvable ou sans token)
    push_reponse_contact(msg, reponse)

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
        return Response({'success': False, 'error': 'Image requise.'}, status=400)

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
