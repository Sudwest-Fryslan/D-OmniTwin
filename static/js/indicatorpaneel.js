/*
 * Indicatorpaneel (#258): beschrijving, eenheid, bron/jaargang/licentie en gemeentegemiddelde van de
 * gekozen indicator, een staafdiagram van de geselecteerde gebieden en een CSV-export.
 *
 * De gegevens komen van GET /api/gebiedsmonitor/indicatorpaneel; de CSV van dezelfde route met .csv.
 * De server bouwt beide, zodat paneel en export dezelfde onderdrukking hebben (n onder de drempel:
 * waarde leeg, status "onderdrukt"). Volgt de kaart via de EventBus: KAARTDATA_GELADEN (indicator of
 * jaar gewijzigd) en SELECTIE_GEWIJZIGD. Kleuren uit de thema-tokens (themaKleur uit kompas.js).
 */
(function () {
  'use strict';

  const API = '/api/gebiedsmonitor/indicatorpaneel';
  let jaar = null;
  let volgnummer = 0;
  let grafiek = null;
  let timer = null;

  const $ = (id) => document.getElementById(id);
  const kleur = (naam, terugval) =>
    (typeof window.themaKleur === 'function' ? window.themaKleur(naam, terugval) : null)
    || getComputedStyle(document.documentElement).getPropertyValue(naam).trim() || terugval;

  function getal(waarde) {
    if (waarde === null || waarde === undefined) return '–';
    return Number(waarde).toLocaleString('nl-NL', { maximumFractionDigits: 2 });
  }

  function params(metSelectie) {
    const s = window.state || {};
    const p = new URLSearchParams({ indicator_uuid: s.currentIndicator });
    const ids = [...(s.selectedGebiedIds || [])];
    if (metSelectie && ids.length) p.set('gebied_ids', ids.join(','));
    if (s.currentGebiedstype) p.set('gebiedstype_id', s.currentGebiedstype);
    if (s.currentGemeenteCode) p.set('gemeente_code', s.currentGemeenteCode);
    if (jaar !== null && jaar !== undefined) p.set('jaar', String(jaar));
    return p;
  }

  function toonLeeg(tekst) {
    $('indicatorpaneel-leeg').textContent = tekst;
    $('indicatorpaneel-leeg').hidden = false;
    $('indicatorpaneel-inhoud').hidden = true;
    if (grafiek) { grafiek.destroy(); grafiek = null; }
  }

  function bronTekst(b) {
    const delen = [];
    let kop = b.titel || b.bron || 'Onbekende bron';
    if (b.uitgever && !kop.includes(b.uitgever)) kop += ` (${b.uitgever})`;
    delen.push(kop);
    if (b.jaargangen && b.jaargangen.length) {
      const j = b.jaargangen;
      delen.push(j.length > 1 ? `jaargangen ${j[0]}–${j[j.length - 1]}` : `jaargang ${j[0]}`);
    }
    if (b.licentie) delen.push(`licentie ${b.licentie}`);
    return delen.join(', ');
  }

  function vulBronnen(bronnen) {
    const lijst = $('ip-bronnen');
    lijst.replaceChildren();
    if (!bronnen.length) {
      lijst.textContent = 'Niet vastgelegd';
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'ip-bronnen-lijst';
    bronnen.forEach((b) => {
      const li = document.createElement('li');
      li.textContent = bronTekst(b);
      ul.appendChild(li);
    });
    lijst.appendChild(ul);
  }

  function vulGemiddelde(gemiddelden, eenheid) {
    const el = $('ip-gemiddelde');
    el.replaceChildren();
    if (!gemiddelden.length) {
      el.textContent = 'Niet te berekenen (geen gebiedstype of gemeente)';
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'ip-bronnen-lijst';
    gemiddelden.forEach((g) => {
      const li = document.createElement('li');
      const waarde = g.waarde === null ? 'geen data' : `${getal(g.waarde)}${eenheid ? ' ' + eenheid : ''}`;
      li.textContent = `${g.gemeenteNaam}${g.jaar ? ' (' + g.jaar + ')' : ''}: ${waarde}`;
      li.title = `Ongewogen gemiddelde van ${g.aantalGebieden} gebieden van hetzelfde type, zonder waterbuurten`;
      ul.appendChild(li);
    });
    el.appendChild(ul);
  }

  function tekenGrafiek(data) {
    const gebieden = data.gebieden;
    const leeg = $('ip-grafiek-leeg');
    const wrap = $('ip-grafiek-wrap');
    const onderdrukt = gebieden.filter((g) => g.status === 'onderdrukt').length;
    const zonder = gebieden.filter((g) => g.status === 'geen-data').length;
    const melding = [];
    if (onderdrukt) melding.push(`${onderdrukt} gebied(en) onderdrukt (minder dan ${data.drempel} waarnemingen)`);
    if (zonder) melding.push(`${zonder} gebied(en) zonder data`);
    $('ip-onderdrukt').textContent = melding.join('; ');
    $('ip-onderdrukt').hidden = !melding.length;

    if (grafiek) { grafiek.destroy(); grafiek = null; }
    if (!gebieden.length || typeof Chart === 'undefined') {
      wrap.hidden = true;
      leeg.hidden = false;
      return;
    }
    wrap.hidden = false;
    leeg.hidden = true;
    wrap.style.height = `${Math.max(140, Math.min(gebieden.length, 40) * 30 + 90)}px`;

    const eenheid = data.indicator.eenheid || '';
    const gem = {};
    data.gemeentegemiddelden.forEach((g) => { gem[`${g.gemeenteCode}|${g.jaar}`] = g; });
    const gemVan = (g) => gem[`${g.gemeenteCode}|${jaar ?? g.jaar}`];
    const tekst = kleur('--text-primary', '#1e293b');
    const subtiel = kleur('--text-secondary', '#64748b');
    const lijn = kleur('--border-color', '#e2e8f0');

    grafiek = new Chart($('ip-grafiek'), {
      data: {
        labels: gebieden.map((g) => g.naam || g.id),
        datasets: [
          {
            type: 'bar',
            label: data.indicator.naam,
            data: gebieden.map((g) => g.waarde),
            backgroundColor: kleur('--primary-fill', '#1e3a8a'),
            borderRadius: 3,
            barPercentage: 0.75,
          },
          {
            type: 'line',
            label: 'Gemeentegemiddelde',
            data: gebieden.map((g) => (gemVan(g) ? gemVan(g).waarde : null)),
            borderColor: kleur('--accent-color', '#c59d00'),
            backgroundColor: kleur('--accent-color', '#c59d00'),
            borderDash: [5, 4],
            borderWidth: 2,
            pointRadius: 0,
            pointHitRadius: 8,
            stepped: 'middle',
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : undefined,
        plugins: {
          legend: { labels: { color: tekst, boxWidth: 12 } },
          tooltip: {
            backgroundColor: kleur('--tooltip-bg', '#0f172a'),
            titleColor: kleur('--tooltip-text', '#ffffff'),
            bodyColor: kleur('--tooltip-text', '#ffffff'),
            borderColor: lijn,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => {
                const g = gebieden[ctx.dataIndex];
                if (ctx.datasetIndex === 0 && g.status === 'onderdrukt') return 'onderdrukt (kleine aantallen)';
                if (ctx.raw === null || ctx.raw === undefined) return `${ctx.dataset.label}: geen data`;
                return `${ctx.dataset.label}: ${getal(ctx.raw)} ${eenheid}`.trim();
              },
            },
          },
        },
        scales: {
          x: { grid: { color: lijn }, ticks: { color: subtiel },
               title: { display: !!eenheid, text: eenheid, color: subtiel } },
          y: { grid: { display: false }, ticks: { color: tekst, font: { size: 11 }, autoSkip: false } },
        },
      },
    });
  }

  function vul(data) {
    const ind = data.indicator;
    $('indicatorpaneel-leeg').hidden = true;
    $('indicatorpaneel-inhoud').hidden = false;
    $('ip-naam').textContent = ind.naam + (jaar ? ` (${jaar})` : '');
    $('ip-beschrijving').textContent = ind.beschrijving || 'Geen beschrijving vastgelegd.';
    $('ip-eenheid').textContent = ind.eenheid || 'Niet vastgelegd';
    vulBronnen(data.bronnen);
    vulGemiddelde(data.gemeentegemiddelden, ind.eenheid);
    tekenGrafiek(data);
    const csv = $('ip-csv');
    csv.href = `${API}.csv?${params(true).toString()}`;
    const aantal = data.gebieden.length;
    $('ip-csv-uitleg').textContent = (window.state.selectedGebiedIds || new Set()).size
      ? `De ${aantal} geselecteerde gebieden en het gemeentegemiddelde`
      : `Alle ${aantal} gebieden op de kaart en het gemeentegemiddelde`;
  }

  async function laad() {
    const s = window.state || {};
    if (!s.currentIndicator) {
      toonLeeg('Kies een indicator voor de kaart om hier de gegevens te zien.');
      return;
    }
    const nr = ++volgnummer;
    const metSelectie = (s.selectedGebiedIds || new Set()).size > 0;
    try {
      // Paneel: de selectie (zonder selectie geen staafdiagram, wel het gemiddelde)
      const p = params(metSelectie);
      if (!metSelectie) p.set('gebieden', 'false');
      const res = await fetch(`${API}?${p.toString()}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (nr !== volgnummer) return; // intussen een nieuwere vraag
      vul(data);
      if (!metSelectie) {
        $('ip-grafiek-leeg').hidden = false;
        $('ip-csv-uitleg').textContent = 'Alle gebieden op de kaart en het gemeentegemiddelde';
      }
    } catch (e) {
      if (nr === volgnummer) toonLeeg('De gegevens van deze indicator zijn niet te laden.');
    }
  }

  function planLaden() {
    clearTimeout(timer);
    timer = setTimeout(laad, 200);
  }

  function init() {
    if (!$('panel-indicator') || !window.EventBus) return;
    window.EventBus.on('KAARTDATA_GELADEN', (d) => { jaar = d && d.jaar != null ? d.jaar : null; planLaden(); });
    window.EventBus.on('SELECTIE_GEWIJZIGD', planLaden);
    // Thema gewisseld: grafiek opnieuw met de nieuwe kleuren
    new MutationObserver(() => { if (grafiek) planLaden(); })
      .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    window.indicatorpaneel = { laad };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
