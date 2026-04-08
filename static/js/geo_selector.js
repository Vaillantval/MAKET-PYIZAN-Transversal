/**
 * GeoSearchSelect — Combobox cherchable pour les formulaires Makèt Peyizan
 *
 * Fonctionne avec <select> ET <input type="text">.
 * Le dropdown se positionne en portal sur document.body pour éviter
 * tout problème d'overflow/clip dans les conteneurs parents.
 */
class GeoSearchSelect {
  constructor(el, { placeholder = 'Rechercher...', disabled = false } = {}) {
    if (!el) return;
    this._el        = el;
    this._isSelect  = el.tagName === 'SELECT';
    this._items     = [];
    this._label     = '';
    this._onChange  = null;
    this._open      = false;

    this._buildDropdown();
    this._buildInput(placeholder);
    this._attachEvents();

    if (disabled) this.setDisabled(true);
  }

  /* ─── Construction du dropdown (portal sur body) ─────────────── */
  _buildDropdown() {
    const dd = document.createElement('div');
    dd.className = 'gss-dropdown';
    dd.style.cssText = [
      'position:fixed',
      'z-index:99999',
      'background:#fff',
      'border:1.5px solid #27ae60',
      'border-radius:8px',
      'box-shadow:0 4px 16px rgba(0,0,0,.14)',
      'max-height:240px',
      'overflow-y:auto',
      'display:none',
      'min-width:180px',
      'font-family:inherit',
    ].join(';');
    document.body.appendChild(dd);
    this._dropdown = dd;
  }

  /* ─── Construction du champ texte visible ────────────────────── */
  _buildInput(placeholder) {
    const el = this._el;

    if (this._isSelect) {
      /* Créer un input texte qui remplace visuellement le select */
      const txt = document.createElement('input');
      txt.type        = 'text';
      txt.placeholder = placeholder;
      txt.autocomplete = 'off';
      /* Copier les classes CSS (sauf ds-select) */
      txt.className = (el.className || '').replace(/\bds-select\b/g, '').trim();
      txt.style.cssText = 'width:100%;box-sizing:border-box;cursor:pointer;';

      /* Input caché qui garde la vraie valeur (slug) */
      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.id   = el.id;
      hidden.name = el.name;

      /* Déplacer l'id/name du select pour éviter les doublons */
      el.id   = '_gss_orig_' + el.id;
      el.name = '';
      el.style.display = 'none';

      el.parentNode.insertBefore(txt, el);
      el.parentNode.insertBefore(hidden, el);

      this._textInput = txt;
      this._hidden    = hidden;
    } else {
      /* Input texte existant : on l'utilise directement */
      el.autocomplete = 'off';
      if (placeholder) el.placeholder = placeholder;
      el.style.cursor = 'text';
      this._textInput = el;
      this._hidden    = el; /* value = label pour communes/sections */
    }
  }

  /* ─── Événements ─────────────────────────────────────────────── */
  _attachEvents() {
    const txt = this._textInput;
    const dd  = this._dropdown;

    txt.addEventListener('focus', () => {
      this._renderList(txt.value);
      this._showDropdown();
    });
    txt.addEventListener('input', () => {
      this._renderList(txt.value);
      if (!this._open) this._showDropdown();
    });
    txt.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { this._closeDropdown(); txt.blur(); }
    });

    /* Fermer si clic hors du champ et du dropdown */
    document.addEventListener('mousedown', (e) => {
      if (e.target !== txt && !dd.contains(e.target)) {
        this._closeDropdown();
      }
    });

    /* Repositionner si scroll/resize pendant que le dropdown est ouvert */
    window.addEventListener('scroll', () => {
      if (this._open) this._positionDropdown();
    }, { passive: true });
    window.addEventListener('resize', () => {
      if (this._open) this._positionDropdown();
    });
  }

  /* ─── Positionnement du dropdown sous le champ ───────────────── */
  _positionDropdown() {
    const rect = this._textInput.getBoundingClientRect();
    const dd   = this._dropdown;
    const viewH = window.innerHeight;
    const spaceBelow = viewH - rect.bottom;
    const spaceAbove = rect.top;

    /* Choisir au-dessous ou au-dessus selon l'espace disponible */
    if (spaceBelow >= 200 || spaceBelow >= spaceAbove) {
      dd.style.top    = (rect.bottom + 3) + 'px';
      dd.style.bottom = 'auto';
      dd.style.maxHeight = Math.max(120, Math.min(240, spaceBelow - 10)) + 'px';
    } else {
      dd.style.bottom = (viewH - rect.top + 3) + 'px';
      dd.style.top    = 'auto';
      dd.style.maxHeight = Math.max(120, Math.min(240, spaceAbove - 10)) + 'px';
    }

    dd.style.left  = rect.left + 'px';
    dd.style.width = rect.width + 'px';
  }

  _showDropdown() {
    this._open = true;
    this._positionDropdown();
    this._dropdown.style.display = 'block';
  }

  _closeDropdown() {
    this._open = false;
    this._dropdown.style.display = 'none';
    /* Si champ texte vide mais valeur sélectionnée → restaurer le label */
    if (this._isSelect && this._textInput.value === '' && this._hidden.value) {
      this._textInput.value = this._label;
    }
    /* Si champ texte vidé → effacer la valeur */
    if (this._textInput.value === '' && this._hidden.value !== '') {
      this._hidden.value = '';
      this._label = '';
      this._fire('');
    }
  }

  /* ─── Rendu de la liste filtrée ──────────────────────────────── */
  _renderList(text) {
    const q  = text.trim().toLowerCase();
    const dd = this._dropdown;
    dd.innerHTML = '';

    const filtered = q
      ? this._items.filter(i => i.label.toLowerCase().startsWith(q))
      : this._items;

    if (this._items.length === 0) {
      const msg = document.createElement('div');
      msg.style.cssText = 'padding:10px 14px;color:#aaa;font-size:13px;';
      msg.textContent = 'Aucun choix disponible';
      dd.appendChild(msg);
      return;
    }

    if (filtered.length === 0) {
      const msg = document.createElement('div');
      msg.style.cssText = 'padding:10px 14px;color:#aaa;font-size:13px;';
      msg.textContent = 'Aucun résultat pour "' + text + '"';
      dd.appendChild(msg);
      return;
    }

    filtered.forEach(item => {
      const row = document.createElement('div');
      row.className = 'gss-option';
      row.style.cssText = 'padding:9px 14px;cursor:pointer;font-size:14px;color:#2c3e50;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      row.textContent = item.label;
      row.addEventListener('mouseenter', () => { row.style.background = '#f0faf4'; });
      row.addEventListener('mouseleave', () => { row.style.background = ''; });
      row.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this._selectItem(item);
      });
      dd.appendChild(row);
    });
  }

  _selectItem(item) {
    this._textInput.value = item.label;
    this._hidden.value    = item.value;
    this._label           = item.label;
    this._dropdown.style.display = 'none';
    this._open = false;
    this._fire(item.value);
  }

  _fire(val) {
    if (this._onChange) this._onChange(val);
    this._hidden.dispatchEvent(new Event('change', { bubbles: true }));
  }

  /* ─── API publique ────────────────────────────────────────────── */

  /** Remplacer la liste d'items et réinitialiser la valeur */
  setItems(items /* [{value, label}] */) {
    this._items           = items;
    this._hidden.value    = '';
    this._textInput.value = '';
    this._label           = '';
  }

  /** Ajouter des items sans effacer la sélection courante */
  addItems(items) {
    this._items = items;
  }

  setDisabled(flag) {
    this._textInput.disabled = flag;
    this._textInput.style.opacity = flag ? '0.55' : '1';
    this._textInput.style.cursor  = flag ? 'not-allowed' : (this._isSelect ? 'pointer' : 'text');
    if (flag) this._closeDropdown();
  }

  setPlaceholder(text) {
    this._textInput.placeholder = text;
  }

  /** Définir la valeur + le label affichés sans passer par la sélection */
  setValue(value, label) {
    this._hidden.value    = value;
    this._textInput.value = label || value;
    this._label           = label || value;
  }

  /** Vider la sélection */
  clear() {
    this._hidden.value    = '';
    this._textInput.value = '';
    this._label           = '';
  }

  get value()  { return this._hidden ? this._hidden.value : ''; }
  get label()  { return this._label; }
  onChange(fn) { this._onChange = fn; }

  destroy() {
    if (this._dropdown && this._dropdown.parentNode) {
      this._dropdown.parentNode.removeChild(this._dropdown);
    }
  }
}


/* ══════════════════════════════════════════════════════════════════
   GeoSelector — Cascade : Département → Commune → Section Communale
   ══════════════════════════════════════════════════════════════════ */
class GeoSelector {
  /**
   * @param {object} opts
   * @param {HTMLElement} opts.deptEl      – <select> département
   * @param {HTMLElement} opts.communeEl   – <input> commune
   * @param {HTMLElement} [opts.sectionEl] – <input> section communale (optionnel)
   * @param {string}      [opts.baseUrl]   – ex. '/api/geo'
   */
  constructor({ deptEl, communeEl, sectionEl = null, baseUrl = '/api/geo' }) {
    if (!deptEl || !communeEl) {
      console.warn('GeoSelector: deptEl et communeEl sont requis.');
      return;
    }

    this._base = baseUrl;

    this._dept    = new GeoSearchSelect(deptEl, { placeholder: 'Choisir un département...' });
    this._commune = new GeoSearchSelect(communeEl, {
      placeholder: 'Choisir d\'abord un département...',
      disabled: true,
    });
    this._section = sectionEl
      ? new GeoSearchSelect(sectionEl, {
          placeholder: 'Choisir d\'abord une commune...',
          disabled: true,
        })
      : null;

    /* Cascade : département → communes */
    this._dept.onChange(slug => {
      this._commune.setItems([]);
      this._commune.setDisabled(true);
      this._commune.setPlaceholder('Choisir d\'abord un département...');
      if (this._section) {
        this._section.setItems([]);
        this._section.setDisabled(true);
        this._section.setPlaceholder('Choisir d\'abord une commune...');
      }
      if (slug) {
        this._commune.setPlaceholder('Chargement…');
        this._loadCommunes(slug);
      }
    });

    /* Cascade : commune → sections */
    if (this._section) {
      this._commune.onChange(nom => {
        this._section.setItems([]);
        this._section.setDisabled(true);
        const dept = this._dept.value;
        if (nom && dept) {
          this._section.setPlaceholder('Chargement…');
          this._loadSections(dept, nom);
        }
      });
    }

    /* Charger les départements au démarrage */
    this._loadDepts();
  }

  async _loadDepts() {
    try {
      const r = await fetch(`${this._base}/departements/`);
      const j = await r.json();
      if (!j.success) return;
      this._dept.addItems(j.data.map(d => ({ value: d.slug, label: d.nom })));
    } catch (e) { console.error('GeoSelector _loadDepts:', e); }
  }

  async _loadCommunes(deptSlug) {
    try {
      const r = await fetch(`${this._base}/communes/?dept=${encodeURIComponent(deptSlug)}`);
      const j = await r.json();
      if (!j.success) return;
      this._commune.setItems(j.data.map(c => ({ value: c.nom, label: c.nom })));
      this._commune.setDisabled(false);
      this._commune.setPlaceholder('Rechercher une commune…');
    } catch (e) { console.error('GeoSelector _loadCommunes:', e); }
  }

  async _loadSections(deptSlug, communeNom) {
    try {
      const url = `${this._base}/sections/?dept=${encodeURIComponent(deptSlug)}&commune=${encodeURIComponent(communeNom)}`;
      const r   = await fetch(url);
      const j   = await r.json();
      if (!j.success) return;
      this._section.setItems(
        j.data.sections_communales.map(s => ({ value: s, label: s }))
      );
      this._section.setDisabled(false);
      this._section.setPlaceholder('Rechercher une section…');
    } catch (e) { console.error('GeoSelector _loadSections:', e); }
  }

  /**
   * Pré-remplir les champs (mode édition).
   * Charge les communes/sections si nécessaire.
   */
  async prefill({ deptSlug, communeNom, sectionNom } = {}) {
    if (!deptSlug) {
      this.reset();
      return;
    }

    /* S'assurer que les depts sont chargés */
    if (this._dept._items.length === 0) await this._loadDepts();

    const deptItem = this._dept._items.find(i => i.value === deptSlug);
    if (deptItem) {
      this._dept.setValue(deptSlug, deptItem.label);
    } else {
      this._dept.setValue(deptSlug, deptSlug);
    }

    if (communeNom) {
      await this._loadCommunes(deptSlug);
      this._commune.setValue(communeNom, communeNom);
    }

    if (sectionNom && this._section) {
      await this._loadSections(deptSlug, communeNom || '');
      this._section.setValue(sectionNom, sectionNom);
    }
  }

  /** Remettre tous les champs à zéro */
  reset() {
    this._dept.clear();
    this._commune.setItems([]);
    this._commune.setDisabled(true);
    this._commune.setPlaceholder('Choisir d\'abord un département...');
    if (this._section) {
      this._section.setItems([]);
      this._section.setDisabled(true);
      this._section.setPlaceholder('Choisir d\'abord une commune...');
    }
  }

  /* Accès aux instances GeoSearchSelect si nécessaire */
  get dept()    { return this._dept; }
  get commune() { return this._commune; }
  get section() { return this._section; }
}
