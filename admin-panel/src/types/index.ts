// TypeScript types for Admin Panel

export interface ScoreType {
    code: string;
    naam: string;
    beschrijving: string;
    voorbeelden: string;
}

export interface ColorSchema {
    id: number;
    naam: string;
    beschrijving: string | null;
    colors: {
        min: string;
        mid: string;
        max: string;
    };
    is_actief: boolean;
}

export interface Indicator {
    uuid: string;
    naam: string;
    omschrijving: string | null;
    bron: string | null;
    eenheid: string | null;
    score_type: string;
    color_schema_id: number | null;
    color_schema_naam: string | null;
    color_schema_colors?: ColorSchema['colors'];
    admin_notes: string | null;
    is_actief?: boolean;
    vervangen_door_id?: string | null;
    // Ontologie validatie velden (Sprint 9 Track B)
    ontologie_status?: OntologieStatus;
    ontologische_beschrijving?: string | null;
    beschrijving_ai?: string | null;
    gevalideerd_door?: string | null;
    gevalideerd_op?: string | null;
    embedding_versie?: string | null;
    gevalideerd_door_naam?: string | null;
}

export interface IndicatorUpdate {
    naam?: string;
    omschrijving?: string;
    bron?: string;
    eenheid?: string;
    score_type?: string;
    color_schema_id?: number;
    admin_notes?: string;
}

export interface IndicatorenResponse {
    indicatoren: Indicator[];
    total: number;
    limit: number;
    offset: number;
}

// ─── Sprint 9 Track B: Ontologie Validatie ──────────────────────────────────

export type OntologieStatus = 'draft' | 'beoordeeld_ai' | 'goedgekeurd_mens';

export interface OntologieValidatiePayload {
    ontologische_beschrijving: string;
    ontologie_status: OntologieStatus;
}

export interface OntologieValidatieStatusResponse {
    statussen: Record<string, number>;
    totaal: number;
    goedgekeurd: number;
    percentage_gereed: number;
}

export interface HierarchyNode {
    id: string;
    naam: string;
    type: 'thema' | 'onderdeel' | 'indicator';
    volgorde?: number;
    uuid?: string;
    score_type?: string;
    children?: HierarchyNode[];
}

export interface HierarchyResponse {
    config_id: number;
    tree: HierarchyNode[];
    stats: {
        themas: number;
        onderdelen: number;
        indicatoren: number;
    };
}

export interface AdminHealth {
    status: string;
    auth: string;
    database: string;
    indicatoren: number;
    color_schemas: number;
}

export interface DashboardStats {
    total_indicators: number;
    with_data_count: number;
    with_data_pct: number;
    metadata_complete_count: number;
    metadata_complete_pct: number;
    trending_count: number;
}

export interface QuadrantCoverage {
    name: string;
    total: number;
    with_data: number;
    coverage_pct: number;
}

export interface IndicatorDashboardItem {
    uuid: string;
    naam: string;
    score_type: string;
    kwadrant: string;
    years_count: number;
    last_updated: string | null;
    last_year: number | null;
    meta_complete: boolean;
    sparkline: number[];
}

export interface DashboardIndicatorsResponse {
    indicators: IndicatorDashboardItem[];
    total: number;
    limit: number;
    offset: number;
}

export interface ReportIndicator {
    indicator: string;
    omschrijving: string;
    meetjaar: number;
    waarde: number;
    gemiddelde: number;
    z_score: number;
    score_type: string;
    score_uitleg: string;
    eenheid: string;
    impact: "bovengemiddeld positief" | "ondergemiddeld negatief" | "bovengemiddeld negatief" | "ondergemiddeld positief" | "neutraal";
}

export interface ReportDataPayload {
    gebied_id: string;
    referentie_groep: string;
    aantal_indicatoren: number;
    metadata?: {
        gebied: string;
        gebiedstype: string;
        referentie_kader: string;
    };
    significante_domeinen: Record<string, ReportIndicator[]>;
}

export interface LLMDebugInfo {
    context: string;
    model: string;
    system_prompt: string;
    user_prompt: string;
}

export interface ReportNarrativeResponse {
    gebied_id: string;
    ai_summary: string;
    domain_summaries?: Record<string, string>;
    debug_info?: LLMDebugInfo[];
    status: string;
}

export interface LLMConfig {
    api_url: string;
    model_name: string;
}

export interface SystemPrompt {
    naam: string;
    beschrijving: string | null;
    prompt_text: string;
    is_actief: boolean;
}

export interface SystemPromptUpdate {
    prompt_text: string;
    beschrijving?: string;
    is_actief?: boolean;
}

// ─── Sjabloon C: Benchmark Vergelijker ──────────────────────────────────────

export type BenchmarkMode = 'gebieden' | 'gemeente' | 'fryslan';

export interface BenchmarkIndicator {
    indicator: string;
    kwadrant: string;
    eenheid: string;
    omschrijving: string;
    waarde_a: number;
    referentie_waarde: number;
    delta: number;
    delta_pct: number;
    score_type: string;
    impact: string;
    n_gebieden: number;
}

export interface BenchmarkPayload {
    gebied_a: { id: string; naam: string };
    referentie_label: string;
    mode: BenchmarkMode;
    vergelijking: BenchmarkIndicator[];
    totaal_indicatoren: number;
}

export interface BenchmarkNarrativeResponse {
    gebied_a: { id: string; naam: string };
    referentie_label: string;
    ai_narrative: string;
    debug_info?: LLMDebugInfo[];
    status: string;
}

// ─── Sjabloon A: Executive Summary ──────────────────────────────────────────

export interface ExecutivePayload {
    gebied_id: string;
    metadata: { gebied: string; gebiedstype: string; referentie_kader: string };
    referentie_groep: string;
    top_kansen: ReportIndicator[];
    top_risicos: ReportIndicator[];
    totaal_uitschieters: number;
    aantal_indicatoren: number;
}

// ─── Gebieden Zoek (voor GebiedSelector) ────────────────────────────────────

export interface GebiedListItem {
    id: string;
    naam: string;
    type: string;
}

// ─── Sprint 18: Externe Kaartlagen Beheer ───────────────────────────────────

export interface ExterneKaartlaag {
    id: number;
    naam: string;
    beschrijving: string | null;
    laag_type: 'selectie' | 'data_koppel';
    bron_type: 'WFS' | 'WMS' | 'GeoJSON' | 'lokaal';
    url: string;
    typename: string | null;
    srsname: string;
    versie: string;
    filter_type: 'bbox' | 'provincie' | 'alles';
    filter_waarde: string | null;
    koppel_veld: string | null;
    kleur_lijn: string;
    kleur_fill: string;
    opacity: number;
    actief: boolean;
    volgorde: number;
    created_at: string | null;
    updated_at: string | null;
}

export type ExterneKaartlaagCreate = Omit<ExterneKaartlaag, 'id' | 'created_at' | 'updated_at'>;
export type ExterneKaartlaagUpdate = Partial<ExterneKaartlaagCreate>;

export interface LokaalBestand {
    bestandsnaam: string;
    grootte_kb: number;
    layers?: string[];
    features?: number;
    crs?: string | null;
    geometry_type?: string;
    fout?: string;
}
