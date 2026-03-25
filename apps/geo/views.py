import json
import os
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

# Charger les données une seule fois au démarrage
_GEO_DATA = None


def _get_geo_data():
    global _GEO_DATA
    if _GEO_DATA is None:
        data_path = os.path.join(
            os.path.dirname(__file__),
            'data', 'haiti_geo.json'
        )
        with open(data_path, 'r', encoding='utf-8') as f:
            _GEO_DATA = json.load(f)
    return _GEO_DATA


def _json_ok(data):
    return JsonResponse({'success': True, 'data': data}, json_dumps_params={'ensure_ascii': False})

def _json_err(message, status=400):
    return JsonResponse({'success': False, 'error': message}, status=status)


# ── GET /api/geo/departements/ ──────────────────────────────────
@require_GET
@cache_page(60 * 60 * 24)
def departements(request):
    data   = _get_geo_data()
    result = [
        {'nom': d['nom'], 'slug': d['slug'], 'capitale': d['capitale']}
        for d in data['departements']
    ]
    return _json_ok(result)


# ── GET /api/geo/arrondissements/?dept=<slug> ───────────────────
@require_GET
@cache_page(60 * 60 * 24)
def arrondissements(request):
    dept_slug = request.GET.get('dept', '').strip().lower()
    if not dept_slug:
        return _json_err("Paramètre 'dept' requis.")

    data = _get_geo_data()
    dept = next((d for d in data['departements'] if d['slug'] == dept_slug), None)
    if not dept:
        return _json_err(f"Département '{dept_slug}' introuvable.", 404)

    result = [{'nom': a['nom']} for a in dept['arrondissements']]
    return _json_ok(result)


# ── GET /api/geo/communes/?dept=<slug>[&arrond=<nom>] ──────────
@require_GET
@cache_page(60 * 60 * 24)
def communes(request):
    dept_slug  = request.GET.get('dept', '').strip().lower()
    arrond_nom = request.GET.get('arrond', '').strip()

    if not dept_slug:
        return _json_err("Paramètre 'dept' requis.")

    data = _get_geo_data()
    dept = next((d for d in data['departements'] if d['slug'] == dept_slug), None)
    if not dept:
        return _json_err(f"Département '{dept_slug}' introuvable.", 404)

    result = []
    for arrond in dept['arrondissements']:
        if arrond_nom and arrond['nom'].lower() != arrond_nom.lower():
            continue
        for commune in arrond['communes']:
            result.append({
                'nom':            commune['nom'],
                'arrondissement': arrond['nom'],
            })

    return _json_ok(result)


# ── GET /api/geo/sections/?dept=<slug>&commune=<nom> ───────────
@require_GET
@cache_page(60 * 60 * 24)
def sections_communales(request):
    dept_slug   = request.GET.get('dept', '').strip().lower()
    commune_nom = request.GET.get('commune', '').strip()

    if not dept_slug or not commune_nom:
        return _json_err("Paramètres 'dept' et 'commune' requis.")

    data = _get_geo_data()
    dept = next((d for d in data['departements'] if d['slug'] == dept_slug), None)
    if not dept:
        return _json_err(f"Département '{dept_slug}' introuvable.", 404)

    for arrond in dept['arrondissements']:
        for commune in arrond['communes']:
            if commune['nom'].lower() == commune_nom.lower():
                return _json_ok({
                    'commune':             commune['nom'],
                    'arrondissement':      arrond['nom'],
                    'departement':         dept['nom'],
                    'sections_communales': commune['sections_communales'],
                })

    return _json_err(f"Commune '{commune_nom}' introuvable.", 404)


# ── GET /api/geo/arbre/ ─────────────────────────────────────────
@require_GET
@cache_page(60 * 60 * 24)
def arbre_complet(request):
    return _json_ok(_get_geo_data())


# ── GET /api/geo/recherche/?q=<terme> ───────────────────────────
@require_GET
def recherche(request):
    terme = request.GET.get('q', '').strip().lower()
    if len(terme) < 2:
        return _json_err("Minimum 2 caractères pour la recherche.")

    data    = _get_geo_data()
    results = []

    for dept in data['departements']:
        if terme in dept['nom'].lower():
            results.append({
                'type':  'departement',
                'nom':   dept['nom'],
                'slug':  dept['slug'],
                'label': f"{dept['nom']} (Département)",
            })

        for arrond in dept['arrondissements']:
            for commune in arrond['communes']:
                if terme in commune['nom'].lower():
                    results.append({
                        'type':           'commune',
                        'nom':            commune['nom'],
                        'arrondissement': arrond['nom'],
                        'departement':    dept['nom'],
                        'dept_slug':      dept['slug'],
                        'label':          f"{commune['nom']}, {arrond['nom']}, {dept['nom']}",
                    })

                for section in commune['sections_communales']:
                    if terme in section.lower():
                        results.append({
                            'type':           'section_communale',
                            'nom':            section,
                            'commune':        commune['nom'],
                            'arrondissement': arrond['nom'],
                            'departement':    dept['nom'],
                            'dept_slug':      dept['slug'],
                            'label':          f"{section}, {commune['nom']}, {dept['nom']}",
                        })

    return _json_ok(results[:50])
