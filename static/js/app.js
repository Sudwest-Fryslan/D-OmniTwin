/**
 * D-OmniTwin Gebiedsmonitor - Frontend Application v2.0
 * ================================================================
 * deck.gl 3D visualisatie met Vertical Tab Bar UI en Mapbox basemap
 */

// ============================================================================
// Configuration & State
// ============================================================================

const API_BASE = '/api/gebiedsmonitor';

// Application State
// #255: kaartmodus per bezoeker onthouden (alleen gemak; zonder opslag: 'waarde')
// #256: 'label' = labels A-E per gebied
const KAART_MODI = ['waarde', 'percentiel', 'label', 'uit'];
function leesKaartModus() {
    try {
        const m = localStorage.getItem('omnitwin-kaartmodus');
        return KAART_MODI.includes(m) ? m : 'waarde';
    } catch (e) {
        return 'waarde';
    }
}

/** Queryparameter voor /kaart_data: alleen percentiel en label vragen iets anders van de backend. */
function kaartModusParam() {
    return ['percentiel', 'label'].includes(state.kaartModus) ? `&modus=${state.kaartModus}` : '';
}

const state = {
    currentGebiedstype: null,
    currentIndicator: null,
    currentGemeenteCode: localStorage.getItem('omnitwin-gemeente') || '', // Default: Alle gemeenten (empty = no filter)
    deckgl: null,
    currentData: null,
    enable3D: false, // CHANGED: Default OFF
    heightScale: 10,
    showAll: false,
    // #255: kaartkleuring 'waarde' (werkelijke waarde), 'percentiel' (klasse 1-8) of 'uit'
    kaartModus: leesKaartModus(),
    activePanelId: null,
    mapboxToken: window.MAPBOX_TOKEN || null,
    mapboxStyle: window.MAPBOX_STYLE || 'mapbox://styles/mapbox/light-v10',
    currentMinValue: 0,
    currentMaxValue: 0,
    currentTheme: 'dark',
    currentViewState: { // Track camera state so 3D toggle doesn't reset it
        latitude: 53.0,
        longitude: 5.8,
        zoom: 8,
        pitch: 0,
        bearing: 0,
        minZoom: 5,
        maxZoom: 20
    },
    // Multi-Gebied Selectie (Sprint 7)
    selectedGebiedIds: new Set(),  // Set van geselecteerde gebied IDs
    // Sprint 18 Track C: Gegroepeerde selectie voor benchmark
    selectedGroepen: [],           // [ { naam: "Makkum", buurtIds: ["BU...", ...], laagId: 5 }, ... ]
    selectedLaagId: null,          // ID van de externe kaartlaag (BAG woonplaatsen) voor rapport
    // 3D BAG Panden (Sprint 12)
    bag3dData: null,               // GeoJSON van opgehaalde 3DBAG panden
    show3DBuildings: false,        // Toggle (wederzijds exclusief met enable3D)
    // Omgevingsvisie Deelgebieden (Selectielaag)
    omgevingsvisieData: null,      // GeoJSON van deelgebieden
    showOmgevingsvisieLayer: false, // Toggle zichtbaarheid overlay
    selectedDeelgebiedNaam: null,   // Naam van actief deelgebied (voor rapport-link)
    // Sprint 16: Viewport vrije-zone centreren
    initialDataLoaded: false,      // Guard: fitBounds() alleen bij nieuw data-laden
    fittedFor: null,               // gebiedstype|gemeente waarop de kaart laatst is ingezoomd
    highlightedGebiedId: null,     // Sprint 18 F3: Visuele highlight voor Top-buurten

    // Sprint 18: Externe kaartlagen (WFS, PDOK, etc.)
    externeKaartlagen: [],         // Actieve lagen definitie [{id, naam, kleur_lijn, ...}]
    externeKaartlaagData: {},      // { laag_id: { laag, geojson } }
};

// Publiceer state op window zodat chat.js en andere modules de kaartselectie kunnen lezen
window.state = state;

// Toegankelijkheid (WCAG 2.1.1): elementen met role="button" die geen echte
// <button> zijn, reageren op Enter en Spatie net als op een klik.
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = e.target;
    if (!(el instanceof HTMLElement) || el.getAttribute('role') !== 'button') return;
    if (el.tagName === 'BUTTON' || el.getAttribute('aria-disabled') === 'true') return;
    e.preventDefault();
    el.click();
});

// Backwards-compatibility: getter/setter voor selectedGebiedId (eerste geselecteerde)
Object.defineProperty(state, 'selectedGebiedId', {
    get() { return this.selectedGebiedIds.size > 0 ? [...this.selectedGebiedIds][0] : null; },
    set(val) {
        this.selectedGebiedIds.clear();
        if (val) this.selectedGebiedIds.add(val);
    }
});

/** Helper: check of een gebied geselecteerd is */
function isGebiedSelected(gebiedId) {
    return state.selectedGebiedIds.has(gebiedId);
}

/** Helper: toggle een gebied in de selectie */
function toggleGebiedSelection(gebiedId) {
    if (state.selectedGebiedIds.has(gebiedId)) {
        state.selectedGebiedIds.delete(gebiedId);
    } else {
        state.selectedGebiedIds.add(gebiedId);
    }
}

/** Helper: clear alle geselecteerde gebieden */
function clearGebiedSelection() {
    state.selectedGebiedIds.clear();
    state.selectedGroepen = [];        // Sprint 18 Track C: wis groepen
    state.selectedLaagId = null;
    state.highlightedGebiedId = null;  // Clear highlight as well
    state.selectedDeelgebiedNaam = null;
    // Track B: Herstel empty state in info-paneel
    showGebiedEmptyState();
}

/**
 * Sprint 18 Track C: Herbereken selectedGebiedIds als union van alle groepen.
 * Wordt aangeroepen na toevoegen/verwijderen van een groep.
 */
function rebuildSelectedGebiedIds() {
    state.selectedGebiedIds.clear();
    for (const groep of state.selectedGroepen) {
        for (const id of groep.buurtIds) {
            state.selectedGebiedIds.add(id);
        }
    }
    // Rebuild deelgebiedNaam uit groepen
    if (state.selectedGroepen.length === 0) {
        state.selectedDeelgebiedNaam = null;
    } else if (state.selectedGroepen.length === 1) {
        state.selectedDeelgebiedNaam = state.selectedGroepen[0].naam;
    } else {
        state.selectedDeelgebiedNaam = state.selectedGroepen.map(g => g.naam).join(', ');
    }
}

/** Sprint 18 F3: Visuele weergave/highlight bij klik op Top-buurt */
window.highlightGebied = function(gebiedId) {
    state.highlightedGebiedId = gebiedId;
    if (state.currentData && state.deckgl) {
        displayOnMap(state.currentData);
    }
};

/** Helper: namen ophalen van geselecteerde gebieden uit currentData */
function getSelectedGebiedNamen() {
    if (!state.currentData || !state.currentData.features) return [];
    return state.currentData.features
        .filter(f => isGebiedSelected(f.id || f.properties?.id))
        .map(f => f.properties?.naam || f.id || f.properties?.id);
}

// ...

// Colors
getFillColor: d => {
    // Check for selection first
    if (state.selectedGebiedId && (d.id === state.selectedGebiedId || d.properties.id === state.selectedGebiedId)) {
        return [197, 157, 0, 200]; // Geo Gold highlight for selection (#c59d00)
    }

    const value = d.properties.indicator_waarde;
    if (value === null || value === undefined) {
        return [200, 200, 200, 100]; // Grijs voor geen data
    }

    // Use Backend Color if available (Sync with Kompas)
    if (d.properties.color) {
        // Parse Hex to RGB and add transparency (0.6 opacity = 153 alpha)
        const hex = d.properties.color;
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return [r, g, b, 153]; // Fixed transparency 60%
    }

    // Fallback (Client-side calc - should be avoided)
    return getColorRGB(value, minValue, maxValue);
},

    // ============================================================================
    // Initialization
    // ============================================================================

    document.addEventListener('DOMContentLoaded', async () => {
        console.log('🚀 D-OmniTwin Gebiedsmonitor v2.0 starten...');

        try {
            initTheme(); // Initialize theme FIRST
            setupThemeToggle(); // Setup toggle listener

            // Track A — Onboarding EERST (Sprint 11B)
            // Modal moet altijd tonen, ook als de backend tijdelijk onbereikbaar is.
            initOnboarding();

            initDeckGL();
            // Initialize Floating Windows FIRST
            if (window.DraggableWindow) {
                state.kompasWindow = new DraggableWindow('kompas-window');
            } else {
                console.error('❌ DraggableWindow class not found');
            }

            await loadGemeenten(); // NEW: Load gemeente options
            await loadGebiedstypes();
            loadDataTellers(); // Kop en voet: aantallen uit de database (niet wachten)
            startVerbindingscontrole(); // Melding alleen bij een verbindingsprobleem
            setupGemeenteSelector(); // NEW: Setup gemeente change handler
            setupEventListeners();
            setupTabBar();

            // Track A2 — Contextuele tooltips (na alle EventBus setup)
            initContextualTooltips();

            // Track B — Directe feedback & micro-interacties (Sprint 11B)
            initFeedbackLayer();

            // Track C — Indicator zoekfunctie (Sprint 11B)
            initIndicatorSearch();

            // Sprint 18: Externe kaartlagen laden (dynamische toggles)
            await loadExterneKaartlagen();

            // DON'T auto-open any panel - let user click tab buttons

            // Escape key → reset actieve indicator
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && state.currentIndicator) {
                    resetKaartIndicator();
                }
            });

            console.log('✅ Applicatie succesvol geladen');
            console.log(`📍 Mapbox: ${state.mapboxToken ? 'Enabled' : 'Disabled'}`);
            console.log(`🎨 Theme: ${state.currentTheme}`);
        } catch (error) {
            console.error('❌ Fout bij initialisatie:', error);
            showError('Fout bij laden van applicatie — controleer de server verbinding.');
        }
    });

// ============================================================================
// Theme Management System
// ============================================================================

const THEME_KEY = 'omnitwin-theme';

function initTheme() {
    // Load theme from localStorage or default to dark
    state.currentTheme = localStorage.getItem(THEME_KEY) || 'dark';
    document.documentElement.setAttribute('data-theme', state.currentTheme);

    // Set Mapbox style based on theme
    if (state.mapboxToken) {
        state.mapboxStyle = state.currentTheme === 'dark'
            ? 'https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1/styles/darkmode__webmercatorquad?f=mapbox'
            : 'https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1/styles/standaard__webmercatorquad?f=mapbox';
        
        // Sync mapbox select if exists
        const styleSelect = document.getElementById('mapbox-style-select');
        if (styleSelect) styleSelect.value = state.mapboxStyle;
    }

    console.log(`🎨 Theme initialized: ${state.currentTheme}`);
    console.log(`🗺️ Mapbox style: ${state.mapboxStyle}`);
}

function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');

    // Set initial icon
    updateThemeIcon();

    // Toggle handler
    themeToggle.addEventListener('click', () => {
        // Switch theme
        state.currentTheme = state.currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', state.currentTheme);
        localStorage.setItem(THEME_KEY, state.currentTheme);

        // Update UI
        updateThemeIcon();
        updateMapboxStyleForTheme();

        // Refresh map colors if data is loaded
        if (state.currentData) {
            displayOnMap(state.currentData);
        }

        console.log(`🎨 Theme switched to: ${state.currentTheme}`);
    });
}

function updateThemeIcon() {
    // Icons are now SVGs handled by CSS visibility based on data-theme attribute
    // No manual textContent update needed
}

function updateMapboxStyleForTheme() {
    if (!state.mapboxToken) return;

    // Use PDOK styles instead of Mapbox styles for the themes
    const targetStyle = state.currentTheme === 'dark'
        ? 'https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1/styles/darkmode__webmercatorquad?f=mapbox'
        : 'https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1/styles/standaard__webmercatorquad?f=mapbox';

    // Only update if changed
    if (state.mapboxStyle === targetStyle) return;

    // Update state
    state.mapboxStyle = targetStyle;

    // Update selector if exists
    const styleSelect = document.getElementById('mapbox-style-select');
    if (styleSelect) {
        styleSelect.value = targetStyle;
    }

    // Apply to map
    changeMapboxStyle(targetStyle);

    console.log(`🗺️ Mapbox style synced: ${targetStyle}`);
}


// ============================================================================
// 3D Lighting System
// ============================================================================

let lightingEnabled = true;
let fpsCounter = 0;
let lastFpsCheck = Date.now();

function create3DLighting() {
    const { LightingEffect, AmbientLight, DirectionalLight } = deck;

    if (!LightingEffect) {
        console.warn('⚠️ LightingEffect not available in deck.gl');
        return null;
    }

    const ambientLight = new AmbientLight({
        color: [255, 255, 255],
        intensity: 0.6  // Moderate ambient
    });

    const dirLight = new DirectionalLight({
        color: [255, 255, 255],
        direction: [-1, -3, -1], // Pointing down and slightly to the side
        intensity: 1.2 // Lower intensity to avoid blowing out colors
    });

    const lightingEffect = new LightingEffect({ ambientLight, dirLight });

    console.log('✨ 3D Lighting enabled');
    return lightingEffect;
}

function checkPerformance() {
    // Optionally track FPS, but DO NOT disable lighting!
    // Disabling lighting while keeping materials causes all 3D objects to become black/grey.
    fpsCounter++;
    const now = Date.now();

    if (now - lastFpsCheck > 1000) {
        fpsCounter = 0;
        lastFpsCheck = now;
    }
}

function showNotification(message) {
    // Simple notification - could be improved with toast UI
    console.log(`📢 ${message}`);
}


// ============================================================================
// Vertical Tab Bar (NEW)
// ============================================================================

function setupTabBar() {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const panelId = e.currentTarget.dataset.panel;
            togglePanel(panelId);
        });
    });
}

function togglePanel(panelId) {
    const container = document.querySelector('.panel-container');
    const panels = document.querySelectorAll('.panel-content');
    const buttons = document.querySelectorAll('.tab-button');

    // Close if clicking active panel
    if (state.activePanelId === panelId) {
        container.classList.remove('open');
        state.activePanelId = null;
        buttons.forEach(btn => btn.classList.remove('active'));
        return;
    }

    // Switch panels
    panels.forEach(p => p.classList.remove('active'));
    const targetPanel = document.querySelector(`#panel-${panelId}`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    // Update UI
    container.classList.add('open');
    state.activePanelId = panelId;

    buttons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.panel === panelId);
    });

    console.log(`📂 Panel opened: ${panelId}`);
}

// ============================================================================
// deck.gl Setup with MapLibre
// ============================================================================

/**
 * Klikherkenning ruimer (#279). deck.gl maakt van pointerdown en pointerup alleen een klik als
 * beide binnen 250 ms *verwerkt* worden; bij pointerdown doet deck.gl eerst synchroon een pick.
 * Zonder GPU (software-WebGL, VDI) of onder belasting duurt die pick 0,2-1,6 s en ging de klik
 * van de gebruiker verloren. Met 1000 ms blijft een klik een klik; slepen herkent deck.gl aan de
 * beweging, niet aan de tijd.
 */
const KLIK_TIJD_MS = 1000;
function ruimeKlikherkenning(deck) {
    try {
        const herkenner = deck?.eventManager?.manager?.get?.('click');
        if (herkenner && (herkenner.options?.time || 0) < KLIK_TIJD_MS) herkenner.set({ time: KLIK_TIJD_MS });
    } catch (e) {
        console.warn('Klikherkenning niet aangepast:', e);
    }
}

function initDeckGL() {
    const { DeckGL, MapView } = deck;

    // MapLibre configuration
    const mapConfig = {
        mapStyle: state.mapboxStyle, // Uses PDOK styles from index.html
        mapOptions: {
            preserveDrawingBuffer: true
        }
    };

    console.log('⚙️ deck.gl config:', mapConfig);

    // Create 3D lighting effect
    const lightingEffect = create3DLighting();

    state.deckgl = new DeckGL({
        container: 'map',
        map: typeof maplibregl !== 'undefined' ? maplibregl : window.mapboxgl,
        views: [new MapView({ repeat: true })],
        ...mapConfig,
        viewState: state.currentViewState,
        onViewStateChange: ({ viewState }) => {
            state.currentViewState = viewState;
            state.deckgl.setProps({ viewState: state.currentViewState });
        },
        controller: true,
        layers: [],
        effects: lightingEffect ? [lightingEffect] : [], // Add 3D lighting
        glOptions: {
            preserveDrawingBuffer: true
        },
        parameters: {
            depthTest: true,
            blend: true,
            blendFunc: [770, 771] // gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA (standard blending)
        },
        onAfterRender: checkPerformance, // Monitor FPS
        onLoad: () => ruimeKlikherkenning(state.deckgl), // #279: klik niet kwijt op trage pc's
        getTooltip: ({ object, layer }) => {
            if (object) {
                const props = object.properties;
                const tooltipStyle = {
                    backgroundColor: 'color-mix(in srgb, var(--tooltip-bg) 95%, transparent)',
                    color: 'var(--tooltip-text)',
                    fontFamily: 'inherit',
                    padding: '12px',
                    borderRadius: 'var(--border-radius-sm)',
                    fontSize: '13px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                };

                // Externe kaartlaag tooltip (Sprint 18)
                if (layer?.id?.startsWith('externe-laag-')) {
                    const featureNaam = props.woonplaats || props.naam || props.name || props.Naam || props.Deelgebied || props.deelgebied || 'Onbekend';
                    return {
                        html: `
                <div>
                  <strong>\u{1F310} ${escapeHtml(featureNaam)}</strong><br/>
                  <small style="opacity:0.5;">Klik om buurten te selecteren</small>
                </div>
              `,
                        style: tooltipStyle
                    };
                }

                // Omgevingsvisie Deelgebied tooltip
                if (layer?.id === 'omgevingsvisie-layer') {
                    return {
                        html: `
                <div>
                  <strong>🗺️ ${escapeHtml(props.deelgebied)}</strong><br/>
                  <small style="opacity:0.7;">${escapeHtml(props.naam)}</small><br/>
                  Oppervlakte: <strong>${escapeHtml(props.oppervlakte_km2)} km²</strong><br/>
                  <small style="opacity:0.5;">Klik om buurten te selecteren</small>
                </div>
              `,
                        style: tooltipStyle
                    };
                }

                // BAG 3D Pand tooltip (Sprint 12)
                if (layer?.id === 'bag3d-layer' || props.identificatie) {
                    const bagId = props.identificatie || 'Onbekend';
                    const bouwjaar = props.oorspronkelijkbouwjaar || 'Onbekend';
                    const hoogte = props.b3_h_50p ?? props.b3_h_dak_50p;
                    const maaiveld = props.b3_h_maaiveld ?? 0;
                    const pandHoogte = hoogte ? (hoogte - maaiveld).toFixed(1) : '?';
                    const opp = props.b3_opp_grond ? props.b3_opp_grond.toFixed(0) : '?';
                    const indicatorInfo = props.indicator_waarde != null
                        ? `<br/><small style="opacity:0.7;">Indicator: ${formatNumber(props.indicator_waarde)}</small>`
                        : '';

                    return {
                        html: `
                <div>
                  <strong>🏠 Pand</strong><br/>
                  <small style="opacity:0.6;">${escapeHtml(bagId)}</small><br/>
                  Bouwjaar: <strong>${escapeHtml(bouwjaar)}</strong><br/>
                  Hoogte: <strong>${pandHoogte} m</strong> · Opp: <strong>${opp} m²</strong>
                  ${indicatorInfo}
                </div>
              `,
                        style: tooltipStyle
                    };
                }

                // Default buurt tooltip: waarde met jaargang en bron (#119)
                const heeftWaarde = props.indicator_waarde !== null && props.indicator_waarde !== undefined;
                // #325: een waarde die op te weinig waarnemingen rust, tonen we niet
                const nDrempel = state.currentData?.metadata?.n_drempel || 10;
                const indicatorValue = heeftWaarde ?
                    formatNumber(props.indicator_waarde) + ' ' + (props.eenheid || '') :
                    (props.onderdrukt ? `Niet getoond (minder dan ${nDrempel} waarnemingen)` : 'Geen data');
                const herkomst = heeftWaarde
                    ? `<br/><small class="tooltip-herkomst" style="opacity:0.75;">Jaar ${escapeHtml(props.jaar || 'onbekend')} · Bron: ${escapeHtml(props.bron || 'onbekend')}</small>`
                    : '';
                // #255: percentielklasse in de tooltip (alleen in die kaartmodus)
                const klasseTekst = state.kaartModus === 'percentiel' && heeftWaarde
                    ? (props.klasse
                        ? `<br/><small class="tooltip-klasse">Percentielklasse ${escapeHtml(props.klasse)} van 8</small>`
                        : `<br/><small class="tooltip-klasse">Geen percentielklasse (${escapeHtml(props.klasse_status || 'geen referentie')})</small>`)
                    : (state.kaartModus === 'label' && heeftWaarde
                        // #256: label A-E in de tooltip
                        ? (props.label
                            ? `<br/><small class="tooltip-klasse">Label ${escapeHtml(props.label)}${state.currentData?.metadata?.label_bron === 'drempels' ? '' : ' (voorlopig, kwintielen)'}</small>`
                            : `<br/><small class="tooltip-klasse">Geen label (${escapeHtml(props.klasse_status || 'geen referentie')})</small>`)
                        : '');

                return {
                    html: `
            <div>
              <strong>${escapeHtml(props.naam)}</strong><br/>
              ${props.indicator_naam ? `${escapeHtml(props.indicator_naam)}: ` : ''}<strong>${escapeHtml(indicatorValue)}</strong>${herkomst}${klasseTekst}
            </div>
          `,
                    style: tooltipStyle
                };
            }
            return null;
        },

        // Track B4: Cursor feedback bij hover over pickable objecten
        getCursor: ({isHovering, isDragging}) => {
            if (isDragging) return 'grabbing';
            if (isHovering) return 'pointer';
            return 'grab';
        }
    });

    // Event listeners
    state.deckgl.setProps({
        onWebGLInitialized: (gl) => {
            console.log('✅ WebGL Initialized');
        }
    });

}

// ============================================================================
// MapLibre Style Switcher
// ============================================================================

function changeMapboxStyle(styleUrl) {
    if (!state.deckgl) {
        console.warn('❌ DeckGL instance not initialized yet');
        return;
    }

    state.mapboxStyle = styleUrl;

    state.deckgl.setProps({
        mapStyle: styleUrl
    });

    console.log(`🗺️ Basemap style changed to: ${styleUrl}`);
}

// ============================================================================
// Data Loading Functions
// ============================================================================

// ---- Gemeente Selector (Multi-gemeente support) ----

// Provincie en eigen gemeenten komen uit de organisatie-instelling (#324):
// benchmark_provincie filtert de lijst, gemeente_codes is de terugval als de API
// met gemeenten niet beschikbaar is. Geen vaste provincie of gemeentelijst in de code.
async function laadOrganisatieVoorGemeenten() {
    try {
        const response = await fetch('/api/organisatie');
        if (response.ok) return await response.json();
    } catch (error) {
        console.warn('⚠️ Organisatie niet beschikbaar');
    }
    return null;
}

// Store loaded gemeenten for lookup
// Store loaded gemeenten for lookup
let loadedGemeenten = [];
let comboboxController = null;

/**
 * Diakrieten- en hoofdletterongevoelige tekstnormalisatie (WCAG/UX).
 * Zoekt bijv. 'sud' en vindt 'Súdwest-Fryslân'.
 */
function normaliseerGemeenteTekst(str) {
    if (!str) return '';
    return str.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();
}

/**
 * Centrale functie voor het instellen van het gemeentefilter.
 * Synchroniseert input, code, dropdown, filter-chip en kaartdata.
 */
function zetGemeente(code, naamOptioneel = null, herlaadKaart = true) {
    const input = document.getElementById('gemeente-input');
    const codeInput = document.getElementById('gemeente-code');
    const info = document.getElementById('gemeente-info');

    const cleanCode = code || '';
    state.currentGemeenteCode = cleanCode;
    try {
        localStorage.setItem('omnitwin-gemeente', cleanCode);
    } catch (e) { /* localStorage beveiliging */ }

    const gemeente = loadedGemeenten.find(g => g.code === cleanCode);
    const naam = gemeente ? gemeente.naam : (naamOptioneel || (cleanCode ? `code ${cleanCode}` : 'Alle gemeenten'));

    if (input) input.value = naam;
    if (codeInput) codeInput.value = cleanCode;
    if (info) info.textContent = cleanCode ? `Geselecteerd: ${naam}` : 'Alle gemeenten';

    updateGemeenteFilterChip();
    if (comboboxController) {
        comboboxController.syncVisualSelection(cleanCode);
    }

    if (herlaadKaart) {
        console.log(`📍 Gemeente ingesteld: ${naam} (${cleanCode || 'alle'})`);
        state.currentData = null;
        clearGebiedSelection();
        updateSelectionUI();

        if (window.kompasViz && window.kompasViz.currentConfigId) {
            window.kompasViz.currentGebiedId = null;
            window.kompasViz.loadHierarchie(window.kompasViz.currentConfigId);
        }

        if (state.currentGebiedstype) {
            loadKaartData();
        }
    }
}

async function loadGemeenten() {
    const info = document.getElementById('gemeente-info');

    let gemeenten = [];
    const organisatie = await laadOrganisatieVoorGemeenten();
    const provincie = organisatie?.benchmark_provincie;
    const provincieFilter = provincie ? `provincie=eq.${encodeURIComponent(provincie)}&` : '';

    try {
        const response = await fetch(`/api/data/gemeenten?${provincieFilter}order=naam.asc`);
        if (response.ok) {
            const data = await response.json();
            if (data && data.length > 0) {
                gemeenten = [{ code: '', naam: 'Alle gemeenten', is_eiland: false }, ...data];
                console.log(`✅ ${data.length} gemeenten geladen van API`);
            }
        }
    } catch (error) {
        console.warn('⚠️ Gemeente API niet beschikbaar, gebruik fallback');
    }

    if (gemeenten.length === 0) {
        // Terugval: de eigen gemeente(n) uit de organisatie-instelling
        gemeenten = [
            { code: '', naam: 'Alle gemeenten', is_eiland: false },
            ...(organisatie?.gemeente_codes || []).map(code => ({ code, naam: code, is_eiland: false }))
        ];
        console.log('📋 Gebruik fallback gemeenten uit de organisatie-instelling');
    }

    loadedGemeenten = gemeenten;

    // Initialiseer initiële waarde via zetGemeente (zonder kaart-reload bij init)
    zetGemeente(state.currentGemeenteCode, null, false);

    const aantalEchteGemeenten = gemeenten.filter(g => g.code !== '').length;
    if (info) {
        info.textContent = state.currentGemeenteCode
            ? `Geselecteerd: ${gemeenteNaam(state.currentGemeenteCode)}`
            : `${aantalEchteGemeenten} gemeenten beschikbaar`;
    }

    if (comboboxController) {
        comboboxController.updateOptions(loadedGemeenten);
    }
}

// ---- Actief gemeentefilter zichtbaar maken (#140) ----

function gemeenteNaam(code) {
    const gemeente = loadedGemeenten.find(g => g.code === code);
    return gemeente ? gemeente.naam : `code ${code}`;
}

/**
 * Toont het actieve gemeentefilter als chip boven de kaart.
 * aantalGebieden === 0: melding dat het filter niets oplevert, met wisknop.
 */
function updateGemeenteFilterChip(aantalGebieden = null) {
    const chip = document.getElementById('gemeente-filter-chip');
    if (!chip) return;
    const code = state.currentGemeenteCode;
    if (!code) {
        chip.hidden = true;
        chip.classList.remove('leeg');
        return;
    }
    const naam = gemeenteNaam(code);
    const leeg = aantalGebieden === 0;
    document.getElementById('gemeente-filter-tekst').textContent = leeg
        ? `Geen gebieden in gemeente ${naam} — filter wissen?`
        : `Gemeente: ${naam}`;
    const knop = document.getElementById('gemeente-filter-wis');
    knop.setAttribute('aria-label', `Gemeentefilter ${naam} wissen`);
    knop.title = `Gemeentefilter ${naam} wissen`;
    chip.classList.toggle('leeg', leeg);
    chip.hidden = false;
}

/** Zet het gemeentefilter terug naar 'Alle gemeenten' en herlaadt de kaart. */
function resetGemeenteFilter() {
    zetGemeente('', 'Alle gemeenten', true);
}

function setupGemeenteSelector() {
    const input = document.getElementById('gemeente-input');
    const listbox = document.getElementById('gemeente-listbox');
    const toggleBtn = document.getElementById('gemeente-toggle-btn');
    const wrapper = document.getElementById('gemeente-combobox-wrapper');
    const info = document.getElementById('gemeente-info');

    if (!input || !listbox) return;

    const wisKnop = document.getElementById('gemeente-filter-wis');
    if (wisKnop) wisKnop.addEventListener('click', resetGemeenteFilter);

    let isOpen = false;
    let activeIndex = -1;
    let currentFiltered = [...loadedGemeenten];

    function renderList(options, activeIdx = -1) {
        listbox.innerHTML = '';
        currentFiltered = options;

        if (options.length === 0) {
            const emptyLi = document.createElement('li');
            emptyLi.id = 'gemeente-opt-empty';
            emptyLi.className = 'combobox-option combobox-empty';
            emptyLi.setAttribute('role', 'option');
            emptyLi.setAttribute('aria-disabled', 'true');
            emptyLi.textContent = 'Geen gemeenten gevonden';
            listbox.appendChild(emptyLi);
            if (info) info.textContent = 'Geen gemeenten gevonden';
            input.removeAttribute('aria-activedescendant');
            return;
        }

        options.forEach((opt, idx) => {
            const li = document.createElement('li');
            li.id = `gemeente-opt-${idx}`;
            li.className = 'combobox-option';
            li.setAttribute('role', 'option');
            li.dataset.code = opt.code;
            li.dataset.naam = opt.naam;

            const isSelected = opt.code === (state.currentGemeenteCode || '');
            li.setAttribute('aria-selected', isSelected ? 'true' : 'false');

            if (idx === activeIdx) {
                li.classList.add('combobox-option-active');
            }

            li.textContent = opt.naam;
            listbox.appendChild(li);
        });

        if (activeIdx >= 0 && activeIdx < options.length) {
            input.setAttribute('aria-activedescendant', `gemeente-opt-${activeIdx}`);
            scrollActiveIntoView(activeIdx);
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }

    function scrollActiveIntoView(index) {
        const item = document.getElementById(`gemeente-opt-${index}`);
        if (!item) return;
        const top = item.offsetTop;
        const bottom = top + item.offsetHeight;
        if (top < listbox.scrollTop) {
            listbox.scrollTop = top;
        } else if (bottom > listbox.scrollTop + listbox.clientHeight) {
            listbox.scrollTop = bottom - listbox.clientHeight;
        }
    }

    function openDropdown() {
        if (isOpen) return;
        isOpen = true;
        listbox.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');

        const val = input.value.trim();
        const huidigeGemeente = loadedGemeenten.find(g => g.code === state.currentGemeenteCode);
        const huidigeNaam = huidigeGemeente ? huidigeGemeente.naam : 'Alle gemeenten';

        if (!val || val === huidigeNaam || val.toLowerCase() === 'alle') {
            filterOptions('');
        } else {
            filterOptions(val);
        }

        const selectIdx = currentFiltered.findIndex(g => g.code === (state.currentGemeenteCode || ''));
        setActiveIndex(selectIdx >= 0 ? selectIdx : 0);
    }

    function closeDropdown(herstelTekst = true) {
        if (!isOpen) return;
        isOpen = false;
        listbox.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        activeIndex = -1;

        if (herstelTekst) {
            const naam = gemeenteNaam(state.currentGemeenteCode);
            input.value = naam;
        }
    }

    function filterOptions(query) {
        const norm = normaliseerGemeenteTekst(query);
        let gefilterd;

        if (!norm || norm === 'alle') {
            gefilterd = [...loadedGemeenten];
        } else {
            gefilterd = loadedGemeenten.filter(g => {
                if (g.code === '') return false;
                return normaliseerGemeenteTekst(g.naam).includes(norm);
            });
        }

        activeIndex = gefilterd.length > 0 ? 0 : -1;
        renderList(gefilterd, activeIndex);

        if (info && norm && norm !== 'alle') {
            info.textContent = `${gefilterd.length} ${gefilterd.length === 1 ? 'gemeente' : 'gemeenten'} gevonden`;
        }
    }

    function setActiveIndex(idx) {
        if (currentFiltered.length === 0) {
            activeIndex = -1;
            input.removeAttribute('aria-activedescendant');
            return;
        }
        activeIndex = Math.max(0, Math.min(idx, currentFiltered.length - 1));
        renderList(currentFiltered, activeIndex);
    }

    function selecteerOptie(optie) {
        if (!optie) return;
        zetGemeente(optie.code, optie.naam, true);
        closeDropdown(false);
    }

    // Toggle button pointer events
    if (toggleBtn) {
        toggleBtn.addEventListener('pointerdown', (e) => {
            e.preventDefault();
        });
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (isOpen) {
                closeDropdown(true);
            } else {
                input.focus();
                openDropdown();
            }
        });
    }

    // Listbox pointer events
    listbox.addEventListener('pointerdown', (e) => {
        e.preventDefault();
    });

    listbox.addEventListener('click', (e) => {
        const li = e.target.closest('li[role="option"]');
        if (!li || li.classList.contains('combobox-empty')) return;
        const code = li.dataset.code;
        const naam = li.dataset.naam;
        selecteerOptie({ code, naam });
    });

    // Input events
    input.addEventListener('input', () => {
        if (!isOpen) {
            isOpen = true;
            listbox.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
        }
        filterOptions(input.value);
    });

    input.addEventListener('focus', () => {
        input.select();
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (e.altKey) {
                openDropdown();
            } else if (!isOpen) {
                openDropdown();
            } else {
                setActiveIndex(activeIndex + 1);
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (e.altKey) {
                closeDropdown(true);
            } else if (isOpen) {
                setActiveIndex(activeIndex - 1);
            }
        } else if (e.key === 'Home') {
            if (isOpen) {
                e.preventDefault();
                setActiveIndex(0);
            }
        } else if (e.key === 'End') {
            if (isOpen) {
                e.preventDefault();
                setActiveIndex(currentFiltered.length - 1);
            }
        } else if (e.key === 'Enter') {
            if (isOpen) {
                e.preventDefault();
                if (activeIndex >= 0 && currentFiltered[activeIndex]) {
                    selecteerOptie(currentFiltered[activeIndex]);
                } else if (currentFiltered.length === 1) {
                    selecteerOptie(currentFiltered[0]);
                } else {
                    const norm = normaliseerGemeenteTekst(input.value);
                    const exact = loadedGemeenten.find(g => normaliseerGemeenteTekst(g.naam) === norm);
                    if (exact) {
                        selecteerOptie(exact);
                    }
                }
            }
        } else if (e.key === 'Escape') {
            if (isOpen) {
                e.preventDefault();
                e.stopPropagation();
                closeDropdown(true);
            }
        } else if (e.key === 'Tab') {
            if (isOpen) {
                closeDropdown(true);
            }
        }
    });

    // Outside pointerdown sluit dropdown
    document.addEventListener('pointerdown', (e) => {
        if (isOpen && wrapper && !wrapper.contains(e.target)) {
            closeDropdown(true);
        }
    });

    comboboxController = {
        updateOptions: (opts) => {
            currentFiltered = [...opts];
            if (isOpen) renderList(currentFiltered, activeIndex);
        },
        syncVisualSelection: (code) => {
            if (isOpen) {
                renderList(currentFiltered, activeIndex);
            }
        }
    };
}

// ---- End Gemeente Selector ----


/**
 * Telt de rijen van een PostgREST-tabel via de Content-Range-header
 * (Prefer: count=exact), zonder de rijen zelf op te halen.
 * Geeft null terug als het aantal niet te bepalen is.
 */
async function fetchPostgrestCount(pad) {
    const res = await fetch(`/api/data/${pad}`, {
        method: 'HEAD',
        headers: { 'Prefer': 'count=exact' }
    });
    if (!res.ok) return null;
    const range = res.headers.get('Content-Range') || '';
    const totaal = parseInt(range.split('/')[1], 10);
    return Number.isNaN(totaal) ? null : totaal;
}

// Verbindingscontrole: toont #verbindingsmelding alleen als /health niet bereikbaar is
async function controleerVerbinding() {
    const melding = document.getElementById('verbindingsmelding');
    if (!melding) return;
    let ok = navigator.onLine;
    if (ok) {
        try {
            const res = await fetch('/health', { cache: 'no-store' });
            ok = res.ok;
        } catch (e) {
            ok = false;
        }
    }
    melding.hidden = ok;
}

function startVerbindingscontrole() {
    controleerVerbinding();
    setInterval(controleerVerbinding, 60000);
    window.addEventListener('online', controleerVerbinding);
    window.addEventListener('offline', controleerVerbinding);
}

async function loadDataTellers() {
    const zet = (id, waarde) => {
        const el = document.getElementById(id);
        if (el) el.textContent = waarde === null ? '?' : waarde.toLocaleString('nl-NL');
    };
    try {
        const [gebieden, indicatoren] = await Promise.all([
            fetchPostgrestCount('gebieden?select=id'),
            fetchPostgrestCount('indicatoren?select=id')
        ]);
        zet('header-gebieden-count', gebieden);
        zet('footer-gebieden-count', gebieden);
        zet('header-indicatoren-count', indicatoren);
    } catch (error) {
        console.warn('⚠️ Tellers konden niet worden geladen:', error);
        ['header-gebieden-count', 'footer-gebieden-count', 'header-indicatoren-count']
            .forEach(id => zet(id, null));
    }
}

async function loadGebiedstypes() {
    showLoading(true, 'Gebiedstypes laden...');

    try {
        const response = await fetch('/api/data/gebiedstypes?select=id,naam,code,beschrijving,bron,niveau&order=naam.asc');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        populateGebiedstypeSelect(data);

        console.log(`✅ ${data.length} gebiedstypes geladen`);
    } catch (error) {
        console.error('❌ Fout bij laden gebiedstypes:', error);
        showError('Fout bij laden van gebiedstypes');
    } finally {
        showLoading(false);
    }
}

async function loadIndicatoren(gebiedstypeId) {
    showLoading(true, 'Indicatoren laden...');

    try {
        const response = await fetch(`/api/data/rpc/get_indicatoren_stats`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        let url = `/api/data/rpc/get_indicatoren_stats`;
        if (gebiedstypeId) {
            // PostgREST verwacht POST voor RPC functies met argumenten of je kunt callen via GET als parameters query params zijn
            url += `?p_gebiedstype_id=${gebiedstypeId}`;
        }
        
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        populateIndicatorSelect(data);

        console.log(`✅ ${data.length} indicatoren geladen`);
    } catch (error) {
        console.error('❌ Fout bij laden indicatoren:', error);
        showError('Fout bij laden van indicatoren');
    } finally {
        showLoading(false);
    }
}

async function loadKaartData() {
    if (!state.currentGebiedstype) {
        showError('Selecteer eerst een gebiedstype');
        return;
    }

    showLoading(true, 'Kaart data laden...');

    try {
        // 1. Fetch Geometries via pg_featureserv (limit=10000 ensures we get all features)
        // We use vw_gebieden_features to ensure we get MultiPolygon instead of Point
        let geoUrl = `/api/geo/collections/public.vw_gebieden_features/items?gebiedstype_id=${state.currentGebiedstype}&properties=id,naam,gebiedstype_id&limit=10000`;
        if (state.currentGemeenteCode) {
            geoUrl += `&gemeente_code=${state.currentGemeenteCode}`;
        }
        
        // 2. Fetch Attributes via FastAPI (Hybride)
        let attrUrl = `/api/gebiedsmonitor/kaart_data/${state.currentGebiedstype}?show_all=${state.showAll}`;
        if (state.currentIndicator) {
            attrUrl += `&indicator_uuid=${state.currentIndicator}${kaartModusParam()}`;
        }
        if (state.currentGemeenteCode) {
            attrUrl += `&gemeente_code=${state.currentGemeenteCode}`;
        }

        const [geoRes, attrRes] = await Promise.all([
            fetch(geoUrl),
            fetch(attrUrl)
        ]);

        if (!geoRes.ok) throw new Error(`Geo HTTP ${geoRes.status}`);
        if (!attrRes.ok) throw new Error(`Attr HTTP ${attrRes.status}`);

        const geojson = await geoRes.json();
        const attributes = await attrRes.json();
        
        // 3. Merge attributes into GeoJSON features
        geojson.features.forEach(f => {
            const props = attributes.data[f.properties.id];
            if (props) {
                Object.assign(f.properties, props);
            }
        });
        geojson.metadata = attributes.metadata;

        state.currentData = geojson;
        // Alleen inzoomen bij een ander gebiedstype of andere gemeente, niet bij een indicatorwissel
        const fitKey = `${state.currentGebiedstype}|${state.currentGemeenteCode || ''}`;
        if (state.fittedFor !== fitKey) {
            state.initialDataLoaded = false;
            state.fittedFor = fitKey;
        }

        displayOnMap(geojson);
        updateFeatureCount(geojson.metadata);
        const gtCountEl = document.getElementById('gebiedstype-count');
        if (gtCountEl && geojson.features) {
            gtCountEl.textContent = `${geojson.features.length} gebieden in selectie`;
        }
        updateGemeenteFilterChip(geojson.features ? geojson.features.length : null);
updateLegenda(geojson);
        // #258: indicatorpaneel bijwerken (actuele waarden)
        window.EventBus?.emit('KAARTDATA_GELADEN', { jaar: null });

        const geojsonBtn = document.getElementById('export-geojson-btn');
        const csvBtn = document.getElementById('export-csv-btn');
        if (geojsonBtn) geojsonBtn.disabled = false;
        if (csvBtn) csvBtn.disabled = false;

        console.log(`✅ ${geojson.features.length} gebieden geladen (Lego architecture merge)`);
    } catch (error) {
        console.error('❌ Fout bij laden kaart data:', error);
        showError('Fout bij laden van kaart data: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function loadGebiedDetails(gebiedId) {
    // Track B2: Toon inline spinner terwijl data wordt geladen
    showInlineLoading('Gebieddetails laden...');

    try {
        const response = await fetch(`/api/gebiedsmonitor/gebieden/${gebiedId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        displayGebiedDetails(data);

        console.log(`✅ Details geladen voor ${gebiedId}`);
    } catch (error) {
        console.error('❌ Fout bij laden gebied details:', error);
        showError('Kon gebied details niet laden: ' + (error.message || 'Onbekende fout'));
        showGebiedEmptyState(); // Fallback naar empty state bij fout
    }
}
// ============================================================================
// 3D BAG Panden (Sprint 12) — On-demand gebouwmodellen
// ============================================================================

/**
 * Laadt 3D panden vanuit de 3DBAG WFS voor de geselecteerde gebieden.
 * Stuurt de actieve indicator_uuid mee voor kleurverrijking.
 * Wederzijds exclusief met CBS buurt-extrusie (enable3D).
 */
async function loadBag3DBuildings() {
    const ids = [...state.selectedGebiedIds];
    if (ids.length === 0 || ids.length > 3) {
        showError('Selecteer 1 t/m 3 gebieden voor de 3D pandweergave.');
        return;
    }

    showLoading(true, '3D panden laden vanuit 3DBAG...');

    try {
        const res = await fetch('/api/3dbag/buildings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                gebied_ids: ids,
                indicator_uuid: state.currentIndicator || null
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        state.bag3dData = data;
        state.show3DBuildings = true;

        // Wederzijds exclusief: deactiveer buurt-extrusie
        if (state.enable3D) {
            state.enable3D = false;
            const cb = document.getElementById('enable-3d');
            if (cb) cb.checked = false;
            document.getElementById('extrusie-controls').style.display = 'none';
        }

        // Camera: fly naar de BAG panden bounding box (dichtbij!)
        if (data.features && data.features.length > 0) {
            let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
            data.features.forEach(f => {
                const coords = f.geometry?.coordinates;
                if (!coords) return;
                // Flatten polygon coordinates
                const flatten = (arr) => {
                    if (typeof arr[0] === 'number') { return [arr]; }
                    return arr.flatMap(flatten);
                };
                flatten(coords).forEach(([lng, lat]) => {
                    if (lng < minLng) minLng = lng;
                    if (lng > maxLng) maxLng = lng;
                    if (lat < minLat) minLat = lat;
                    if (lat > maxLat) maxLat = lat;
                });
            });
            const centerLng = (minLng + maxLng) / 2;
            const centerLat = (minLat + maxLat) / 2;
            // Zoom level: dichter bij dan de buurt-overzicht
            const latSpan = maxLat - minLat;
            const lngSpan = maxLng - minLng;
            const maxSpan = Math.max(latSpan, lngSpan);
            // Bereken zoom zodat de panden goed in beeld passen (straatniveau)
            const zoom = Math.min(18, Math.max(15.5, -Math.log2(maxSpan / 0.003)));

            state.currentViewState = {
                ...state.currentViewState,
                longitude: centerLng,
                latitude: centerLat,
                zoom: zoom,
                pitch: 50,
                bearing: -15,
                ...A11y.cameraTransition(1200),
            };
        } else {
            state.currentViewState = {
                ...state.currentViewState,
                pitch: 50,
                ...A11y.cameraTransition(800),
            };
        }
        state.deckgl.setProps({ viewState: state.currentViewState });

        // Re-render kaart met BAG laag
        if (state.currentData) {
            displayOnMap(state.currentData);
        }
        updateSelectionUI();

        const mode = data.metadata?.kleur_mode || 'geen';
        console.log(`🏗️ ${data.metadata?.panden_count || data.features?.length} 3D panden geladen (kleur: ${mode})`);
        console.log(`📋 ${data.metadata?.copyright}`);

    } catch (e) {
        console.error('❌ 3D BAG fout:', e);
        const msg = e.message && (e.message.includes('503') || e.message.includes('tijdelijk') || e.message.includes('niet bereikbaar'))
            ? '🏗️ 3D BAG service (TU Delft) is tijdelijk niet bereikbaar of overbelast. Probeer het over enkele ogenblikken opnieuw.'
            : '3D panden konden niet worden geladen: ' + e.message;
        showError(msg);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// Omgevingsvisie Deelgebieden (Selectielaag)
// ============================================================================

/**
 * Laadt de omgevingsvisie-deelgebieden als GeoJSON overlay.
 * Wordt eenmalig aangeroepen bij eerste toggle-activatie; data wordt gecached in state.
 */
async function loadOmgevingsvisieLayer() {
    showLoading(true, 'Omgevingsvisie deelgebieden laden...');
    try {
        const res = await fetch('/api/geo/collections/public.omgevingsvisie_deelgebieden/items?limit=100');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const geojson = await res.json();
        state.omgevingsvisieData = geojson;

        console.log(`🗺️ ${geojson.features.length} omgevingsvisie-deelgebieden geladen`);
    } catch (e) {
        console.error('❌ Fout bij laden omgevingsvisie:', e);
        showError('Omgevingsvisie deelgebieden konden niet worden geladen: ' + e.message);
        state.showOmgevingsvisieLayer = false;
        const toggle = document.getElementById('toggle-omgevingsvisie');
        if (toggle) toggle.checked = false;
    } finally {
        showLoading(false);
    }
}

/**
 * Selecteert alle CBS-buurten die binnen een omgevingsvisie-deelgebied vallen.
 * Gebruikt een -10m inward buffer om grensoverlap te voorkomen.
 *
 * @param {number} deelgebiedId - Database ID van het deelgebied
 * @param {string} deelgebiedNaam - Naam voor logging en UI feedback
 */
async function selectBuurtenFromDeelgebied(deelgebiedId, deelgebiedNaam) {
    showLoading(true, `Buurten laden voor ${deelgebiedNaam}...`);
    try {
        // SQL-functie postgisftw.buurten_in_deelgebied, gepubliceerd door pg_featureserv (#68)
        const bufferM = -10;
        const params = new URLSearchParams({ deelgebied_id: deelgebiedId, buffer_m: bufferM, limit: 10000 });
        const res = await fetch(`/api/geo/functions/postgisftw.buurten_in_deelgebied/items?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const geojson = await res.json();
        const buurten = (geojson.features || []).map(f => ({
            id: f.properties?.id ?? f.id,
            naam: f.properties?.naam
        }));
        const data = { buurten, totaal: buurten.length, buffer_m: bufferM };

        // Clear huidige selectie en voeg alle buurten toe
        clearGebiedSelection();
        state.selectedDeelgebiedNaam = deelgebiedNaam;  // Bewaar voor rapport-link
        data.buurten.forEach(b => state.selectedGebiedIds.add(b.id));

        // Update UI
        updateSelectionUI();
        if (state.currentData) {
            displayOnMap(state.currentData);
        }

        // Reload kompas data als die open is
        if (state.kompasWindow && state.kompasWindow.isVisible && window.kompasViz && window.kompasViz.currentConfigId) {
            loadKompasForSelection(window.kompasViz.currentConfigId);
        }

        console.log(`📍 ${data.totaal} buurten geselecteerd via deelgebied ${deelgebiedNaam} (buffer: ${data.buffer_m}m)`);

    } catch (e) {
        console.error('❌ Fout bij selecteren buurten:', e);
        showError('Buurten konden niet worden geladen: ' + e.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// Externe Kaartlagen (Sprint 18 — PDOK WFS proxy)
// ============================================================================

// Label voor interne lagen en indicatoren (#254): die komen alleen na inloggen met de rol lezer of
// beheerder in de lijsten (de API's filteren); het label laat zien dat ze niet openbaar zijn.
const INTERN_TITEL = 'Intern: alleen zichtbaar na inloggen (rol lezer of beheerder)';
const INTERN_LABEL_HTML = `<span class="label-intern" title="${INTERN_TITEL}">intern</span>`;

function internLabel() {
    const s = document.createElement('span');
    s.className = 'label-intern';
    s.title = INTERN_TITEL;
    s.textContent = 'intern';
    return s;
}

/**
 * Laadt actieve externe kaartlagen en rendert toggles in het kaartlagen-paneel.
 */
async function loadExterneKaartlagen() {
    try {
        const res = await fetch('/api/data/externe_kaartlagen?actief=eq.true&order=volgorde.asc,naam.asc');
        if (!res.ok) return;
        const data = await res.json();
        state.externeKaartlagen = data || [];

        const container = document.getElementById('externe-lagen-list');
        if (!container) return;

        // Render compacte toggles veilig via DOM API (geen innerHTML)
        container.replaceChildren();
        state.externeKaartlagen.forEach(laag => {
            // Compact row wrapper
            const item = document.createElement('div');
            item.className = 'externe-laag-item';

            // Label wrapper (checkbox + kleur-dot + naam)
            const label = document.createElement('label');
            label.className = 'checkbox-label externe-laag-label';

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `toggle-externe-laag-${laag.id}`;
            checkbox.dataset.laagId = String(laag.id);

            // Custom checkbox span
            const checkboxCustom = document.createElement('span');
            checkboxCustom.className = 'checkbox-custom';

            // Kleur-dot die de lijnkleur van de laag toont
            const colorDot = document.createElement('span');
            colorDot.className = 'layer-color-dot';
            colorDot.style.backgroundColor = laag.kleur_lijn || '#8B5CF6';

            // Laagnaam (compact, zonder emoji)
            const labelText = document.createElement('span');
            labelText.className = 'layer-naam';
            labelText.textContent = laag.naam;

            label.appendChild(checkbox);
            label.appendChild(checkboxCustom);
            label.appendChild(colorDot);
            label.appendChild(labelText);
            // Interne laag (#254): alleen na inloggen in de lijst; met een label
            if (laag.toegang === 'intern') label.appendChild(internLabel());
            item.appendChild(label);

            // Inline beschrijving (verborgen, verschijnt bij klik op ℹ)
            let descDiv = null;
            if (laag.beschrijving) {
                // Info button
                const infoBtn = document.createElement('button');
                infoBtn.type = 'button';
                infoBtn.className = 'layer-info-btn';
                infoBtn.setAttribute('aria-label', `Informatie over ${laag.naam}`);
                infoBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
                item.appendChild(infoBtn);

                // Beschrijving div (inline, onder het item)
                descDiv = document.createElement('div');
                descDiv.className = 'layer-desc';
                descDiv.textContent = laag.beschrijving;

                // Click handler: toggle beschrijving
                infoBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // Sluit alle andere beschrijvingen
                    container.querySelectorAll('.layer-desc.open').forEach(d => {
                        if (d !== descDiv) d.classList.remove('open');
                    });
                    descDiv.classList.toggle('open');
                });
            }

            container.appendChild(item);
            if (descDiv) container.appendChild(descDiv);

            // Toggle event listener
            checkbox.addEventListener('change', async (e) => {
                if (e.target.checked) {
                    await laadExterneKaartlaagFeatures(laag);
                } else {
                    verwijderExterneKaartlaag(laag.id);
                }
            });
        });

        if (state.externeKaartlagen.length > 0) {
            console.log(`\u{1F310} ${state.externeKaartlagen.length} externe kaartlagen beschikbaar`);
        }
    } catch (e) {
        console.warn('\u26A0\uFE0F Externe kaartlagen konden niet worden geladen:', e.message);
    }
}

/**
 * Haalt features op via de backend WFS proxy en toont ze op de kaart.
 */
async function laadExterneKaartlaagFeatures(laag) {
    showLoading(true, `${laag.naam} laden...`);
    try {
        const res = await fetch(`/api/externe-lagen/${laag.id}/features`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const geojson = await res.json();

        state.externeKaartlaagData[laag.id] = { laag, geojson };

        // Re-render kaart met de nieuwe laag
        if (state.currentData) {
            displayOnMap(state.currentData);
        } else {
            renderExterneLagenOnly();
        }

        const count = geojson.features?.length || 0;
        console.log(`\u{1F310} ${laag.naam}: ${count} features geladen`);
    } catch (e) {
        console.error(`\u274C Fout bij laden ${laag.naam}:`, e);
        showError(`${laag.naam} kon niet worden geladen`);
        // Toggle terugzetten
        const toggle = document.getElementById(`toggle-externe-laag-${laag.id}`);
        if (toggle) toggle.checked = false;
    } finally {
        showLoading(false);
    }
}

/**
 * Verwijdert een externe kaartlaag van de kaart.
 */
function verwijderExterneKaartlaag(laagId) {
    delete state.externeKaartlaagData[laagId];
    if (state.currentData) {
        displayOnMap(state.currentData);
    } else {
        renderExterneLagenOnly();
    }
    console.log(`\u{1F310} Externe laag ${laagId} verwijderd van kaart`);
}

/**
 * Rendert alleen externe kaartlagen op de Deck.gl kaart,
 * voor gebruik wanneer er nog geen CBS-buurtdata geladen is.
 */
function renderExterneLagenOnly() {
    if (!state.deckgl) return;
    const { GeoJsonLayer } = deck;
    const layers = [];

    for (const [laagIdStr, entry] of Object.entries(state.externeKaartlaagData)) {
        const { laag, geojson: laagGeojson } = entry;
        if (!laagGeojson || !laagGeojson.features) continue;

        const hexToRgb = (hex) => {
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return [r, g, b];
        };
        const lijnKleur = hexToRgb(laag.kleur_lijn || '#8B5CF6');
        const fillKleur = hexToRgb(laag.kleur_fill || '#8B5CF6');
        const fillOpacity = Math.round((laag.opacity || 0.15) * 255);

        const externeLaag = new GeoJsonLayer({
            id: `externe-laag-${laagIdStr}`,
            data: laagGeojson,
            filled: true,
            stroked: true,
            extruded: false,

            getFillColor: [...fillKleur, fillOpacity],
            getLineColor: [...lijnKleur, 200],
            lineWidthUnits: 'pixels',
            getLineWidth: 3,
            lineWidthMinPixels: 2,

            pickable: true,
            autoHighlight: true,
            highlightColor: [...lijnKleur, 80],

            parameters: {
                depthTest: false,
                blend: true
            },

            onClick: (info) => {
                if (info.object && laag.laag_type === 'selectie') {
                    selectBuurtenVanExterneLaag(laag, info.object);
                }
            },

            updateTriggers: {
                getFillColor: [laagGeojson]
            }
        });
        layers.push(externeLaag);
    }

    state.deckgl.setProps({ layers });
}

/**
 * Selecteert CBS-buurten die binnen een extern laag-feature vallen.
 * Converteert GeoJSON geometry naar WKT en stuurt naar backend ST_Intersects.
 */
async function selectBuurtenVanExterneLaag(laag, feature) {
    const wkt = geojsonGeomToWkt(feature.geometry);
    if (!wkt) {
        console.warn('\u26A0\uFE0F Kon geometrie niet naar WKT converteren');
        return;
    }

    const groepNaam = feature.properties?.woonplaats || feature.properties?.naam || feature.properties?.name || feature.properties?.Naam || feature.properties?.Deelgebied || feature.properties?.deelgebied || null;
    if (!groepNaam) {
        console.warn('\u26A0\uFE0F Feature heeft geen naam/woonplaats property');
        return;
    }

    // Sprint 18 Track C: Toggle-logica — als deze woonplaats al geselecteerd is, verwijder de groep
    const bestaandeIndex = state.selectedGroepen.findIndex(g => g.naam === groepNaam);
    if (bestaandeIndex !== -1) {
        state.selectedGroepen.splice(bestaandeIndex, 1);
        rebuildSelectedGebiedIds();
        updateSelectionUI();
        if (state.currentData) displayOnMap(state.currentData);
        if (state.kompasWindow && state.kompasWindow.isVisible && window.kompasViz && window.kompasViz.currentConfigId) {
            loadKompasForSelection(window.kompasViz.currentConfigId);
        }
        console.log(`\u{1F4CD} Groep '${groepNaam}' verwijderd (toggle). ${state.selectedGroepen.length} groepen actief.`);
        return;
    }

    // Nieuwe groep toevoegen
    showLoading(true, `Buurten selecteren voor ${groepNaam}...`);
    try {
        const res = await fetch(`/api/externe-lagen/${laag.id}/buurten`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wkt: wkt })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.buurten.length === 0) {
            console.warn(`\u26A0\uFE0F Geen buurten gevonden voor '${groepNaam}'`);
            return;
        }

        // Voeg groep toe
        state.selectedGroepen.push({
            naam: groepNaam,
            buurtIds: data.buurten.map(b => b.id),
            laagId: laag.id
        });
        state.selectedLaagId = laag.id;
        rebuildSelectedGebiedIds();

        updateSelectionUI();
        if (state.currentData) {
            displayOnMap(state.currentData);
        }

        // Reload kompas als open
        if (state.kompasWindow && state.kompasWindow.isVisible && window.kompasViz && window.kompasViz.currentConfigId) {
            loadKompasForSelection(window.kompasViz.currentConfigId);
        }

        console.log(`\u{1F4CD} Groep '${groepNaam}' toegevoegd (${data.totaal} buurten). ${state.selectedGroepen.length} groepen actief.`);
    } catch (e) {
        console.error('\u274C Buurten selectie fout:', e);
        showError('Buurten konden niet worden geselecteerd');
    } finally {
        showLoading(false);
    }
}

/**
 * Converteert een GeoJSON geometry naar WKT string (voor ST_Intersects).
 * Ondersteunt Polygon en MultiPolygon.
 */
function geojsonGeomToWkt(geometry) {
    if (!geometry || !geometry.coordinates) return null;

    function ringToWkt(ring) {
        return ring.map(coord => `${coord[0]} ${coord[1]}`).join(', ');
    }

    if (geometry.type === 'Polygon') {
        const rings = geometry.coordinates.map(ring => `(${ringToWkt(ring)})`);
        return `POLYGON(${rings.join(', ')})`;
    }
    if (geometry.type === 'MultiPolygon') {
        const polygons = geometry.coordinates.map(poly => {
            const rings = poly.map(ring => `(${ringToWkt(ring)})`);
            return `(${rings.join(', ')})`;
        });
        return `MULTIPOLYGON(${polygons.join(', ')})`;
    }
    return null;
}

// ============================================================================
// Map Visualization with deck.gl
// ============================================================================

function displayOnMap(geojson) {
    const { GeoJsonLayer } = deck;

    // Bronvermelding 3DBAG (CC BY 4.0) alleen tonen als de panden zichtbaar zijn
    const bron3dbag = document.getElementById('bronvermelding-3dbag');
    if (bron3dbag) bron3dbag.hidden = !(state.show3DBuildings && state.bag3dData);

    if (!geojson.features || geojson.features.length === 0) {
        // Prevent blocking alert on re-renders/clicks if data is unexpectedly empty
        console.warn('⚠️ displayOnMap called with empty/invalid data');
        if (!state.currentData && !state.selectedGebiedId) {
            // Only show alert if truly no data and not in a selection flow
            showError('Geen gebieden gevonden voor deze combinatie');
        }
        return;
    }

    // Calculate min/max voor color scale
    const values = geojson.features
        .map(f => f.properties.indicator_waarde)
        .filter(v => v !== null && v !== undefined);

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);

    // Store for legenda
    state.currentMinValue = minValue;
    state.currentMaxValue = maxValue;

    console.log(`📊 Data range: ${minValue} - ${maxValue}`);

    // Debug data values
    console.log(`📊 Validating data for ${geojson.features.length} features`);
    const validValues = values.filter(v => typeof v === 'number');
    console.log(`📊 Numeric values: ${validValues.length}, NaN: ${values.length - validValues.length}`);
    if (validValues.length > 0) {
        console.log(`📊 Range: ${Math.min(...validValues)} - ${Math.max(...validValues)}`);
    }

    // Performance FIX: DO NOT sort the features array. Mutating/recreating the data object 
    // destroys Deck.gl's internal caching and forces a full re-tessellation of all polygons, 
    // causing massive lag on click.
    const renderGeojson = geojson;

    // Create GeoJsonLayer (Unieke ID per scope dwingt deck.gl om WebGL- en tessellatie-buffers
    // volledig te vernieuwen bij scope-wissels. Voorkomt buffer-corruptie/spikes.
    // Transitions vervallen hierdoor bewust bij gemeente/type-wissel).
    const layer = new GeoJsonLayer({
        id: `gebieden-layer-${state.enable3D ? '3d' : '2d'}-${state.currentGebiedstype || 'def'}-${state.currentGemeenteCode || 'all'}`,
        data: renderGeojson,

        // Rendering
        filled: true,
        stroked: true,
        extruded: state.enable3D,
        wireframe: false,

        // Colors
        getFillColor: d => {
            // Track D: Geselecteerde buurten behouden hun indicator-kleur
            // (gouden outline vervangt de oude gold fill-override)
            const value = d.properties.indicator_waarde;
            // #255: kaartmodus 'uit' kleurt als zonder data; de indicator blijft gekozen
            // #373: subtiele, lichte tint zodat de ondergrond (PDOK) goed zichtbaar blijft
            if (value === null || value === undefined || state.kaartModus === 'uit') {
                const isDark = state.currentTheme === 'dark';
                const r = isDark ? 160 : 180;
                const g = isDark ? 160 : 180;
                const b = isDark ? 160 : 180;
                // Subtiele transparantie (in 3D plat op de grond, geen donker blok omhoog)
                const a = isDark
                    ? (state.enable3D ? 60 : 35)
                    : (state.enable3D ? 70 : 45);
                return [r, g, b, a];
            }

            // Use Backend Color if available (Sync with Kompas)
            if (d.properties.color) {
                const hex = d.properties.color;
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                const opacity = state.enable3D ? 255 : (state.currentTheme === 'dark' ? 204 : 240);
                return [r, g, b, opacity];
            }

            // Fallback (Client-side calc)
            return getColorRGB(value, minValue, maxValue, state.enable3D);
        },

        // Track D: Gouden outline bij selectie, borders voor overige
        getLineColor: d => {
            const featureId = d.id || d.properties?.id;
            if (featureId && isGebiedSelected(featureId)) {
                return [234, 179, 8, 255]; // Selectie goud (#eab308)
            }
            const value = d.properties?.indicator_waarde;
            const isNoData = value === null || value === undefined || state.kaartModus === 'uit';
            if (isNoData) {
                // #373: Randen van gebieden zonder data herkenbaar houden op lichte/donkere ondergrond
                return state.currentTheme === 'dark'
                    ? [200, 200, 200, 160]
                    : [120, 120, 120, 160];
            }
            return [255, 255, 255, 200]; // Witte border voor ingekleurde gebieden
        },
        getLineWidth: d => {
            const featureId = d.id || d.properties?.id;
            if (featureId && isGebiedSelected(featureId)) {
                return 80; // Dikke gouden rand bij selectie
            }
            return 20; // Standaard dunne rand
        },

        // 3D Height (#373: bij geen data of modus 'uit' altijd plat op de grond)
        getElevation: d => {
            if (!state.enable3D || state.kaartModus === 'uit') return 0;

            const value = d.properties.indicator_waarde;
            if (value === null || value === undefined) return 0;

            // Normalize en scale
            const normalized = (value - minValue) / (maxValue - minValue);
            return normalized * 1000 * state.heightScale;
        },

        // Interactivity
        pickable: true,
        autoHighlight: true,
        highlightColor: [234, 179, 8, 150], // Geo Gold hover (#eab308)

        // Track B4: Hover cursor feedback
        onHover: (info) => {
            setMapHoverCursor(!!info.object);
        },

        // 3D Material Properties for Lighting (Only in 3D)
        material: state.enable3D ? {
            ambient: 0.8,    // High ambient reflection to preserve base color
            diffuse: 0.6,    // Moderate diffuse
            shininess: 0,    // Pure matte (0 shininess)
            specularColor: [0, 0, 0] // No white specular highlights to prevent washing out the flat tops
        } : false, // Explicitly disable complex material lighting for 2D map

        // Render Parameters to prevent Z-fighting in 2D
        parameters: {
            depthTest: state.enable3D, // Disable depth testing in 2D to avoid z-fighting with basemap
            blend: true
        },

        onClick: (info, event) => {
            // Sprint 18 F3: Clear visual highlight on any map click
            if (state.highlightedGebiedId) {
                state.highlightedGebiedId = null;
            }

            if (info.object) {
                const gebiedId = info.object.id || (info.object.properties && info.object.properties.id);
                const gebiedNaam = (info.object.properties && info.object.properties.naam) ? info.object.properties.naam : gebiedId;

                if (!gebiedId) return;

                // Multi-Select: Shift+Click voegt toe/verwijdert, normale click vervangt
                const isMultiSelect = event?.srcEvent?.shiftKey || event?.srcEvent?.ctrlKey || event?.srcEvent?.metaKey;

                if (isMultiSelect) {
                    toggleGebiedSelection(gebiedId);
                    console.log(`🔀 Multi-select toggle: ${gebiedNaam} (${gebiedId}). Totaal: ${state.selectedGebiedIds.size}`);
                } else {
                    clearGebiedSelection();
                    state.selectedGebiedIds.add(gebiedId);
                    console.log(`📍 Gebied geselecteerd: ${gebiedNaam} (${gebiedId})`);
                }

                // Update Rapport Output UI
                updateSelectionUI();

                // Load gebied details (voor het laatst aangeklikte gebied)
                loadGebiedDetails(gebiedId);

                // Kompas-paneel actief: open het Kompas-venster automatisch (zoals de hint belooft)
                if (state.activePanelId === 'kompas' && state.kompasWindow && !state.kompasWindow.isVisible) {
                    state.kompasWindow.open();
                }

                // Trigger re-render to show selection highlight
                // Reload kompas data if window is already open
                if (state.kompasWindow && state.kompasWindow.isVisible && window.kompasViz && window.kompasViz.currentConfigId) {
                    loadKompasForSelection(window.kompasViz.currentConfigId);
                }

                if (state.currentData && state.currentData.features && state.currentData.features.length > 0) {
                    try {
                        displayOnMap(state.currentData);
                    } catch (e) {
                        console.error('⚠️ Fout tijdens displayOnMap:', e);
                    }
                } else {
                    console.warn('⚠️ Cannot re-render map: state.currentData is empty/invalid');
                }

                // Camera: Auto-pan to selected area (UI Polish)
                if (!isMultiSelect) {
                    const originalFeature = state.currentData && state.currentData.features 
                        ? state.currentData.features.find(f => (f.id || f.properties?.id) === gebiedId) 
                        : null;
                    const safeFeature = originalFeature || info.object;
                    // Diepe kopie van coördinaten om garbage collection/recycling te voorkomen
                    const safeCoordinate = info.coordinate ? [...info.coordinate] : null;

                    // Decouple from MapController event loop
                    setTimeout(() => {
                        try {
                            flyToGebied(safeFeature, safeCoordinate);
                        } catch (e) {
                            console.error('⚠️ Fout tijdens flyToGebied animatie:', e);
                        }
                    }, 50);
                }
                
                return true; // Stop propagation to prevent MapController from canceling the transition
            }
        },

        // Smooth transitions - RESTORED per UI Polish Plan
        // Note: Artifacts may occur when switching 2D/3D, but smooth data updates are preferred
        transitions: {
            getFillColor: 300,
            getElevation: 500
        },

        // Track D: lineWidthMinPixels zodat gouden rand altijd zichtbaar is
        lineWidthMinPixels: 1,

        // Performance - CRITICAL FIX: Force re-render on state changes
        updateTriggers: {
            getFillColor: [minValue, maxValue, state.enable3D, state.currentTheme, state.kaartModus],
            getLineColor: [state.currentTheme, state.kaartModus, Array.from(state.selectedGebiedIds).join(',')],
            getLineWidth: [Array.from(state.selectedGebiedIds).join(',')],
            getElevation: [state.enable3D, state.heightScale, minValue, maxValue, state.kaartModus],
            extruded: [state.enable3D]
        }

    });

    // Build layers array (gebieden + optioneel BAG panden)
    const layers = [layer];

    // Performance FIX: Add a separate layer for selected borders to ensure they are drawn on top,
    // without sorting the base layer data.
    if (state.selectedGebiedIds.size > 0 && geojson.features) {
        const selectedFeatures = geojson.features.filter(f => {
            const id = f.id || f.properties?.id;
            return state.selectedGebiedIds.has(id);
        });

        if (selectedFeatures.length > 0) {
            const { GeoJsonLayer } = deck;
            const selectionLayer = new GeoJsonLayer({
                id: 'selection-overlay-layer',
                data: { type: 'FeatureCollection', features: selectedFeatures },
                filled: false,
                stroked: true,
                lineWidthMinPixels: 2,
                getLineColor: [234, 179, 8, 255], // Geo Gold (#eab308)
                lineWidthUnits: 'pixels',
                getLineWidth: 3,
                pickable: false,
                parameters: {
                    depthTest: false // Force draw on top in 2D
                }
            });
            layers.push(selectionLayer);
        }
    }

    // Sprint 18 F3: Extra layer voor Top-buurt highlight (Altijd on top, onafhankelijk van dash bugs in 3D/base layer)
    if (state.highlightedGebiedId && geojson.features) {
        const highlightFeature = geojson.features.find(f => {
            const id = f.id || f.properties?.id;
            return id === state.highlightedGebiedId;
        });
        
        if (highlightFeature) {
            const { GeoJsonLayer } = deck;
            const highlightLayer = new GeoJsonLayer({
                id: 'highlight-layer',
                data: { type: 'FeatureCollection', features: [highlightFeature] },
                extensions: [new deck.PathStyleExtension({dash: true})],
                stroked: true,
                filled: false,
                lineWidthUnits: 'pixels',
                getLineColor: [236, 201, 75, 255], // Geo Gold (#ECC94B)
                getLineWidth: 6, // 6 pixels dik, consistent ongeacht zoom level
                getLineDashArray: d => [2, 1], // [dash, gap]
                getDashArray: d => [2, 1], // Sometimes required instead of getLineDashArray
                dashJustified: false, // Zet op false om render-issues met justifed path lengths te voorkomen
                dashGapPickable: true,
                pickable: false, // Klik-events vangen we al op de base layer
                parameters: {
                    depthTest: false // FORCEERT rendering BÓVENOP alle andere 2D/3D lagen
                }
            });
            layers.push(highlightLayer);
        }
    }

    // Sprint 12: 3D BAG Panden layer
    if (state.show3DBuildings && state.bag3dData && state.bag3dData.features) {
        const bag3dLayer = new GeoJsonLayer({
            id: 'bag3d-layer',
            data: state.bag3dData,
            filled: true,
            stroked: true,
            extruded: true,
            wireframe: false,

            getElevation: f => {
                const dakHoogte = f.properties.b3_h_50p ?? f.properties.b3_h_dak_50p ?? 8;
                const maaiveld = f.properties.b3_h_maaiveld ?? 0;
                return Math.max(dakHoogte - maaiveld, 3); // Minimaal 3m hoogte
            },

            // Indicator-kleur (verrijkt door backend)
            getFillColor: f => {
                const hex = f.properties.indicator_color;
                if (!hex || hex === '#888888') return [160, 160, 160, 220];
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                return [r, g, b, 230];
            },
            getLineColor: [255, 255, 255, 60],
            getLineWidth: 1,

            pickable: true,
            autoHighlight: true,
            highlightColor: [234, 179, 8, 150],

            material: {
                ambient: 0.65,
                diffuse: 0.7,
                shininess: 0,
                specularColor: [0, 0, 0]
            },

            parameters: {
                depthTest: true,
                blend: true
            },

            updateTriggers: {
                getFillColor: [state.bag3dData],
                getElevation: [state.bag3dData]
            }
        });
        layers.push(bag3dLayer);
    }

    // Sprint 18: Externe kaartlagen overlay layers
    for (const [laagIdStr, entry] of Object.entries(state.externeKaartlaagData)) {
        const { laag, geojson: laagGeojson } = entry;
        if (!laagGeojson || !laagGeojson.features) continue;

        // Parse kleur hex naar RGB array
        const hexToRgb = (hex) => {
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return [r, g, b];
        };
        const lijnKleur = hexToRgb(laag.kleur_lijn || '#8B5CF6');
        const fillKleur = hexToRgb(laag.kleur_fill || '#8B5CF6');
        const fillOpacity = Math.round((laag.opacity || 0.15) * 255);

        const externeLaag = new GeoJsonLayer({
            id: `externe-laag-${laagIdStr}`,
            data: laagGeojson,
            filled: true,
            stroked: true,
            extruded: false,

            getFillColor: [...fillKleur, fillOpacity],
            getLineColor: [...lijnKleur, 200],
            lineWidthUnits: 'pixels',
            getLineWidth: 3,
            lineWidthMinPixels: 2,

            pickable: true,
            autoHighlight: true,
            highlightColor: [...lijnKleur, 80],

            parameters: {
                depthTest: false,
                blend: true
            },

            onClick: (info) => {
                if (info.object && laag.laag_type === 'selectie') {
                    selectBuurtenVanExterneLaag(laag, info.object);
                }
            },

            updateTriggers: {
                getFillColor: [laagGeojson]
            }
        });
        layers.push(externeLaag);
    }

    // Omgevingsvisie Deelgebieden overlay layer
    if (state.showOmgevingsvisieLayer && state.omgevingsvisieData && state.omgevingsvisieData.features) {
        const omgVisieLayer = new GeoJsonLayer({
            id: 'omgevingsvisie-layer',
            data: state.omgevingsvisieData,
            filled: true,
            stroked: true,
            extruded: false,

            // Semi-transparante fill zodat CBS-laag eronder zichtbaar blijft
            getFillColor: [138, 43, 226, 25],    // Paars, zeer transparant
            getLineColor: [138, 43, 226, 255],   // Paars, duidelijk zichtbaar
            lineWidthUnits: 'pixels',
            getLineWidth: 3,                     // 3px breed = duidelijk zichtbare grens
            lineWidthMinPixels: 3,

            pickable: true,
            autoHighlight: true,
            highlightColor: [138, 43, 226, 80],   // Paars hover highlight

            parameters: {
                depthTest: false,
                blend: true
            },

            onClick: (info) => {
                if (info.object) {
                    const props = info.object.properties;
                    selectBuurtenFromDeelgebied(props.id, props.deelgebied);
                }
            },

            updateTriggers: {
                getFillColor: [state.omgevingsvisieData]
            }
        });
        layers.push(omgVisieLayer);
    }

    state.deckgl.setProps({ layers });

    // Auto-zoom to data (Sprint 16: alleen bij initieel laden, niet bij selectie-re-renders)
    if (geojson.features.length > 0 && !state.initialDataLoaded) {
        // #258: bij de eerste kaart de laatste kaartpositie van de ingelogde gebruiker
        if (state.herstelPositie) {
            zetKaartPositie(state.herstelPositie);
            state.herstelPositie = null;
        } else {
            fitBounds(geojson);
        }
        state.initialDataLoaded = true;
    }
}

/** #258: camera naar een bewaarde kaartpositie ({longitude, latitude, zoom, pitch, bearing}). */
function zetKaartPositie(positie) {
    if (!state.deckgl || !positie) return;
    state.currentViewState = {
        ...state.currentViewState,
        longitude: positie.longitude,
        latitude: positie.latitude,
        zoom: positie.zoom,
        pitch: positie.pitch ?? state.currentViewState.pitch,
        bearing: positie.bearing ?? state.currentViewState.bearing,
    };
    state.deckgl.setProps({ viewState: state.currentViewState });
}
window.zetKaartPositie = zetKaartPositie;

function fitBounds(geojson) {
    // Bounding box over alle coördinaten (Polygon en MultiPolygon)
    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    const walk = (arr) => {
        if (!Array.isArray(arr)) return;
        if (typeof arr[0] === 'number') {
            minLon = Math.min(minLon, arr[0]);
            maxLon = Math.max(maxLon, arr[0]);
            minLat = Math.min(minLat, arr[1]);
            maxLat = Math.max(maxLat, arr[1]);
        } else {
            arr.forEach(walk);
        }
    };
    geojson.features.forEach(feature => {
        if (feature.geometry) walk(feature.geometry.coordinates);
    });
    if (minLon === Infinity) return;

    // Kaartgrootte en padding: vrije zone naast linkerpaneel en chat, ruimte voor de badge
    const mapEl = document.getElementById('map');
    const width = (mapEl && mapEl.clientWidth) || window.innerWidth;
    const height = (mapEl && mapEl.clientHeight) || window.innerHeight;
    const leftPanel = document.querySelector('.panel-container.open') ? 360 : 0;
    const chatOpen = document.getElementById('chat-panel')?.classList.contains('open');
    let padding = { top: 40, bottom: 80, left: 70 + leftPanel + 40, right: (chatOpen ? 380 : 0) + 40 };
    if (width - padding.left - padding.right < 100 || height - padding.top - padding.bottom < 100) {
        padding = 20;
    }

    let longitude, latitude, zoom;
    if (typeof deck !== 'undefined' && deck.WebMercatorViewport) {
        const vp = new deck.WebMercatorViewport({ width, height })
            .fitBounds([[minLon, minLat], [maxLon, maxLat]], { padding, maxZoom: 16 });
        ({ longitude, latitude, zoom } = vp);
    } else {
        // Handmatig (Web Mercator): zoom waarbij de bbox binnen het vrije deel past
        const pad = typeof padding === 'number'
            ? { top: padding, bottom: padding, left: padding, right: padding } : padding;
        const mercY = lat => Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));
        const worldX = Math.max(maxLon - minLon, 1e-9) / 360;
        const worldY = Math.max(mercY(maxLat) - mercY(minLat), 1e-9) / (2 * Math.PI);
        const zoomX = Math.log2((width - pad.left - pad.right) / (512 * worldX));
        const zoomY = Math.log2((height - pad.top - pad.bottom) / (512 * worldY));
        zoom = Math.min(zoomX, zoomY, 16);
        // Midden van de bbox naar het midden van de vrije zone schuiven
        const scale = 512 * Math.pow(2, zoom);
        const centerY = (mercY(maxLat) + mercY(minLat)) / 2
            - ((pad.bottom - pad.top) / 2) / scale * 2 * Math.PI;
        longitude = (minLon + maxLon) / 2 - ((pad.left - pad.right) / 2) / scale * 360;
        latitude = (2 * Math.atan(Math.exp(centerY)) - Math.PI / 2) * 180 / Math.PI;
    }

    // Zelfde mechanisme als de rest van de app: gecontroleerde viewState
    state.currentViewState = {
        ...state.currentViewState,
        longitude,
        latitude,
        zoom,
        pitch: state.enable3D ? 45 : 0,
        bearing: 0,
        ...A11y.cameraTransition(1000, true)
    };
    state.deckgl.setProps({ viewState: state.currentViewState });
}

// ============================================================================
// Color Scale Function (Theme-Aware)
// ============================================================================

function getColorRGB(value, min, max) {
    // Normalize value to 0-1
    const normalized = Math.max(0, Math.min(1, (value - min) / (max - min) || 0));

    // Dark mode: brighter neon colors
    if (state.currentTheme === 'dark') {
        if (normalized < 0.5) {
            // Cyan to Yellow (brighter)
            const t = normalized * 2;
            return [
                Math.round(30 + (225 * t)),     // R: 30 → 255
                Math.round(144 + (111 * t)),    // G: 144 → 255
                Math.round(255 * (1 - t)),      // B: 255 → 0
                255                              // Force 100% opacity to debug visibility
            ];
        } else {
            // Yellow to Red
            const t = (normalized - 0.5) * 2;
            return [
                255,                             // R: 255
                Math.round(255 * (1 - t)),       // G: 255 → 30
                0,                               // B: 0
                255                              // Force 100% opacity to debug visibility
            ];
        }
    } else {
        // Light mode: original muted colors
        if (normalized < 0.5) {
            // Blue to Yellow (muted)
            const t = normalized * 2;
            return [
                Math.round(0 + (255 * t)),       // R: 0 → 255
                Math.round(100 + (155 * t)),     // G: 100 → 255
                Math.round(255 * (1 - t)),       // B: 255 → 0
                240                              // Higher opacity (~94%) for light mode visibility
            ];
        } else {
            // Yellow to Red
            const t = (normalized - 0.5) * 2;
            return [
                255,                             // R: 255
                Math.round(255 * (1 - t)),       // G: 255 → 0
                0,                               // B: 0
                240                              // Higher opacity (~94%) for light mode visibility
            ];
        }
    }
}

// ============================================================================
// Legenda Generator (NEW)
// ============================================================================

/**
 * #255: klassen in de legenda. Percentiel: klasse 1-8 met label; werkelijke waarde: het
 * bereik van de gebieden per kleur. Met klassen vervangt de lijst het kleurverloop.
 * Modus 'uit': geen kleuren, wel een melding.
 */
function renderLegendaKlassen(metadata) {
    document.querySelectorAll('input[name="kaart-modus"]').forEach(r => {
        r.checked = r.value === state.kaartModus;
    });
    const lijst = document.getElementById('legenda-klassen');
    if (!lijst) return;
    const uit = state.kaartModus === 'uit';
    const klassen = (!uit && Array.isArray(metadata?.klassen)) ? metadata.klassen : [];
    const uitTekst = document.getElementById('legenda-modus-uit');
    // via display: .help-text zet display en zou het hidden-attribuut overrulen
    if (uitTekst) uitTekst.style.display = uit ? '' : 'none';
    const verloop = !uit && klassen.length === 0;
    const svg = document.getElementById('color-gradient-bar');
    const labels = document.querySelector('#color-scale-container .legenda-labels');
    if (svg) svg.style.display = verloop ? '' : 'none';
    if (labels) labels.style.display = verloop ? '' : 'none';

    const eenheid = metadata?.eenheid ? ` ${metadata.eenheid}` : '';
    lijst.dataset.modus = uit ? 'uit' : (metadata?.modus || 'waarde');
    lijst.innerHTML = klassen.map(k => {
        const label = metadata.modus === 'percentiel'
            ? k.label
            : metadata.modus === 'label'
            ? k.omschrijving  // #256: 'label A (gunstigst), kwintiel 80–100%'
            : (k.van === k.tot
                ? `${formatNumber(k.van)}${eenheid}`
                : `${formatNumber(k.van)} – ${formatNumber(k.tot)}${eenheid}`);
        const aantal = k.aantal !== undefined
            ? `<span class="legenda-klasse-aantal" title="aantal gebieden">${escapeHtml(k.aantal)}</span>`
            : '';
        return `<li data-klasse="${escapeHtml(k.klasse ?? '')}">`
            + `<span class="legenda-klasse-kleur" style="background:${escapeHtml(k.kleur)}"></span>`
            + `<span>${escapeHtml(label)}</span>${aantal}</li>`;
    }).join('');
}

/**
 * #255: kaartmodus wisselen. 'uit' (en terug naar de geladen data) tekent alleen opnieuw;
 * een andere modus haalt de kaartdata opnieuw op.
 */
async function setKaartModus(modus) {
    if (!KAART_MODI.includes(modus) || modus === state.kaartModus) return;
    const vorige = state.kaartModus;
    state.kaartModus = modus;
    try { localStorage.setItem('omnitwin-kaartmodus', modus); } catch (e) { /* geen opslag */ }
    if (!state.currentIndicator || !state.currentData) {
        renderLegendaKlassen(state.currentData?.metadata);
        return;
    }
    const geladen = state.currentData.metadata?.modus || 'waarde';
    if (modus === 'uit' || (vorige === 'uit' && geladen === modus)) {
        displayOnMap(state.currentData);
        updateLegenda(state.currentData);
    } else {
        await loadKaartData();
    }
}
window.setKaartModus = setKaartModus;

function updateLegenda(geojson) {
    /**
     * Unified Legend Update Function
     * Called from:
     *   1. loadKaartData() - after loading map data via Kaart Configuratie
     *   2. handleIndicatorSelection() - after Kompas indicator click (via EventBus)
     * 
     * Updates:
     *   - Color gradient bar (SVG)
     *   - Min/Max labels  
     *   - Coverage bar + text
     *   - Help text visibility
     */
    const container = document.getElementById('color-scale-container');
    const svg = document.getElementById('color-gradient-bar');
    const minLabel = document.getElementById('legend-min-label');
    const maxLabel = document.getElementById('legend-max-label');
    const coverageText = document.getElementById('coverage-text');
    const coverageFill = document.getElementById('coverage-fill');
    const helpText = document.querySelector('#legenda-content > .help-text');
    const labels = document.querySelector('.legenda-labels');

    console.log('📊 updateLegenda called', {
        hasGeojson: !!geojson,
        hasMetadata: !!geojson?.metadata,
        currentIndicator: state.currentIndicator
    });

    // No indicator selected → show placeholder text, hide reset button
    if (!state.currentIndicator) {
        if (container) container.style.display = 'none';
        if (helpText) helpText.style.display = 'block';
        const resetBtn = document.getElementById('reset-indicator-btn');
        if (resetBtn) resetBtn.style.display = 'none';
        return;
    }

    // Indicator active → show reset button
    const resetBtn = document.getElementById('reset-indicator-btn');
    if (resetBtn) resetBtn.style.display = 'flex';

    // No data yet → keep existing state
    if (!geojson || !geojson.metadata) {
        console.warn('⚠️ updateLegenda: waiting for data...');
        return;
    }

    // Hide placeholder, show legend
    if (helpText) helpText.style.display = 'none';
    if (container) container.style.display = 'block';

    // Get indicator name from dropdown or metadata
    let indicatorNaam = 'Indicator';
    const select = document.getElementById('indicator-select');
    if (select && select.selectedIndex >= 0) {
        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.text) {
            indicatorNaam = selectedOption.text.split(' (')[0];
        }
    }
    // Fallback: use metadata indicator name if available
    if (geojson.metadata.indicator_naam) {
        indicatorNaam = geojson.metadata.indicator_naam;
    }

    // Update min/max labels
    if (minLabel) minLabel.textContent = formatNumber(state.currentMinValue);
    if (maxLabel) maxLabel.textContent = formatNumber(state.currentMaxValue);

    // Also update .legenda-labels for CSS gradient display
    if (labels) {
        labels.innerHTML = `
            <span>${formatNumber(state.currentMinValue)}</span>
            <span>${formatNumber(state.currentMaxValue)}</span>
        `;
    }

    // Generate SVG gradient bar — dynamisch op basis van backend color_ramp (Gap G7 fix)
    if (svg) {
        const colorRamp = geojson.metadata?.color_ramp;
        let stopsHtml = '';

        if (colorRamp && colorRamp.length > 0) {
            // Dynamisch: verdeel de klassen gelijkmatig over 0%–100%
            const step = colorRamp.length > 1 ? 100 / (colorRamp.length - 1) : 100;
            colorRamp.forEach((hexColor, i) => {
                const offset = colorRamp.length > 1 ? i * step : 0;
                stopsHtml += `<stop offset="${offset.toFixed(1)}%" style="stop-color:${escapeHtml(hexColor)};stop-opacity:1" />\n`;
            });
        } else {
            // Fallback naar de oude hardcoded blauw-geel-rood
            stopsHtml = `
                <stop offset="0%"   style="stop-color:rgb(0,100,255);stop-opacity:1" />
                <stop offset="50%"  style="stop-color:rgb(255,255,0);stop-opacity:1" />
                <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />`;
        }

        svg.innerHTML = `
            <defs>
                <linearGradient id="color-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    ${stopsHtml}
                </linearGradient>
            </defs>
            <rect width="100%" height="100%" fill="url(#color-gradient)" />
        `;
    }

    // #255: kaartmodus en klassen (percentielklasse of bereik per kleur)
    renderLegendaKlassen(geojson.metadata);

    // Update coverage bar
    const total = geojson.metadata.total_features || 0;
    const withData = geojson.metadata.features_with_data || 0;
    const percentage = total > 0 ? Math.round((withData / total) * 100) : 0;

    if (coverageText) coverageText.textContent = `${withData} van ${total} gebieden (${percentage}%)`;
    if (coverageFill) coverageFill.style.width = `${percentage}%`;

    // Track D: Selectie- en no-data hints in legenda
    let hintsContainer = document.getElementById('legenda-hints');
    if (!hintsContainer && container) {
        hintsContainer = document.createElement('div');
        hintsContainer.id = 'legenda-hints';
        container.parentElement.appendChild(hintsContainer);
    }
    if (hintsContainer) {
        // #161: geen spreiding in de waarden (alle gebieden dezelfde waarde)
        const melding = geojson.metadata.legenda_melding;
        hintsContainer.innerHTML = `
            ${melding ? `<p class="legenda-melding help-text" role="note">${escapeHtml(melding)}</p>` : ''}
            <div class="legenda-selectie-hint">
                <span class="legenda-selectie-sample"></span>
                <span>Geselecteerd gebied</span>
            </div>
            <div class="legenda-nodata-hint">
                <span class="legenda-nodata-sample"></span>
                <span>Geen data beschikbaar</span>
            </div>
        `;
    }

    console.log(`📊 Legenda updated: ${indicatorNaam}, range: ${formatNumber(state.currentMinValue)} - ${formatNumber(state.currentMaxValue)}, coverage ${percentage}%`);
}


// ============================================================================
// UI Update Functions
// ============================================================================

/**
 * Reset de kaart naar basisweergave (geen indicator-kleuring).
 * Behoudt de gebiedsselectie en configuratie, wist alleen de indicator.
 */
function resetKaartIndicator() {
    console.log('🔄 Kaart reset: indicator wissen');

    // Reset state
    state.currentIndicator = null;
    state.currentData = null;
    state.currentMinValue = null;
    state.currentMaxValue = null;

    // Track B3: Badge wissen
    updateIndicatorBadge(null);

    // Reset indicator dropdown
    const select = document.getElementById('indicator-select');
    if (select) select.value = '';
    const coverageEl = document.getElementById('indicator-coverage');
    if (coverageEl) coverageEl.textContent = 'Selecteer een indicator';

    // Hide reset button & legend
    const resetBtn = document.getElementById('reset-indicator-btn');
    if (resetBtn) resetBtn.style.display = 'none';
    const container = document.getElementById('color-scale-container');
    if (container) container.style.display = 'none';
    const helpText = document.querySelector('#legenda-content > .help-text');
    if (helpText) helpText.style.display = 'block';

    // Reload map without indicator (just geometries, default grey)
    if (typeof loadKaartData === 'function') {
        loadKaartData();
    }

    updateButtonState();
    console.log('✅ Kaart gereset naar basisweergave');
}

function populateGebiedstypeSelect(gebiedstypes) {
    const select = document.getElementById('gebiedstype-select');
    select.innerHTML = '<option value="">Selecteer een gebiedstype</option>';

    select.addEventListener('change', (e) => {
        state.currentGebiedstype = e.target.value;
        const selectedOption = e.target.options[e.target.selectedIndex];
        
        if (e.target.value) {
            document.getElementById('gebiedstype-count').textContent = 'Gegevens laden...';
        } else {
            document.getElementById('gebiedstype-count').textContent = 'Selecteer een gebiedstype';
        }
    });

    gebiedstypes.forEach(gt => {
        const option = document.createElement('option');
        option.value = gt.id;
        option.textContent = gt.naam;
        select.appendChild(option);
    });

    document.getElementById('gebiedstype-count').textContent = 'Selecteer een gebiedstype';
}

function populateIndicatorSelect(indicatoren) {
    const select = document.getElementById('indicator-select');
    select.innerHTML = '<option value="">Selecteer een indicator</option>';
    select.disabled = false;

    indicatoren.forEach(ind => {
        const option = document.createElement('option');
        option.value = ind.uuid;

        // Show coverage in option text
        const coverage = ind.aantal_gebieden_met_data || 0;
        option.textContent = coverage > 0
            ? `${ind.naam} (${coverage} gebieden)`
            : `${ind.naam} (geen data)`;

        if (ind.toegang === 'intern') option.textContent += ' · intern';  // #254: alleen na inloggen
        option.dataset.coverage = coverage;
        option.dataset.eenheid = ind.eenheid || '';

        // Disable options without data
        if (coverage === 0) {
            option.disabled = true;
            option.style.color = 'var(--text-secondary)';
        }

        select.appendChild(option);
    });

    const totalWithData = indicatoren.filter(i => (i.aantal_gebieden_met_data || 0) > 0).length;
    document.getElementById('indicator-coverage').textContent =
        `${totalWithData} van ${indicatoren.length} indicatoren hebben data`;

    // Track C: Bouw ook de accordion (async, wacht niet)
    buildIndicatorAccordion(indicatoren);

    // Enable button if both selected
    updateButtonState();
}

function updateButtonState() {
    const btn = document.getElementById('toon-kaart-btn');
    const gebiedstypeSelected = !!state.currentGebiedstype;

    // Enable if gebiedstype selected (indicator OPTIONAL)
    btn.disabled = !gebiedstypeSelected;

    // Update text based on selection
    if (gebiedstypeSelected && !state.currentIndicator) {
        // SVG icon + text update
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-map" style="margin-right: 8px;">
                <path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z" />
                <path d="M15 5.764v15" />
                <path d="M9 3.236v15" />
            </svg>
            Toon Gebieden (outlines)
        `;
    } else {
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-map" style="margin-right: 8px;">
                <path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z" />
                <path d="M15 5.764v15" />
                <path d="M9 3.236v15" />
            </svg>
            Toon op Kaart
        `;
    }
}

function updateFeatureCount(metadata) {
    const countEl = document.getElementById('feature-count');
    const valueEl = document.getElementById('feature-count-value');

    if (metadata) {
        valueEl.textContent = metadata.features_with_data || metadata.total_features;
        countEl.style.display = 'block';
        countEl.classList.add('fade-in');
    } else {
        countEl.style.display = 'none';
    }
}

function displayGebiedDetails(data) {
    const panel = document.getElementById('gebied-info');
    const content = document.getElementById('gebied-details');

    const gebied = data.gebied;
    const indicatoren = data.indicatoren;

    // Note: Rapport panel text is managed by updateSelectionUI() (Sprint 7 multi-select)

    // Sprint 7: Als meerdere gebieden geselecteerd, toon vergelijking
    if (state.selectedGebiedIds.size > 1) {
        displayMultiGebiedComparison(data);
        return;
    }

    let html = `
    <div class="detail-row">
      <span class="detail-label">ID:</span>
      <span class="detail-value">${escapeHtml(gebied.id)}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Naam:</span>
      <span class="detail-value">${escapeHtml(gebied.naam)}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Type:</span>
      <span class="detail-value">${escapeHtml(gebied.gebiedstype.naam)}</span>
    </div>
  `;

    if (indicatoren && indicatoren.length > 0) {
        html += '<h4>Indicatoren</h4>';
        indicatoren.slice(0, 10).forEach(ind => {
            html += `
        <div class="detail-row">
          <span class="detail-label">${escapeHtml(ind.naam)}:</span>
          <span class="detail-value">${formatNumber(ind.waarde)} ${escapeHtml(ind.eenheid || '')}</span>
        </div>
      `;
        });

        if (indicatoren.length > 10) {
            html += `<p><small>... en ${indicatoren.length - 10} meer</small></p>`;
        }
    } else {
        html += '<p><em>Geen indicator data beschikbaar</em></p>';
    }

    content.innerHTML = html;
    panel.style.display = 'block';
}

/**
 * Sprint 7: Vergelijkende barcharts weergave bij multi-select.
 * Haalt data op voor alle geselecteerde gebieden en toont ze naast elkaar.
 */
async function displayMultiGebiedComparison(lastClickedData) {
    const panel = document.getElementById('gebied-info');
    const content = document.getElementById('gebied-details');
    const ids = [...state.selectedGebiedIds];

    // Toon laad-indicator
    content.innerHTML = `<p style="opacity:0.6;">⏳ Vergelijking laden voor ${ids.length} gebieden...</p>`;
    panel.style.display = 'block';

    try {
        // Fetch all selected areas' details in parallel
        const promises = ids.map(id =>
            fetch(`${API_BASE}/gebieden/${id}`).then(r => r.ok ? r.json() : null)
        );
        const allData = (await Promise.all(promises)).filter(Boolean);

        if (allData.length === 0) {
            content.innerHTML = '<p><em>Geen data beschikbaar voor vergelijking</em></p>';
            return;
        }

        // Header
        let html = `
        <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
            <strong style="font-size: 1rem;"><img src="/static/images/chart-bar.svg" alt="" class="thema-icoon" style="width:18px; height:18px; vertical-align:-3px; margin-right: 4px;">Vergelijking: ${ids.length} gebieden</strong>
            <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 4px;">
                ${escapeHtml(allData.map(d => d.gebied.naam).join(' · '))}
            </div>
        </div>`;

        // Find common indicators (present in ALL selected areas)
        const firstIndicators = allData[0].indicatoren || [];

        // For each indicator, collect values from all areas
        const comparisonData = [];
        firstIndicators.forEach(ind => {
            const entry = { naam: ind.naam, eenheid: ind.eenheid || '', waarden: [] };
            allData.forEach(areaData => {
                const match = (areaData.indicatoren || []).find(i => i.naam === ind.naam);
                entry.waarden.push({
                    gebiedNaam: areaData.gebied.naam,
                    waarde: match ? match.waarde : null
                });
            });
            // Only include if at least 2 areas have data
            const validCount = entry.waarden.filter(w => w.waarde !== null && w.waarde !== undefined).length;
            if (validCount >= 2) {
                comparisonData.push(entry);
            }
        });

        // Render barcharts (max 8 indicators)
        const toShow = comparisonData.slice(0, 8);

        if (toShow.length === 0) {
            html += '<p style="opacity:0.6;">Onvoldoende overlappende indicatoren voor vergelijking.</p>';
        } else {
            // Color palette for areas
            const areaColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

            toShow.forEach(ind => {
                const validWaarden = ind.waarden.filter(w => w.waarde !== null && w.waarde !== undefined);
                const maxVal = Math.max(...validWaarden.map(w => Math.abs(w.waarde)), 1);
                const gemiddelde = validWaarden.reduce((s, w) => s + w.waarde, 0) / validWaarden.length;

                html += `
                <div style="margin-bottom: 14px;">
                    <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">
                        ${escapeHtml(ind.naam)} <span style="opacity:0.5; font-weight:400;">(${escapeHtml(ind.eenheid)})</span>
                    </div>`;

                ind.waarden.forEach((w, idx) => {
                    if (w.waarde === null || w.waarde === undefined) return;
                    const pct = Math.max(5, (Math.abs(w.waarde) / maxVal) * 100);
                    const color = areaColors[idx % areaColors.length];
                    const isAboveAvg = w.waarde >= gemiddelde;

                    html += `
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 3px; font-size: 0.75rem;">
                        <span style="width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; opacity: 0.8;" title="${escapeHtml(w.gebiedNaam)}">
                            ${escapeHtml(w.gebiedNaam.length > 12 ? w.gebiedNaam.slice(0, 11) + '…' : w.gebiedNaam)}
                        </span>
                        <div style="flex: 1; height: 16px; background: var(--tint); border-radius: 4px; overflow: hidden;">
                            <div style="width: ${pct}%; height: 100%; background: ${color}; border-radius: 4px; transition: width 0.3s;"></div>
                        </div>
                        <span style="width: 55px; text-align: right; font-weight: 500; font-variant-numeric: tabular-nums;">
                            ${formatNumber(w.waarde)}
                        </span>
                    </div>`;
                });

                // Gemiddelde lijn
                html += `
                    <div style="font-size: 0.7rem; opacity: 0.5; text-align: right; margin-top: 2px;">
                        Gem: ${formatNumber(gemiddelde)} ${escapeHtml(ind.eenheid)}
                    </div>
                </div>`;
            });

            if (comparisonData.length > 8) {
                html += `<p style="opacity:0.5; font-size: 0.8rem;">... en ${comparisonData.length - 8} meer indicatoren</p>`;
            }
        }

        content.innerHTML = html;
    } catch (error) {
        console.error('❌ Fout bij multi-gebied vergelijking:', error);
        content.innerHTML = '<p><em>Fout bij laden vergelijking</em></p>';
    }
}

/**
 * Toon een rapportkeuze-modal als toegankelijke dialoog (#67): role="dialog",
 * focus in de dialoog en vastgehouden, Escape of klik op de achtergrond sluit,
 * focus terug naar de knop die de modal opende.
 * @returns {Function} sluit()
 */
function toonRapportDialoog(modal) {
    const bestaand = document.getElementById(modal.id);
    if (bestaand) (bestaand._sluit || (() => bestaand.remove()))();

    document.body.appendChild(modal);
    let dialoog = null;
    const sluit = () => {
        if (dialoog) dialoog.close();
        modal.remove();
    };
    dialoog = A11y.openDialog(modal.firstElementChild, { labelledBy: 'rapport-modal-titel', onEscape: sluit });
    modal._sluit = sluit;
    modal.addEventListener('click', (e) => { if (e.target === modal) sluit(); });
    return sluit;
}

/**
 * Sprint 8D: Rapport type keuze modal — Gebiedsdossier vs Benchmark
 */
function openRapportTypeModal(gebiedId, baseUrl) {
    const modal = document.createElement('div');
    modal.id = 'rapport-type-modal';
    modal.className = 'rapport-dialoog-overlay';
    modal.innerHTML = `
        <div class="rapport-dialoog">
            <h3 id="rapport-modal-titel">Kies Rapport Type</h3>
            <p class="rapport-dialoog-intro">
                Welk rapport wil je genereren?
            </p>
            <div class="rapport-keuzes">
                ${state.selectedDeelgebiedNaam ? `
                <button id="rapport-modal-deelgebied-single" class="rapport-keuze rapport-keuze--primair">🏘️ Woonplaatsanalyse (${escapeHtml(state.selectedDeelgebiedNaam)})<br>
                    <span>
                        Gewogen stadsbrede analyse per thema
                    </span>
                </button>
                ` : ''}
                <button id="rapport-modal-dossier" class="rapport-keuze${state.selectedDeelgebiedNaam ? '' : ' rapport-keuze--primair'}">📄 Gebiedsdossier<br>
                    <span>
                        Volledige analyse van dit gebied
                    </span>
                </button>
                <button id="rapport-modal-thema" class="rapport-keuze">📊 Thema-Analyse<br>
                    <span>
                        Diepgaande analyse per Kompas thema
                    </span>
                </button>
                <button id="rapport-modal-benchmark" class="rapport-keuze">⚖️ Benchmark Vergelijker<br>
                    <span>
                        Vergelijk met andere gebieden, een gemeente of de provincie
                    </span>
                </button>
            </div>
            <button id="rapport-modal-sluiten" class="rapport-dialoog-annuleer">Annuleren</button>
        </div>
    `;

    const sluit = toonRapportDialoog(modal);

    document.getElementById('rapport-modal-deelgebied-single')?.addEventListener('click', () => {
        const ids = Array.from(state.selectedGebiedIds).length > 0 ? Array.from(state.selectedGebiedIds) : [gebiedId];
        const naam = encodeURIComponent(state.selectedDeelgebiedNaam);
        // Zonder gekozen gemeente kiest de backend die van de eigen organisatie (#231)
        const gemeente = state.gemeenteCode ? `&gemeente=${encodeURIComponent(state.gemeenteCode)}` : '';
        let extraParams = '';
        if (state.selectedGroepen && state.selectedGroepen.length > 0 && state.selectedLaagId) {
            extraParams += `&laag_id=${state.selectedLaagId}`;
            const woonplaatsen = state.selectedGroepen.map(g => encodeURIComponent(g.naam)).join(',');
            extraParams += `&woonplaatsen=${woonplaatsen}`;
        }
        window.open(`${baseUrl}/rapport/deelgebied?gebieden=${ids.join(',')}&naam=${naam}${gemeente}${extraParams}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-dossier').addEventListener('click', () => {
        window.open(`${baseUrl}/rapport/${gebiedId}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-thema').addEventListener('click', () => {
        window.open(`${baseUrl}/rapport/thema-analyse?gebieden=${gebiedId}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-benchmark').addEventListener('click', () => {
        window.open(`${baseUrl}/rapport/benchmark?gebied_a=${gebiedId}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-sluiten').addEventListener('click', sluit);
}

/**
 * Multi-select rapport keuze modal — Benchmark vs Multi-Gebiedsdossier
 */
function openMultiSelectRapportModal(ids, baseUrl) {
    const deelgebiedNaam = state.selectedDeelgebiedNaam || `${ids.length} buurten`;
    const modal = document.createElement('div');
    modal.id = 'rapport-type-modal';
    modal.className = 'rapport-dialoog-overlay';
    modal.innerHTML = `
        <div class="rapport-dialoog rapport-dialoog--breed">
            <h3 id="rapport-modal-titel">Kies Rapport Type</h3>
            <p class="rapport-dialoog-intro">
                ${ids.length} gebieden geselecteerd ${state.selectedDeelgebiedNaam ? `(${escapeHtml(state.selectedDeelgebiedNaam)})` : ''}
            </p>
            <div class="rapport-keuzes">
                <button id="rapport-modal-deelgebied" class="rapport-keuze rapport-keuze--primair">🏘️ Woonplaats- & Deelgebiedsanalyse<br>
                    <span>
                        Gewogen stadsanalyse per thema met Top 10
                    </span>
                </button>
                <button id="rapport-modal-multi-gebied" class="rapport-keuze">🗺️ Multi-Gebiedsdossier<br>
                    <span>
                        Z-score analyse met kaart en ranking
                    </span>
                </button>
                <button id="rapport-modal-thema-analyse" class="rapport-keuze">📊 Thema-Analyse<br>
                    <span>
                        Alle indicatoren per thema/onderdeel
                    </span>
                </button>
                <button id="rapport-modal-benchmark" class="rapport-keuze">⚖️ Benchmark Vergelijker<br>
                    <span>
                        Vergelijk gebieden onderling met delta-tabel
                    </span>
                </button>
            </div>
            <button id="rapport-modal-sluiten-multi" class="rapport-dialoog-annuleer">Annuleren</button>
        </div>
    `;

    const sluit = toonRapportDialoog(modal);

    document.getElementById('rapport-modal-deelgebied').addEventListener('click', () => {
        const gebiedenParam = ids.join(',');
        const naam = encodeURIComponent(deelgebiedNaam);
        // Zonder gekozen gemeente kiest de backend die van de eigen organisatie (#231)
        const gemeente = state.gemeenteCode ? `&gemeente=${encodeURIComponent(state.gemeenteCode)}` : '';
        let extraParams = '';
        if (state.selectedGroepen && state.selectedGroepen.length > 0 && state.selectedLaagId) {
            extraParams += `&laag_id=${state.selectedLaagId}`;
            const woonplaatsen = state.selectedGroepen.map(g => encodeURIComponent(g.naam)).join(',');
            extraParams += `&woonplaatsen=${woonplaatsen}`;
        }
        window.open(`${baseUrl}/rapport/deelgebied?gebieden=${gebiedenParam}&naam=${naam}${gemeente}${extraParams}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-benchmark').addEventListener('click', () => {
        const [a, ...rest] = ids;
        window.open(`${baseUrl}/rapport/benchmark?gebied_a=${a}&gebieden_b=${rest.join(',')}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-multi-gebied').addEventListener('click', () => {
        const gebiedenParam = ids.join(',');
        const naam = encodeURIComponent(deelgebiedNaam);
        // Sprint 18 Track C: extra params voor woonplaatslaag in rapport
        let extraParams = '';
        if (state.selectedGroepen.length > 0 && state.selectedLaagId) {
            extraParams += `&laag_id=${state.selectedLaagId}`;
            const woonplaatsen = state.selectedGroepen.map(g => encodeURIComponent(g.naam)).join(',');
            extraParams += `&woonplaatsen=${woonplaatsen}`;
        }
        window.open(`${baseUrl}/rapport/multi-gebied?gebieden=${gebiedenParam}&naam=${naam}${extraParams}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-thema-analyse').addEventListener('click', () => {
        const gebiedenParam = ids.join(',');
        const naam = encodeURIComponent(deelgebiedNaam);
        let extraParams = '';
        if (state.selectedGroepen.length > 0 && state.selectedLaagId) {
            extraParams += `&laag_id=${state.selectedLaagId}`;
            const woonplaatsen = state.selectedGroepen.map(g => encodeURIComponent(g.naam)).join(',');
            extraParams += `&woonplaatsen=${woonplaatsen}`;
        }
        window.open(`${baseUrl}/rapport/thema-analyse?gebieden=${gebiedenParam}&naam=${naam}${extraParams}`, '_blank');
        sluit();
    });
    document.getElementById('rapport-modal-sluiten-multi').addEventListener('click', sluit);
}

// ============================================================================
// Multi-Gebied Selection UI (Sprint 7)
// ============================================================================

/**
 * Updates the UI elements to reflect the current multi-selection state:
 * - Rapport panel text & button state
 * - Selection badge (floating counter)
 */
function updateSelectionUI() {
    const rapportInfo = document.getElementById('rapport-gebied-info');
    const rapportBtn = document.getElementById('open-rapport-btn');
    const count = state.selectedGebiedIds.size;

    if (rapportInfo && rapportBtn) {
        if (count === 0) {
            rapportInfo.innerHTML = '<em>Klik op een gebied op de kaart</em>';
            rapportBtn.disabled = true;
        } else if (count === 1) {
            const namen = getSelectedGebiedNamen();
            rapportInfo.innerHTML = `<strong>Geselecteerd:</strong> ${escapeHtml(namen[0])} (${escapeHtml(state.selectedGebiedId)})`;
            rapportBtn.disabled = false;
        } else {
            const namen = getSelectedGebiedNamen();
            const namenTekst = namen.length <= 3
                ? namen.join(', ')
                : `${namen.slice(0, 3).join(', ')} (+${namen.length - 3})`;
            rapportInfo.innerHTML = `<strong>Selectie (${count}):</strong> ${escapeHtml(namenTekst)}`;
            rapportBtn.disabled = false;
        }
    }

    // Update or create floating selection badge (Sprint 12: ook bij count=1 voor 3D panden knop)
    // Opbouw (#79): naam als label (niet klikbaar), daarna twee losse knoppen:
    // "3D-panden" (toggle) en "Selectie wissen" (✕). Eenmalig opgebouwd, zodat de
    // toetsenbordfocus bij het bijwerken op de knop blijft.
    let badge = document.getElementById('selection-badge');
    if (count >= 1) {
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'selection-badge';
            badge.className = 'selection-badge';
            badge.setAttribute('role', 'group');
            badge.setAttribute('aria-label', 'Selectie');
            badge.innerHTML = `
                <span class="selection-badge-label">
                    <img src="/static/images/map-pin-plus.svg" alt="" class="selection-badge-icon">
                    <span id="selection-badge-naam"></span>
                </span>
                <button type="button" id="bag3d-toggle-btn" class="selection-badge-btn" aria-pressed="false">
                    <img src="/static/images/building.svg" alt="" class="selection-badge-icon"> 3D-panden
                </button>
                <button type="button" id="selection-clear-btn" class="selection-badge-btn selection-badge-clear"
                        aria-label="Selectie wissen" title="Selectie wissen">✕</button>`;
            document.body.appendChild(badge);

            document.getElementById('selection-clear-btn').addEventListener('click', () => {
                clearGebiedSelection();
                updateSelectionUI();
                if (state.currentData) displayOnMap(state.currentData);
            });
            document.getElementById('bag3d-toggle-btn').addEventListener('click', () => {
                if (state.show3DBuildings) {
                    // Toggle OFF
                    state.show3DBuildings = false;
                    state.bag3dData = null;
                    if (state.currentData) displayOnMap(state.currentData);
                    updateSelectionUI();
                    console.log('🏗️ BAG 3D panden uitgeschakeld');
                } else {
                    // Toggle ON
                    loadBag3DBuildings();
                }
            });
        }
        // Badge tekst: single vs multi, met groepsnamen als beschikbaar
        let badgeTekst;
        if (state.selectedGroepen.length >= 2) {
            const namen = state.selectedGroepen.map(g => g.naam);
            badgeTekst = namen.length <= 3
                ? `${namen.join(', ')} (${count} buurten)`
                : `${namen.length} kernen (${count} buurten)`;
        } else if (state.selectedGroepen.length === 1) {
            badgeTekst = `${state.selectedGroepen[0].naam} (${count} buurten)`;
        } else if (count === 1) {
            badgeTekst = `${getSelectedGebiedNamen()[0] || '1 gebied'}`;
        } else {
            badgeTekst = `${count} gebieden geselecteerd`;
        }
        document.getElementById('selection-badge-naam').textContent = badgeTekst;

        // 3D-pandenknop alleen bij 1 t/m 3 gebieden
        const bag3dBtn = document.getElementById('bag3d-toggle-btn');
        bag3dBtn.hidden = count > 3;
        bag3dBtn.setAttribute('aria-pressed', state.show3DBuildings ? 'true' : 'false');
        bag3dBtn.title = state.show3DBuildings ? 'BAG-panden verbergen' : 'Laad 3D-panden vanuit de 3DBAG';

        badge.style.display = 'flex';
    } else if (badge) {
        badge.style.display = 'none';
    }
    // #258: indicatorpaneel en favorieten volgen de selectie
    window.EventBus?.emit('SELECTIE_GEWIJZIGD', { ids: [...state.selectedGebiedIds] });
}

/**
 * Open het Kompas-venster en laad de huidige selectie (of de hiërarchie zonder selectie).
 * Gedeeld door de knop "Open Kompas Venster" en de chatactie OPEN_KOMPAS (#79).
 */
function openKompasVenster() {
    if (!state.kompasWindow) {
        console.error('❌ Kompas window state not initialized');
        return;
    }
    state.kompasWindow.open();

    // Load data for selected area(s) if available
    if (state.selectedGebiedIds.size > 0 && window.kompasViz && window.kompasViz.currentConfigId) {
        loadKompasForSelection(window.kompasViz.currentConfigId);
    } else if (window.kompasViz && window.kompasViz.currentConfigId) {
        window.kompasViz.loadHierarchie(window.kompasViz.currentConfigId);
    }
}
window.openKompasVenster = openKompasVenster;

/**
 * Sprint 7: Laad kompas voor de huidige selectie.
 * Kiest automatisch single of multi-gebied methode.
 */
function loadKompasForSelection(configId) {
    if (!window.kompasViz) return;
    const ids = [...state.selectedGebiedIds];
    if (ids.length === 0) return;

    if (ids.length === 1) {
        window.kompasViz.loadGebiedData(configId, ids[0]);
    } else {
        window.kompasViz.loadMultiGebiedData(configId, ids);
    }
}

// ============================================================================
// Export Functions (NEW)
// ============================================================================

function exportScreenshot() {
    if (!state.deckgl) {
        showError('Geen kaart geladen om te exporteren');
        return;
    }

    try {
        // Use deck.gl's internal canvas (preserves WebGL context)
        const canvas = state.deckgl.canvas;

        if (!canvas) {
            showError('Canvas niet beschikbaar');
            return;
        }

        // Convert canvas to blob and download
        canvas.toBlob(blob => {
            if (!blob) {
                showError('Screenshot gefaald - probeer opnieuw');
                return;
            }

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `omnitwin-kaart-${new Date().toISOString().split('T')[0]}.png`;
            a.click();
            URL.revokeObjectURL(url);
            console.log('📸 Screenshot geëxporteerd');
        }, 'image/png');
    } catch (error) {
        console.error('Screenshot error:', error);
        showError('Fout bij maken screenshot');
    }
}

function exportGeoJSON() {
    if (!state.currentData) {
        showError('Geen data geladen om te exporteren');
        return;
    }

    const json = JSON.stringify(state.currentData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `omnitwin-data-${new Date().toISOString().split('T')[0]}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
    console.log('🗺️ GeoJSON geëxporteerd');
}

function exportCSV() {
    if (!state.currentData || !state.currentData.features) {
        showError('Geen data geladen om te exporteren');
        return;
    }

    // Generate CSV
    const headers = ['id', 'naam', 'indicator_naam', 'indicator_waarde', 'eenheid', 'jaar'];
    const rows = state.currentData.features.map(f => {
        const p = f.properties;
        return [p.id, p.naam, p.indicator_naam, p.indicator_waarde, p.eenheid || '', p.jaar || ''].join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `omnitwin-data-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    console.log('📊 CSV geëxporteerd');
}

// ============================================================================
// Event Handlers
// ============================================================================

function setupEventListeners() {
    // Gebiedstype selection
    document.getElementById('gebiedstype-select').addEventListener('change', async (e) => {
        const selectedId = e.target.value;
        state.currentGebiedstype = selectedId || null;
        state.currentIndicator = null;

        if (selectedId) {
            // Aantal gebieden van dit type ophalen (de gebiedstypes-query levert geen aantal)
            const countEl = document.getElementById('gebiedstype-count');
            countEl.textContent = '… gebieden in dit type';
            fetchPostgrestCount(`gebieden?select=id&gebiedstype_id=eq.${encodeURIComponent(selectedId)}`)
                .then(count => {
                    // Niet overschrijven als intussen een ander type gekozen is of de kaart al geladen is
                    if (state.currentGebiedstype !== selectedId || !countEl.textContent.startsWith('…')) return;
                    countEl.textContent = count === null
                        ? 'Aantal gebieden onbekend'
                        : `${count} gebieden in dit type`;
                })
                .catch(() => {
                    if (countEl.textContent.startsWith('…')) countEl.textContent = 'Aantal gebieden onbekend';
                });

            await loadIndicatoren(selectedId);
        } else {
            document.getElementById('indicator-select').disabled = true;
            document.getElementById('indicator-select').innerHTML =
                '<option value="">Selecteer eerst gebiedstype</option>';
            document.getElementById('indicator-coverage').textContent =
                'Selecteer een indicator';
        }

        updateButtonState();
    });

    // #255: kaartmodus (percentielklasse / werkelijke waarde / uit)
    document.querySelectorAll('input[name="kaart-modus"]').forEach(radio => {
        radio.checked = radio.value === state.kaartModus;
        radio.addEventListener('change', (e) => {
            if (e.target.checked) setKaartModus(e.target.value);
        });
    });

    // Indicator selection
    document.getElementById('indicator-select').addEventListener('change', (e) => {
        const selectedId = e.target.value;
        state.currentIndicator = selectedId || null;

        if (selectedId) {
            const selectedOption = e.target.options[e.target.selectedIndex];
            const coverage = selectedOption.dataset.coverage;
            document.getElementById('indicator-coverage').textContent =
                coverage ? `${coverage} gebieden met data` : 'Data beschikbaarheid onbekend';
        }

        updateButtonState();
    });

    // 3D Toggle (wederzijds exclusief met BAG panden)
    document.getElementById('enable-3d').addEventListener('change', (e) => {
        state.enable3D = e.target.checked;

        // Wederzijds exclusief: buurt-3D aan → BAG panden uit
        if (state.enable3D && state.show3DBuildings) {
            state.show3DBuildings = false;
            state.bag3dData = null;
            console.log('🏗️ BAG panden uitgeschakeld (buurt-extrusie actief)');
        }

        // Toggle height scale controls
        document.getElementById('extrusie-controls').style.display =
            state.enable3D ? 'block' : 'none';

        // Update map if data loaded
        if (state.currentData) {
            displayOnMap(state.currentData);
        }

        // Update camera pitch
        const currentViewState = state.currentViewState;
        state.currentViewState = {
            ...currentViewState,
            pitch: state.enable3D ? 45 : 0,
            ...A11y.cameraTransition(500)
        };
        state.deckgl.setProps({
            viewState: state.currentViewState
        });
        updateSelectionUI(); // Update 3D panden knop state
    });

    // Height Scale
    document.getElementById('height-scale').addEventListener('input', (e) => {
        state.heightScale = parseInt(e.target.value);
        document.getElementById('height-value').textContent = `${state.heightScale}x`;

        // Update map if data loaded and 3D enabled
        if (state.currentData && state.enable3D) {
            displayOnMap(state.currentData);
        }
    });

    // Show All Toggle
    document.getElementById('show-all').addEventListener('change', (e) => {
        state.showAll = e.target.checked;
    });

    // Toon Kaart Button
    document.getElementById('toon-kaart-btn').addEventListener('click', () => {
        loadKaartData();
    });

    // Mapbox Style Selector (if available)
    const mapboxSelect = document.getElementById('mapbox-style-select');
    if (mapboxSelect) {
        mapboxSelect.addEventListener('change', (e) => {
            changeMapboxStyle(e.target.value);
        });
    }

    // Omgevingsvisie Deelgebieden Toggle
    const omgVisieToggle = document.getElementById('toggle-omgevingsvisie');
    if (omgVisieToggle) {
        omgVisieToggle.addEventListener('change', async (e) => {
            state.showOmgevingsvisieLayer = e.target.checked;
            const info = document.getElementById('omgevingsvisie-info');

            if (state.showOmgevingsvisieLayer && !state.omgevingsvisieData) {
                // Eerste keer: laad data
                await loadOmgevingsvisieLayer();
            }

            if (state.showOmgevingsvisieLayer && state.omgevingsvisieData) {
                const count = state.omgevingsvisieData.features?.length || 0;
                if (info) info.textContent = `${count} deelgebieden zichtbaar. Klik om buurten te selecteren.`;
            } else {
                if (info) info.textContent = 'Toont deelgebieden uit de omgevingsvisie. Klik om buurten te selecteren.';
            }

            // Re-render kaart met/zonder overlay
            if (state.currentData) {
                displayOnMap(state.currentData);
            }
        });
    }

    // Export Buttons
    const screenshotBtn = document.getElementById('export-screenshot-btn');
    if (screenshotBtn) {
        screenshotBtn.addEventListener('click', exportScreenshot);
    }

    const geojsonBtn = document.getElementById('export-geojson-btn');
    if (geojsonBtn) {
        geojsonBtn.addEventListener('click', exportGeoJSON);
    }

    const csvBtn = document.getElementById('export-csv-btn');
    if (csvBtn) {
        csvBtn.addEventListener('click', exportCSV);
    }

    // AI Rapport Output Button — Sprint 8D: Keuze-overlay (Gebiedsdossier vs Benchmark)
    const rapportBtn = document.getElementById('open-rapport-btn');
    if (rapportBtn) {
        rapportBtn.addEventListener('click', () => {
            const ids = [...state.selectedGebiedIds];
            if (ids.length === 0) return;

            // Altijd relatieve URLs gebruiken — werkt met localhost, ngrok, en productie
            const baseUrl = '';

            if (ids.length > 1) {
                // Multi-select: keuze-modal (Benchmark vs Multi-Gebiedsdossier)
                openMultiSelectRapportModal(ids, baseUrl);
            } else {
                // Single-select: toon inline keuze-overlay
                openRapportTypeModal(ids[0], baseUrl);
            }
        });
    }

    // Kompas Sync Handler - Updates map AND legend when indicator clicked in Kompas
    const handleIndicatorSelection = async (data) => {
        const { uuid, name } = data;
        console.log('🔗 Kompas sync event received:', name, uuid);

        state.currentIndicator = uuid;

        // Track B3: Update indicator badge
        updateIndicatorBadge(name);

        // Update UI dropdown to match Kompas selection
        const select = document.getElementById('indicator-select');
        if (select) {
            select.value = uuid;
            // Show coverage if possible
            const option = select.querySelector(`option[value="${uuid}"]`);
            if (option) {
                const coverage = option.dataset.coverage;
                document.getElementById('indicator-coverage').textContent =
                    coverage ? `${coverage} gebieden met data` : 'Data beschikbaarheid onbekend';
            }
        }

        updateButtonState();

        // 1. Open Legenda Panel (ensure it's visible)
        togglePanel('legenda');

        // 2. Load Map Data (this calls updateLegenda internally via loadKaartData)
        await loadKaartData();

        // 3. EXPLICIT: Force legend update after data is loaded
        //    This ensures the legend syncs even if loadKaartData's internal call had timing issues
        if (state.currentData) {
            updateLegenda(state.currentData);
            console.log('✅ Legend explicitly synced after Kompas selection:', name);
        }
    };

    // Initialize Event Listeners
    if (window.EventBus) {
        console.log('🚌 Subscribing to EventBus: INDICATOR_SELECTED, GEMEENTE_SELECTED, GEBIEDSTYPE_SELECTED');
        window.EventBus.on('INDICATOR_SELECTED', handleIndicatorSelection);

        // A3: Timeslider Year Changed
        window.EventBus.on('YEAR_CHANGED', async (data) => {
            console.log(`⏱️ Year changed via Timeslider: ${data.jaar}`);
            if (state.currentGebiedstype && state.currentIndicator === data.uuid) {
                // We keep the map view but update the data for the specific year
                try {
                    let attrUrl = `/api/gebiedsmonitor/kaart_data/${state.currentGebiedstype}?show_all=${state.showAll}&indicator_uuid=${state.currentIndicator}&jaar=${data.jaar}${kaartModusParam()}`;
                    if (state.currentGemeenteCode) {
                        attrUrl += `&gemeente_code=${state.currentGemeenteCode}`;
                    }

                    const response = await fetch(attrUrl);
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);

                    const attributes = await response.json();
                    
                    // Merge attributes into existing GeoJSON features
                    if (state.currentData && state.currentData.features) {
                        state.currentData.features.forEach(f => {
                            const props = attributes.data[f.properties.id];
                            f.properties.onderdrukt = false; // #325: niet meenemen uit het vorige jaar
                            if (props) {
                                Object.assign(f.properties, props);
                            } else {
                                // Clear missing data
                                f.properties.indicator_waarde = null;
                                f.properties.jaar = null;
                                f.properties.bron = null;
                                f.properties.color = '#94A3B8';
                            }
                        });
                        state.currentData.metadata = attributes.metadata;

                        displayOnMap(state.currentData);
                        updateLegenda(state.currentData);
                        window.EventBus?.emit('KAARTDATA_GELADEN', { jaar: data.jaar }); // #258
                    }
                } catch (error) {
                    console.error('❌ Fout bij laden historische kaart data:', error);
                }
            }
        });

        // Chat -> Map: Select Municipality (code-based lookup)
        window.EventBus.on('GEMEENTE_SELECTED', (data) => {
            console.log('📍 Chat sync: selecting gemeente', data.name, data.code);
            zetGemeente(data.code, data.name, true);
            console.log(`✅ Gemeente via chat: ${data.name} (${data.code})`);
        });

        // Chat -> Map: Select Gebiedstype (direct state update)
        window.EventBus.on('GEBIEDSTYPE_SELECTED', async (data) => {
            console.log('🏙 Chat sync: selecting gebiedstype', data.name, data.id);
            const select = document.getElementById('gebiedstype-select');
            if (!select) return;
            
            // Try to find matching option by UUID or by name
            let matchedId = null;
            for (const opt of select.options) {
                if (opt.value === data.id) {
                    matchedId = opt.value;
                    break;
                }
                // Fallback: match by name (case-insensitive, partial)
                if (data.name && opt.textContent.toLowerCase().includes(data.name.toLowerCase())) {
                    matchedId = opt.value;
                    break;
                }
            }
            
            if (!matchedId) {
                console.warn('⚠️ Gebiedstype niet gevonden:', data.name, data.id);
                return;
            }
            
            // Update select UI
            select.value = matchedId;
            
            // Update state
            state.currentGebiedstype = matchedId;
            state.currentIndicator = null;
            
            // Load indicatoren for this type
            await loadIndicatoren(matchedId);
            
            // Load map data
            await loadKaartData();
            
            updateButtonState();
            console.log(`✅ Gebiedstype via chat: ${data.name} (${matchedId})`);
        });

        // #149: Chat -> Kaart: gebieden uit een antwoord op een datavraag selecteren,
        // optioneel met de indicator op de kaart of het Kompas voor die gebieden.
        // Ook automatisch na een antwoord (kaart_actie, zoom: true): de kaart beweegt mee.
        window.EventBus.on('CHAT_GEBIEDEN_TONEN', async (data) => {
            const ids = (data.ids || []).filter(Boolean);
            if (data.gebiedstypeId && state.currentGebiedstype !== data.gebiedstypeId) {
                const select = document.getElementById('gebiedstype-select');
                if (select && [...select.options].some(o => o.value === data.gebiedstypeId)) {
                    select.value = data.gebiedstypeId;
                    state.currentGebiedstype = data.gebiedstypeId;
                    state.currentIndicator = null;
                    await loadIndicatoren(data.gebiedstypeId);
                }
            }
            // Een gemeentefilter op een andere gemeente zou de gebieden verbergen
            if (data.gemeenteCode && state.currentGemeenteCode && state.currentGemeenteCode !== data.gemeenteCode) {
                zetGemeente(data.gemeenteCode, null, false);
                state.currentData = null;
            }

            clearGebiedSelection();
            ids.forEach(id => state.selectedGebiedIds.add(id));

            if (data.uuid) {
                await handleIndicatorSelection({ uuid: data.uuid, name: data.name || '' });
            } else if (state.currentData) {
                displayOnMap(state.currentData);
            } else if (state.currentGebiedstype) {
                await loadKaartData();
            }
            updateGemeenteFilterChip(state.currentData?.features?.length ?? null);
            updateSelectionUI();
            updateButtonState();
            if (data.zoom) zoomNaarGebieden(ids);

            if (data.openKompas && state.kompasWindow) {
                state.kompasWindow.open();
                if (window.kompasViz && window.kompasViz.currentConfigId) {
                    loadKompasForSelection(window.kompasViz.currentConfigId);
                }
            }
            console.log(`✅ Chat: ${ids.length} gebied(en) geselecteerd`, ids);
        });
    } else {
        console.error('❌ EventBus not available for subscription');
    }

    // Open Kompas Button (in Sidebar)
    const openKompasBtn = document.getElementById('open-kompas-btn');
    if (openKompasBtn) {
        openKompasBtn.addEventListener('click', () => {
            console.log('🔘 Open Kompas button clicked');
            openKompasVenster();
        });
    }

    // Kompas Config Selector (Moved to Panel)
    const kompasConfigSelect = document.getElementById('kompas-config-select');
    if (kompasConfigSelect) {
        kompasConfigSelect.addEventListener('change', (e) => {
            const newConfigId = e.target.value;
            if (window.kompasViz) {
                window.kompasViz.currentConfigId = newConfigId;
                console.log('🔄 Kompas config changed to:', newConfigId);

                // If window is open, reload data
                const kompasWindow = document.getElementById('kompas-window');
                if (kompasWindow && kompasWindow.style.display !== 'none') {
                    if (state.selectedGebiedIds.size > 0) {
                        loadKompasForSelection(newConfigId);
                    } else {
                        window.kompasViz.loadHierarchie(newConfigId);
                    }
                }
            }
        });
    }

    // Luister naar requests voor snapshots vanuit test/admin dashboards
    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'requestMapSnapshot') {
            console.log('📸 MapSnapshot request received van admin dashboard');
            if (state.deckgl) {
                // Kleine timeout om er zeker van te zijn dat eventuele overlays klaar zijn.
                // Mapbox heeft preserveDrawingBuffer: true, dus het vangen moet altijd kunnen.
                setTimeout(() => {
                    try {
                        // Verzamel alle canvases (Mapbox base map + Deck.gl overlay) in de div
                        const canvases = document.querySelectorAll('#map canvas');
                        if (canvases.length > 0) {
                            const mergedCanvas = document.createElement('canvas');
                            mergedCanvas.width = canvases[0].width;
                            mergedCanvas.height = canvases[0].height;
                            const ctx = mergedCanvas.getContext('2d');

                            // Teken alle lagen over elkaar heen met behoud van the resolutie (High-DPI)
                            canvases.forEach(canvas => {
                                if (canvas.width > 0 && canvas.height > 0) {
                                    ctx.drawImage(canvas, 0, 0, mergedCanvas.width, mergedCanvas.height);
                                }
                            });

                            try {
                                const base64Image = mergedCanvas.toDataURL('image/png');
                                event.source.postMessage({
                                    type: 'mapSnapshot',
                                    image: base64Image
                                }, event.origin || '*');
                            } catch (err) {
                                // Als de .toDataURL crasht, komt dit bijna 100% door TaintedCanvas / CORS policy
                                console.error('❌ Tainted Canvas / CORS Error in toDataURL:', err);
                                event.source.postMessage({
                                    type: 'mapSnapshotError',
                                    error: err.toString()
                                }, event.origin || '*');
                            }
                        } else {
                            console.warn('⚠️ Geen map canvases gevonden om te exporteren.');
                            event.source.postMessage({
                                type: 'mapSnapshotError',
                                error: 'Geen map canvases gevonden'
                            }, event.origin || '*');
                        }
                    } catch (err) {
                        console.error('❌ Failed to create MapSnapshot:', err);
                        event.source.postMessage({
                            type: 'mapSnapshotError',
                            error: err.toString()
                        }, event.origin || '*');
                    }
                }, 100);
            }
        }

        if (event.data && event.data.type === 'requestKompasSnapshot') {
            console.log('🧭 KompasSnapshot request received van admin dashboard');
            const targetGebiedId = event.data.gebiedId;

            const takeKompasSnapshot = () => {
                const svgElement = document.querySelector('#kompas-container svg');
                if (svgElement) {
                    try {
                        // SVG clonen om styles inline te injecteren voor print-baarheid
                        const clone = svgElement.cloneNode(true);
                        // Dwing een lichte achtergrond af op de kloon als die transparant is
                        clone.style.backgroundColor = 'white';

                        const serializer = new XMLSerializer();
                        let svgString = serializer.serializeToString(clone);

                        // Converteer naar een data url
                        const base64SVG = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgString)));

                        event.source.postMessage({
                            type: 'kompasSnapshot',
                            image: base64SVG
                        }, event.origin || '*');
                    } catch (err) {
                        console.error('❌ Failed to create KompasSnapshot:', err);
                        event.source.postMessage({
                            type: 'kompasSnapshotError',
                            error: err.toString()
                        }, event.origin || '*');
                    }
                } else {
                    console.warn('⚠️ Geen kompas SVG gevonden om te exporteren.');
                    event.source.postMessage({
                        type: 'kompasSnapshotError',
                        error: 'Geen kompas SVG gevonden in hoofdapplicatie. Open the kompas in the D-OmniTwin monitor of the ververs the pagina.'
                    }, event.origin || '*');
                }
            };

            // Forceer lokaal inladen als the kompas instantie bestaat maar the data nog niet getekend is voor DIT gebied
            if (window.kompasViz && targetGebiedId && window.kompasViz.currentConfigId) {
                if (window.kompasViz.currentGebiedId !== targetGebiedId) {
                    console.log(`🧭 Auto-loading kompas for snapshot: ${targetGebiedId}`);
                    window.kompasViz.loadGebiedData(window.kompasViz.currentConfigId, targetGebiedId)
                        .then(() => {
                            // Geef D3 eventjes de tijd om de the render transition the voltooien (normaal is 750ms in de animatie, maar SVG rendering is sync)
                            setTimeout(takeKompasSnapshot, 250);
                        })
                        .catch(err => {
                            console.error('❌ Fout bij dynamisch laden kompas data:', err);
                            takeKompasSnapshot(); // Fallback to normal error handling or empty svg
                        });
                } else {
                    // Data is al thekening
                    takeKompasSnapshot();
                }
            } else {
                // Kon the kompas niet dynamisch laden of is al getriggerd, we thest the direct path
                takeKompasSnapshot();
            }
        }
    });

    // Enable export buttons when data is loaded
    document.addEventListener('dataLoaded', () => {
        if (geojsonBtn) geojsonBtn.disabled = false;
        if (csvBtn) csvBtn.disabled = false;
    });
}

// ============================================================================
// Legenda & Colors
// ============================================================================

// NOTE: updateLegenda is now defined once, near line 895 (consolidated)
// Previously there was a duplicate here that caused override issues

function getColorRGB(value, min, max, is3D = false) {
    // Fallback client-side interpolation (Red -> Yellow -> Green)
    // Used if backend color is missing (#373: subtiele tint conform getFillColor)
    if (value === null || value === undefined) {
        const isDark = typeof state !== 'undefined' && state.currentTheme === 'dark';
        const r = isDark ? 160 : 180;
        const g = isDark ? 160 : 180;
        const b = isDark ? 160 : 180;
        const a = isDark ? (is3D ? 60 : 35) : (is3D ? 70 : 45);
        return [r, g, b, a];
    }

    // Normalize
    const t = (value - min) / (max - min);

    // Red to Green
    // 0.0 -> Red (255, 0, 0)
    // 0.5 -> Yellow (255, 255, 0)
    // 1.0 -> Green (0, 255, 0)

    let r, g, b;

    if (t < 0.5) {
        // Red to Yellow
        r = 255;
        g = Math.round(255 * (t * 2));
        b = 0;
    } else {
        // Yellow to Green
        r = Math.round(255 * (2 - t * 2));
        g = 255;
        b = 0;
    }

    const opacity = is3D ? 255 : 153;
    return [r, g, b, opacity]; // 60% opacity in 2D, 100% in 3D
}

// ============================================================================
// Export Functions
// ============================================================================

function exportScreenshot() {
    if (!state.deckgl) return;
    const canvas = document.querySelector('#map canvas');
    if (canvas) {
        const link = document.createElement('a');
        link.download = `omnitwin-screenshot-${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }
}

function exportGeoJSON() {
    if (!state.currentData) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state.currentData));
    const link = document.createElement('a');
    link.href = dataStr;
    link.download = `omnitwin-export-${Date.now()}.json`;
    link.click();
}

function exportCSV() {
    if (!state.currentData || !state.currentData.features) return;

    const features = state.currentData.features;
    if (features.length === 0) return;

    // Get headers
    const props = features[0].properties;
    const headers = Object.keys(props).join(',');

    // Get rows
    const rows = features.map(f => {
        return Object.values(f.properties).map(val => {
            if (typeof val === 'string') return `"${val}"`;
            return val;
        }).join(',');
    });

    // Blob in plaats van data-URI: in een data-URI kapt een '#' (bv. in kleurcodes) de inhoud af
    const blob = new Blob([[headers, ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `omnitwin-export-${Date.now()}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ============================================================================
// Utility Functions
// ============================================================================

function showLoading(show, message = 'Laden...') {
    const overlay = document.getElementById('loading-indicator');
    const text = overlay.querySelector('.loading-text');

    if (text) text.textContent = message;
    overlay.style.display = show ? 'flex' : 'none';
}

function showError(message) {
    console.error(message);
    // Toast notificatie (Sprint 11B upgrade van alert() → non-blocking)
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.innerHTML = `
        <span class="error-toast-icon">⚠️</span>
        <span class="error-toast-msg">${escapeHtml(message)}</span>
        <button class="error-toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    document.body.appendChild(toast);
    // Auto-verwijder na 6 seconden
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, 6000);
}

function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    return new Intl.NumberFormat('nl-NL', {
        maximumFractionDigits: 2
    }).format(num);
}




// ============================================================================
// Console Welcome Message
// ============================================================================

console.log(`
%c🌍 D-OmniTwin Gebiedsmonitor v2.0 
%cPowered by deck.gl | FastAPI | PostgreSQL/PostGIS | Mapbox
`,
    'font-size: 20px; font-weight: bold; color: #2563eb;',
    'font-size: 12px; color: #64748b;'
);

// ============================================================================
// Camera Logic (UI Polish) — Sprint 16: Vrije-Zone Centreren
// ============================================================================

/**
 * Berekent het X-pixel centrum van de vrije (onbedekte) kaartzone.
 * Houdt rekening met: tab bar, linker panel, chat panel en Kompas venster.
 * Blend het vrije-zone-midden met het overall schermmidden om extreme offsets te voorkomen.
 */
function getFreezone() {
    const W = window.innerWidth;
    const MIN_ZONE = 150;       // Minimale bruikbare segmentbreedte (px)

    // Vaste panels (links)
    const tabBar = 70;
    const leftPanel = document.querySelector('.panel-container.open') ? 360 : 0;
    const leftEdge = tabBar + leftPanel;

    // Chat panel (rechts)
    const chatOpen = document.getElementById('chat-panel')?.classList.contains('open');
    const rightEdge = chatOpen ? 380 : 0;

    // Vrije zone zonder Kompas
    const freeLeft = leftEdge;
    const freeRight = W - rightEdge;
    const baseCenterX = freeLeft + (freeRight - freeLeft) / 2;

    // Kompas venster (zwevend, draggable)
    const kompasEl = document.getElementById('kompas-window');
    const kompasVisible = kompasEl && kompasEl.style.display !== 'none';

    if (!kompasVisible) {
        return { centerX: baseCenterX, screenCenterX: W / 2 };
    }

    const kr = kompasEl.getBoundingClientRect();
    const spaceLeft  = Math.max(0, kr.left - freeLeft);
    const spaceRight = Math.max(0, freeRight - kr.right);

    let centerX;
    if (spaceLeft >= MIN_ZONE || spaceRight >= MIN_ZONE) {
        // Bepaal het midden van het grootste vrije segment
        const zoneCenter = (spaceLeft > spaceRight)
            ? freeLeft + (spaceLeft / 2)
            : kr.right + (spaceRight / 2);

        // Blend met het overall schermmidden: voorkomt dat brede polygonen
        // van de tegenoverliggende schermrand vallen bij extreme Kompas-posities
        centerX = (zoneCenter + baseCenterX) / 2;
    } else {
        centerX = baseCenterX;
    }

    // Zorg dat centerX binnen het bruikbare schermgebied blijft
    centerX = Math.max(freeLeft + 50, Math.min(freeRight - 50, centerX));

    return { centerX, screenCenterX: W / 2 };
}

function flyToGebied(feature, clickCoordinate = null) {
    if (!feature || !feature.geometry) return;

    let centroid = [0, 0];

    // Gebruik de klik-coördinaat als die er is (altijd accuraat binnen de MultiPolygon)
    if (clickCoordinate && Array.isArray(clickCoordinate) && clickCoordinate.length >= 2) {
        centroid = [clickCoordinate[0], clickCoordinate[1]];
    } else {
        // Fallback: Calculate centroid by averaging all vertices
        let count = 0;
        const coords = feature.geometry.coordinates;

        const flatten = (arr) => {
            if (typeof arr[0] === 'number') {
                centroid[0] += arr[0];
                centroid[1] += arr[1];
                count++;
            } else {
                arr.forEach(flatten);
            }
        };

        flatten(coords);

        if (count > 0) {
            centroid[0] /= count;
            centroid[1] /= count;
        } else {
            return; // Geen geldige geometrie
        }
    }

    // Gebruik altijd state.currentViewState als bron van waarheid voor de huidige camera
    // DeckGL kan soms transitions missen als initialViewState niet genoeg verschilt van de vorige initialViewState,
    // maar door de actuele (gepande) currentViewState te gebruiken, dwingen we altijd een verandering af.
    const baseState = state.currentViewState || state.deckgl.props.initialViewState || { zoom: 12, pitch: 45, bearing: 0 };
    const zoom = Math.max(baseState.zoom || 12, 12);

    // Sprint 16: Verschuif longitude zodat buurt in de vrije zone valt
    const { centerX, screenCenterX } = getFreezone();
    const pixelOffset = screenCenterX - centerX; // positief = vrije zone is links van midden
    // Graden per pixel bij gegeven zoom (Web Mercator)
    const degreesPerPixel = 360 / (256 * Math.pow(2, zoom));
    const lngOffset = pixelOffset * degreesPerPixel;

    console.log(`🎥 Flying to area:`, centroid, `offset: ${pixelOffset.toFixed(0)}px → ${lngOffset.toFixed(4)}°`);

        state.deckgl.setProps({
            viewState: {
                ...baseState,
                longitude: centroid[0] + lngOffset,
                latitude: centroid[1],
                zoom: zoom,
                ...A11y.cameraTransition(800, true)
            }
        });
}

/**
 * #149: zoom in op een set gebieden (bbox van hun geometrie in state.currentData).
 * Met prefers-reduced-motion zonder animatie. Retourneert true als er ingezoomd is.
 */
function zoomNaarGebieden(ids) {
    if (!state.deckgl || !state.currentData || !Array.isArray(state.currentData.features)) return false;
    const gezocht = new Set(ids);
    let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
    const walk = (arr) => {
        if (!Array.isArray(arr)) return;
        if (typeof arr[0] === 'number') {
            minLon = Math.min(minLon, arr[0]); maxLon = Math.max(maxLon, arr[0]);
            minLat = Math.min(minLat, arr[1]); maxLat = Math.max(maxLat, arr[1]);
        } else {
            arr.forEach(walk);
        }
    };
    state.currentData.features
        .filter(f => gezocht.has(f.properties?.id ?? f.id))
        .forEach(f => f.geometry && walk(f.geometry.coordinates));
    if (minLon === Infinity) return false;

    // Vrije zone: linkerpaneel en chat niet over de gebieden heen
    const mapEl = document.getElementById('map');
    const width = (mapEl && mapEl.clientWidth) || window.innerWidth;
    const height = (mapEl && mapEl.clientHeight) || window.innerHeight;
    const leftPanel = document.querySelector('.panel-container.open') ? 360 : 0;
    const chatOpen = document.getElementById('chat-panel')?.classList.contains('open');
    let padding = { top: 60, bottom: 100, left: 110 + leftPanel, right: (chatOpen ? 380 : 0) + 60 };
    if (width - padding.left - padding.right < 100 || height - padding.top - padding.bottom < 100) padding = 20;

    let longitude = (minLon + maxLon) / 2, latitude = (minLat + maxLat) / 2, zoom = 13;
    if (typeof deck !== 'undefined' && deck.WebMercatorViewport) {
        try {
            const vp = new deck.WebMercatorViewport({ width, height })
                .fitBounds([[minLon, minLat], [maxLon, maxLat]], { padding, maxZoom: 15 });
            ({ longitude, latitude, zoom } = vp);
        } catch (e) {
            console.warn('zoomNaarGebieden: fitBounds mislukt, midden van de gebieden', e);
        }
    }

    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const base = state.currentViewState || state.deckgl.props.viewState || state.deckgl.props.initialViewState || {};
    state.currentViewState = {
        ...base,
        longitude, latitude, zoom,
        transitionDuration: reduceMotion ? 0 : 1000,
        ...(reduceMotion ? {} : { transitionInterpolator: new deck.FlyToInterpolator() })
    };
    state.deckgl.setProps({ viewState: state.currentViewState });
    return true;
}


// ============================================================================
// Track A1 — Initiële Onboarding (Welkomstmodal)
// Sprint 11B | localStorage flag: 'omnitwin_welcomed'
// ============================================================================

const ONBOARDING_KEY = 'omnitwin_welcomed';
let welcomeDialog = null;

/**
 * Initialiseer de welkomstmodal.
 * Toont de modal alleen als de gebruiker nog niet eerder heeft bezocht.
 */
function initOnboarding() {
    if (localStorage.getItem(ONBOARDING_KEY)) return; // Al eerder welkom geheten

    const overlay = document.getElementById('welcome-modal-overlay');
    if (!overlay) return;

    // Toon de overlay
    overlay.style.display = 'flex';

    // Sluit modal bij klik op overlay (buiten modal)
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) dismissWelcomeModal();
    });

    // Focus in de modal en vasthouden; Escape sluit (#67)
    welcomeDialog = A11y.openDialog(overlay, { labelledBy: 'welcome-title', onEscape: dismissWelcomeModal });

    console.log('👋 Welkomstmodal getoond (eerste bezoek)');
}

/**
 * Verwerk CTA-klik vanuit de welkomstmodal.
 * @param {'kaart'|'kompas'} action
 */
function startOnboarding(action) {
    dismissWelcomeModal();

    // Kleine vertraging zodat de fade-out zichtbaar is
    setTimeout(() => {
        if (action === 'kaart') {
            // Open het Kaartconfiguratie-paneel
            togglePanel('controls');
            window.EventBus.emit('ONBOARDING_ACTION', { action: 'kaart' });
        } else if (action === 'kompas') {
            // Open het Kompas-paneel
            togglePanel('kompas');
            window.EventBus.emit('ONBOARDING_ACTION', { action: 'kompas' });
        }
    }, 300);
}

/**
 * Sluit de welkomstmodal met fade-out animatie en sla de flag op.
 */
function dismissWelcomeModal() {
    const overlay = document.getElementById('welcome-modal-overlay');
    if (!overlay) return;

    if (welcomeDialog) {
        welcomeDialog.close();
        welcomeDialog = null;
    }

    overlay.classList.add('fade-out');
    setTimeout(() => {
        overlay.style.display = 'none';
        overlay.classList.remove('fade-out');
    }, 260);

    localStorage.setItem(ONBOARDING_KEY, '1');
    console.log('✅ Welkomstmodal gesloten — flag opgeslagen');
}


// ============================================================================
// Track A2 — Contextuele Onboarding (Just-in-time tooltips)
// Sprint 11B | Eén localStorage flag per feature
// ============================================================================

const TOOLTIP_FLAGS = {
    indicator: 'omnitwin_tt_indicator',
    buurt:     'omnitwin_tt_buurt',
    kompas:    'omnitwin_tt_kompas',
    ai:        'omnitwin_tt_ai',
};

const TOOLTIP_MESSAGES = {
    indicator: '💡 Tip: Elke indicator heeft een score-type (+/+ of -/+). Een hoge waarde kan zowel positief als negatief zijn — kijk altijd naar de legenda.',
    buurt:     '💡 Tip: Klik op meerdere buurten (Shift+klik) om ze te vergelijken. Open het Kompas voor een volledig gebiedsprofiel.',
    kompas:    '💡 Tip: Het Kompas toont een hiërarchische structuur van indicatoren. Klik op een segment om in te zoomen op een thema.',
    ai:        '💡 Tip: De D-Omni Assistent werkt op basis van lokale AI. De output is ondersteunend — controleer altijd de brondata.',
};

let tooltipTimeout = null;

/**
 * Initialiseer de contextuele tooltip-engine.
 * Koppelt EventBus-luisteraars voor elke te bewaken feature.
 */
function initContextualTooltips() {
    const closeBtn = document.getElementById('contextual-tooltip-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => hideContextualTooltip());
    }

    // Guard: EventBus moet beschikbaar zijn
    if (!window.EventBus) {
        console.warn('⚠️ EventBus niet beschikbaar — contextuele tooltips uitgeschakeld');
        return;
    }

    // Luister naar relevante events via de EventBus
    window.EventBus.on('INDICATOR_SELECTED', () => {
        showContextualTooltip('indicator');
    });

    window.EventBus.on('GEBIED_SELECTED', () => {
        showContextualTooltip('buurt');
    });

    window.EventBus.on('KOMPAS_OPENED', () => {
        showContextualTooltip('kompas');
    });

    window.EventBus.on('AI_RESPONSE_RECEIVED', () => {
        showContextualTooltip('ai');
    });

    console.log('💬 Contextuele tooltips geïnitialiseerd');
}

/**
 * Toon een contextuele tooltip als de flag nog niet gezet is.
 * @param {'indicator'|'buurt'|'kompas'|'ai'} key
 */
function showContextualTooltip(key) {
    const flag = TOOLTIP_FLAGS[key];
    const message = TOOLTIP_MESSAGES[key];
    if (!flag || !message) return;
    if (localStorage.getItem(flag)) return; // Al eerder gezien

    const tooltip = document.getElementById('contextual-tooltip');
    const textEl  = document.getElementById('contextual-tooltip-text');
    if (!tooltip || !textEl) return;

    textEl.textContent = message;
    tooltip.classList.remove('fade-out');
    tooltip.style.display = 'block';

    // Auto-dismiss na 8 seconden
    clearTimeout(tooltipTimeout);
    tooltipTimeout = setTimeout(() => hideContextualTooltip(), 8000);

    localStorage.setItem(flag, '1');
    console.log(`💬 Contextuele tooltip getoond: ${key}`);
}

/**
 * Verberg de contextuele tooltip met fade-out.
 */
function hideContextualTooltip() {
    const tooltip = document.getElementById('contextual-tooltip');
    if (!tooltip || tooltip.style.display === 'none') return;

    tooltip.classList.add('fade-out');
    setTimeout(() => {
        tooltip.style.display = 'none';
        tooltip.classList.remove('fade-out');
    }, 260);
}


// ============================================================================
// Track B — Directe Feedback & Micro-interacties (Sprint 11B)
// B1: Empty state | B2: Inline spinner | B3: Indicator badge | B4: Hover cursor
// ============================================================================

/**
 * Initialiseer Track B feedback-elementen.
 * Roep aan na setupEventListeners() in DOMContentLoaded.
 */
function initFeedbackLayer() {
    // B3: Luister naar indicator-selectie voor badge update
    if (window.EventBus) {
        window.EventBus.on('INDICATOR_SELECTED', (data) => {
            updateIndicatorBadge(data?.name || null);
        });
    }

    // B4: Hover cursor feedback via deck.gl onHover
    // (geïntegreerd via onHover callback in displayOnMap, zie patch hieronder)

    console.log('🎯 Track B feedback layer geïnitialiseerd');
}

/**
 * B1: Herstel de empty state in het info-paneel.
 * Wordt aangeroepen bij reset/deselectie.
 */
function showGebiedEmptyState() {
    const content = document.getElementById('gebied-details');
    if (!content) return;

    content.innerHTML = `
        <div class="empty-state" id="gebied-empty-state">
            <svg class="empty-state-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/>
                <circle cx="12" cy="10" r="3"/>
            </svg>
            <p class="empty-state-title">Klik op een buurt</p>
            <p class="empty-state-text">
                Selecteer een buurt op de kaart om details te bekijken.
                Gebruik <kbd>Shift+klik</kbd> om meerdere buurten te vergelijken.
            </p>
        </div>
    `;
}

/**
 * B2: Toon inline loading spinner in het info-paneel.
 * @param {string} message
 */
function showInlineLoading(message = 'Laden...') {
    const content = document.getElementById('gebied-details');
    if (!content) return;

    content.innerHTML = `
        <div class="inline-spinner-container">
            <div class="inline-spinner"></div>
            <span class="inline-spinner-text">${escapeHtml(message)}</span>
        </div>
    `;
}

/**
 * B3: Update de actieve indicator badge boven het info-paneel.
 * @param {string|null} indicatorName - null om te verbergen
 */
function updateIndicatorBadge(indicatorName) {
    const badge = document.getElementById('active-indicator-badge');
    const nameEl = document.getElementById('active-indicator-name');
    if (!badge || !nameEl) return;

    if (indicatorName) {
        nameEl.textContent = indicatorName;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

/**
 * B4: Update de hover-cursor op de kaart-container.
 * @param {boolean} isHovering
 */
function setMapHoverCursor(isHovering) {
    const container = document.querySelector('.map-container');
    if (container) {
        container.dataset.hovering = isHovering ? 'true' : 'false';
    }
}


// ============================================================================
// Track C — Indicator Accordion & Zoekbalk (Sprint 11B)
// Vervangt de flat dropdown met een gegroepeerd, doorzoekbaar accordeon
// ============================================================================

/** Cache voor de Kompas-hiërarchie (thema → indicator mapping) */
let kompasHierarchie = null;
let accordionIndicatoren = []; // Flat list met thema-info voor zoekfilter

/**
 * Haal de Kompas-hiërarchie op en bouw een thema→indicator mapping.
 * Wordt éénmalig aangeroepen bij eerste loadIndicatoren.
 */
async function fetchKompasHierarchie() {
    if (kompasHierarchie) return kompasHierarchie;

    try {
        // Standaard-kompasconfiguratie van deze instantie, geen vaste ID (#231)
        const resp = await fetch('/api/kompas/standaard/hierarchie');
        if (!resp.ok) return null;
        const data = await resp.json();

        // Bouw een map: indicator_uuid → thema-pad
        const themaMap = {};
        function walk(node, path) {
            if (!node) return;
            if (node.type === 'indicator' && node.uuid) {
                themaMap[node.uuid] = path.length > 0 ? path[0] : 'Overig';
            }
            if (node.children) {
                for (const child of node.children) {
                    const newPath = node.name && node.name !== 'Root'
                        ? [node.name, ...path.slice(1)]
                        : path;
                    walk(child, newPath.length > 0 ? newPath : [node.name || 'Overig']);
                }
            }
        }

        const root = data.hierarchie || data;
        if (root.children) {
            for (const topLevel of root.children) {
                walk(topLevel, [topLevel.name || 'Overig']);
            }
        }

        kompasHierarchie = themaMap;
        console.log(`📂 Kompas-hiërarchie geladen: ${Object.keys(themaMap).length} indicatoren gemapt`);
        return themaMap;
    } catch (e) {
        console.warn('⚠️ Kompas-hiërarchie niet beschikbaar, fallback naar flat lijst:', e.message);
        return null;
    }
}

/**
 * Bouw de accordion UI op basis van geladen indicatoren + Kompas thema-mapping.
 * @param {Array} indicatoren - Array van indicator objecten uit de API
 */
async function buildIndicatorAccordion(indicatoren) {
    const container = document.getElementById('indicator-accordion');
    const searchInput = document.getElementById('indicator-search');
    if (!container) return;

    // Haal Kompas-hiërarchie op (gecachet na eerste call)
    const themaMap = await fetchKompasHierarchie();

    // Groepeer indicatoren per thema
    const groepen = {};
    indicatoren.forEach(ind => {
        const thema = (themaMap && themaMap[ind.uuid]) || 'Overig';
        if (!groepen[thema]) groepen[thema] = [];
        groepen[thema].push(ind);
    });

    // Sorteer groepen: 'Overig' altijd als laatste
    const themaNames = Object.keys(groepen).sort((a, b) => {
        if (a === 'Overig') return 1;
        if (b === 'Overig') return -1;
        return a.localeCompare(b, 'nl');
    });

    // Kleuren per thema (hergebruik Kompas kleuren)
    const themaKleuren = {
        'Kwaliteit fysieke leefomgeving': '#3B82F6',
        'Kwaliteit voorzieningen': '#8B5CF6',
        'Sociale samenhang': '#EC4899',
        'Veiligheid': '#EF4444',
        'Bevolking & Huishouden': '#F59E0B',
        'Gezondheid': '#10B981',
        'Onderwijs': '#6366F1',
        'Inkomen & Participatie': '#F97316',
        'Wonen': '#14B8A6',
        'Overig': '#6B7280',
    };

    // Bouw flat list voor zoekfilter
    accordionIndicatoren = [];
    indicatoren.forEach(ind => {
        const thema = (themaMap && themaMap[ind.uuid]) || 'Overig';
        accordionIndicatoren.push({
            uuid: ind.uuid,
            naam: ind.naam,
            thema: thema,
            coverage: ind.aantal_gebieden_met_data || 0,
            eenheid: ind.eenheid || '',
        });
    });

    // Render accordion
    let html = '';
    themaNames.forEach(thema => {
        const items = groepen[thema];
        const withData = items.filter(i => (i.aantal_gebieden_met_data || 0) > 0).length;
        const kleur = themaKleuren[thema] || '#6B7280';

        html += `<div class="accordion-group" data-thema="${escapeHtml(thema)}">
            <div class="accordion-header" role="button" tabindex="0" aria-expanded="false" onclick="toggleAccordionGroup(this)">
                <svg class="accordion-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                </svg>
                <span class="accordion-color-dot" style="background:${kleur}"></span>
                <span class="accordion-label">${escapeHtml(thema)}</span>
                <span class="accordion-count">${withData}/${items.length}</span>
            </div>
            <div class="accordion-body">`;

        // Sorteer: items met data bovenaan, dan alfabet
        items.sort((a, b) => {
            const aCov = a.aantal_gebieden_met_data || 0;
            const bCov = b.aantal_gebieden_met_data || 0;
            if (aCov > 0 && bCov === 0) return -1;
            if (aCov === 0 && bCov > 0) return 1;
            return a.naam.localeCompare(b.naam, 'nl');
        });

        items.forEach(ind => {
            const coverage = ind.aantal_gebieden_met_data || 0;
            const noData = coverage === 0;
            const activeClass = state.currentIndicator === ind.uuid ? ' active' : '';
            const noDataClass = noData ? ' no-data' : '';

            html += `<div class="indicator-item${activeClass}${noDataClass}"
                        data-uuid="${escapeHtml(ind.uuid)}" data-naam="${escapeHtml(ind.naam)}"
                        ${noData ? 'aria-disabled="true"' : 'role="button" tabindex="0"'}
                        ${noData ? '' : 'onclick="selectAccordionIndicator(this.dataset.uuid, this.dataset.naam)"'}>
                <span class="indicator-item-name">${escapeHtml(ind.naam)}</span>${ind.toegang === 'intern' ? INTERN_LABEL_HTML : ''}
                <span class="indicator-item-coverage">${coverage > 0 ? coverage : '—'}</span>
            </div>`;
        });

        html += `</div></div>`;
    });

    container.innerHTML = html;

    // Enable zoekbalk
    if (searchInput) {
        searchInput.disabled = false;
        searchInput.value = '';
    }

    console.log(`📂 Accordion gebouwd: ${themaNames.length} thema's, ${indicatoren.length} indicatoren`);
}

/**
 * Toggle een accordion-groep open/dicht.
 */
function toggleAccordionGroup(headerEl) {
    const group = headerEl.closest('.accordion-group');
    if (group) {
        const open = group.classList.toggle('open');
        headerEl.setAttribute('aria-expanded', String(open));
    }
}

/**
 * Selecteer een indicator vanuit de accordion.
 * Synct met het hidden select element en triggert EventBus.
 */
function selectAccordionIndicator(uuid, naam) {
    // Update visuele state in accordion
    document.querySelectorAll('.indicator-item.active').forEach(el => el.classList.remove('active'));
    const item = document.querySelector(`.indicator-item[data-uuid="${uuid}"]`);
    if (item) item.classList.add('active');

    // Sync met hidden select
    const select = document.getElementById('indicator-select');
    if (select) select.value = uuid;

    // Update state
    state.currentIndicator = uuid;
    updateButtonState();

    // Track B3: Update badge
    updateIndicatorBadge(naam);

    // Emit EventBus event (identiek aan Kompas-selectie flow)
    if (window.EventBus) {
        window.EventBus.emit('INDICATOR_SELECTED', { uuid, name: naam });
    }

    // Direct kaart laden
    loadKaartData();

    // Open legenda paneel
    togglePanel('legenda');

    console.log(`🎯 Indicator geselecteerd via accordion: ${naam}`);
}

/**
 * C1: Zoekfilter met debounce 150ms.
 * Filtert de accordion op indicator-naam.
 */
let searchDebounceTimer = null;

function initIndicatorSearch() {
    const searchInput = document.getElementById('indicator-search');
    const clearBtn = document.getElementById('indicator-search-clear');
    if (!searchInput) return;

    searchInput.addEventListener('input', () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            filterAccordion(searchInput.value.trim());
        }, 150);

        // Toggle clear button
        if (clearBtn) {
            clearBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
        }
    });

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearBtn.style.display = 'none';
            filterAccordion('');
            searchInput.focus();
        });
    }

    console.log('🔍 Indicator zoekfunctie geïnitialiseerd');
}

/**
 * Filter de accordion items op basis van zoekterm.
 * @param {string} query
 */
function filterAccordion(query) {
    const container = document.getElementById('indicator-accordion');
    if (!container) return;

    const groups = container.querySelectorAll('.accordion-group');
    const lowerQuery = query.toLowerCase();

    if (!query) {
        // Reset: alle groepen tonen, alle dichtklappen
        groups.forEach(group => {
            group.style.display = '';
            group.classList.remove('open');
            group.querySelector('.accordion-header')?.setAttribute('aria-expanded', 'false');
            group.querySelectorAll('.indicator-item').forEach(item => {
                item.style.display = '';
                // Reset highlight
                const nameEl = item.querySelector('.indicator-item-name');
                if (nameEl) nameEl.textContent = item.dataset.naam;
            });
        });
        return;
    }

    // Filter: toon alleen matches, open groepen met matches
    groups.forEach(group => {
        const items = group.querySelectorAll('.indicator-item');
        let hasMatch = false;

        items.forEach(item => {
            const naam = item.dataset.naam || '';
            const nameEl = item.querySelector('.indicator-item-name');

            if (naam.toLowerCase().includes(lowerQuery)) {
                item.style.display = '';
                hasMatch = true;
                // Highlight match
                if (nameEl) {
                    const idx = naam.toLowerCase().indexOf(lowerQuery);
                    const before = naam.slice(0, idx);
                    const match = naam.slice(idx, idx + query.length);
                    const after = naam.slice(idx + query.length);
                    nameEl.innerHTML = `${escapeHtml(before)}<mark>${escapeHtml(match)}</mark>${escapeHtml(after)}`;
                }
            } else {
                item.style.display = 'none';
            }
        });

        group.style.display = hasMatch ? '' : 'none';
        if (hasMatch) {
            group.classList.add('open');
            group.querySelector('.accordion-header')?.setAttribute('aria-expanded', 'true');
        }
    });
}
