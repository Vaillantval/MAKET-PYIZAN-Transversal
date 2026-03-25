def site_settings(request):
    """
    Injecte les paramètres du site dans tous les templates.
    Disponible via {{ site_settings.nom_site }}, {{ site_settings.logo }}, etc.
    """
    try:
        from apps.core.models import SiteSettings
        settings_obj = SiteSettings.get_solo()
    except Exception:
        settings_obj = None
    return {'site_settings': settings_obj}
