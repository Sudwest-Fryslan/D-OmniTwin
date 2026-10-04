/*
 * Favorieten en laatste kaartpositie van de ingelogde gebruiker (#258).
 *
 * Alleen ingelogd (meta omnitwin-ingelogd = 1): /api/mijn/favorieten en /api/mijn/instellingen.
 * Anoniem verandert er niets (geen opslag van de kaartpositie, zoals voorheen).
 * - Favoriet = de huidige gebiedenselectie met een naam; terughalen via dezelfde weg als de chat
 *   (CHAT_GEBIEDEN_TONEN: gebiedstype, selectie en inzoomen).
 * - Kaartpositie: bij openen hersteld (app.js: state.herstelPositie / zetKaartPositie), bewaard
 *   als de kaart een tijdje stilstaat en bij het verlaten van de pagina.
 */
(function () {
  'use strict';

  const API = '/api/mijn';
  const $ = (id) => document.getElementById(id);
  let laatstBewaard = '';
  let favorieten = [];

  function ingelogd() {
    const m = document.querySelector('meta[name="omnitwin-ingelogd"]');
    return !!m && m.content === '1';
  }

  async function api(pad, opties = {}) {
    const res = await fetch(`${API}${pad}`, {
      credentials: 'same-origin',
      headers: opties.body ? { 'Content-Type': 'application/json' } : {},
      ...opties,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  }

  function melding(tekst, fout = false) {
    const el = $('mijn-melding');
    if (!el) return;
    el.textContent = tekst;
    el.classList.toggle('mijn-fout', fout);
  }

  // ── Kaartpositie ──────────────────────────────────────────────────────────

  function huidigePositie() {
    const v = (window.state || {}).currentViewState;
    if (!v || typeof v.longitude !== 'number') return null;
    const r = (x, n) => Math.round(x * 10 ** n) / 10 ** n;
    return { longitude: r(v.longitude, 6), latitude: r(v.latitude, 6), zoom: r(v.zoom, 3),
             pitch: r(v.pitch || 0, 1), bearing: r(v.bearing || 0, 1) };
  }

  function bewaarPositie(bijVerlaten) {
    const p = huidigePositie();
    if (!p) return;
    const sleutel = JSON.stringify(p);
    if (sleutel === laatstBewaard) return;
    laatstBewaard = sleutel;
    // keepalive: het verzoek gaat ook door als de pagina sluit
    fetch(`${API}/instellingen`, {
      method: 'PUT', credentials: 'same-origin', keepalive: !!bijVerlaten,
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kaartpositie: p }),
    }).catch(() => { laatstBewaard = ''; });
  }

  async function herstelPositie() {
    try {
      const data = await api('/instellingen');
      const p = data && data.kaartpositie;
      if (!p) return;
      laatstBewaard = JSON.stringify(p);
      const s = window.state;
      if (typeof window.zetKaartPositie === 'function') window.zetKaartPositie(p);
      // Nog geen kaartdata: app.js zoomt dan bij de eerste kaart niet in, maar houdt deze positie
      if (!s.initialDataLoaded) s.herstelPositie = p;
    } catch (e) { /* geen instellingen: gewoon de standaard */ }
  }

  // ── Favorieten ────────────────────────────────────────────────────────────

  function selectieIds() {
    return [...((window.state || {}).selectedGebiedIds || [])];
  }

  function tekenFavorieten() {
    const lijst = $('mijn-favorieten-lijst');
    if (!lijst) return;
    lijst.replaceChildren();
    $('mijn-favorieten-leeg').hidden = favorieten.length > 0;
    favorieten.forEach((f) => {
      const li = document.createElement('li');
      li.className = 'mijn-favoriet';
      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'mijn-favoriet-open';
      open.textContent = `${f.naam} (${f.gebiedIds.length})`;
      open.title = `Selecteer de ${f.gebiedIds.length} gebieden van "${f.naam}"`;
      open.addEventListener('click', () => openFavoriet(f));
      const weg = document.createElement('button');
      weg.type = 'button';
      weg.className = 'mijn-favoriet-weg';
      weg.textContent = '✕';
      weg.setAttribute('aria-label', `Favoriet ${f.naam} verwijderen`);
      weg.title = 'Verwijderen';
      weg.addEventListener('click', () => verwijder(f));
      li.append(open, weg);
      lijst.appendChild(li);
    });
  }

  async function laadFavorieten() {
    try {
      favorieten = (await api('/favorieten')).favorieten || [];
      tekenFavorieten();
    } catch (e) {
      melding('Favorieten zijn niet te laden.', true);
    }
  }

  async function bewaarSelectie() {
    const ids = selectieIds();
    const invoer = $('mijn-favoriet-naam');
    const naam = (invoer.value || '').trim();
    if (!ids.length) { melding('Selecteer eerst gebieden op de kaart.', true); return; }
    if (!naam) { melding('Geef de selectie een naam.', true); invoer.focus(); return; }
    try {
      const f = await api('/favorieten', {
        method: 'POST',
        body: JSON.stringify({ naam, gebiedIds: ids, gebiedstypeId: window.state.currentGebiedstype || null }),
      });
      invoer.value = '';
      melding(`Bewaard: ${f.naam} (${f.gebiedIds.length} gebieden)`);
      await laadFavorieten();
    } catch (e) {
      melding(e.message, true);
    }
  }

  async function verwijder(f) {
    try {
      await api(`/favorieten/${encodeURIComponent(f.id)}`, { method: 'DELETE' });
      melding(`Verwijderd: ${f.naam}`);
      await laadFavorieten();
    } catch (e) {
      melding(e.message, true);
    }
  }

  function openFavoriet(f) {
    window.EventBus.emit('CHAT_GEBIEDEN_TONEN', { ids: f.gebiedIds, gebiedstypeId: f.gebiedstypeId, zoom: true });
    melding(`Geselecteerd: ${f.naam}`);
  }

  function werkKnopBij() {
    const knop = $('mijn-bewaar-selectie');
    if (knop) knop.disabled = selectieIds().length === 0;
    // Knop in de selectiebadge: naar het favorietenblok
    const badge = document.getElementById('selection-badge');
    if (badge && !document.getElementById('selection-bewaar-btn')) {
      const b = document.createElement('button');
      b.type = 'button';
      b.id = 'selection-bewaar-btn';
      b.className = 'selection-badge-btn';
      b.textContent = '☆ Bewaar';
      b.title = 'Bewaar deze selectie als favoriet';
      b.addEventListener('click', () => {
        const knopInfo = document.querySelector('.tab-button[data-panel="info"]');
        if (knopInfo && !knopInfo.classList.contains('active')) knopInfo.click();
        $('mijn-favoriet-naam').focus();
      });
      const wis = document.getElementById('selection-clear-btn');
      badge.insertBefore(b, wis || null);
    }
  }

  function init() {
    const blok = $('mijn-favorieten');
    if (!blok || !window.EventBus || !ingelogd()) return;
    blok.hidden = false;
    $('mijn-bewaar-selectie').addEventListener('click', bewaarSelectie);
    $('mijn-favoriet-naam').addEventListener('keydown', (e) => { if (e.key === 'Enter') bewaarSelectie(); });
    window.EventBus.on('SELECTIE_GEWIJZIGD', werkKnopBij);
    werkKnopBij();
    laadFavorieten();
    herstelPositie();
    // Kaartpositie: elke 15 s als hij veranderd is, en bij het verlaten van de pagina
    setInterval(() => { if (document.visibilityState === 'visible') bewaarPositie(false); }, 15000);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') bewaarPositie(true); });
    window.addEventListener('pagehide', () => bewaarPositie(true));
    window.mijnVoorkeuren = { bewaarPositie, laadFavorieten };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
