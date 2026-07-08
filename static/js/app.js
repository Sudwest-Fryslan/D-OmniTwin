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
const state = {
    currentGebiedstype: null,
    currentIndicator: null,
    currentGemeenteCode: localStorage.getItem('omnitwin-gemeente') || '', // Default: Alle gemeenten (empty = no filter)
    deckgl: null,
    currentData: null,
    enable3D: false, // CHANGED: Default OFF
    heightScale: 10,
    showAll: false,
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
    highlightedGebiedId: null,     // Sprint 18 F3: Visuele highlight voor Top-buurten

    // Sprint 18: Externe kaartlagen (WFS, PDOK, etc.)
    externeKaartlagen: [],         // Actieve lagen definitie [{id, naam, kleur_lijn, ...}]
    externeKaartlaagData: {},      // { laag_id: { laag, geojson } }
};

// Publiceer state op window zodat chat.js en andere modules de kaartselectie kunnen lezen
window.state = state;

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
        getTooltip: ({ object, layer }) => {
            if (object) {
                const props = object.properties;
                const tooltipStyle = {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    color: 'white',
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                };

                // Externe kaartlaag tooltip (Sprint 18)
                if (layer?.id?.startsWith('externe-laag-')) {
                    const featureNaam = props.woonplaats || props.naam || props.name || props.Naam || props.Deelgebied || props.deelgebied || 'Onbekend';
                    return {
                        html: `
                <div style="font-family: Inter, sans-serif;">
                  <strong>\u{1F310} ${featureNaam}</strong><br/>
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
                <div style="font-family: Inter, sans-serif;">
                  <strong>🗺️ ${props.deelgebied}</strong><br/>
                  <small style="opacity:0.7;">${props.naam}</small><br/>
                  Oppervlakte: <strong>${props.oppervlakte_km2} km²</strong><br/>
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
                <div style="font-family: Inter, sans-serif;">
                  <strong>🏠 Pand</strong><br/>
                  <small style="opacity:0.6;">${bagId}</small><br/>
                  Bouwjaar: <strong>${bouwjaar}</strong><br/>
                  Hoogte: <strong>${pandHoogte} m</strong> · Opp: <strong>${opp} m²</strong>
                  ${indicatorInfo}
                </div>
              `,
                        style: tooltipStyle
                    };
                }

                // Default buurt tooltip
                const indicatorLabel = props.indicator_naam || 'Indicator';
                const indicatorValue = props.indicator_waarde !== null ?
                    formatNumber(props.indicator_waarde) + ' ' + (props.eenheid || '') :
                    'Geen data';

                return {
                    html: `
            <div style="font-family: Inter, sans-serif;">
              <strong>${props.naam}</strong><br/>
              ${props.indicator_naam ? `${props.indicator_naam}: ` : ''}<strong>${indicatorValue}</strong><br/>
              <small>${props.jaar || 'Onbekend'}</small>
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

// Fallback lijst Friese gemeenten (voor als API niet beschikbaar is)
const FRIESE_GEMEENTEN = [
    { code: '', naam: 'Alle gemeenten', is_eiland: false },
    { code: '0059', naam: 'Achtkarspelen', is_eiland: false },
    { code: '0060', naam: 'Ameland', is_eiland: true },
    { code: '1891', naam: 'Dantumadiel', is_eiland: false },
    { code: '1921', naam: 'De Fryske Marren', is_eiland: false },
    { code: '0072', naam: 'Harlingen', is_eiland: false },
    { code: '0074', naam: 'Heerenveen', is_eiland: false },
    { code: '0080', naam: 'Leeuwarden', is_eiland: false },
    { code: '1970', naam: 'Noardeast-Fryslân', is_eiland: false },
    { code: '0085', naam: 'Ooststellingwerf', is_eiland: false },
    { code: '0086', naam: 'Opsterland', is_eiland: false },
    { code: '0088', naam: 'Schiermonnikoog', is_eiland: true },
    { code: '0140', naam: 'Smallingerland', is_eiland: false },
    { code: '1900', naam: 'Súdwest-Fryslân', is_eiland: false },
    { code: '0093', naam: 'Terschelling', is_eiland: true },
    { code: '0737', naam: 'Tytsjerksteradiel', is_eiland: false },
    { code: '0096', naam: 'Vlieland', is_eiland: true },
    { code: '1949', naam: 'Waadhoeke', is_eiland: false },
    { code: '0098', naam: 'Weststellingwerf', is_eiland: false }
];

// Store loaded gemeenten for lookup
let loadedGemeenten = [];

async function loadGemeenten() {
    const datalist = document.getElementById('gemeente-options');
    const input = document.getElementById('gemeente-input');
    const codeInput = document.getElementById('gemeente-code');
    const info = document.getElementById('gemeente-info');

    let gemeenten = [];

    try {
        const response = await fetch('/api/data/gemeenten?provincie=eq.Frysl%C3%A2n&order=naam.asc');
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
        gemeenten = FRIESE_GEMEENTEN;
        console.log('📋 Gebruik fallback gemeenten lijst');
    }

    loadedGemeenten = gemeenten;

    // Populate datalist
    datalist.innerHTML = '';
    gemeenten.forEach(gemeente => {
        const option = document.createElement('option');
        option.value = gemeente.naam;
        option.dataset.code = gemeente.code;
        datalist.appendChild(option);
    });

    // Set initial value from state
    const currentGemeente = gemeenten.find(g => g.code === state.currentGemeenteCode);
    if (currentGemeente) {
        input.value = currentGemeente.naam;
        codeInput.value = currentGemeente.code;
    } else {
        input.value = 'Alle gemeenten';
        codeInput.value = '';
    }

    info.textContent = `${gemeenten.length - 1} gemeenten beschikbaar`;
}

function setupGemeenteSelector() {
    const input = document.getElementById('gemeente-input');
    const codeInput = document.getElementById('gemeente-code');
    const info = document.getElementById('gemeente-info');

    if (!input) return;

    // Handle selection from datalist
    input.addEventListener('change', (e) => {
        const inputValue = e.target.value;
        const gemeente = loadedGemeenten.find(g => g.naam === inputValue);

        if (gemeente) {
            state.currentGemeenteCode = gemeente.code;
            codeInput.value = gemeente.code;
            localStorage.setItem('omnitwin-gemeente', gemeente.code);

            console.log(`📍 Gemeente: ${gemeente.naam} (${gemeente.code || 'alle'})`);
            info.textContent = gemeente.code ? `Geselecteerd: ${gemeente.naam}` : 'Alle gemeenten';

            state.currentData = null;
            clearGebiedSelection();
            updateSelectionUI();
            
            // Werk ook het Kompas paneel bij naar de gemeente of landelijk niveau
            if (window.kompasViz && window.kompasViz.currentConfigId) {
                if (gemeente.id) {
                    window.kompasViz.loadGebiedData(window.kompasViz.currentConfigId, gemeente.id);
                } else {
                    // Geen ID (bijv. "Alle gemeenten")
                    window.kompasViz.currentGebiedId = null;
                    window.kompasViz.loadHierarchie(window.kompasViz.currentConfigId);
                }
            }

            // Herlaad kaart data met nieuwe gemeente filter
            if (state.currentGebiedstype) {
                loadKaartData();
            }
        } else if (inputValue === '' || inputValue.toLowerCase() === 'alle') {
            state.currentGemeenteCode = '';
            codeInput.value = '';
            localStorage.setItem('omnitwin-gemeente', '');
            input.value = 'Alle gemeenten';
            info.textContent = 'Alle gemeenten';
            
            if (window.kompasViz && window.kompasViz.currentConfigId) {
                window.kompasViz.currentGebiedId = null;
                window.kompasViz.loadHierarchie(window.kompasViz.currentConfigId);
            }

            // Herlaad kaart data zonder gemeente filter
            if (state.currentGebiedstype) {
                loadKaartData();
            }
        }
    });

    // Select all text on focus for easy replacement
    input.addEventListener('focus', () => {
        input.select();
    });
}

// ---- End Gemeente Selector ----


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
            attrUrl += `&indicator_uuid=${state.currentIndicator}`;
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
        state.initialDataLoaded = false;

        displayOnMap(geojson);
        updateFeatureCount(geojson.metadata);
        updateLegenda(geojson);

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
                transitionDuration: 1200,
            };
        } else {
            state.currentViewState = {
                ...state.currentViewState,
                pitch: 50,
                transitionDuration: 800,
            };
        }
        state.deckgl.setProps({ initialViewState: state.currentViewState });

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
        showError('3D panden konden niet worden geladen: ' + e.message);
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
        const res = await fetch(`/api/omgevingsvisie/deelgebieden/${deelgebiedId}/buurten`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

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

        // Render toggles veilig via DOM API (geen innerHTML)
        container.replaceChildren();
        state.externeKaartlagen.forEach(laag => {
            // Label wrapper
            const label = document.createElement('label');
            label.className = 'checkbox-label';

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `toggle-externe-laag-${laag.id}`;
            checkbox.dataset.laagId = String(laag.id);

            // Custom checkbox span
            const checkboxCustom = document.createElement('span');
            checkboxCustom.className = 'checkbox-custom';

            // Label text with icon
            const labelText = document.createElement('span');
            labelText.textContent = `\u{1F310} ${laag.naam}`;

            label.appendChild(checkbox);
            label.appendChild(checkboxCustom);
            label.appendChild(labelText);
            container.appendChild(label);

            // Help text
            if (laag.beschrijving) {
                const helpText = document.createElement('span');
                helpText.className = 'help-text';
                helpText.textContent = laag.beschrijving;
                container.appendChild(helpText);
            }

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
    }
    console.log(`\u{1F310} Externe laag ${laagId} verwijderd van kaart`);
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

    // Create GeoJsonLayer (Different IDs prevent WebGL buffer corruption during 2D/3D toggle)
    const layer = new GeoJsonLayer({
        id: `gebieden-layer-${state.enable3D ? '3d' : '2d'}`,
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
            if (value === null || value === undefined) {
                // Determine "No Data" color based on theme
                const r = state.currentTheme === 'dark' ? 200 : 80;
                const g = state.currentTheme === 'dark' ? 200 : 80;
                const b = state.currentTheme === 'dark' ? 200 : 80;
                const a = state.enable3D ? 255 : (state.currentTheme === 'dark' ? 100 : 200);
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

        // Track D: Gouden outline bij selectie, witte borders voor overige
        getLineColor: d => {
            const featureId = d.id || d.properties?.id;
            if (featureId && isGebiedSelected(featureId)) {
                return [234, 179, 8, 255]; // Selectie goud (#eab308)
            }
            return [255, 255, 255, 200]; // White border
        },
        getLineWidth: d => {
            const featureId = d.id || d.properties?.id;
            if (featureId && isGebiedSelected(featureId)) {
                return 80; // Dikke gouden rand bij selectie
            }
            return 20; // Standaard dunne rand
        },

        // 3D Height
        getElevation: d => {
            if (!state.enable3D) return 0;

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
            getFillColor: [minValue, maxValue, state.enable3D, state.currentTheme],
            getLineColor: [state.currentTheme, Array.from(state.selectedGebiedIds).join(',')],
            getLineWidth: [Array.from(state.selectedGebiedIds).join(',')],
            getElevation: [state.enable3D, state.heightScale, minValue, maxValue],
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
        fitBounds(geojson);
        state.initialDataLoaded = true;
    }
}

function fitBounds(geojson) {
    // Calculate bounding box
    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    geojson.features.forEach(feature => {
        if (!feature.geometry || !feature.geometry.coordinates) return;
        const coords = feature.geometry.coordinates;

        // Flatten coordinates (works for MultiPolygon)
        const flattenCoords = (arr, depth = 0) => {
            if (depth >= 3) return arr;
            return arr.flatMap(item => flattenCoords(item, depth + 1));
        };

        const allCoords = flattenCoords(coords);

        allCoords.forEach(coord => {
            if (Array.isArray(coord) && coord.length >= 2) {
                minLon = Math.min(minLon, coord[0]);
                maxLon = Math.max(maxLon, coord[0]);
                minLat = Math.min(minLat, coord[1]);
                maxLat = Math.max(maxLat, coord[1]);
            }
        });
    });

    if (minLon !== Infinity) {
        const centerLon = (minLon + maxLon) / 2;
        const centerLat = (minLat + maxLat) / 2;

        // Calculate appropriate zoom level
        const latDiff = maxLat - minLat;
        const lonDiff = maxLon - minLon;
        const maxDiff = Math.max(latDiff, lonDiff);

        let zoom = 7;
        if (maxDiff < 0.1) zoom = 12;
        else if (maxDiff < 0.5) zoom = 10;
        else if (maxDiff < 2) zoom = 8;

        state.deckgl.setProps({
            initialViewState: {
                longitude: centerLon,
                latitude: centerLat,
                zoom: zoom,
                pitch: state.enable3D ? 45 : 0,
                bearing: 0,
                transitionDuration: 1000,
                transitionInterpolator: new deck.FlyToInterpolator()
            }
        });
    }
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
                stopsHtml += `<stop offset="${offset.toFixed(1)}%" style="stop-color:${hexColor};stop-opacity:1" />\n`;
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
        hintsContainer.innerHTML = `
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
        option.dataset.count = gt.aantal_gebieden || 0;
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

        option.dataset.coverage = coverage;
        option.dataset.eenheid = ind.eenheid || '';

        // Disable options without data
        if (coverage === 0) {
            option.disabled = true;
            option.style.color = '#94a3b8'; // Muted color
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
      <span class="detail-value">${gebied.id}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Naam:</span>
      <span class="detail-value">${gebied.naam}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Type:</span>
      <span class="detail-value">${gebied.gebiedstype.naam}</span>
    </div>
  `;

    if (indicatoren && indicatoren.length > 0) {
        html += '<h4>Indicatoren</h4>';
        indicatoren.slice(0, 10).forEach(ind => {
            html += `
        <div class="detail-row">
          <span class="detail-label">${ind.naam}:</span>
          <span class="detail-value">${formatNumber(ind.waarde)} ${ind.eenheid || ''}</span>
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
        <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border, rgba(255,255,255,0.1));">
            <strong style="font-size: 1rem;"><img src="/static/images/chart-bar.svg" alt="" style="width:18px; height:18px; vertical-align:-3px; filter: brightness(0) invert(1); margin-right: 4px;">Vergelijking: ${ids.length} gebieden</strong>
            <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 4px;">
                ${allData.map(d => d.gebied.naam).join(' · ')}
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
                    <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 4px; color: var(--color-text-primary, #e2e8f0);">
                        ${ind.naam} <span style="opacity:0.5; font-weight:400;">(${ind.eenheid})</span>
                    </div>`;

                ind.waarden.forEach((w, idx) => {
                    if (w.waarde === null || w.waarde === undefined) return;
                    const pct = Math.max(5, (Math.abs(w.waarde) / maxVal) * 100);
                    const color = areaColors[idx % areaColors.length];
                    const isAboveAvg = w.waarde >= gemiddelde;

                    html += `
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 3px; font-size: 0.75rem;">
                        <span style="width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; opacity: 0.8;" title="${w.gebiedNaam}">
                            ${w.gebiedNaam.length > 12 ? w.gebiedNaam.slice(0, 11) + '…' : w.gebiedNaam}
                        </span>
                        <div style="flex: 1; height: 16px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden;">
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
                        Gem: ${formatNumber(gemiddelde)} ${ind.eenheid}
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
 * Sprint 8D: Rapport type keuze modal — Gebiedsdossier vs Benchmark
 */
function openRapportTypeModal(gebiedId, baseUrl) {
    // Verwijder bestaande modal indien aanwezig
    document.getElementById('rapport-type-modal')?.remove();

    const modal = document.createElement('div');
    modal.id = 'rapport-type-modal';
    modal.style.cssText = `
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0,0,0,0.6); display: flex;
        align-items: center; justify-content: center;
    `;
    modal.innerHTML = `
        <div style="
            background: var(--color-surface, #1e2535);
            border: 1px solid var(--color-border, rgba(255,255,255,0.1));
            border-radius: 12px; padding: 1.5rem; width: 340px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        ">
            <h3 style="margin:0 0 0.5rem; font-size:1rem;">Kies Rapport Type</h3>
            <p style="margin:0 0 1.25rem; font-size:0.85rem; opacity:0.6;">
                Welk rapport wil je genereren?
            </p>
            <div style="display:flex; flex-direction:column; gap:0.75rem;">
                <button id="rapport-modal-dossier" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: var(--color-primary, #3b82f6); color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                ">📄 Gebiedsdossier<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Volledige analyse van dit gebied
                    </span>
                </button>
                <button id="rapport-modal-thema" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: #8b5cf6; color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                ">📊 Thema-Analyse<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Diepgaande analyse per Kompas thema
                    </span>
                </button>
                <button id="rapport-modal-benchmark" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: var(--color-bg-alt, #2d3748); color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                    border: 1px solid var(--color-border, rgba(255,255,255,0.15));
                ">⚖️ Benchmark Vergelijker<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Vergelijk met andere gebieden of Fryslân
                    </span>
                </button>
            </div>
            <button id="rapport-modal-sluiten" style="
                margin-top:1rem; background:none; border:none; color:inherit;
                opacity:0.5; cursor:pointer; font-size:0.85rem; width:100%; text-align:center;
            ">Annuleren</button>
        </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('rapport-modal-dossier').addEventListener('click', () => {
        window.open(`${baseUrl}/admin/rapport/${gebiedId}`, '_blank');
        modal.remove();
    });
    document.getElementById('rapport-modal-thema').addEventListener('click', () => {
        window.open(`${baseUrl}/admin/rapport/thema-analyse?gebieden=${gebiedId}`, '_blank');
        modal.remove();
    });
    document.getElementById('rapport-modal-benchmark').addEventListener('click', () => {
        window.open(`${baseUrl}/admin/rapport/benchmark?gebied_a=${gebiedId}`, '_blank');
        modal.remove();
    });
    document.getElementById('rapport-modal-sluiten').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

/**
 * Multi-select rapport keuze modal — Benchmark vs Multi-Gebiedsdossier
 */
function openMultiSelectRapportModal(ids, baseUrl) {
    document.getElementById('rapport-type-modal')?.remove();

    const deelgebiedNaam = state.selectedDeelgebiedNaam || `${ids.length} buurten`;
    const modal = document.createElement('div');
    modal.id = 'rapport-type-modal';
    modal.style.cssText = `
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0,0,0,0.6); display: flex;
        align-items: center; justify-content: center;
    `;
    modal.innerHTML = `
        <div style="
            background: var(--color-surface, #1e2535);
            border: 1px solid var(--color-border, rgba(255,255,255,0.1));
            border-radius: 12px; padding: 1.5rem; width: 380px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        ">
            <h3 style="margin:0 0 0.5rem; font-size:1rem;">Kies Rapport Type</h3>
            <p style="margin:0 0 1.25rem; font-size:0.85rem; opacity:0.6;">
                ${ids.length} gebieden geselecteerd ${state.selectedDeelgebiedNaam ? `(${state.selectedDeelgebiedNaam})` : ''}
            </p>
            <div style="display:flex; flex-direction:column; gap:0.75rem;">
                <button id="rapport-modal-benchmark" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: var(--color-bg-alt, #2d3748); color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                    border: 1px solid var(--color-border, rgba(255,255,255,0.15));
                ">⚖️ Benchmark Vergelijker<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Vergelijk gebieden onderling met delta-tabel
                    </span>
                </button>
                <button id="rapport-modal-multi-gebied" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: var(--color-primary, #3b82f6); color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                ">🗺️ Multi-Gebiedsdossier<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Z-score analyse met kaart en ranking
                    </span>
                </button>
                <button id="rapport-modal-thema-analyse" style="
                    padding: 0.75rem 1rem; border-radius: 8px; border: none;
                    background: var(--color-bg-alt, #2d3748); color: white;
                    font-size:0.95rem; font-weight:600; cursor:pointer; text-align:left;
                    border: 1px solid var(--color-border, rgba(255,255,255,0.15));
                ">📊 Thema-Analyse<br>
                    <span style="font-weight:400; font-size:0.8rem; opacity:0.8;">
                        Alle indicatoren per thema/onderdeel
                    </span>
                </button>
            </div>
            <button id="rapport-modal-sluiten-multi" style="
                margin-top:1rem; background:none; border:none; color:inherit;
                opacity:0.5; cursor:pointer; font-size:0.85rem; width:100%; text-align:center;
            ">Annuleren</button>
        </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('rapport-modal-benchmark').addEventListener('click', () => {
        const [a, ...rest] = ids;
        window.open(`${baseUrl}/admin/rapport/benchmark?gebied_a=${a}&gebieden_b=${rest.join(',')}`, '_blank');
        modal.remove();
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
        window.open(`${baseUrl}/admin/rapport/multi-gebied?gebieden=${gebiedenParam}&naam=${naam}${extraParams}`, '_blank');
        modal.remove();
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
        window.open(`${baseUrl}/admin/rapport/thema-analyse?gebieden=${gebiedenParam}&naam=${naam}${extraParams}`, '_blank');
        modal.remove();
    });
    document.getElementById('rapport-modal-sluiten-multi').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
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
            rapportInfo.innerHTML = `<strong>Geselecteerd:</strong> ${namen[0]} (${state.selectedGebiedId})`;
            rapportBtn.disabled = false;
        } else {
            const namen = getSelectedGebiedNamen();
            const namenTekst = namen.length <= 3
                ? namen.join(', ')
                : `${namen.slice(0, 3).join(', ')} (+${namen.length - 3})`;
            rapportInfo.innerHTML = `<strong>Selectie (${count}):</strong> ${namenTekst}`;
            rapportBtn.disabled = false;
        }
    }

    // Update or create floating selection badge (Sprint 12: ook bij count=1 voor 3D panden knop)
    let badge = document.getElementById('selection-badge');
    if (count >= 1) {
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'selection-badge';
            badge.style.cssText = `
                position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%); z-index: 1000;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white; padding: 10px 18px; border-radius: 24px;
                font-size: 14px; font-weight: 600; cursor: pointer;
                box-shadow: 0 4px 16px rgba(0,0,0,0.3);
                display: flex; align-items: center; gap: 8px;
                transition: transform 0.2s, opacity 0.2s;
            `;
            badge.title = 'Klik om selectie op te heffen';
            badge.addEventListener('click', () => {
                clearGebiedSelection();
                updateSelectionUI();
                if (state.currentData) displayOnMap(state.currentData);
            });
            document.body.appendChild(badge);
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

        // Build badge content with optional 3D panden button  
        const bag3dBtnHtml = (count >= 1 && count <= 3)
            ? `<button id="bag3d-toggle-btn" style="
                background: ${state.show3DBuildings ? 'rgba(234,179,8,0.9)' : 'rgba(255,255,255,0.15)'};
                border: 1px solid rgba(255,255,255,0.3); border-radius: 12px;
                color: white; padding: 4px 10px; font-size: 12px; cursor: pointer;
                margin-left: 4px; transition: background 0.2s;
              " title="${state.show3DBuildings ? 'BAG panden verbergen' : 'Laad 3D panden vanuit de 3DBAG'}">
                <img src="/static/images/building.svg" alt="" style="width:14px; height:14px; filter: brightness(0) invert(1); vertical-align: -1px;"> ${state.show3DBuildings ? 'Panden uit' : '3D Panden'}
              </button>`
            : '';

        badge.innerHTML = `<img src="/static/images/map-pin-plus.svg" alt="" style="width:18px; height:18px; filter: brightness(0) invert(1);"> ${badgeTekst} ${bag3dBtnHtml} <span style="opacity:0.7; font-size:12px;">✕</span>`;
        badge.style.display = 'flex';
        // Ensure centered position (also fixes pre-existing badges from cache)
        badge.style.position = 'fixed';
        badge.style.bottom = '40px';
        badge.style.left = '50%';
        badge.style.transform = 'translateX(-50%)';
        badge.style.right = '';

        // Attach 3D BAG button handler (re-attached on every UI update)
        const bag3dBtn = document.getElementById('bag3d-toggle-btn');
        if (bag3dBtn) {
            bag3dBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent badge click (clear selection)
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
    } else if (badge) {
        badge.style.display = 'none';
    }
}

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
            const selectedOption = e.target.options[e.target.selectedIndex];
            const count = selectedOption.dataset.count;
            document.getElementById('gebiedstype-count').textContent =
                `${count} gebieden in dit type`;

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
            transitionDuration: 500
        };
        state.deckgl.setProps({
            initialViewState: state.currentViewState
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
                    let attrUrl = `/api/gebiedsmonitor/kaart_data/${state.currentGebiedstype}?show_all=${state.showAll}&indicator_uuid=${state.currentIndicator}&jaar=${data.jaar}`;
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
                            if (props) {
                                Object.assign(f.properties, props);
                            } else {
                                // Clear missing data
                                f.properties.indicator_waarde = null;
                                f.properties.color = '#94A3B8';
                            }
                        });
                        state.currentData.metadata = attributes.metadata;
                        state.initialDataLoaded = false; // Prevents reset of camera

                        displayOnMap(state.currentData);
                        updateLegenda(state.currentData);
                    }
                } catch (error) {
                    console.error('❌ Fout bij laden historische kaart data:', error);
                }
            }
        });

        // Chat -> Map: Select Municipality (code-based lookup)
        window.EventBus.on('GEMEENTE_SELECTED', (data) => {
            console.log('📍 Chat sync: selecting gemeente', data.name, data.code);
            const input = document.getElementById('gemeente-input');
            const codeInput = document.getElementById('gemeente-code');
            const info = document.getElementById('gemeente-info');
            
            if (!input || !codeInput) return;
            
            // Lookup gemeente by code in the loaded list
            const gemeente = loadedGemeenten.find(g => g.code === data.code);
            const naam = gemeente ? gemeente.naam : data.name;
            const code = data.code;
            
            // Update UI
            input.value = naam;
            codeInput.value = code;
            info.textContent = `Geselecteerd: ${naam}`;
            
            // Update state
            state.currentGemeenteCode = code;
            localStorage.setItem('omnitwin-gemeente', code);
            
            // Clear selection and reload map
            state.currentData = null;
            clearGebiedSelection();
            updateSelectionUI();
            if (state.currentGebiedstype) loadKaartData();
            
            console.log(`✅ Gemeente via chat: ${naam} (${code})`);
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
    } else {
        console.error('❌ EventBus not available for subscription');
    }

    // Open Kompas Button (in Sidebar)
    const openKompasBtn = document.getElementById('open-kompas-btn');
    if (openKompasBtn) {
        openKompasBtn.addEventListener('click', () => {
            console.log('🔘 Open Kompas button clicked');
            if (state.kompasWindow) {
                state.kompasWindow.open();

                // Load data for selected area(s) if available
                if (state.selectedGebiedIds.size > 0 && window.kompasViz && window.kompasViz.currentConfigId) {
                    loadKompasForSelection(window.kompasViz.currentConfigId);
                } else if (window.kompasViz && window.kompasViz.currentConfigId) {
                    window.kompasViz.loadHierarchie(window.kompasViz.currentConfigId);
                }
            } else {
                console.error('❌ Kompas window state not initialized');
            }
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
    // Used if backend color is missing
    if (value === null || value === undefined) return [200, 200, 200, is3D ? 255 : 100];

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

    const csvContent = "data:text/csv;charset=utf-8," +
        [headers, ...rows].join('\n');

    const link = document.createElement('a');
    link.href = csvContent;
    link.download = `omnitwin-export-${Date.now()}.csv`;
    link.click();
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
        <span class="error-toast-msg">${message}</span>
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
 * Plaatst het centrum dicht bij de Kompas-rand (max 200px) i.p.v. midden in de vrije zone.
 */
function getFreezone() {
    const W = window.innerWidth;
    const MIN_ZONE = 150;       // Minimale bruikbare segmentbreedte (px)
    const MAX_KOMPAS_DIST = 200; // Max afstand centrum vanaf Kompas-rand (px)

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
        if (spaceLeft > spaceRight) {
            // Links van Kompas: cap afstand op MAX_KOMPAS_DIST
            const dist = Math.min(spaceLeft / 2, MAX_KOMPAS_DIST);
            centerX = kr.left - dist;
        } else {
            // Rechts van Kompas: cap afstand op MAX_KOMPAS_DIST
            const dist = Math.min(spaceRight / 2, MAX_KOMPAS_DIST);
            centerX = kr.right + dist;
        }
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
                transitionDuration: 800,
                transitionInterpolator: new deck.FlyToInterpolator()
            }
        });
}


// ============================================================================
// Track A1 — Initiële Onboarding (Welkomstmodal)
// Sprint 11B | localStorage flag: 'omnitwin_welcomed'
// ============================================================================

const ONBOARDING_KEY = 'omnitwin_welcomed';

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

    // Sluit modal bij Escape
    document.addEventListener('keydown', function onEscapeWelcome(e) {
        if (e.key === 'Escape') {
            dismissWelcomeModal();
            document.removeEventListener('keydown', onEscapeWelcome);
        }
    });

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
            <span class="inline-spinner-text">${message}</span>
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
        const resp = await fetch('/api/kompas/1/hierarchie');
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

        html += `<div class="accordion-group" data-thema="${thema}">
            <div class="accordion-header" onclick="toggleAccordionGroup(this)">
                <svg class="accordion-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                </svg>
                <span class="accordion-color-dot" style="background:${kleur}"></span>
                <span class="accordion-label">${thema}</span>
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
                        data-uuid="${ind.uuid}" data-naam="${ind.naam}"
                        ${noData ? '' : `onclick="selectAccordionIndicator('${ind.uuid}', '${ind.naam.replace(/'/g, "\\'")}')"` }>
                <span class="indicator-item-name">${ind.naam}</span>
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
    if (group) group.classList.toggle('open');
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
            group.querySelectorAll('.indicator-item').forEach(item => {
                item.style.display = '';
                // Reset highlight
                const nameEl = item.querySelector('.indicator-item-name');
                if (nameEl) nameEl.innerHTML = item.dataset.naam;
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
                    nameEl.innerHTML = `${before}<mark>${match}</mark>${after}`;
                }
            } else {
                item.style.display = 'none';
            }
        });

        group.style.display = hasMatch ? '' : 'none';
        if (hasMatch) group.classList.add('open');
    });
}
