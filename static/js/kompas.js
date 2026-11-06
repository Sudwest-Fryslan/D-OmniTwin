/**
 * D-Omni Kompas - D3.js Sunburst Visualization
 * 
 * Interactive hierarchical visualization for multi-kompas configurations
 * Uses D3.js v7 partition layout with zoom capabilities
 */

/**
 * Kleur uit het thema (#89) voor Chart.js, dat geen CSS-variabelen kent.
let _dummyColorProbe = null;

/**
 * Leest de berekende waarde van een variabele uit styles.css, bv. '--text-secondary'.
 * Lost CSS-variabelen betrouwbaar op naar echte rgb/hex waarden voor Canvas/Chart.js.
 */
function themaKleur(naam, terugval) {
    try {
        if (!_dummyColorProbe && document.body) {
            _dummyColorProbe = document.createElement('span');
            _dummyColorProbe.style.display = 'none';
            _dummyColorProbe.id = 'kompas-theme-color-probe';
            document.body.appendChild(_dummyColorProbe);
        }
        if (_dummyColorProbe) {
            const cssVar = naam.startsWith('--') ? `var(${naam})` : naam;
            _dummyColorProbe.style.color = '';
            _dummyColorProbe.style.color = cssVar;
            const computed = getComputedStyle(_dummyColorProbe).color;
            if (computed && computed !== '') {
                return computed;
            }
        }
    } catch (_) {}

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const fallback = isDark && terugval === '#1e293b' ? '#f1f5f9'
                   : (isDark && terugval === '#64748b' ? '#94a3b8'
                   : (isDark && terugval === '#e2e8f0' ? '#334155' : terugval));

    const waarde = getComputedStyle(document.documentElement).getPropertyValue(naam).trim();
    if (!waarde || waarde.startsWith('var(')) {
        return fallback;
    }
    return waarde;
}

window.themaKleur = themaKleur;

let _measureCanvasCtx = null;
function getMeasureCanvasCtx() {
    if (!_measureCanvasCtx && typeof document !== 'undefined') {
        const c = document.createElement('canvas');
        _measureCanvasCtx = c.getContext ? c.getContext('2d') : null;
        if (_measureCanvasCtx) {
            _measureCanvasCtx.font = '500 10px Inter, sans-serif';
        }
    }
    return _measureCanvasCtx;
}

class KompasVisualization {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.currentConfigId = null;
        this.currentGebiedId = null;
        this.currentData = null;
        this.currentNode = null;  // Track current zoom level

        // Dimensions (calculated in init())
        this.width = null;
        this.height = null;
        this.radius = null;
        this.radiusScale = 1;

        // Store root for zoom operations
        this.root = null;

        // D3 objects
        this.svg = null;
        this.g = null;

        // History for zoom out
        this.zoomStack = [];

        // Request tracking om verouderde async responses te negeren (#463/#466)
        this._loadRequestId = 0;
        this._detailsRequestId = 0;
        this._benchmarkRequestId = 0;
        this._lastGebiedReq = null;
        this._lastDetailsReq = null;

        // Choreografie synchronisatie (#465/#466): uitstel van D3 render tot camera landing
        this.deferNextRenderUntilLanding = false;
        this._pendingRender = null;

        // Init
        this.init();
    }

    triggerDeferredRender() {
        this.deferNextRenderUntilLanding = false;
        if (typeof this._pendingRender === 'function') {
            const fn = this._pendingRender;
            this._pendingRender = null;
            fn();
        }
    }

    init() {
        // Vaste coördinatenruimte (600x600) voor stabiele layout en native SVG-schaling
        this.width = 600;
        this.height = 600;
        this.radius = this.width / 10;  // 60, ruimte voor 4 lagen + labels

        // Create SVG with responsive sizing
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', '100%')  // Responsive width
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${this.width} ${this.height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet')
            .style('font-family', 'Inter, sans-serif')
            .style('display', 'block')
            .style('margin', '0 auto');

        // STRUCTURAL REFACTOR FOR STABLE ZOOM/ROTATION
        // 1. Center Group (Translates to middle)
        this.centerG = this.svg.append('g')
            .attr('class', 'kompas-center-group')
            .attr('transform', `translate(${this.width / 2}, ${this.height / 2})`);

        // 2. Rotate Group (Static -45deg rotation)
        this.rotateG = this.centerG.append('g')
            .attr('class', 'kompas-rotate-group')
            .attr('transform', 'rotate(-45)');

        // 3. Scale/Vis Group (Dynamic Scaling for Zoom)
        // We attach 'this.g' here so all existing code using this.g works as expected (appending paths etc)
        this.g = this.rotateG.append('g')
            .attr('class', 'kompas-scale-group');

        // Tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'kompas-tooltip')
            .style('position', 'absolute')
            .style('visibility', 'hidden');

        console.log('✅ Kompas visualization initialized:', this.width, 'x', this.height, 'radius:', this.radius);

        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                this.handleResize();
            }
        });
        resizeObserver.observe(this.container);

        // Ensure collapsed state on init (no expanded class)
        const windowEl = document.getElementById('kompas-window');
        if (windowEl) {
            windowEl.classList.remove('expanded');
        }

        // Setup A1 Tabs
        const tabDef = document.getElementById('tab-definitie');
        const tabOnt = document.getElementById('tab-ontologie');
        if (tabDef) tabDef.addEventListener('click', () => this._switchTab('definitie'));
        if (tabOnt) tabOnt.addEventListener('click', () => this._switchTab('ontologie'));

        // Setup A3 Timeslider
        this._setupTimesliderControls();
    }

    handleResize() {
        /**
         * Responsieve schaling van het kompas gebeurt via de SVG viewBox en CSS.
         * We her-renderen de sunburst hier bewust NOOIT: dat zou de actieve drill-down
         * en geselecteerde indicator afbreken zodra containers van grootte veranderen
         * (bijv. scrollbars die verschijnen bij openen van het detailpaneel).
         */
        if (this.trendChart?.resize) {
            this.trendChart.resize();
        }
        const isDockCollapsed = document.getElementById('rechter-dock')?.classList.contains('collapsed') && window.state?.dockMode !== 'floating';
        if (this._uitgesteldIpData && document.getElementById('ip-grafiek-wrap')?.clientWidth && !isDockCollapsed) {
            const data = this._uitgesteldIpData;
            this._uitgesteldIpData = null;
            this._renderBenchmarkGrafiek(data);
        } else if (this._ipChart?.resize) {
            this._ipChart.resize();
        }
    }

    async loadConfigurations() {
        /**
         * Laad alle beschikbare kompas configuraties
         * Populate dropdown selector
         */
        try {
            const response = await fetch('/api/kompas/configuraties');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            this.populateConfigSelector(data);

            return data;
        } catch (error) {
            console.error('❌ Fout bij ophalen configuraties:', error);
            this.showError('Kon configuraties niet laden');
        }
    }

    populateConfigSelector(data) {
        // Custom Dropdown Elements
        const container = document.getElementById('kompas-config-container');
        const trigger = document.getElementById('custom-select-trigger');
        const triggerText = document.getElementById('selected-config-text');
        const optionsList = document.getElementById('custom-options');
        const hiddenInput = document.getElementById('kompas-config-select');

        if (!container || !optionsList) return;

        // Clear existing
        optionsList.innerHTML = '';

        // Helper to determine icon
        const getIconHtml = (config) => {
            // Check for specific keywords to map to Lucide icons
            const nameLower = config.naam.toLowerCase();

            // Earth/Globe icon for "Volledig"
            if (nameLower.includes('volledig') || config.icoon.includes('🌍')) {
                return `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-globe option-icon"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`;
            }
            // Thermometer icon for "Klimaat"
            else if (nameLower.includes('klimaat') || config.icoon.includes('🌡️')) {
                return `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-thermometer option-icon"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/></svg>`;
            }

            // Fallback to emoji from DB if no match
            return `<span class="option-emoji">${escapeHtml(config.icoon)}</span>`;
        };

        // Populate Options
        data.configuraties.forEach(config => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'custom-option';
            optionDiv.dataset.value = config.id;
            // Toetsenbordbediening (WCAG 2.1.1); Enter/Spatie via globale handler in app.js
            optionDiv.setAttribute('role', 'button');
            optionDiv.tabIndex = 0;

            optionDiv.innerHTML = `
                ${getIconHtml(config)}
                <span>${escapeHtml(config.naam)}</span>
            `;

            if (config.is_standaard) {
                optionDiv.classList.add('selected');
                triggerText.innerHTML = optionDiv.innerHTML; // Set initial text/icon
                hiddenInput.value = config.id;
            }

            // Click Handler
            optionDiv.addEventListener('click', () => {
                // Update selection
                hiddenInput.value = config.id;
                triggerText.innerHTML = optionDiv.innerHTML;

                // Visual feedback
                document.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('selected'));
                optionDiv.classList.add('selected');

                // Close dropdown
                container.classList.remove('open');
                trigger.setAttribute('aria-expanded', 'false');
                trigger.focus();

                // Trigger change event manually for app.js listener
                const event = new Event('change');
                hiddenInput.dispatchEvent(event);
            });

            optionsList.appendChild(optionDiv);
        });

        // Toggle Dropdown
        trigger.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent document click closing immediately
            const open = container.classList.toggle('open');
            trigger.setAttribute('aria-expanded', String(open));
        });

        // Escape sluit de lijst en zet de focus terug op de trigger
        container.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && container.classList.contains('open')) {
                e.preventDefault(); // niet ook een omringende dialoog sluiten
                container.classList.remove('open');
                trigger.setAttribute('aria-expanded', 'false');
                trigger.focus();
            }
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                container.classList.remove('open');
                trigger.setAttribute('aria-expanded', 'false');
            }
        });

        // Update info text
        const info = document.getElementById('kompas-config-info');
        if (info) info.textContent = `${data.configuraties.length} configuraties beschikbaar`;

        // Set current config
        if (data.standaard_config_id) {
            this.currentConfigId = data.standaard_config_id;
        }
    }

    async loadHierarchie(configId) {
        /**
         * Laad hiërarchie voor specifieke configuratie (zonder data en kleuren)
         * NOTE: Deze wordt alleen gebruikt als fallback. Gebruik loadGebiedKompas() voor data.
         */
        try {
            const response = await fetch(`/api/kompas/${configId}/hierarchie`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            this.currentData = data;
            this.currentConfigId = configId;
            this.currentGebiedId = null;

            // Update UI
            document.getElementById('kompas-info').innerHTML =
                `<p class="help-text"><strong>${escapeHtml(data.config_naam)}</strong> - ${escapeHtml(data.total_indicators)} indicatoren</p>`;

            // Render sunburst
            this.renderSunburst(data.hierarchie);

            if (this._pendingIndicatorUuid) {
                const pending = this._pendingIndicatorUuid;
                this._pendingIndicatorUuid = null;
                setTimeout(() => this.navigateToIndicator(pending), 100);
            }

            return data;
        } catch (error) {
            console.error('❌ Fout bij ophalen hiërarchie:', error);
            this.showError('Kon hiërarchie niet laden');
        }
    }

    async loadGebiedData(configId, gebiedId) {
        /**
         * Laad kompas data voor specifiek gebied (met waarden)
         */
        // B1 deduplicatie: identieke aanroep binnen 300 ms negeren (#465/#466)
        const reqKey = `${configId}|${gebiedId}`;
        const nu = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
        if (this._lastGebiedReq && this._lastGebiedReq.key === reqKey && (nu - this._lastGebiedReq.time < 300)) {
            return Promise.resolve(this.currentData);
        }
        this._lastGebiedReq = { key: reqKey, time: nu };

        // Sprint 7 / #444 / #463: Bewaar expanded state EN indicator UUID vóór re-render
        const wasExpanded = this.isExpanded;
        const expandedIndicatorUuid = this._lastExpandedIndicatorUuid
            || (wasExpanded && this.currentNode?.data?.uuid ? this.currentNode.data.uuid : null);
        const zoomPath = this._getZoomPath();
        const reqId = ++this._loadRequestId;

        this.showLoading();

        try {
            const response = await fetch(`/api/kompas/${configId}/gebied/${gebiedId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (reqId !== this._loadRequestId) {
                console.log('🔄 Verouderde gebied data genegeerd (#463)');
                this.hideLoading();
                return;
            }
            this.currentData = data;
            this.currentConfigId = configId;
            this.currentGebiedId = gebiedId;

            // Update UI
            document.getElementById('kompas-info').innerHTML =
                `<p class="help-text"><strong>${escapeHtml(data.gebied_naam)}</strong><br>` +
                `Configuratie: ${escapeHtml(data.config_naam)}<br>` +
                `Indicatordekking: ${escapeHtml(data.coverage_percentage)}%` +
                (data.classificatie === 'percentiel_8'
                    ? '<br><span class="kompas-classificatie">Kleur: percentielklasse (8 × 12,5%)</span>' : '') +
                `</p>` + this._labelLegenda(data);

            // Bepaal actuele toestand (ook als gebruiker tijdens de fetch doorklikte, #463)
            const currentZoomPath = (this.currentNode === this.root)
                ? []
                : (this._getZoomPath().length > 0 ? this._getZoomPath() : zoomPath);
            const activeIndicatorUuid = this.isExpanded
                ? (this._currentIndicatorUuid || this._lastExpandedIndicatorUuid || (this.currentNode?.data?.uuid ? this.currentNode.data.uuid : null))
                : null;

            // Render sunburst with data (of stel uit tot landing camera, #465/#466)
            const doRender = () => {
                this.renderSunburst(data.hierarchie);
                this.updateSelectedAreasBadges();

                // Sprint 7 / #444 / #463: Herstel zoom-pad en actieve indicator direct zonder race condition
                if (currentZoomPath.length > 0) {
                    this._navigateToPath(currentZoomPath);
                }
                if (activeIndicatorUuid && this.root) {
                    const targetNode = this._findNodeByUuid(this.root, activeIndicatorUuid);
                    if (targetNode) {
                        this.expandDetails(targetNode);
                    }
                }
            };

            if (this.deferNextRenderUntilLanding) {
                this._pendingRender = () => {
                    doRender();
                    this.hideLoading();
                };
            } else {
                doRender();
                this.hideLoading();
            }

            return data;
        } catch (error) {
            this.hideLoading();
            if (reqId !== this._loadRequestId) return;
            console.error('❌ Fout bij ophalen gebied data:', error);
            this.showError('Kon gebied data niet laden: ' + (error.message || 'Onbekende fout'));
        }
    }

    async loadMultiGebiedData(configId, gebiedIds) {
        /**
         * Sprint 7: Laad kompas data voor MEERDERE gebieden en bereken gemiddelden.
         * Fetcht per gebied parallel, merget de hiërarchie-trees door waarden te middelen.
         * Behoudt expanded indicator state als het detailpaneel open is.
         */
        if (!gebiedIds || gebiedIds.length === 0) return;

        // Single area: delegate to existing method
        if (gebiedIds.length === 1) {
            return this.loadGebiedData(configId, gebiedIds[0]);
        }

        // Sprint 7 / #444 / #463: Bewaar expanded state EN indicator UUID vóór re-render
        const wasExpanded = this.isExpanded;
        const expandedIndicatorUuid = this._lastExpandedIndicatorUuid
            || (wasExpanded && this.currentNode?.data?.uuid ? this.currentNode.data.uuid : null);
        const zoomPath = this._getZoomPath();
        const reqId = ++this._loadRequestId;

        this.showLoading();
        console.log(`📊 Multi-gebied Kompas: ${gebiedIds.length} gebieden laden...`);
        if (zoomPath.length > 0) {
            console.log(`🔄 Bewaar zoom-pad: ${zoomPath.join(' > ')}`);
        }

        try {
            // Fetch all areas in parallel
            const promises = gebiedIds.map(id =>
                fetch(`/api/kompas/${configId}/gebied/${id}`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status} for ${id}`);
                    return r.json();
                })
            );
            const results = await Promise.all(promises);
            if (reqId !== this._loadRequestId) {
                console.log('🔄 Verouderde multi-gebied data genegeerd (#463)');
                this.hideLoading();
                return;
            }

            // Use the first result as a template
            const merged = JSON.parse(JSON.stringify(results[0]));

            // Recursively average the hierarchie values
            this._mergeHierarchies(merged.hierarchie, results.map(r => r.hierarchie));

            // #255/#256: bij percentielklassen en labels de klassen over de hele selectie uit de backend
            let selectie = null;
            if (['percentiel_8', 'label_ae'].includes(results[0].classificatie)) {
                const qs = gebiedIds.map(id => `gebied_id=${encodeURIComponent(id)}`).join('&');
                const sel = await fetch(`/api/kompas/${configId}/selectie?${qs}`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status} selectie`);
                    return r.json();
                });
                if (reqId !== this._loadRequestId) {
                    console.log('🔄 Verouderde selectie data genegeerd (#463)');
                    this.hideLoading();
                    return;
                }
                this._neemKlassenOver(merged.hierarchie, sel.hierarchie);
                selectie = sel;
            }

            // Build area names list
            const namen = results.map(r => r.gebied_naam);
            const namenTekst = namen.length <= 3
                ? namen.join(', ')
                : `${namen.slice(0, 2).join(', ')} (+${namen.length - 2})`;

            // Calculate average coverage
            const avgCoverage = Math.round(
                results.reduce((sum, r) => sum + (r.coverage_percentage || 0), 0) / results.length
            );

            // Store merged data
            merged.gebied_naam = `Selectie: ${gebiedIds.length} gebieden`;
            merged.coverage_percentage = avgCoverage;
            merged._multiGebiedNamen = namen;
            merged._multiGebiedIds = gebiedIds;

            this.currentData = merged;
            this.currentConfigId = configId;
            this.currentGebiedId = gebiedIds[0]; // Primary for history lookups

            // Update UI
            document.getElementById('kompas-info').innerHTML =
                `<p class="help-text"><strong><img src="/static/images/chart-bar.svg" alt="" style="width:16px; height:16px; vertical-align: -2px; filter: brightness(0) invert(1); margin-right: 4px;">${escapeHtml(namenTekst)}</strong><br>` +
                `Gemiddelde van ${gebiedIds.length} gebieden<br>` +
                `Indicatordekking: ${escapeHtml(avgCoverage)}%` +
                (results[0].classificatie === 'percentiel_8'
                    ? '<br><span class="kompas-classificatie">Kleur: percentielklasse over de selectie (8 × 12,5%)</span>' : '') +
                `</p>` + this._labelLegenda(selectie || results[0], true);

            // Bepaal actuele toestand (ook als gebruiker tijdens de fetch doorklikte, #463)
            const currentZoomPath = (this.currentNode === this.root)
                ? []
                : (this._getZoomPath().length > 0 ? this._getZoomPath() : zoomPath);
            const activeIndicatorUuid = this.isExpanded
                ? (this._currentIndicatorUuid || this._lastExpandedIndicatorUuid || (this.currentNode?.data?.uuid ? this.currentNode.data.uuid : null))
                : null;

            // Render sunburst with merged data (of stel uit tot landing camera, #465/#466)
            const doRender = () => {
                this.renderSunburst(merged.hierarchie);
                this.updateSelectedAreasBadges();

                // Sprint 7 / #444 / #463: Herstel zoom-pad en actieve indicator direct zonder race condition
                if (currentZoomPath.length > 0) {
                    this._navigateToPath(currentZoomPath);
                }
                if (activeIndicatorUuid && this.root) {
                    const targetNode = this._findNodeByUuid(this.root, activeIndicatorUuid);
                    if (targetNode) {
                        this.expandDetails(targetNode);
                    }
                }
            };

            if (this.deferNextRenderUntilLanding) {
                this._pendingRender = () => {
                    doRender();
                    this.hideLoading();
                };
            } else {
                doRender();
                this.hideLoading();
            }

            console.log(`✅ Multi-gebied Kompas geladen: ${gebiedIds.length} gebieden gemiddeld`);
            return merged;
        } catch (error) {
            if (reqId !== this._loadRequestId) return;
            console.error('❌ Fout bij multi-gebied kompas:', error);
            this.showError('Kon multi-gebied data niet laden');
            this.hideLoading();
        }
    }

    _findNodeByUuid(node, uuid) {
        /**
         * Sprint 7: Recursief zoeken naar een node met specifiek UUID in de D3 hiërarchie.
         */
        if (node.data?.uuid === uuid) return node;
        if (node.children) {
            for (const child of node.children) {
                const found = this._findNodeByUuid(child, uuid);
                if (found) return found;
            }
        }
        return null;
    }

    _getZoomPath() {
        /**
         * Sprint 7: Geeft het pad van node-namen terug van root naar het huidige zoom-niveau.
         * Bijv. ["Kwaliteit fysieke leefomgeving", "Verkeer"]
         * Als currentNode een leaf (indicator) is, gebruik dan de ouder als zoom-target,
         * zodat het pad alleen de intermediate niveaus bevat.
         */
        if (!this.currentNode || this.currentNode === this.root) return [];

        // Als current node een leaf is (geen children), gebruik parent voor zoom-pad
        let node = this.currentNode;
        if (!node.children && node.parent) {
            node = node.parent;
        }

        if (!node || node === this.root) return [];

        const path = [];
        while (node && node.parent) {
            path.unshift(node.data.name);
            node = node.parent;
        }
        return path;
    }

    _navigateToPath(path) {
        /**
         * Sprint 7: Navigeer de sunburst naar het opgegeven pad door
         * programmatisch de zoom-functie aan te roepen.
         */
        if (!this.root || !this._zoomFn || path.length === 0) return;

        let currentNode = this.root;
        for (const name of path) {
            if (!currentNode.children) break;
            const child = currentNode.children.find(c => c.data.name === name);
            if (!child) {
                console.warn(`⚠️ Zoom-pad node "${name}" niet gevonden`);
                break;
            }
            currentNode = child;
        }

        if (currentNode !== this.root) {
            console.log(`🔍 Zoom hersteld naar: ${currentNode.data.name}`);
            this._zoomFn(null, currentNode);
        }
    }

    _labelLegenda(data, selectie = false) {
        /**
         * #256: bij classificatie label_ae de labels A-E met kleur, en zolang er geen
         * vastgestelde drempels zijn de melding 'voorlopige drempels (kwintielen)'.
         */
        if (!data || data.classificatie !== 'label_ae') return '';
        const items = (data.klassen_legenda || []).map(k =>
            `<li data-label="${escapeHtml(k.label)}"><span class="legenda-klasse-kleur" style="background:${escapeHtml(k.kleur)}"></span>`
            + `<span>${escapeHtml(k.omschrijving || k.label)}</span></li>`).join('');
        return `<p class="help-text kompas-classificatie">Kleur: label A–E${selectie ? ' over de selectie' : ''}</p>`
            + `<ul class="legenda-klassen kompas-labels" aria-label="Labels">${items}</ul>`
            + (data.label_melding
                ? `<p class="help-text kompas-label-melding" role="note">${escapeHtml(data.label_melding)}</p>` : '');
    }

    _neemKlassenOver(target, bron) {
        /**
         * #255: klasse, klasse_kleur en klasse_status van de selectie overnemen
         * (zelfde profiel, dus dezelfde boom in dezelfde volgorde).
         */
        if (!target || !bron) return;
        target.klasse = bron.klasse ?? null;
        target.klasse_kleur = bron.klasse_kleur ?? null;
        target.klasse_status = bron.klasse_status ?? null;
        target.label = bron.label ?? null;            // #256
        target.label_bron = bron.label_bron ?? null;
        if (target.type === 'indicator' && bron.color) target.color = bron.color;
        (target.children || []).forEach((kind, i) => this._neemKlassenOver(kind, bron.children?.[i]));
    }

    _mergeHierarchies(target, sources) {
        /**
         * Recursief samenvoegen van hiërarchie-trees door waarden te middelen.
         * Null-waarden worden overgeslagen (delen door werkelijk aantal).
         */
        // Collect values from all sources for this node
        const values = sources
            .map(s => s?.value)
            .filter(v => v !== null && v !== undefined && typeof v === 'number');

        if (values.length > 0) {
            target.value = values.reduce((sum, v) => sum + v, 0) / values.length;
        } else {
            target.value = null;
        }

        // Recalculate color based on averaged score (if score_type exists)
        if (target.score !== undefined) {
            const scores = sources
                .map(s => s?.score)
                .filter(v => v !== null && v !== undefined && typeof v === 'number');
            if (scores.length > 0) {
                target.score = scores.reduce((sum, v) => sum + v, 0) / scores.length;
                // Re-derive color from averaged score using same 0-100 blue-red scale
                target.color = this._scoreToColor(target.score);
            }
        }

        // Recurse into children
        if (target.children && target.children.length > 0) {
            target.children.forEach((child, i) => {
                const childSources = sources.map(s => s?.children?.[i]).filter(Boolean);
                if (childSources.length > 0) {
                    this._mergeHierarchies(child, childSources);
                }
            });
        }
    }

    _scoreToColor(score) {
        /**
         * Convert a 0-100 score to a hex color on the blue→red scale.
         * 0 = Red (#e53e3e), 50 = Yellow (#ecc94b), 100 = Blue (#3182ce)
         */
        const s = Math.max(0, Math.min(100, score));
        let r, g, b;

        if (s <= 50) {
            // Red → Yellow (0-50)
            const t = s / 50;
            r = Math.round(229 + (236 - 229) * t);
            g = Math.round(62 + (201 - 62) * t);
            b = Math.round(62 + (75 - 62) * t);
        } else {
            // Yellow → Blue (50-100)
            const t = (s - 50) / 50;
            r = Math.round(236 + (49 - 236) * t);
            g = Math.round(201 + (130 - 201) * t);
            b = Math.round(75 + (206 - 75) * t);
        }

        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    renderSunburst(hierarchie) {
        /**
         * Render D3.js sunburst diagram
         * Following exact D3 Observable zoomable sunburst pattern
         */
        if (!hierarchie) {
            console.warn('⚠️ Geen hiërarchie data om te renderen');
            return;
        }

        // Clear existing
        this.g.selectAll('*').remove();
        this.currentNode = null;

        // Create hierarchy and compute layout
        // Create hierarchy
        const root = d3.hierarchy(hierarchie);

        // 1. Force Equal Sizing Logic (override count/sum based sizing)
        // Root = 4. Each quadrant = 1. Children split parent value equally.
        this.assignEqualValues(root, 4);

        // 2. Custom Sort for Quadrants (User defined order)
        // Top: Fysieke leefomgeving
        // Right: Sociale leefomgeving
        // Bottom: Samenstelling
        // Left: Kwaliteit van leven
        root.sort((a, b) => this.kompasSort(a, b));

        const partition = d3.partition()
            .size([2 * Math.PI, root.height + 1]);

        partition(root);

        // CRITICAL: Store current state on each node (d.current pattern)
        root.each(d => d.current = d);

        // Store root for zoom operations
        this.root = root;

        // Arc generator using d.current with direct radius multiplication
        // Apply -45 degree rotation offset in start/end angles if needed, 
        // OR rotate the entire group. Moving rotation to <g> transform is cleaner.
        const radius = this.radius;
        const arc = d3.arc()
            .startAngle(d => d.x0)
            .endAngle(d => d.x1)
            .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
            .padRadius(radius * 1.5)
            .innerRadius(d => d.y0 * radius)
            .outerRadius(d => Math.max(d.y0 * radius, d.y1 * radius - 1));

        // Use arc centroid for horizontal positioning
        // We need to pass this into labelTransform
        this.arc = arc;

        // ROTATION: Now handled by static this.rotateG in init()
        // Reset scale group to default
        this.g.attr('transform', 'scale(1)');

        // Parent circle for zoom out (click center hole to go back, sits behind arcs)
        const parent = this.g.append('circle')
            .datum(root)
            .attr('r', radius)
            .attr('fill', 'none')
            .attr('pointer-events', 'all')
            .style('cursor', 'pointer');

        // Draw arcs using d.current
        const path = this.g.append('g')
            .selectAll('path')
            .data(root.descendants().slice(1))
            .join('path')
            .attr('class', 'kompas-arc-path')
            .attr('fill', d => this.getNodeColor(d))
            // Removed fading: opacity 1.0 for all visible arcs to fix "washed out" colors
            .attr('fill-opacity', d => this.arcVisible(d.current) ? 1.0 : 0)
            .attr('pointer-events', d => this.arcVisible(d.current) ? 'auto' : 'none')
            .attr('d', d => arc(d.current));

        // Make clickable
        path.filter(d => d.children)
            .style('cursor', 'pointer');

        // Add labels using d.current
        const label = this.g.append('g')
            .attr('pointer-events', 'none')
            .attr('text-anchor', 'middle')
            .style('user-select', 'none')
            .selectAll('text')
            .data(root.descendants().slice(1))
            .join('text')
            .attr('dy', '0.35em')
            .attr('fill-opacity', d => +this.labelVisible(d.current))
            .attr('transform', d => this.labelTransform(d.current, radius))
            .style('fill', 'var(--text-primary)')
            .style('font-size', '10px')
            .style('font-weight', '500')
            .text(d => d.data.name)
            .call((text) => this.wrapText(text, radius)); // Apply wrapping
        // Center visual circle
        this.g.append('circle')
            .attr('r', radius * 0.2)
            .style('fill', 'var(--tint-subtle)')
            .style('stroke', 'var(--panel-border)')
            .attr('stroke-width', 2)
            .attr('pointer-events', 'none');

        // Center Text Label (Initially Empty - used for "Sluiten" button)
        this.g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('class', 'kompas-center-label')
            .style('fill', 'var(--text-primary)')
            .style('font-weight', '600')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .text(''); // Empty by default per user request

        const self = this;

        // Click handler following D3 Observable pattern
        function clicked(event, p) {
            // Check if we are clicking the center (parent) while expanded
            if (self.isExpanded && p === (parent.datum() || root)) {
                // Clicking center when expanded -> Close details
                self.collapseDetails();
                return;
            }

            // Update parent datum for zoom out
            parent.datum(p.parent || root);
            self.currentNode = p;

            // Leaf node - EXPAND Window behavior
            if (!p.children && p.data.uuid) {
                // Sync to map immediately (Interactive Legend)
                self.syncIndicatorToMap(p.data.uuid, p.data.name);

                // Update breadcrumb om de volledige keten tot de indicator te tonen
                self.updateBreadcrumb(p);

                // Expand window and show details panel
                self.expandDetails(p);

                // Verberg hover-tooltip zodat deze niet blijft hangen
                self.handleMouseOut();
                return;
            } else {
                // Collapse details when navigating out
                self.collapseDetails();
            }

            console.log('🔍 Zooming to:', p.data.name);

            // ZOOM SCALING: Calculate scale factor to fill screen
            // Total height (levels) = root.height + 1
            // Current remaining levels = p.height + 1
            // Scale = Total / Remaining
            const maxLayers = root.height + 1;
            const remainingLayers = p.height + 1;
            // Clamp scale to minimal 1 (no shrinking)
            const k = Math.max(1, maxLayers / remainingLayers);

            // Calculate target positions for all nodes
            // Apply scale factor k directly to Y geometry to fill screen
            root.each(d => d.target = {
                x0: Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
                x1: Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
                y0: Math.max(0, d.y0 - p.depth) * k,
                y1: Math.max(0, d.y1 - p.depth) * k
            });

            // Minder beweging (prefers-reduced-motion): direct naar de eindstand (#67)
            const duur = window.A11y ? window.A11y.motionDuration(750) : 750;
            const t = self.g.transition().duration(duur);

            // REFACTOR: CSS Scale removed. Geometry handles scaling now.
            // Reset transforms just in case
            // self.g.transition(t).attr('transform', 'scale(1)'); 

            // Transition arcs (fill-opacity permanent 1.0 voor zichtbare segmenten conform #450)
            path.transition(t)
                .tween('data', d => {
                    const i = d3.interpolate(d.current, d.target);
                    return t => d.current = i(t);
                })
                .filter(function (d) {
                    return +this.getAttribute('fill-opacity') || self.arcVisible(d.target);
                })
                .attr('fill-opacity', d => self.arcVisible(d.target) ? 1.0 : 0)
                .attr('pointer-events', d => self.arcVisible(d.target) ? 'auto' : 'none')
                .attrTween('d', d => () => arc(d.current));

            // Transition labels
            label.filter(function (d) {
                return +this.getAttribute('fill-opacity') || self.labelVisible(d.target);
            }).transition(t)

                .attr('fill-opacity', d => +self.labelVisible(d.target))
                .attrTween('transform', d => () => self.labelTransform(d.current, radius))
                .style('font-size', '10px') // Keep text readable at all zoom levels
                .on("end", function (d) {
                    // Re-wrap text after transition since alignment might change size availability? 
                    // Actually wrapping is static text content, but we might want to ensure it stays wrapped.
                    // For now, keep wrapping static.
                });

            // Transition Center Label (keep readable but not huge)
            self.g.select('.kompas-center-label')
                .transition(t)
                .style('font-size', self.isExpanded ? '14px' : '12px'); // Keep center label readable

            // Update breadcrumb
            self.updateBreadcrumb(p);
        }

        // Attach click handlers
        path.on('click', clicked);
        parent.on('click', clicked);

        // Sprint 7: Store clicked function for programmatic zoom restore
        this._zoomFn = clicked;
        this._pathSelection = path;
        this._labelSelection = label;
        this._parentSelection = parent;

        // Hover effects: behoud volle kleurdekking (1.0), visuele feedback via stroke in CSS (#450)
        path.on('mouseover', function (event, d) {
            self.handleMouseOver(event, d);
        })
            .on('mousemove', function (event) {
                self._positionTooltip(event);
            })
            .on('mouseout', function (event, d) {
                self.handleMouseOut();
            });

        console.log('✅ Sunburst rendered:', root.descendants().length, 'nodes');

        // Initialize default breadcrumb state on load
        this.updateBreadcrumb(root); // Initialize with Root (will trigger "Start" text logic)
    }

    arcVisible(d) {
        // Show all layers for arcs (visual blocks)
        return d.y1 <= 5 && d.y0 >= 1 && d.x1 > d.x0;
    }

    labelVisible(d) {
        // Visibility Logic:
        // 1. Must be within generic bounds
        // 2. Must have enough area ( > 0.03 radiants)
        // 3. User Requirement: "Max 2 niveau's tekst presenteren"
        //    Relative to current zoom, this means y0 (start radius) must be < 3.
        //    y0=1 (Ring 1), y0=2 (Ring 2). y0=3 (Ring 3) should be hidden.
        return d.y1 <= 5 && d.y0 >= 1 && (d.y1 - d.y0) * (d.x1 - d.x0) > 0.03 && d.y0 < 3;
    }

    labelTransform(d, radius) {
        // Horizontal Alignment Logic
        if (!this.arc) return '';

        const [x, y] = this.arc.centroid(d);

        // Return pure translation to centroid + rotation correcection.
        // The main group is rotated -45 degrees.
        // To make text horizontal (0 degrees on screen), we must rotate +45.
        return `translate(${x},${y}) rotate(45)`;
    }

    wrapText(textSelection, radius) {
        /**
         * Wraps text to max 3 lines.
         * Adds '...' if truncated.
         * Woordomloop via canvas.measureText i.p.v. getComputedTextLength (#465/#466)
         * Voorkomt synchrone DOM forced reflows (layout thrashing) bij elk woord.
         */
        const ctx = getMeasureCanvasCtx();
        textSelection.each(function (d) {
            const text = d3.select(this);
            // Heuristic for width: Use arc length at mid-radius, clamped.
            const midRadius = (d.current.y0 + d.current.y1) / 2 * radius;
            const angle = d.current.x1 - d.current.x0;
            const arcLength = angle * midRadius;

            // Width constraint: 
            // For large angles (>90deg), use radius.
            // For small angles, restrict width to avoid overlapping too much neighbors.
            const width = Math.min(radius * 0.9, Math.max(40, arcLength * 0.8));

            // #256: bij label_ae het label voor de naam ('B · Hittestress')
            const naam = d.data.label ? `${d.data.label} · ${d.data.name}` : d.data.name;
            const words = naam.split(/\s+/).reverse();
            let word;
            let line = [];
            let lineNumber = 0;
            const lineHeight = 1.1; // ems
            const dy = parseFloat(text.attr("dy") || 0);

            const lines = [];
            while ((word = words.pop())) {
                line.push(word);
                const testLine = line.join(" ");
                const textWidth = ctx ? ctx.measureText(testLine).width : (testLine.length * 6);
                if (textWidth > width) {
                    line.pop();
                    lines.push(line.join(" "));
                    line = [word];
                    lineNumber++;

                    // Max 3 lines constraint
                    if (lineNumber >= 2) {
                        line = [word + "..."];
                        break;
                    }
                }
            }
            if (line.length > 0) {
                lines.push(line.join(" "));
            }

            text.text(null);
            const totalLines = Math.max(1, lines.length);
            const shift = -((totalLines - 1) * lineHeight) / 2;

            lines.forEach((lText, idx) => {
                text.append("tspan")
                    .attr("x", 0)
                    .attr("y", shift + "em")
                    .attr("dy", (idx * lineHeight + dy) + "em")
                    .text(lText);
            });
        });
    }

    getNodeColor(d) {
        /**
         * Get color for node
         * Priority:
         * 1. Leaf nodes (indicators): use backend color
         * 2. Parent nodes: aggregate from children
         * 3. Fallback: gray
         */
        // #255: percentielklasse (profiel percentiel_8): de backend kleurt elke node,
        // ook onderdeel, thema en kwadrant (gewogen klasse-aggregatie)
        if (d.data.klasse_kleur) {
            return d.data.klasse_kleur;
        }

        // Leaf node with data color from backend
        if (!d.children && d.data.color) {
            return d.data.color;
        }

        // Parent node: aggregate children colors
        if (d.children && d.children.length > 0) {
            return this.aggregateChildrenColor(d.children);
        }

        // Fallback: gray for no data
        return '#94A3B8';
    }

    aggregateChildrenColor(children) {
        /**
         * Calculate average color from children (weighted by presence)
         * Ignores gray (#94A3B8) children (no data)
         */
        const validChildren = children.filter(c => {
            const color = this.getChildColor(c);
            return color && color !== '#94A3B8';
        });

        if (validChildren.length === 0) {
            return '#94A3B8'; // All children no-data
        }

        // Average the RGB values
        let avgR = 0, avgG = 0, avgB = 0;
        validChildren.forEach(child => {
            const color = this.getChildColor(child);
            const rgb = this.hexToRgb(color);
            avgR += rgb.r;
            avgG += rgb.g;
            avgB += rgb.b;
        });

        avgR = Math.round(avgR / validChildren.length);
        avgG = Math.round(avgG / validChildren.length);
        avgB = Math.round(avgB / validChildren.length);

        return this.rgbToHex(avgR, avgG, avgB);
    }

    getChildColor(child) {
        /**
         * Get color from a child node (recursive)
         */
        if (child.data && child.data.color) {
            return child.data.color;
        }
        if (child.children && child.children.length > 0) {
            return this.aggregateChildrenColor(child.children);
        }
        return '#94A3B8';
    }

    hexToRgb(color) {
        /**
         * Convert HEX or RGB color to RGB object
         */
        if (!color) return { r: 148, g: 163, b: 184 };
        if (typeof color === 'string' && color.startsWith('rgb')) {
            const m = color.match(/\d+/g);
            if (m && m.length >= 3) {
                return { r: parseInt(m[0], 10), g: parseInt(m[1], 10), b: parseInt(m[2], 10) };
            }
        }
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(color);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 148, g: 163, b: 184 }; // gray fallback
    }

    rgbToHex(r, g, b) {
        /**
         * Convert RGB to HEX color
         */
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    _positionTooltip(event) {
        if (!event) return;
        const tooltipEl = this.tooltip.node();
        const tooltipWidth = tooltipEl ? (tooltipEl.offsetWidth || 250) : 250;
        const tooltipHeight = tooltipEl ? (tooltipEl.offsetHeight || 80) : 80;
        const padding = 14;

        let left = event.pageX + padding;
        // Als de tooltip voorbij de rechter schermrand valt (bijv. in het gedockte rechterpaneel):
        // val naar links van de cursor zodat het detailpaneel volledig zichtbaar blijft
        if (event.clientX + tooltipWidth + padding > window.innerWidth) {
            left = event.pageX - tooltipWidth - padding;
        }
        if (left < padding) {
            left = padding;
        }

        let top = event.pageY - 10;
        // Als de tooltip onderaan buiten beeld dreigt te vallen: schuif omhoog
        if (event.clientY + tooltipHeight + padding > window.innerHeight) {
            top = event.pageY - tooltipHeight + 10;
        }
        if (top < padding) {
            top = padding;
        }

        this.tooltip
            .style('left', left + 'px')
            .style('top', top + 'px');
    }

    handleMouseOver(event, d) {
        /**
         * Show tooltip on hover
         */
        let html = `<strong>${escapeHtml(d.data.name)}</strong>`;

        // Show value or "Geen data" text
        if (d.data.value !== null && d.data.value !== undefined) {
            html += `<div class="tooltip-value">${d.data.value.toFixed(2)}`;
            if (d.data.eenheid) {
                html += ` ${escapeHtml(d.data.eenheid)}`;
            }
            html += `</div>`;
        } else if (d.data.type === 'indicator') {
            // Indicator zonder data
            html += `<div class="tooltip-value" style="opacity: 0.6">Geen data</div>`;
        }

        // #256: label A-E (classificatie label_ae)
        if (d.data.label) {
            const voorlopig = d.data.type === 'indicator' ? d.data.label_bron !== 'drempels'
                : !!this.currentData?.label_melding;
            html += `<div class="tooltip-value">Label ${escapeHtml(d.data.label)}${voorlopig ? ' (voorlopig, kwintielen)' : ''}</div>`;
        }

        // Build path
        const path = [];
        let node = d;
        while (node.parent) {
            path.unshift(node.data.name);
            node = node.parent;
        }
        if (path.length > 1) {
            html += `<div class="tooltip-path">${escapeHtml(path.join(' › '))}</div>`;
        }

        this.tooltip
            .html(html)
            .style('visibility', 'visible');
        this._positionTooltip(event);
    }

    handleMouseOut() {
        this.tooltip.style('visibility', 'hidden');
    }

    updateBreadcrumb(node) {
        /**
         * Update breadcrumb trail (FE-2.2: Doorklikbaar kruimelpad)
         */
        const breadcrumb = document.getElementById('kompas-breadcrumb');
        if (!breadcrumb) return;

        breadcrumb.style.minHeight = '24px';
        breadcrumb.style.display = 'flex';
        breadcrumb.style.alignItems = 'center';
        breadcrumb.style.flexWrap = 'wrap';
        breadcrumb.style.visibility = 'visible';

        const path = [];
        let current = node;
        while (current && current.parent) {
            path.unshift({ name: current.data.name, node: current });
            current = current.parent;
        }

        if (path.length > 0) {
            breadcrumb.replaceChildren();

            const rootBtn = document.createElement('button');
            rootBtn.type = 'button';
            rootBtn.className = 'breadcrumb-item breadcrumb-root';
            rootBtn.textContent = 'Kompas';
            rootBtn.title = 'Terug naar startoverzicht';
            rootBtn.setAttribute('aria-label', 'Navigeer naar Kompas start');
            rootBtn.addEventListener('click', () => {
                this.collapseDetails();
                this.reset();
            });
            breadcrumb.appendChild(rootBtn);

            const sep0 = document.createElement('span');
            sep0.className = 'breadcrumb-separator';
            sep0.textContent = '›';
            breadcrumb.appendChild(sep0);

            path.forEach((item, idx) => {
                if (idx < path.length - 1) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'breadcrumb-item';
                    btn.textContent = item.name;
                    btn.title = `Navigeer naar ${item.name}`;
                    btn.setAttribute('aria-label', `Navigeer naar ${item.name}`);
                    btn.addEventListener('click', () => {
                        this.collapseDetails();
                        if (this._zoomFn) {
                            this._zoomFn(null, item.node);
                        }
                    });
                    breadcrumb.appendChild(btn);

                    const sep = document.createElement('span');
                    sep.className = 'breadcrumb-separator';
                    sep.textContent = '›';
                    breadcrumb.appendChild(sep);
                } else {
                    const span = document.createElement('span');
                    span.className = 'breadcrumb-current';
                    span.textContent = item.name;
                    span.title = `Geselecteerde indicator: ${item.name}`;
                    breadcrumb.appendChild(span);
                }
            });
        } else {
            breadcrumb.innerHTML = `<span style="opacity: 0.6; font-style: italic;">Start: Selecteer een onderdeel</span>`;
        }
    }

    zoomOut() {
        /**
         * Stap één niveau omhoog in de thema-hiërarchie
         */
        this.collapseDetails();
        if (this.currentNode && this.currentNode.parent && this._zoomFn) {
            const target = (!this.currentNode.children && this.currentNode.parent.parent)
                ? this.currentNode.parent.parent
                : (this.currentNode.parent || this.root);
            this._zoomFn(null, target);
        } else if (this._zoomFn && this.root) {
            this._zoomFn(null, this.root);
        } else if (this.currentData && this.currentData.hierarchie) {
            this.renderSunburst(this.currentData.hierarchie);
        }
    }

    reset() {
        /**
         * Reset kompas naar het beginniveau (root)
         */
        this._loadRequestId++;
        this.deferNextRenderUntilLanding = false;
        this._pendingRender = null;
        this._lastExpandedIndicatorUuid = null;
        this._currentIndicatorUuid = null;
        this.hideLoading();
        this.collapseDetails();
        this.currentNode = this.root;
        if (this.root) {
            this.updateBreadcrumb(this.root);
        }
        if (this._zoomFn && this.root) {
            this._zoomFn(null, this.root);
        } else if (this.currentData && this.currentData.hierarchie) {
            this.renderSunburst(this.currentData.hierarchie);
        }
    }

    syncIndicatorToMap(indicatorUuid, indicatorName) {
        /**
         * Trigger map update when clicking indicator in kompas
         * Uses EventBus for decoupled communication
         */
        console.log('🔗 Sync indicator to map:', indicatorName, indicatorUuid);

        if (window.EventBus) {
            // Set guard to prevent the Kompas from re-processing its own event
            this._isSyncing = true;
            window.EventBus.emit('INDICATOR_SELECTED', {
                uuid: indicatorUuid,
                name: indicatorName
            });
            console.log('✅ Event dispatched via EventBus: INDICATOR_SELECTED');
            // Reset guard after event propagation completes
            setTimeout(() => { this._isSyncing = false; }, 100);
        } else {
            console.error('❌ EventBus not available!');
        }
    }

    showLoading() {
        this.container.classList.add('loading');
    }

    hideLoading() {
        this.container.classList.remove('loading');
    }

    assignEqualValues(node, value) {
        /**
         * Recursively assign values to ensure equal sizing.
         * The partition layout uses node.value to determine sector size.
         * By splitting the parent's value equally among children, we ensure equal visual distribution
         * regardless of how many descendants a child has.
         */
        node.value = value;

        if (node.children && node.children.length > 0) {
            const childValue = value / node.children.length;
            node.children.forEach(child => this.assignEqualValues(child, childValue));
        }
    }

    kompasSort(a, b) {
        /**
         * Custom sort logic for Kompas Quadrants
         * Order: Top -> Right -> Bottom -> Left
         * Rotation -45deg will align:
         * 1. 0-90 (Top)
         * 2. 90-180 (Right)
         * 3. 180-270 (Bottom)
         * 4. 270-360 (Left)
         */

        // Define fixed order for root children (Titles)
        const quadrantOrder = {
            "Kwaliteit fysieke leefomgeving": 1, // Top
            "Kwaliteit sociale leefomgeving": 2, // Right
            "Samenstelling": 3,                  // Bottom
            "Kwaliteit van leven": 4             // Left
        };

        if (a.depth === 1 && b.depth === 1) {
            const orderA = quadrantOrder[a.data.name] || 99;
            const orderB = quadrantOrder[b.data.name] || 99;
            return orderA - orderB;
        }

        // For deeper levels, sort alphabetically to stay consistent
        return a.data.name.localeCompare(b.data.name);
    }

    async fetchHistory(gebiedId, indicatorUuid) {
        try {
            const configId = this.currentConfigId || 1;
            console.log(`fetching history for ${gebiedId}, indicator ${indicatorUuid}`);
            const response = await fetch(`/api/kompas/${configId}/history/${gebiedId}/${indicatorUuid}`);
            if (!response.ok) {
                console.warn('History fetch failed:', response.status);
                return null;
            }
            const data = await response.json();
            console.log('History data received:', data);
            return data;
        } catch (error) {
            console.error('Error fetching history:', error);
            return null;
        }
    }

    async showActionOverlay(d) {
        /**
         * Show action buttons and history chart when a leaf node (indicator) is selected
         */
        d3.select(this.container).selectAll('.kompas-action-overlay').remove();

        if (!d.data.uuid) return;

        const overlay = d3.select(this.container).append('div')
            .attr('class', 'kompas-action-overlay')
            .style('position', 'absolute')
            .style('top', '50%')
            .style('left', '50%')
            .style('transform', 'translate(-50%, -50%)')
            .style('text-align', 'center')
            .style('pointer-events', 'auto')
            .style('z-index', '10')
            .style('background', 'color-mix(in srgb, var(--tooltip-bg) 95%, transparent)')
            .style('color', 'var(--tooltip-text)')
            .style('backdrop-filter', 'blur(8px)')
            .style('padding', '20px')
            .style('border-radius', '16px')
            .style('border', '1px solid color-mix(in srgb, var(--tooltip-text) 12%, transparent)')
            .style('box-shadow', '0 10px 25px -5px rgba(0, 0, 0, 0.5)')
            .style('min-width', '320px');

        // Content Header
        let html = `
            <div class="kompas-selected-indicator" style="position: relative;">
                <button class="btn-kompas-close" id="btn-kompas-close" title="Sluiten" aria-label="Sluiten" style="position: absolute; top: -10px; right: -10px; background: none; border: none; color: inherit; cursor: pointer;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
                <h4 style="margin: 0 0 10px; color: inherit; font-size: 1.1rem;">${escapeHtml(d.data.name)}</h4>
        `;

        if (d.data.value !== null) {
            const eenheidText = d.data.eenheid ? ` ${escapeHtml(d.data.eenheid)}` : '';
            const swatch = d.data.color ? `<span aria-hidden="true" style="width: 14px; height: 14px; border-radius: 3px; margin-right: 8px; background: ${escapeHtml(d.data.color)};"></span>` : '';
            html += `<div class="value" style="font-size: 1.5rem; font-weight: 700; color: inherit; margin-bottom: 15px; display:flex; align-items:center; justify-content:center;">${swatch}${d.data.value.toFixed(2)} <span style="font-size: 0.8em; font-weight: 400; opacity: 0.8; margin-left:4px;">${eenheidText}</span></div>`;
        } else {
            html += `<div class="value no-data" style="color: inherit; opacity: 0.75; margin-bottom: 15px;">Geen recente data</div>`;
        }

        // Placeholder for Chart
        html += `<div id="kompas-history-chart" style="width: 100%; height: 120px; margin-bottom: 15px;"></div>`;

        html += `
                <div class="actions" style="display: flex; gap: 10px; justify-content: center;">
                    <button class="btn-kompas-action" id="btn-toon-kaart" style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: color-mix(in srgb, var(--tooltip-text) 10%, transparent); border: 1px solid color-mix(in srgb, var(--tooltip-text) 25%, transparent); border-radius: var(--border-radius-sm); color: inherit; cursor: pointer; transition: all 0.2s;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
                        Toon op kaart
                    </button>
                </div>
            </div>
        `;

        overlay.html(html);

        // Fetch and Render Chart
        if (this.currentGebiedId) {
            const historyData = await this.fetchHistory(this.currentGebiedId, d.data.uuid);
            if (historyData && historyData.history && historyData.history.length > 1) {
                this.renderHistoryChart(historyData.history);
            } else {
                d3.select('#kompas-history-chart').html('<p style="font-size: 0.8rem; opacity: 0.75; padding-top: 40px;">Onvoldoende data voor trend</p>');
            }
        }

        // Attach event listeners
        document.getElementById('btn-toon-kaart').addEventListener('click', (e) => {
            e.stopPropagation();
            this.syncIndicatorToMap(d.data.uuid, d.data.name);
            // Keep overlay open or close? Usually keep open or user decides.
        });

        document.getElementById('btn-kompas-close').addEventListener('click', (e) => {
            e.stopPropagation();
            d3.select(this.container).selectAll('.kompas-action-overlay').remove();
            if (d.parent) this.zoomOut();
        });
    }

    renderHistoryChart(history) {
        const container = d3.select('#kompas-history-chart');
        const width = 280;
        const height = 120;
        const margin = { top: 10, right: 10, bottom: 20, left: 30 };

        const svg = container.append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`);

        // Scales
        const x = d3.scaleLinear()
            .domain(d3.extent(history, d => d.jaar))
            .range([margin.left, width - margin.right]);

        // Y domain: include 0 if positive, or just extent with padding
        const yExtent = d3.extent(history, d => d.waarde);
        const yPadding = (yExtent[1] - yExtent[0]) * 0.1 || 1;
        const y = d3.scaleLinear()
            .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
            .range([height - margin.bottom, margin.top]);

        // Line
        const line = d3.line()
            .x(d => x(d.jaar))
            .y(d => y(d.waarde))
            .curve(d3.curveMonotoneX);

        // Grid
        // svg.append("g")
        //     .attr("transform", `translate(0,${height - margin.bottom})`)
        //     .call(d3.axisBottom(x).ticks(history.length).tickFormat(d3.format("d")).tickSizeInner(-(height - margin.top - margin.bottom)).tickSizeOuter(0))
        //     .call(g => g.select(".domain").remove())
        //     .call(g => g.selectAll(".tick line").attr("stroke-opacity", 0.1));

        // Path
        svg.append("path")
            .datum(history)
            .attr("fill", "none")
            .attr("stroke", "#22C55E")
            .attr("stroke-width", 2)
            .attr("d", line);

        // Dots
        svg.selectAll("circle")
            .data(history)
            .join("circle")
            .attr("cx", d => x(d.jaar))
            .attr("cy", d => y(d.waarde))
            .attr("r", 3)
            .attr("fill", "#fff")
            .attr("stroke", "#22C55E");

        // Labels (First and Last Year)
        svg.append("g")
            .attr("transform", `translate(0,${height - margin.bottom})`)
            .call(d3.axisBottom(x).tickValues([history[0].jaar, history[history.length - 1].jaar]).tickFormat(d3.format("d")).tickSize(0))
            .select(".domain").remove();

        // Y Axis (minimal)
        svg.append("g")
            .attr("transform", `translate(${margin.left},0)`)
            .call(d3.axisLeft(y).ticks(3))
            .select(".domain").remove();
    }


    showError(message) {
        this.container.innerHTML = `
            <div class="kompas-empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <p>${escapeHtml(message)}</p>
            </div>
        `;
    }

    // =========================================================================
    // Track A1: Tabbed Metadata & Track A3: Timeslider Logic
    // =========================================================================

    _updateIndicatorMetadata(historyData) {
        const history = historyData.history || [];
        if (history.length > 0) {
            document.getElementById('details-jaar').textContent = history[history.length - 1].jaar;
        } else {
            document.getElementById('details-jaar').textContent = '-';
        }
        
        // Bron & Lineage (Sprint 22 Track C)
        const bronEl = document.getElementById('details-bron');
        const bronLinkEl = document.getElementById('details-bron-link');
        const bronBadgeEl = document.getElementById('details-bron-badge');
        
        if (bronEl) {
            // Bron van de getoonde waarde (meest recente jaar); per jaar kan die verschillen (#119)
            const laatste = history.length > 0 ? history[history.length - 1] : null;
            bronEl.textContent = (laatste && laatste.bron) || historyData.bron || 'Onbekend';
            let tooltip = `Bron: ${historyData.bron || 'Onbekend'}`;
            if (historyData.bron_tabel_referentie) {
                tooltip += `\nDataset/Tabel: ${historyData.bron_tabel_referentie}`;
            }
            if (historyData.laatste_check_datum) {
                tooltip += `\nLaatste controle: ${historyData.laatste_check_datum}`;
            }
            bronEl.title = tooltip;
        }
        
        if (bronLinkEl) {
            if (historyData.bron_url) {
                bronLinkEl.href = safeUrl(historyData.bron_url);
                bronLinkEl.style.display = 'inline-flex';
                bronLinkEl.title = `Open officiële dataset (${historyData.bron_tabel_referentie || 'catalogus'})`;
            } else {
                bronLinkEl.style.display = 'none';
            }
        }
        
        if (bronBadgeEl) {
            if (historyData.bron_tabel_referentie) {
                bronBadgeEl.textContent = historyData.bron_tabel_referentie;
                bronBadgeEl.style.display = 'inline-block';
                bronBadgeEl.title = `Dataset code: ${historyData.bron_tabel_referentie} (${historyData.bron_systeem_api || 'API'})`;
            } else {
                bronBadgeEl.style.display = 'none';
            }
        }

        if (historyData.definitie) document.getElementById('details-definitie').textContent = historyData.definitie;
        else document.getElementById('details-definitie').textContent = "Geen definitie beschikbaar.";
        
        // A1: Ontologie tab
        const ontologieText = historyData.ontologische_beschrijving;
        const tabOntologie = document.getElementById('tab-ontologie');
        if (ontologieText && ontologieText.trim() !== '') {
            document.getElementById('details-ontologie').textContent = ontologieText;
            if (tabOntologie) tabOntologie.style.display = 'block';
        } else {
            document.getElementById('details-ontologie').textContent = "Geen ontologische beschrijving beschikbaar.";
            if (tabOntologie) tabOntologie.style.display = 'none';
            // Switch back to definitie if it was on ontologie
            this._switchTab('definitie');
        }
    }

    _switchTab(tabName) {
        const tabDef = document.getElementById('tab-definitie');
        const tabOnt = document.getElementById('tab-ontologie');
        const contDef = document.getElementById('content-definitie');
        const contOnt = document.getElementById('content-ontologie');
        
        if (!tabDef || !contDef) return;

        if (tabName === 'definitie') {
            tabDef.classList.add('active');
            tabDef.style.opacity = '1';
            tabDef.style.borderBottom = '2px solid var(--accent-color)';
            if (tabOnt) {
                tabOnt.classList.remove('active');
                tabOnt.style.opacity = '0.7';
                tabOnt.style.borderBottom = 'none';
            }
            contDef.style.display = 'block';
            if (contOnt) contOnt.style.display = 'none';
        } else if (tabName === 'ontologie') {
            if (tabOnt) {
                tabOnt.classList.add('active');
                tabOnt.style.opacity = '1';
                tabOnt.style.borderBottom = '2px solid var(--accent-color)';
            }
            tabDef.classList.remove('active');
            tabDef.style.opacity = '0.7';
            tabDef.style.borderBottom = 'none';
            if (contOnt) contOnt.style.display = 'block';
            contDef.style.display = 'none';
        }
    }

    _setupTimesliderControls() {
        const slider = document.getElementById('timeslider-input');
        const playBtn = document.getElementById('timeslider-play-btn');
        
        if (!slider || !playBtn) return;
        
        slider.addEventListener('input', (e) => {
            if (this._timesliderHistory && this._timesliderHistory.length > 0) {
                const idx = parseInt(e.target.value);
                const item = this._timesliderHistory[idx];
                if (item) {
                    this._updateTimesliderUI(item.jaar);
                    // Dispatch to map
                    this._dispatchMapYear(item.jaar);
                }
            }
        });
        
        playBtn.addEventListener('click', () => {
            if (this._timesliderInterval) {
                this._pauseTimeslider();
            } else {
                this._playTimeslider();
            }
        });
    }

    _initTimeslider(history) {
        this._timesliderHistory = history;
        this._pauseTimeslider(); // Stop any running
        
        const slider = document.getElementById('timeslider-input');
        if (!slider) return;
        
        slider.min = 0;
        slider.max = history.length - 1;
        slider.value = history.length - 1; // Default to latest
        
        this._updateTimesliderUI(history[history.length - 1].jaar);
    }
    
    _updateTimesliderUI(jaar) {
        const label = document.getElementById('timeslider-label');
        if (label) label.textContent = jaar;
        
        const detJaar = document.getElementById('details-jaar');
        if (detJaar) detJaar.textContent = jaar;

        // Bron hoort bij het gekozen jaar (#119)
        const punt = (this._timesliderHistory || []).find(h => h.jaar === jaar);
        const bronEl = document.getElementById('details-bron');
        if (bronEl && punt && punt.bron) bronEl.textContent = punt.bron;

        // Update waarde behorende bij het gekozen peiljaar
        if (punt && punt.waarde !== undefined && punt.waarde !== null) {
            const valEl = document.getElementById('details-value');
            if (valEl) {
                const isMulti = this.currentData?._multiGebiedIds?.length > 1;
                const node = this.currentNode;
                const eenheid = (node && node.data && node.data.eenheid) || '';
                const eenheidText = eenheid ? ` ${eenheid}` : '';
                valEl.textContent = `${isMulti ? '⌀ ' : ''}${Number(punt.waarde).toFixed(2)}${eenheidText}`;
            }
        }
    }
    
    _dispatchMapYear(jaar) {
        // Resolveer indicator UUID robuust (currentNode, cached indicator UUID, of active indicator in state)
        const uuid = (this.currentNode && this.currentNode.data && this.currentNode.data.uuid)
            || this._currentIndicatorUuid
            || this._lastExpandedIndicatorUuid
            || (window.state && window.state.currentIndicator);

        if (window.EventBus && uuid) {
            // Actively dispatch the specific year for rendering
            window.EventBus.emit('YEAR_CHANGED', {
                uuid: uuid,
                jaar: jaar
            });
        } else {
            console.warn('⚠️ _dispatchMapYear: geen indicator UUID gevonden');
        }
    }
    
    _playTimeslider() {
        const slider = document.getElementById('timeslider-input');
        const iconPlay = document.getElementById('icon-play');
        const iconPause = document.getElementById('icon-pause');
        
        if (!slider || !this._timesliderHistory) return;
        
        if (iconPlay) iconPlay.style.display = 'none';
        if (iconPause) iconPause.style.display = 'block';
        
        // If at the end, restart
        if (parseInt(slider.value) >= parseInt(slider.max)) {
            slider.value = 0;
            const item = this._timesliderHistory[0];
            this._updateTimesliderUI(item.jaar);
            this._dispatchMapYear(item.jaar);
        }
        
        this._timesliderInterval = setInterval(() => {
            let val = parseInt(slider.value);
            val++;
            
            if (val > parseInt(slider.max)) {
                this._pauseTimeslider();
                return;
            }
            
            slider.value = val;
            const item = this._timesliderHistory[val];
            this._updateTimesliderUI(item.jaar);
            this._dispatchMapYear(item.jaar);
            
        }, 1500);
    }
    
    _pauseTimeslider() {
        const iconPlay = document.getElementById('icon-play');
        const iconPause = document.getElementById('icon-pause');
        
        if (iconPlay && iconPause) {
            iconPlay.style.display = 'block';
            iconPause.style.display = 'none';
        }
        
        if (this._timesliderInterval) {
            clearInterval(this._timesliderInterval);
            this._timesliderInterval = null;
        }
    }

    // =========================================================================
    // Horizontal Expansion Logic (Sprint 4C)
    // =========================================================================

    expandDetails(node) {
        /**
         * Toon detailpaneel met trendlijn en benchmark voor geselecteerde indicator
         */
        this.isExpanded = true;
        this.currentNode = node;
        this._currentIndicatorUuid = node.data?.uuid || null;
        this._lastExpandedIndicatorUuid = node.data?.uuid || null;
        this.updateBreadcrumb(node);

        const windowEl = document.getElementById('kompas-window');
        const detailsPanel = document.getElementById('kompas-details-panel');

        if (!windowEl || !detailsPanel) return;

        // Update Center Label to "Sluiten"
        const centerLabel = this.g?.select('.kompas-center-label');
        if (centerLabel && !centerLabel.empty()) {
            centerLabel
                .text('✕ Sluiten')
                .style('fill', 'var(--secondary-color)')
                .style('cursor', 'pointer')
                .style('pointer-events', 'none') // Still none, as parent circle handles click
                .style('font-size', '14px');
        }

        // 1. Expand Window
        // CSS .expanded uses !important to override inline styles from DraggableWindow
        windowEl.classList.add('expanded');

        detailsPanel.style.display = 'flex'; // Make visible for transition

        // 2. Check Bounds (Shift left if off-screen, only if floating)
        if (window.state?.dockMode === 'floating') {
            this.checkWindowBounds();
        }

        // 3. Populate Basic Data
        const titleEl = document.getElementById('details-title');
        if (titleEl) titleEl.textContent = node.data.name;
        const ipNaam = document.getElementById('ip-naam');
        if (ipNaam) ipNaam.textContent = node.data.name;
        const ipEenheid = document.getElementById('ip-eenheid');
        if (ipEenheid) ipEenheid.textContent = node.data.eenheid || '';

        // Sprint 7: Bij multi-select, toon gemiddelde waarde met label
        const isMulti = this.currentData?._multiGebiedIds?.length > 1;
        const valueEl = document.getElementById('details-value');
        const eenheidText = node.data.eenheid ? ` ${node.data.eenheid}` : '';
        if (isMulti) {
            valueEl.textContent = node.data.value !== null
                ? `⌀ ${node.data.value.toFixed(2)}${eenheidText}`
                : '-';
        } else {
            valueEl.textContent = node.data.value !== null
                ? `${node.data.value.toFixed(2)}${eenheidText}`
                : '-';
        }
        valueEl.style.color = node.data.color || 'var(--text-primary)';

        // Reset dynamic content
        document.getElementById('details-definitie').innerHTML = '<span class="loading-pulse">Gegevens laden...</span>';
        document.getElementById('details-trend').textContent = '-';
        document.getElementById('details-jaar').textContent = '-';

        // 4. Fetch Details & History (or comparison barchart)
        this.loadIndicatorDetails(node);
    }

    collapseDetails() {
        /**
         * Sluit het detailpaneel onder het kompas
         */
        this.isExpanded = false;
        this._currentIndicatorUuid = null;
        this._lastExpandedIndicatorUuid = null;

        const windowEl = document.getElementById('kompas-window');
        const detailsPanel = document.getElementById('kompas-details-panel');

        // Restore Center Label (Clear it, as default is empty)
        const centerLabel = this.g?.select('.kompas-center-label');
        if (centerLabel && !centerLabel.empty()) {
            centerLabel.text('');
        }

        if (windowEl) {
            windowEl.classList.remove('expanded');
        }

        if (detailsPanel) {
            detailsPanel.style.display = 'none';
        }

        // Als huidige node een leaf indicator was, stap terug naar het bovenliggende thema
        if (this.currentNode && !this.currentNode.children) {
            this.currentNode = this.currentNode.parent || this.root;
            if (this.currentNode) {
                this.updateBreadcrumb(this.currentNode);
            }
        }
    }

    checkWindowBounds() {
        /**
         * Ensure expanded window fits on screen
         */
        const windowEl = document.getElementById('kompas-window');
        if (!windowEl) return;
        
        const rect = windowEl.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const currentWidth = rect.width || 650;

        // If right edge exceeds viewport
        if (rect.left + currentWidth > viewportWidth) {
            const overflow = (rect.left + currentWidth) - viewportWidth + 20; // 20px padding
            const newLeft = Math.max(20, rect.left - overflow);
            windowEl.style.left = `${newLeft}px`;
            
            // Also update top if it's too high/low
            if (rect.top < 0) windowEl.style.top = '20px';
        }
    }

    async loadIndicatorDetails(node) {
        /**
         * Fetch history and metadata.
         * Sprint 7: Bij multi-select, toon vergelijkende barchart i.p.v. trendlijn.
         * Sprint 18 Track C: Bij 2+ groepen, toon benchmarktabel.
         */
        if (!node || !node.data.uuid) return;
        if (!this.currentGebiedId && window.state?.selectedGebiedIds?.size > 0) {
            this.currentGebiedId = [...window.state.selectedGebiedIds][0];
        }

        const detailsReqId = ++this._detailsRequestId;

        // FE-2.4: Laad altijd benchmark staafdiagram en CSV export (#444)
        this._loadBenchmarkBarChart(node);

        // Sprint 18 Track C: Benchmark-modus — 2+ groepen (woonplaatsen) actief
        const groepen = window.state?.selectedGroepen || [];
        if (groepen.length >= 2) {
            await this._loadBenchmarkComparison(node);
            return;
        }

        // Multi-select gebieden → multi-line trendgrafiek (max 5 buurten)
        const s = window.state || {};
        const gebiedIds = s.selectedGebiedIds && s.selectedGebiedIds.size > 0
            ? [...s.selectedGebiedIds]
            : (this.currentData?._multiGebiedIds || (this.currentGebiedId ? [this.currentGebiedId] : []));

        const isMulti = gebiedIds.length > 1;

        if (isMulti) {
            await this._loadMultiGebiedIndicatorComparison(node);
            return;
        }

        try {
            // Fetch History + Top Buurten in parallel
            const [historyData, topBuurtenData] = await Promise.all([
                this.fetchHistory(this.currentGebiedId, node.data.uuid),
                this._fetchTopBuurten(node.data.uuid, this.currentGebiedId)
            ]);

            if (detailsReqId !== this._detailsRequestId) {
                console.log('🔄 Verouderde indicator details genegeerd (B2)');
                return;
            }

            // Update fallback eenheid if missing
            if (historyData && historyData.eenheid && !node.data.eenheid) {
                node.data.eenheid = historyData.eenheid;
                const eenheidText = node.data.eenheid ? ` ${node.data.eenheid}` : '';
                document.getElementById('details-value').textContent = node.data.value !== null 
                    ? `${isMulti ? '⌀ ' : ''}${node.data.value.toFixed(2)}${eenheidText}`
                    : '-';
            }

            // Render Chart
            if (historyData && historyData.history && historyData.history.length > 1) {
                const chartWrapper = document.getElementById('chart-container-wrapper');
                if (chartWrapper) chartWrapper.style.display = 'block';
                document.getElementById('chart-fallback-message').style.display = 'none';
                document.getElementById('kompas-trend-chart').style.display = 'block';
                document.getElementById('timeslider-container').style.display = 'flex';

                this.renderTrendChart(historyData.history, node.data.color);
                this._initTimeslider(historyData.history);

                // Update Trend Text (simple logic: last vs first)
                const history = historyData.history;
                const start = history[0].waarde;
                const end = history[history.length - 1].waarde;
                const diff = end - start;
                const trendEl = document.getElementById('details-trend');

                if (diff > 0) {
                    trendEl.innerHTML = `<span style="color: var(--action-color)">▲ Stijgend</span>`;
                } else if (diff < 0) {
                    trendEl.innerHTML = `<span style="color: var(--secondary-color)">▼ Dalend</span>`;
                } else {
                    trendEl.innerHTML = "Stabiel";
                }

                // A1: Update Metadata
                this._updateIndicatorMetadata(historyData);

            } else if (historyData && historyData.history && historyData.history.length === 1) {
                // A3: 1 data point = fallback
                this.destroyChart();
                const chartWrapper = document.getElementById('chart-container-wrapper');
                if (chartWrapper) chartWrapper.style.display = 'block';
                document.getElementById('chart-fallback-message').style.display = 'flex';
                document.getElementById('kompas-trend-chart').style.display = 'none';
                document.getElementById('timeslider-container').style.display = 'none';
                
                document.getElementById('details-trend').textContent = '-';
                
                this._updateIndicatorMetadata(historyData);
                
            } else if (historyData) {
                // Geen data
                this.destroyChart();
                const chartWrapper = document.getElementById('chart-container-wrapper');
                if (chartWrapper) chartWrapper.style.display = 'none';
                document.getElementById('timeslider-container').style.display = 'none';
                document.getElementById('details-trend').textContent = '-';
                
                this._updateIndicatorMetadata(historyData);
            } else {
                this.destroyChart();
                const chartWrapper = document.getElementById('chart-container-wrapper');
                if (chartWrapper) chartWrapper.style.display = 'none';
                document.getElementById('timeslider-container').style.display = 'none';
                document.getElementById('details-definitie').textContent = "Geen trenddata beschikbaar.";
            }

            // F2: Render Top Buurten
            this._renderTopBuurten(topBuurtenData);

        } catch (e) {
            console.error('Error loading details:', e);
            document.getElementById('details-definitie').textContent = "Fout bij laden gegevens.";
        }
    }

    async _fetchTopBuurten(indicatorUuid, gebiedId) {
        try {
            const url = gebiedId 
                ? `/api/kompas/indicator/${indicatorUuid}/top-buurten?gebied_id=${gebiedId}`
                : `/api/kompas/indicator/${indicatorUuid}/top-buurten`;
            const resp = await fetch(url);
            if (!resp.ok) return null;
            return await resp.json();
        } catch (e) {
            console.warn('Top buurten niet beschikbaar:', e.message);
            return null;
        }
    }

    _renderTopBuurten(data) {
        // Verwijder eventueel bestaand blok
        const existing = document.getElementById('kompas-top-buurten');
        if (existing) existing.remove();

        if (!data || (!data.top_positief?.length && !data.top_negatief?.length)) return;

        const container = document.createElement('div');
        container.id = 'kompas-top-buurten';
        container.style.cssText = 'margin-top: 15px; border-top: 1px solid var(--panel-border); padding: 15px; background: var(--tint-subtle); border-radius: 6px;';

        const eenheid = data.eenheid || '';
        const contextNaam = data.context_naam || 'Alle gemeenten';
        
        let html = `<div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between;">
            <div>Top Uitschieters: <span style="color: var(--text-primary);">${escapeHtml(contextNaam)}</span></div>
            <div title="Deze afwijkingen worden berekend middels de z-score methodiek (het verschil ten opzichte van het gemiddelde)." style="cursor: help; width: 16px; height: 16px; border-radius: 50%; border: 1.5px solid var(--text-secondary); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; font-family: monospace; color: var(--text-secondary); opacity: 0.8; transition: all 0.2s ease;" onmouseover="this.style.opacity='1'; this.style.color='var(--action-color)'; this.style.borderColor='var(--action-color)'" onmouseout="this.style.opacity='0.8'; this.style.color='var(--text-secondary)'; this.style.borderColor='var(--text-secondary)'">i</div>
        </div>`;

        // Top positief (↑)
        if (data.top_positief?.length) {
            html += `<div style="margin-bottom: 8px;"><div style="font-size: 0.72rem; color: var(--action-color); font-weight: 600; margin-bottom: 4px;">↑ Hoogste waarden</div>`;
            data.top_positief.forEach((b, i) => {
                html += this._topBuurtRow(b, i + 1, eenheid, 'var(--action-color)');
            });
            html += `</div>`;
        }

        // Top negatief (↓)
        if (data.top_negatief?.length) {
            html += `<div><div style="font-size: 0.72rem; color: var(--secondary-color); font-weight: 600; margin-bottom: 4px;">↓ Laagste waarden</div>`;
            data.top_negatief.forEach((b, i) => {
                html += this._topBuurtRow(b, i + 1, eenheid, 'var(--secondary-color)');
            });
            html += `</div>`;
        }

        container.innerHTML = html;

        // Click & keyboard handlers — flyToGebied (#450: toegankelijk met Enter/Spatie)
        container.querySelectorAll('[data-buurt-id]').forEach(el => {
            const activeer = () => {
                const buurtId = el.dataset.buurtId;
                // Zoek de feature in de huidige kaartdata
                if (window.state?.currentData?.features) {
                    const feature = window.state.currentData.features.find(
                        f => f.properties.id === buurtId || f.properties.buurt_id === buurtId
                    );
                    if (feature && typeof flyToGebied === 'function') {
                        flyToGebied(feature);
                        // Sprint 18 F3: Highlight top-buurt without hard selection
                        if (typeof window.highlightGebied === 'function') {
                            const actualId = feature.id || feature.properties?.id || buurtId;
                            window.highlightGebied(actualId);
                        }
                    }
                }
            };

            el.addEventListener('click', activeer);
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    activeer();
                }
            });
        });

        // Voeg toe aan het detailpaneel
        const detailsPanel = document.getElementById('kompas-details-panel');
        if (detailsPanel) {
            detailsPanel.appendChild(container);
        }
    }

    _topBuurtRow(buurt, rank, eenheid, accentColor) {
        return `
            <div data-buurt-id="${escapeHtml(buurt.buurt_id)}" role="button" tabindex="0" style="display: flex; align-items: center; justify-content: space-between; padding: 3px 6px; margin: 2px 0; border-radius: 4px; cursor: pointer; font-size: 0.78rem; transition: background 0.15s;" 
                 onmouseover="this.style.background='var(--tint)'" 
                 onmouseout="this.style.background='transparent'"
                 title="Klik om naar ${escapeHtml(buurt.buurt_naam)} te vliegen">
                <span style="color: var(--text-secondary); width: 18px;">${rank}.</span>
                <span style="flex: 1; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(buurt.buurt_naam)}</span>
                <span style="font-family: monospace; margin-left: 8px; color: var(--text-secondary);">${escapeHtml(buurt.waarde)} ${escapeHtml(eenheid)}</span>
                <span style="font-family: monospace; font-weight: 600; margin-left: 8px; min-width: 50px; text-align: right; color: ${accentColor};">${buurt.z_score > 0 ? '+' : ''}${escapeHtml(buurt.z_score)}</span>
            </div>`;
    }

    async _loadMultiGebiedIndicatorComparison(node) {
        /**
         * Multi-buurt vergelijking (#444):
         * Toont een multi-line trendlijn van alle geselecteerde buurten (max 5) in het bovenste grafiekvak.
         * De liggende staafdiagrammen worden uitsluitend in de onderste benchmarksectie getoond,
         * zodat er geen dubbele staafdiagrammen ontstaan.
         */
        const s = window.state || {};
        const gebiedIds = s.selectedGebiedIds && s.selectedGebiedIds.size > 0
            ? [...s.selectedGebiedIds]
            : (this.currentData?._multiGebiedIds || []);
        if (gebiedIds.length === 0) return;

        const indicatorUuid = node.data.uuid;

        // Bepaal namen van buurten
        const getNaam = (id, idx) => {
            if (this.currentData?._multiGebiedNamen && this.currentData._multiGebiedNamen[idx]) {
                return this.currentData._multiGebiedNamen[idx];
            }
            if (s.currentData?.features) {
                const feat = s.currentData.features.find(f => f.properties?.id === id || f.id === id);
                if (feat?.properties?.naam) return feat.properties.naam;
            }
            return id;
        };

        const trendEl = document.getElementById('details-trend');
        if (trendEl) trendEl.innerHTML = `<span style="color: var(--action-color)">Vergelijking</span>`;

        try {
            // Haal historie op voor alle geselecteerde gebieden (max 5 voor de trendlijnen)
            const maxLijnen = 5;
            const actieveGebiedIds = gebiedIds.slice(0, maxLijnen);
            const promises = actieveGebiedIds.map(id => this.fetchHistory(id, indicatorUuid));
            const results = await Promise.all(promises);

            // Update metadata van eerste resultaat
            if (results[0]) {
                this._updateIndicatorMetadata(results[0]);
                if (results[0].definitie) {
                    document.getElementById('details-definitie').textContent = results[0].definitie;
                }
            }

            // Verzamel alle unieke jaren over alle geselecteerde gebieden
            const allYears = [...new Set(results.flatMap(r => (r?.history || []).map(h => h.jaar)))].sort((a, b) => a - b);

            const ctx = document.getElementById('kompas-trend-chart');
            const chartWrapper = document.getElementById('chart-container-wrapper');
            const fallback = document.getElementById('chart-fallback-message');
            const tijdschuif = document.getElementById('timeslider-container');

            if (allYears.length >= 2) {
                // Tijdreeks beschikbaar: render multi-line trendgrafiek
                if (chartWrapper) chartWrapper.style.display = 'block';
                if (fallback) fallback.style.display = 'none';
                if (ctx) ctx.style.display = 'block';
                if (tijdschuif) tijdschuif.style.display = 'flex';

                const areaColors = ['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4'];
                const datasets = results.map((r, idx) => {
                    const naam = r?.gebied?.naam || r?.gebied_naam || getNaam(actieveGebiedIds[idx], idx);
                    const histMap = new Map((r?.history || []).map(h => [h.jaar, h.waarde]));
                    const color = areaColors[idx % areaColors.length];
                    return {
                        label: naam.length > 20 ? naam.slice(0, 19) + '…' : naam,
                        data: allYears.map(yr => histMap.has(yr) ? histMap.get(yr) : null),
                        borderColor: color,
                        backgroundColor: 'transparent',
                        pointBackgroundColor: color,
                        pointBorderColor: color,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        fill: false,
                        tension: 0.3,
                        spanGaps: true
                    };
                });

                // "+N overige buurten" annotatie als selectie > 5
                const remaining = gebiedIds.length - maxLijnen;
                const noteEl = ctx.parentElement?.querySelector('.chart-overflow-note');
                if (remaining > 0) {
                    if (noteEl) {
                        noteEl.textContent = `+${remaining} overige buurten (alle ${gebiedIds.length} getoond in vergelijking hieronder)`;
                        noteEl.style.display = 'block';
                    } else {
                        const note = document.createElement('div');
                        note.className = 'chart-overflow-note';
                        note.style.cssText = 'font-size: 0.75rem; color: var(--text-secondary); text-align: center; padding-top: 4px;';
                        note.textContent = `+${remaining} overige buurten (alle ${gebiedIds.length} getoond in vergelijking hieronder)`;
                        ctx.parentElement?.appendChild(note);
                    }
                } else if (noteEl) {
                    noteEl.style.display = 'none';
                }

                this.destroyChart();

                const tekst = themaKleur('--text-primary', '#1e293b');
                const subtiel = themaKleur('--text-secondary', '#64748b');
                const lijn = themaKleur('--border-color', '#e2e8f0');
                const eenheid = node.data?.eenheid || '';

                this.trendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: allYears,
                        datasets: datasets
                    },
                    options: {
                        onClick: (e, elements) => {
                            if (elements.length > 0) {
                                const idx = elements[0].index;
                                const slider = document.getElementById('timeslider-input');
                                if (slider) {
                                    slider.value = idx;
                                    const evt = new Event('input');
                                    slider.dispatchEvent(evt);
                                }
                            }
                        },
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : undefined,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: {
                                    boxWidth: 12,
                                    color: tekst,
                                    font: { size: 11 }
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                backgroundColor: themaKleur('--tooltip-bg', '#0f172a'),
                                titleColor: themaKleur('--tooltip-text', '#ffffff'),
                                bodyColor: themaKleur('--tooltip-text', '#ffffff'),
                                borderColor: lijn,
                                borderWidth: 1,
                                callbacks: {
                                    label: (item) => {
                                        const v = item.raw !== null && item.raw !== undefined ? Number(item.raw).toLocaleString('nl-NL', { maximumFractionDigits: 2 }) : '-';
                                        const eenh = eenheid ? ` ${eenheid}` : '';
                                        return `${item.dataset.label}: ${v}${eenh}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: { color: lijn, drawBorder: false },
                                ticks: { color: subtiel, font: { size: 11 } }
                            },
                            y: {
                                grid: { color: lijn, drawBorder: false },
                                ticks: { color: tekst, font: { size: 11 }, autoSkip: false },
                                title: { display: !!eenheid, text: eenheid, color: subtiel, font: { size: 11 } }
                            }
                        }
                    }
                });

                this._initTimeslider(allYears.map(yr => ({ jaar: yr })));

            } else if (allYears.length === 1) {
                // Slechts 1 peiljaar (bijv. BAG/Kadaster): toon een vergelijkende staafgrafiek van de gebieden
                const barData = results.map((r, idx) => {
                    const hist = r?.history || [];
                    const val = hist.length > 0 ? hist[0].waarde : null;
                    return {
                        naam: r?.gebied?.naam || r?.gebied_naam || getNaam(actieveGebiedIds[idx], idx),
                        waarde: val
                    };
                });
                this._renderComparisonBarChart(barData, node.data?.eenheid || '');
            } else {
                this.destroyChart();
                if (chartWrapper) chartWrapper.style.display = 'none';
                if (tijdschuif) tijdschuif.style.display = 'none';
            }

            // Jaren tekst bijwerken
            if (allYears.length > 0) {
                const min = allYears[0], max = allYears[allYears.length - 1];
                const jaarEl = document.getElementById('details-jaar');
                if (jaarEl) {
                    jaarEl.textContent = min === max ? String(min) : `${min}–${max}`;
                }
            }

        } catch (e) {
            console.error('Error loading multi-area trend:', e);
            document.getElementById('details-definitie').textContent = 'Fout bij laden vergelijking.';
        }
    }

    _renderComparisonBarChart(barData, eenheid) {
        /**
         * Sprint 7: Render een horizontale barchart in het bestaande Kompas chart canvas.
         * Toont max 5 gebieden gesorteerd op waarde, met "+N meer" als er meer zijn.
         */
        const ctx = document.getElementById('kompas-trend-chart');
        if (!ctx) return;

        // Een eerdere indicator met één datapunt verbergt de grafiek; voor de vergelijking weer tonen (#280)
        const chartWrapper = document.getElementById('chart-container-wrapper');
        if (chartWrapper) chartWrapper.style.display = 'block';
        const fallback = document.getElementById('chart-fallback-message');
        if (fallback) fallback.style.display = 'none';
        ctx.style.display = 'block';
        const tijdschuif = document.getElementById('timeslider-container');
        if (tijdschuif) tijdschuif.style.display = 'none';

        this.destroyChart();

        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        // Filter valid data and sort by value descending
        const validData = barData.filter(d => d.waarde !== null && d.waarde !== undefined);
        validData.sort((a, b) => b.waarde - a.waarde);

        // Top 5 for the chart
        const top5 = validData.slice(0, 5);
        const remaining = validData.length - top5.length;

        const areaColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

        const labels = top5.map(d => {
            const naam = d.naam || '?';
            return naam.length > 18 ? naam.slice(0, 17) + '…' : naam;
        });
        const values = top5.map(d => d.waarde);
        const colors = top5.map((_, i) => areaColors[i % areaColors.length]);

        // Show "+N meer" annotation if needed
        if (remaining > 0) {
            const remainAvg = validData.slice(5).reduce((s, d) => s + d.waarde, 0) / remaining;
            const noteEl = ctx.parentElement?.querySelector('.chart-overflow-note');
            if (noteEl) {
                noteEl.textContent = `+${remaining} meer gebieden (gem: ${remainAvg.toFixed(2)} ${eenheid})`;
                noteEl.style.display = 'block';
            } else {
                // Create note element if it doesn't exist
                const note = document.createElement('div');
                note.className = 'chart-overflow-note';
                note.style.cssText = 'font-size: 0.75rem; color: var(--text-secondary); text-align: center; padding-top: 4px;';
                note.textContent = `+${remaining} meer gebieden (gem: ${remainAvg.toFixed(2)} ${eenheid})`;
                ctx.parentElement?.appendChild(note);
            }
        } else {
            // Hide overflow note if not needed
            const noteEl = ctx.parentElement?.querySelector('.chart-overflow-note');
            if (noteEl) noteEl.style.display = 'none';
        }

        this.trendChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(c => c),
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.7
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: themaKleur('--tooltip-bg', '#0f172a'),
                        titleColor: themaKleur('--tooltip-text', '#ffffff'),
                        bodyColor: themaKleur('--tooltip-text', '#ffffff'),
                        borderColor: themaKleur('--border-color', '#e2e8f0'),
                        borderWidth: 1,
                        callbacks: {
                            label: (ctx) => `${ctx.parsed.x?.toFixed(2) ?? '-'} ${eenheid}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: themaKleur('--border-color', '#e2e8f0'), drawBorder: false },
                        ticks: { color: themaKleur('--text-secondary', '#64748b'), font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: themaKleur('--text-primary', '#1e293b'), font: { size: 11 }, autoSkip: false }
                    }
                }
            }
        });
    }

    // ─── Sprint 18 Track C: Benchmark vergelijking ──────────────────────────

    async _loadBenchmarkComparison(node) {
        /**
         * Laad benchmark data voor alle actieve groepen (woonplaatsen)
         * en toon als vergelijkingstabel in het detailpaneel.
         */
        const groepen = window.state.selectedGroepen;
        const indicatorUuid = node.data.uuid;
        const configId = this.currentConfigId;

        // Update trend label
        const trendEl = document.getElementById('details-trend');
        if (trendEl) trendEl.innerHTML = `<span style="color: var(--action-color)">⚖️ Benchmark</span>`;

        try {
            const payload = {
                groepen: groepen.map(g => ({
                    naam: g.naam,
                    buurt_ids: g.buurtIds
                })),
                gemeente_code: window.state?.currentGemeenteCode || null
            };

            const resp = await fetch(`/api/kompas/${configId}/benchmark`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const benchmarkData = await resp.json();

            // Render benchmark tabel voor deze indicator
            this._renderBenchmarkTable(benchmarkData, indicatorUuid, node);

        } catch (e) {
            console.error('Error loading benchmark comparison:', e);
            document.getElementById('details-definitie').textContent = 'Fout bij laden benchmark vergelijking.';
        }
    }

    _renderBenchmarkTable(benchmarkData, indicatorUuid, node) {
        /**
         * Render een compacte vergelijkingstabel met kolom per woonplaats.
         * Toont de waarde voor de geselecteerde indicator + afwijking t.o.v. referentie.
         */
        const { groepen, referentie, indicator_meta } = benchmarkData;
        const meta = indicator_meta?.[indicatorUuid];
        const eenheid = meta?.eenheid || node.data.eenheid || '';

        // Gebruik chart-container voor de tabel
        this.destroyChart();
        const chartWrapper = document.getElementById('chart-container-wrapper');
        if (chartWrapper) chartWrapper.style.display = 'block';
        document.getElementById('chart-fallback-message').style.display = 'none';
        document.getElementById('kompas-trend-chart').style.display = 'none';
        document.getElementById('timeslider-container').style.display = 'none';

        // Verwijder eventueel bestaande benchmarktabel
        const existing = document.getElementById('kompas-benchmark-table');
        if (existing) existing.remove();

        // Referentiewaarde
        const refWaarde = referentie?.indicatoren?.[indicatorUuid];
        const refNaam = referentie?.naam || 'Gemeente';

        // Bouw tabel
        const table = document.createElement('div');
        table.id = 'kompas-benchmark-table';
        table.style.cssText = 'margin-top: 10px; overflow-x: auto;';

        let html = `
            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 8px;">
                ⚖️ Vergelijking ${groepen.length} kernen${referentie ? ` · Ref: ${escapeHtml(refNaam)}` : ''}
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--panel-border);">`;

        // Kolomkoppen: per groep + referentie
        for (const groep of groepen) {
            html += `<th style="padding: 6px 8px; text-align: center; font-weight: 600; color: var(--text-primary);">${escapeHtml(groep.naam)}</th>`;
        }
        if (referentie) {
            html += `<th style="padding: 6px 8px; text-align: center; font-weight: 500; color: var(--text-secondary); font-style: italic;">${escapeHtml(refNaam)}</th>`;
        }

        html += `</tr></thead><tbody><tr>`;

        // Waarden per groep
        for (const groep of groepen) {
            const waarde = groep.indicatoren?.[indicatorUuid];
            if (waarde == null) {
                html += `<td style="padding: 8px; text-align: center; color: var(--text-secondary);">-</td>`;
            } else {
                // Bereken afwijking t.o.v. referentie
                let afwijkingHtml = '';
                if (refWaarde != null) {
                    const diff = waarde - refWaarde;
                    const pct = refWaarde !== 0 ? ((diff / Math.abs(refWaarde)) * 100).toFixed(0) : 0;
                    // Kleur volgt de polariteit van de indicator (#323)
                    const { kleur, oordeel } = afwijkingDuiding(diff, meta?.richting);
                    const teken = diff > 0 ? `↑ +${pct}%` : diff < 0 ? `↓ ${pct}%` : '= 0%';
                    afwijkingHtml = `<div style="font-size: 0.7rem; color: var(${kleur});" title="${oordeel}">${teken}</div>`;
                }
                html += `<td style="padding: 8px; text-align: center;">
                    <div style="font-weight: 600; color: var(--text-primary);">${waarde.toFixed(1)}</div>
                    <div style="font-size: 0.65rem; color: var(--text-secondary);">${escapeHtml(eenheid)}</div>
                    ${afwijkingHtml}
                </td>`;
            }
        }

        // Referentiekolom
        if (referentie) {
            if (refWaarde != null) {
                html += `<td style="padding: 8px; text-align: center; background: var(--tint-subtle);">
                    <div style="font-weight: 500; color: var(--text-secondary);">${refWaarde.toFixed(1)}</div>
                    <div style="font-size: 0.65rem; color: var(--text-secondary);">${escapeHtml(eenheid)}</div>
                </td>`;
            } else {
                html += `<td style="padding: 8px; text-align: center; color: var(--text-secondary);">-</td>`;
            }
        }

        html += `</tr></tbody></table>`;
        table.innerHTML = html;

        // Insert na chart-container-wrapper
        chartWrapper.insertAdjacentElement('afterend', table);
    }

    renderTrendChart(history, color) {
        const ctx = document.getElementById('kompas-trend-chart');
        if (!ctx) return;

        // Destroy existing chart
        this.destroyChart();

        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        const labels = history.map(d => d.jaar);
        const data = history.map(d => d.waarde);
        const chartColor = color || '#3b82f6'; // Trust Blue Dark (was SWF Keperblauw)
        const tekst = themaKleur('--text-primary', '#1e293b');
        const subtiel = themaKleur('--text-secondary', '#64748b');
        const lijn = themaKleur('--border-color', '#e2e8f0');
        const eenheid = this.currentNode?.data?.eenheid || '';

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Trend',
                    data: data,
                    borderColor: chartColor,
                    backgroundColor: (() => {
                        const rgb = this.hexToRgb(chartColor);
                        return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.12)`;
                    })(),
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: themaKleur('--bg-secondary', '#ffffff'),
                    pointBorderColor: chartColor,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                onClick: (e, elements, chart) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const slider = document.getElementById('timeslider-input');
                        if (slider) {
                            slider.value = idx;
                            const evt = new Event('input');
                            slider.dispatchEvent(evt);
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false,
                animation: window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : undefined,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: themaKleur('--tooltip-bg', '#0f172a'),
                        titleColor: themaKleur('--tooltip-text', '#ffffff'),
                        bodyColor: themaKleur('--tooltip-text', '#ffffff'),
                        borderColor: lijn,
                        borderWidth: 1,
                        callbacks: {
                            label: (item) => {
                                const v = item.raw !== null && item.raw !== undefined ? Number(item.raw).toLocaleString('nl-NL', { maximumFractionDigits: 2 }) : '-';
                                const eenh = eenheid ? ` ${eenheid}` : '';
                                return `Waarde: ${v}${eenh}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: lijn, drawBorder: false },
                        ticks: { color: subtiel, font: { size: 11 } }
                    },
                    y: {
                        grid: { color: lijn, drawBorder: false },
                        ticks: { color: tekst, font: { size: 11 }, autoSkip: false },
                        title: { display: !!eenheid, text: eenheid, color: subtiel, font: { size: 11 } }
                    }
                }
            }
        });
    }

    destroyChart() {
        if (this.trendChart) {
            this.trendChart.destroy();
            this.trendChart = null;
        }
    }

    /**
     * AI Search Integration (Sprint 8F)
     */
    setupAISearch() {
        const searchInput = document.getElementById('kompas-ai-search');
        const resultsDropdown = document.getElementById('kompas-search-results');
        if (!searchInput || !resultsDropdown) return;

        let debounceTimer;

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            clearTimeout(debounceTimer);
            if (query.length < 2) {
                resultsDropdown.style.display = 'none';
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/ai/kompas/search?q=${encodeURIComponent(query)}&limit=5`);
                    if (!response.ok) throw new Error("Search failed");

                    const results = await response.json();
                    // F1: Controleer of results een array is (bescherming tegen fout-responses)
                    this.renderSearchResults(Array.isArray(results) ? results : []);
                } catch (err) {
                    console.error("AI Search Error:", err);
                    // F1: Toon foutmelding in dropdown ipv silent fail / undefined
                    this.renderSearchResults([]);
                }
            }, 300);
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !resultsDropdown.contains(e.target)) {
                resultsDropdown.style.display = 'none';
            }
        });
    }

    renderSearchResults(results) {
        const resultsDropdown = document.getElementById('kompas-search-results');
        if (!resultsDropdown) return;

        if (results.length === 0) {
            resultsDropdown.innerHTML = '<div class="search-result-item" style="cursor: default; opacity: 0.6;">Geen resultaten gevonden.</div>';
        } else {
            resultsDropdown.innerHTML = results.map(res => `
                <div class="search-result-item" role="button" tabindex="0" data-uuid="${escapeHtml(res.uuid)}">
                    <div class="result-category">${escapeHtml(res.categorie || 'Indicator')}</div>
                    <div class="result-name">${escapeHtml(res.naam)}</div>
                    ${res.relevantie ? `<div class="result-score">Relevantie: ${escapeHtml(res.relevantie)}</div>` : ''}
                </div>
            `).join('');

            // #312: label AI als het embeddingmodel meedeed (usecase C)
            if (window.OmniAI && results.some(r => r.ai)) {
                const zoekterm = document.getElementById('kompas-ai-search')?.value || '';
                resultsDropdown.appendChild(window.OmniAI.label({
                    usecase: 'C', vraag: zoekterm, resultaat: results.map(r => r.naam).join(', '),
                    bronnen: results.map(r => r.naam), pagina: 'Viewer: Kompas-zoeken',
                }));
            }

            // Click results
            resultsDropdown.querySelectorAll('.search-result-item').forEach(item => {
                item.addEventListener('click', () => {
                    const uuid = item.dataset.uuid;
                    this.navigateToIndicator(uuid);
                    resultsDropdown.style.display = 'none';
                    document.getElementById('kompas-ai-search').value = '';
                });
            });
        }

        resultsDropdown.style.display = 'block';
    }

    navigateToIndicator(uuid) {
        /**
         * Navigeer het kompas naar een specifieke indicator op basis van UUID.
         */
        if (!this.root || !this._zoomFn) {
            console.warn("⚠️ Kompas niet klaar voor navigatie, uitgesteld");
            this._pendingIndicatorUuid = uuid;
            return;
        }

        const targetNode = this._findNodeByUuid(this.root, uuid);
        if (targetNode) {
            console.log(`🎯 AI Zoek-navigatie naar: ${targetNode.data.name}`);

            // 1. Zoom naar de parent (Thema) om context te tonen, of naar de node zelf als deze kinderen heeft
            const zoomTarget = targetNode.children ? targetNode : (targetNode.parent || targetNode);
            this._zoomFn(null, zoomTarget);

            // 2. Open details paneel na een korte delay (ivm zoom animatie)
            setTimeout(() => {
                this.expandDetails(targetNode);
                // 3. Sync naar kaart
                this.syncIndicatorToMap(targetNode.data.uuid, targetNode.data.name);
            }, 800);
        } else {
            console.warn(`⚠️ Indicator met UUID ${uuid} niet gevonden in huidige hiërarchie.`);
            // Misschien waarschuwing tonen aan user
        }
    }

    /**
     * Benchmark & Bar Chart Integratie (#258/#444)
     * Haalt data op via /api/gebiedsmonitor/indicatorpaneel en vult:
     * - Horizontaal staafdiagram met gemeentegemiddelde (#ip-grafiek)
     * - Bronvermelding (#ip-bronnen)
     * - Gemeentegemiddelde (#ip-gemiddelde)
     * - Waarschuwing onderdrukking kleine aantallen (#ip-onderdrukt)
     * - CSV download link (#ip-csv)
     */
    async _loadBenchmarkBarChart(indicatorOrNode) {
        const uuid = typeof indicatorOrNode === 'string'
            ? indicatorOrNode
            : (indicatorOrNode?.data?.uuid || indicatorOrNode?.uuid || window.state?.currentIndicator);
        if (!uuid) return;
        const s = window.state || {};
        const benchReqId = ++this._benchmarkRequestId;

        // Bepaal selectie
        const ids = s.selectedGebiedIds && s.selectedGebiedIds.size > 0
            ? [...s.selectedGebiedIds]
            : (this.currentGebiedId ? [this.currentGebiedId] : []);
        const metSelectie = ids.length > 0;

        const p = new URLSearchParams({ indicator_uuid: uuid });
        if (metSelectie) {
            p.set('gebied_ids', ids.join(','));
        } else {
            p.set('gebieden', 'false');
        }
        if (s.currentGebiedstype) p.set('gebiedstype_id', s.currentGebiedstype);
        if (s.currentGemeenteCode) p.set('gemeente_code', s.currentGemeenteCode);
        if (this._currentJaar) p.set('jaar', String(this._currentJaar));

        try {
            const res = await fetch(`/api/gebiedsmonitor/indicatorpaneel?${p.toString()}`, { credentials: 'same-origin' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (benchReqId !== this._benchmarkRequestId) {
                console.log('🔄 Verouderde benchmark data genegeerd (B2)');
                return;
            }

            // Synchroon naam en eenheid wegschrijven voor tests en DOM
            const detailsPanel = document.getElementById('kompas-details-panel');
            if (detailsPanel) detailsPanel.style.display = 'block';
            const ipNaam = document.getElementById('ip-naam');
            if (ipNaam) ipNaam.textContent = data.indicator.naam + (this._currentJaar ? ` (${this._currentJaar})` : '');
            const ipEenheid = document.getElementById('ip-eenheid');
            if (ipEenheid) ipEenheid.textContent = data.indicator.eenheid || '';
            const ipBeschrijving = document.getElementById('ip-beschrijving');
            if (ipBeschrijving) ipBeschrijving.textContent = data.indicator.beschrijving || '';

            // Bronnen & Gemeentegemiddelde
            this._renderIpBronnen(data.bronnen);
            this._renderIpGemiddelde(data.gemeentegemiddelden, data.indicator.eenheid);

            // Staafdiagram
            this._renderBenchmarkGrafiek(data);

            // CSV Link
            const csvBtn = document.getElementById('ip-csv');
            if (csvBtn) {
                const csvParams = new URLSearchParams(p);
                csvParams.delete('gebieden');
                if (ids.length) csvParams.set('gebied_ids', ids.join(','));
                csvBtn.href = `/api/gebiedsmonitor/indicatorpaneel.csv?${csvParams.toString()}`;
            }
            const csvUitleg = document.getElementById('ip-csv-uitleg');
            if (csvUitleg) {
                const aantal = (data.gebieden || []).length;
                csvUitleg.textContent = ids.length
                    ? `De ${aantal} geselecteerde gebieden en het gemeentegemiddelde`
                    : `Alle ${aantal} gebieden op de kaart en het gemeentegemiddelde`;
            }
        } catch (e) {
            console.warn('Fout bij laden benchmark data:', e);
            const leeg = document.getElementById('ip-grafiek-leeg');
            if (leeg) {
                leeg.textContent = 'De benchmarkgegevens van deze indicator zijn niet te laden.';
                leeg.hidden = false;
            }
            const wrap = document.getElementById('ip-grafiek-wrap');
            if (wrap) wrap.hidden = true;
        }
    }

    _renderIpBronnen(bronnen) {
        const lijst = document.getElementById('ip-bronnen');
        if (!lijst) return;
        lijst.replaceChildren();
        if (!bronnen || !bronnen.length) {
            lijst.textContent = 'Niet vastgelegd';
            return;
        }
        const ul = document.createElement('ul');
        ul.className = 'ip-bronnen-lijst';
        bronnen.forEach((b) => {
            const li = document.createElement('li');
            const delen = [];
            let kop = b.titel || b.bron || 'Onbekende bron';
            if (b.uitgever && !kop.includes(b.uitgever)) kop += ` (${b.uitgever})`;
            delen.push(kop);
            if (b.jaargangen && b.jaargangen.length) {
                delen.push(b.jaargangen.length > 1 ? `jaargangen ${b.jaargangen[0]}–${b.jaargangen[b.jaargangen.length - 1]}` : `jaargang ${b.jaargangen[0]}`);
            }
            if (b.licentie) delen.push(`licentie ${b.licentie}`);
            li.textContent = delen.join(', ');
            ul.appendChild(li);
        });
        lijst.appendChild(ul);
    }

    _renderIpGemiddelde(gemiddelden, eenheid) {
        const el = document.getElementById('ip-gemiddelde');
        if (!el) return;
        el.replaceChildren();
        if (!gemiddelden || !gemiddelden.length) {
            el.textContent = 'Niet te berekenen (geen gebiedstype of gemeente)';
            return;
        }
        const ul = document.createElement('ul');
        ul.className = 'ip-bronnen-lijst';
        gemiddelden.forEach((g) => {
            const li = document.createElement('li');
            const waarde = g.waarde === null ? 'geen data' : `${Number(g.waarde).toLocaleString('nl-NL', { maximumFractionDigits: 2 })}${eenheid ? ' ' + eenheid : ''}`;
            li.textContent = `${g.gemeenteNaam}${g.jaar ? ' (' + g.jaar + ')' : ''}: ${waarde}`;
            li.title = `Ongewogen gemiddelde van ${g.aantalGebieden} gebieden van hetzelfde type, zonder waterbuurten`;
            ul.appendChild(li);
        });
        el.appendChild(ul);
    }

    _renderBenchmarkGrafiek(data) {
        const gebieden = data.gebieden || [];
        const leeg = document.getElementById('ip-grafiek-leeg');
        const wrap = document.getElementById('ip-grafiek-wrap');
        const canvas = document.getElementById('ip-grafiek');
        if (!wrap || !canvas) return;

        const onderdrukt = gebieden.filter((g) => g.status === 'onderdrukt').length;
        const zonder = gebieden.filter((g) => g.status === 'geen-data').length;
        const melding = [];
        if (onderdrukt) melding.push(`${onderdrukt} gebied(en) onderdrukt (minder dan ${data.drempel} waarnemingen)`);
        if (zonder) melding.push(`${zonder} gebied(en) zonder data`);
        
        const onderdruktEl = document.getElementById('ip-onderdrukt');
        if (onderdruktEl) {
            onderdruktEl.textContent = melding.join('; ');
            onderdruktEl.hidden = !melding.length;
        }

        if (this._ipChart) {
            this._ipChart.destroy();
            this._ipChart = null;
        }
        window.ipChartInstance = null;
        this._uitgesteldIpData = null;

        if (!gebieden.length || typeof Chart === 'undefined') {
            wrap.hidden = true;
            if (leeg) {
                leeg.textContent = 'Selecteer gebieden op de kaart voor een vergelijking.';
                leeg.hidden = false;
            }
            return;
        }

        wrap.hidden = false;
        if (leeg) leeg.hidden = true;
        wrap.style.height = `${Math.max(140, Math.min(gebieden.length, 40) * 30 + 90)}px`;

        // Als de container nog 0 breedte heeft (dock schuift nog open) of dock is ingeklapt
        const isDockCollapsed = document.getElementById('rechter-dock')?.classList.contains('collapsed') && window.state?.dockMode !== 'floating';
        if (!wrap.clientWidth || isDockCollapsed) {
            this._uitgesteldIpData = data;
            return;
        }

        const eenheid = data.indicator.eenheid || '';
        const gem = {};
        (data.gemeentegemiddelden || []).forEach((g) => { gem[`${g.gemeenteCode}|${g.jaar}`] = g; });
        const gemVan = (g) => gem[`${g.gemeenteCode}|${this._currentJaar ?? g.jaar}`];
        
        const tekst = themaKleur('--text-primary', '#1e293b');
        const subtiel = themaKleur('--text-secondary', '#64748b');
        const lijn = themaKleur('--border-color', '#e2e8f0');

        this._ipChart = new Chart(canvas, {
            data: {
                labels: gebieden.map((g) => g.naam || g.id),
                datasets: [
                    {
                        type: 'bar',
                        label: data.indicator.naam,
                        data: gebieden.map((g) => g.waarde),
                        backgroundColor: themaKleur('--primary-fill', '#1e3a8a'),
                        borderRadius: 3,
                        barPercentage: 0.75,
                    },
                    {
                        type: 'line',
                        label: 'Gemeentegemiddelde',
                        data: gebieden.map((g) => (gemVan(g) ? gemVan(g).waarde : null)),
                        borderColor: themaKleur('--accent-color', '#c59d00'),
                        backgroundColor: themaKleur('--accent-color', '#c59d00'),
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
                        backgroundColor: themaKleur('--tooltip-bg', '#0f172a'),
                        titleColor: themaKleur('--tooltip-text', '#ffffff'),
                        bodyColor: themaKleur('--tooltip-text', '#ffffff'),
                        borderColor: lijn,
                        borderWidth: 1,
                        callbacks: {
                            label: (ctx) => {
                                const g = gebieden[ctx.dataIndex];
                                if (ctx.datasetIndex === 0 && g && g.status === 'onderdrukt') return 'onderdrukt (kleine aantallen)';
                                if (ctx.raw === null || ctx.raw === undefined) return `${ctx.dataset.label}: geen data`;
                                return `${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString('nl-NL', { maximumFractionDigits: 2 })} ${eenheid}`.trim();
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
        window.ipChartInstance = this._ipChart;
    }

    updateSelectedAreasBadges() {
        const container = document.getElementById('kompas-selected-areas');
        if (!container) return;
        container.innerHTML = '';

        const s = window.state || {};
        const ids = s.selectedGebiedIds && s.selectedGebiedIds.size > 0
            ? [...s.selectedGebiedIds]
            : (this.currentGebiedId ? [this.currentGebiedId] : []);

        if (ids.length === 0) {
            container.style.display = 'none';
            return;
        }
        container.style.display = 'flex';

        const getName = (id) => {
            if (this.currentData?._multiGebiedIds && this.currentData?._multiGebiedNamen) {
                const idx = this.currentData._multiGebiedIds.indexOf(id);
                if (idx >= 0 && this.currentData._multiGebiedNamen[idx]) return this.currentData._multiGebiedNamen[idx];
            }
            if (this.currentGebiedId === id && this.currentData?.gebied_naam) {
                return this.currentData.gebied_naam;
            }
            if (window.state?.currentData?.features) {
                const feat = window.state.currentData.features.find(f => f.properties?.id === id || f.id === id);
                if (feat?.properties?.naam) return feat.properties.naam;
            }
            return id;
        };

        const maxBadges = 5;
        const showIds = ids.slice(0, maxBadges);
        const overflowCount = ids.length - maxBadges;

        showIds.forEach(id => {
            const badge = document.createElement('span');
            badge.className = 'area-chip';
            badge.textContent = getName(id);
            badge.title = `Klik om naar ${getName(id)} te vliegen`;
            badge.style.cursor = 'pointer';
            badge.addEventListener('click', () => {
                if (window.state?.currentData?.features) {
                    const feat = window.state.currentData.features.find(f => f.properties?.id === id || f.id === id);
                    if (feat && typeof window.flyToGebied === 'function') {
                        window.flyToGebied(feat);
                    }
                }
            });
            container.appendChild(badge);
        });

        if (overflowCount > 0) {
            const overflow = document.createElement('span');
            overflow.className = 'area-chip-overflow';
            overflow.textContent = `+ ${overflowCount} overige buurten`;
            container.appendChild(overflow);
        }
    }
}

// Initialize Kompas when DOM is ready
let kompasViz = null;

document.addEventListener('DOMContentLoaded', async function () {
    console.log('🎨 Initializing Kompas module...');

    // Create kompas instance
    kompasViz = new KompasVisualization('kompas-container');
    window.kompasViz = kompasViz; // Make globally available immediately

    // Load configuraties
    await kompasViz.loadConfigurations();

    // Load default hierarchie
    if (kompasViz.currentConfigId) {
        await kompasViz.loadHierarchie(kompasViz.currentConfigId);
    }

    // AI Search Setup
    kompasViz.setupAISearch();

    // ===================================================================
    // Chat ↔ Kompas Sync: Luister naar INDICATOR_SELECTED vanuit de chat
    // Als het Kompas open is en data heeft, navigeer naar de indicator.
    // Guard: _isSyncing voorkomt loop (navigateToIndicator → syncIndicatorToMap → emit → listener)
    // ===================================================================
    if (window.EventBus) {
        kompasViz._isSyncing = false;

        window.EventBus.on('INDICATOR_SELECTED', (data) => {
            if (!data || !data.uuid) return;
            if (!kompasViz || !kompasViz.root) {
                if (kompasViz) kompasViz._pendingIndicatorUuid = data.uuid;
                return;
            }
            if (kompasViz._isSyncing) return; // ← LOOP GUARD
            
            // Rechter dock architectuur (#444): open het Kompas tabblad
            if (typeof window.openRechterDock === 'function') {
                window.openRechterDock('kompas');
            }

            console.log('🧭↔🤖 Kompas sync: navigating to indicator', data.name, data.uuid);
            kompasViz._isSyncing = true;
            kompasViz.navigateToIndicator(data.uuid);
            // Reset guard na animatie (navigateToIndicator heeft 800ms delay)
            setTimeout(() => { kompasViz._isSyncing = false; }, 1200);
        });

        // Selectie of kaartdata gewijzigd -> update badges, multi-trendlijn en benchmark staafdiagram
        window.EventBus.on('SELECTIE_GEWIJZIGD', () => {
            kompasViz.updateSelectedAreasBadges();
            if (kompasViz.currentNode && kompasViz.currentNode.data?.uuid) {
                kompasViz.loadIndicatorDetails(kompasViz.currentNode);
            } else if (window.state?.currentIndicator) {
                kompasViz._loadBenchmarkBarChart(window.state.currentIndicator);
            }
        });

        window.EventBus.on('KAARTDATA_GELADEN', (d) => {
            if (d && d.jaar != null) kompasViz._currentJaar = d.jaar;
            if (kompasViz.currentNode && kompasViz.currentNode.data?.uuid) {
                kompasViz._loadBenchmarkBarChart(kompasViz.currentNode);
            } else if (window.state?.currentIndicator) {
                kompasViz._loadBenchmarkBarChart(window.state.currentIndicator);
            }
        });

        // Thema gewisseld: grafieken opnieuw met de nieuwe kleuren
        new MutationObserver(() => {
            if (kompasViz && kompasViz.currentNode && kompasViz.currentNode.data?.uuid) {
                kompasViz.loadIndicatorDetails(kompasViz.currentNode);
            }
        }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

        // Chat -> Kompas: Change Config
        window.EventBus.on('KOMPAS_CONFIG_SELECTED', async (data) => {
            console.log('🧭 Chat sync: selecting kompas config', data.name, data.id);
            const select = document.getElementById('kompas-config-select');
            if (select) {
                select.value = data.id;
                // Trigger change event to fire the existing listener
                select.dispatchEvent(new Event('change'));
            }
        });

        // Chat -> Kompas: Open Window / Dock
        window.EventBus.on('KOMPAS_OPEN_REQUESTED', () => {
            console.log('🧭 Chat sync: opening kompas window');
            if (typeof window.openRechterDock === 'function') {
                window.openRechterDock('kompas');
            } else if (typeof window.openKompasVenster === 'function') {
                window.openKompasVenster();
            } else if (window.state && window.state.kompasWindow) {
                window.state.kompasWindow.open();
            }
            // Toon de huidige kaartselectie
            const ids = window.state?.selectedGebiedIds ? [...window.state.selectedGebiedIds] : [];
            const configId = kompasViz.currentConfigId;
            if (ids.length > 0 && configId) {
                if (ids.length === 1) kompasViz.loadGebiedData(configId, ids[0]);
                else kompasViz.loadMultiGebiedData(configId, ids);
            }
        });

        console.log('🧭 Kompas subscribed to EventBus chat sync events');

        // Backwards compatibility shim voor scripts die indicatorpaneel.laad aanroepen (#258/#444)
        window.indicatorpaneel = {
            laad: () => {
                if (kompasViz && kompasViz.currentNode) {
                    kompasViz._loadBenchmarkBarChart(kompasViz.currentNode);
                }
            }
        };
    }

    // Config selector change
    const configSelect = document.getElementById('kompas-config-select');
    if (configSelect) {
        configSelect.addEventListener('change', async function (e) {
            const configId = parseInt(e.target.value);
            if (!configId) return;

            // If we have gebied loaded, reload with new config
            if (kompasViz.currentGebiedId) {
                await kompasViz.loadGebiedData(configId, kompasViz.currentGebiedId);
            } else {
                await kompasViz.loadHierarchie(configId);
            }
        });
    }

    // Zoom out button
    const zoomOutBtn = document.getElementById('kompas-zoom-out');
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function () {
            kompasViz.zoomOut();
        });
    }

    // Reset button
    const resetBtn = document.getElementById('kompas-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            kompasViz.reset();
        });
    }

    // Close Details Panel Button
    // Close Details Panel Button - Event Delegation (Robust Fix)
    document.addEventListener('click', function (e) {
        // Handle clicks on #close-details-btn or its children
        const btn = e.target.closest('#close-details-btn') || e.target.closest('.close-details-btn');

        if (btn) {
            e.preventDefault(); // Prevent default button behavior
            e.stopPropagation(); // Stop bubbling
            console.log('🔘 Close details clicked (Delegation)');

            if (window.kompasViz) {
                window.kompasViz.collapseDetails();
            } else {
                console.error('❌ KompasViz instance not found on window');
            }
        }
    });

    console.log('✅ Kompas module ready');
});

// Export for use in app.js
window.kompasViz = kompasViz;
