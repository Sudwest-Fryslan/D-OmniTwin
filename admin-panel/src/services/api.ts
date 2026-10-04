import axios from 'axios';
import type {
    ScoreType,
    ColorSchema,
    Indicator,
    IndicatorUpdate,
    IndicatorenResponse,
    HierarchyResponse,

    AdminHealth,
    DashboardStats,
    QuadrantCoverage,
    DashboardIndicatorsResponse,
    LLMConfig,
    SystemPrompt,
    SystemPromptUpdate,
    OntologieValidatiePayload,
    OntologieValidatieStatusResponse
} from '../types';

// API client; authenticatie via de sessie-cookie
const api = axios.create({
    baseURL: '/api/admin',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Alleen de sessie-cookie (HttpOnly); de X-Admin-Key is voor scripts, niet voor de UI (#65)

// Health check
export const healthAPI = {
    check: () => api.get<AdminHealth>('/health'),
};

// LLM Configuration API
export const llmAPI = {
    getConfig: () => api.get<LLMConfig>('/llm/config'),
    updateConfig: (data: LLMConfig) => api.put<LLMConfig>('/llm/config', data),
    getModels: () => api.get<{ models: string[], error?: string }>('/llm/models'),
};

// System Prompts API
export const systemPromptsAPI = {
    getAll: () => api.get<SystemPrompt[]>('/prompts'),
    update: (naam: string, data: SystemPromptUpdate) => api.put<SystemPrompt>(`/prompts/${naam}`, data),
};

// Score types
export const scoreTypesAPI = {
    getAll: () => api.get<ScoreType[]>('/score-types'),
};

// Color schemas
export const colorSchemasAPI = {
    getAll: () => api.get<ColorSchema[]>('/color-schemas'),
    create: (data: Omit<ColorSchema, 'id' | 'is_actief'>) =>
        api.post<ColorSchema>('/color-schemas', data),
};

// Indicators
export const indicatorenAPI = {
    getAll: (params?: { search?: string; score_type?: string; ontologie_status?: string; limit?: number; offset?: number }) =>
        api.get<IndicatorenResponse>('/indicatoren', { params }),

    getOne: (uuid: string) =>
        api.get<Indicator>(`/indicatoren/${uuid}`),

    update: (uuid: string, data: IndicatorUpdate) =>
        api.put<Indicator>(`/indicatoren/${uuid}`, data),

    // Sprint 9 Track B: Ontologie Validatie
    valideer: (uuid: string, data: OntologieValidatiePayload) =>
        api.patch<Indicator>(`/indicatoren/${uuid}/valideer`, data),

    getOntologieStatus: () =>
        api.get<OntologieValidatieStatusResponse>('/ontologie/status'),
};

// Data Controle & Kwaliteit
export const dataControleAPI = {
    getDeduplicatieKandidaten: () => api.get<any[]>('/data-controle/deduplicatie/kandidaten'),
    mergeDeduplicatie: (data: { primary_uuid: string; duplicate_uuids: string[]; actie: string }) => 
        api.post('/data-controle/deduplicatie/merge', data),
    runDataLineage: () => api.get('/data-controle/run'),
    genereerOntologie: (indicator_uuids: string[]) => 
        api.post('/data-controle/acties/genereer-ontologie', { indicator_uuids }),
    herberekenStatistieken: (indicator_uuids: string[]) => 
        api.post('/data-controle/acties/herbereken-statistieken', { indicator_uuids }),
    markeerUitzondering: (indicator_uuids: string[]) =>
        api.post('/data-controle/deduplicatie/uitzondering', { indicator_uuids }),
};

// PostgREST Direct API
export const postgrestAPI = {
    getIndicatorenMutaties: (days: number = 30) => {
        const d = new Date();
        d.setDate(d.getDate() - days);
        const isoDate = d.toISOString();
        // Fetch items where created_at is newer than X days, or updated_at is newer than X days
        // PostgREST syntax for OR: or=(created_at.gte.2023-01-01,updated_at.gte.2023-01-01)
        return axios.get(`/api/data/indicatoren?or=(created_at.gte.${isoDate},updated_at.gte.${isoDate})&order=updated_at.desc`);
    }
};


// Hierarchy
export const hierarchyAPI = {
    getTree: (configId: number = 1) =>
        api.get<HierarchyResponse>('/hierarchie/tree', { params: { config_id: configId } }),
};

// Dashboard
export const dashboardAPI = {
    getStats: () => api.get<DashboardStats>('/dashboard/stats'),
    getQuadrants: (configId: number = 1) => api.get<QuadrantCoverage[]>('/dashboard/quadrants', { params: { config_id: configId } }),
    getIndicators: (params?: { search?: string; sort?: string; direction?: string; filter_status?: string; limit?: number; offset?: number }) =>
        api.get<DashboardIndicatorsResponse>('/dashboard/indicators', { params }),
    getExport: () => api.get('/dashboard/export', { responseType: 'blob' })
};

// Externe Kaartlagen (Sprint 18 Track B)
export const externeKaartlagenAPI = {
    getAll: () => api.get<{ lagen: import('../types').ExterneKaartlaag[]; totaal: number }>('/externe-lagen'),
    create: (data: import('../types').ExterneKaartlaagCreate) => api.post<{ id: number; naam: string; status: string }>('/externe-lagen', data),
    update: (id: number, data: import('../types').ExterneKaartlaagUpdate) => api.put<{ id: number; status: string }>(`/externe-lagen/${id}`, data),
    delete: (id: number) => api.delete<{ id: number; naam: string; status: string }>(`/externe-lagen/${id}`),
    getLokaalBestanden: () => api.get<{ bestanden: import('../types').LokaalBestand[]; totaal: number }>('/externe-lagen/lokale-bestanden'),
    upload: (file: File) => {
        const formData = new FormData();
        formData.append('bestand', file);
        return api.post<import('../types').LokaalBestand & { status: string }>('/externe-lagen/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

// Visualisatie - uses /api/visualisatie endpoints (separate prefix from /api/admin)
const vizApi = axios.create({
    baseURL: '/api/visualisatie',
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
});

export const visualisatieAPI = {
    // Admin endpoints (auth required)
    getPaletten: () => vizApi.get('/admin/paletten'),
    createPalette: (data: any) => vizApi.post('/admin/paletten', data),
    updatePalette: (id: number, data: any) => vizApi.put(`/admin/paletten/${id}`, data),
    getProfielen: () => vizApi.get('/admin/profielen'),
    createProfiel: (data: any) => vizApi.post('/admin/profielen', data),
    updateProfiel: (id: number, data: any) => vizApi.put(`/admin/profielen/${id}`, data),
    deleteProfiel: (id: number) => vizApi.delete(`/admin/profielen/${id}`),
    // Public endpoints (used by map frontend)
    getPublicPaletten: () => vizApi.get('/paletten'),
    getIndicatorConfig: (uuid: string) => vizApi.get(`/config/${uuid}`),
};

// Report API - used for UI reporting module
const reportApiClient = axios.create({
    baseURL: '/api/report',
    headers: { 'Content-Type': 'application/json' },
});

// Auth API - Used by AuthContext for Login/Logout
const authApiClient = axios.create({
    baseURL: '/api/admin/auth',
    withCredentials: true,
});

// Welke manieren van inloggen staan aan (#251): Keycloak (OIDC) en/of lokale accounts
export interface AuthConfig {
    oidc: boolean;
    lokaal: boolean;
    noodtoegang: boolean;
    gebruikersbeheer_url: string | null;
    account_url: string | null;
    demo?: boolean;   // OMNITWIN_OMGEVING=demo: demobalk (#245)
}

export type AuthUser = { id: string; username: string; is_admin: boolean; bron?: string };

// Inloggen via Keycloak: de backend doet de OIDC-flow en zet het sessiecookie (BFF, ADR 0008)
export const oidcInlogUrl = (terug = '/admin/dashboard') =>
    `/api/admin/auth/oidc/login?terug=${encodeURIComponent(terug)}`;

export const authAPI = {
    getConfig: () => authApiClient.get<AuthConfig>('/config'),
    login: (formData: URLSearchParams) => authApiClient.post<{ message: string; user: { id: string; username: string } }>('/login', formData, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }),
    // uitlog_url: bij een Keycloak-sessie daarheen, zodat ook Keycloak uitlogt
    logout: () => authApiClient.post<{ message: string; uitlog_url?: string | null }>('/logout'),
    getMe: () => authApiClient.get<{ authenticated: boolean; user: AuthUser | null }>('/me'),
    changePassword: (data: { old_password: string; new_password: string }) => authApiClient.post<{ message: string }>('/change-password', data),
};

export const reportAPI = {
    getData: (gebiedId: string) => reportApiClient.get<import('../types').ReportDataPayload>(`/data/${gebiedId}`),
    getNarrative: (gebiedId: string) => reportApiClient.get<import('../types').ReportNarrativeResponse>(`/narrative/${gebiedId}`),

    // Sjabloon C: Benchmark Vergelijker
    getBenchmark: (params: {
        gebied_a: string;
        mode: import('../types').BenchmarkMode;
        gebieden_b?: string[];
        referentie_gemeente?: string;
    }) => reportApiClient.get<import('../types').BenchmarkPayload>('/benchmark', {
        params: {
            gebied_a: params.gebied_a,
            mode: params.mode,
            gebieden_b: params.gebieden_b?.join(',') || undefined,
            referentie_gemeente: params.referentie_gemeente || undefined,
        }
    }),
    getBenchmarkNarrative: (params: {
        gebied_a: string;
        mode: import('../types').BenchmarkMode;
        gebieden_b?: string[];
        referentie_gemeente?: string;
    }) => reportApiClient.get<import('../types').BenchmarkNarrativeResponse>('/benchmark/narrative', {
        params: {
            gebied_a: params.gebied_a,
            mode: params.mode,
            gebieden_b: params.gebieden_b?.join(',') || undefined,
            referentie_gemeente: params.referentie_gemeente || undefined,
        }
    }),

    // Sjabloon A: Executive Summary
    getExecutive: (gebiedId: string) => reportApiClient.get<import('../types').ExecutivePayload>(`/executive/${gebiedId}`),

    // Sjabloon D: Multi-Gebiedsdossier
    getMultiGebied: (payload: { gebied_ids: string[]; referentie: string; gemeente_code?: string; deelgebied_naam?: string; thema?: string }) =>
        reportApiClient.post<any>('/multi-gebied', payload),
    getMultiGebiedGeoJSON: (payload: { gebied_ids: string[]; referentie: string; gemeente_code?: string; thema?: string }) =>
        reportApiClient.post<any>('/multi-gebied/geojson', payload),

    // Sjabloon E: Thema-Analyse
    getThemaAnalyse: (payload: { gebied_ids: string[]; referentie: string; gemeente_code?: string; deelgebied_naam?: string; categorie?: string; thema_naam?: string; onderdeel_naam?: string }) =>
        reportApiClient.post<any>('/thema-analyse', payload),
    getThemaAnalyseGeoJSON: (payload: { gebied_ids: string[]; referentie: string; gemeente_code?: string; categorie?: string; thema_naam?: string; onderdeel_naam?: string }) =>
        reportApiClient.post<any>('/thema-analyse/geojson', payload),

    // Sjabloon F: Woonplaats- & Deelgebiedsanalyse
    getDeelgebied: (payload: {
        gebied_ids: string[];
        referentie: string;
        gemeente_code?: string;
        deelgebied_naam?: string;
    }) => reportApiClient.post<any>('/deelgebied', payload),
    getDeelgebiedKaart: (payload: {
        gebied_ids: string[];
        referentie: string;
        gemeente_code?: string;
        deelgebied_naam?: string;
    }) => reportApiClient.post<{ svg: string }>('/deelgebied/kaart', payload),
};

// Public API client — voor gebieden/gemeenten endpoint (geen auth nodig)
const publicApi = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
});

// De eigen organisatie van deze instantie (#231): naam, gemeentecode(s), logo's, contact
export interface Organisatie {
    code: string;
    naam: string;
    korte_naam: string | null;
    oin: string | null;
    gemeente_codes: string[];
    standaard_gemeente_code: string | null;
    benchmark_provincie: string | null;
    contact_email: string | null;
    thema: string;
    logos: OrganisatieLogo[];
}

export interface OrganisatieLogo { pad: string; naam: string | null; rol: string }

// Wat de beheerder instelt (PUT /api/organisatie, #253); de eerste gemeentecode is de standaard
export interface OrganisatieInvoer {
    code: string;
    naam: string;
    korte_naam: string | null;
    oin: string | null;
    gemeente_codes: string[];
    benchmark_provincie: string | null;
    contact_email: string | null;
    thema: string;
    logos: OrganisatieLogo[];
}

// Thema uit static/css/themes, met de kleurtokens (#hex) van het lichte en donkere blok
export interface ThemaInfo {
    naam: string;
    titel: string;
    /** WCAG 2.1 AA volgens het kopcommentaar van het thema (#284); null/ontbrekend = onbekend */
    wcag_aa?: boolean | null;
    kleuren: { licht: Record<string, string>; donker: Record<string, string> };
}

export interface OrganisatieExport {
    formaat: 'd-omnitwin/organisatie';
    versie: 1;
    organisatie: OrganisatieInvoer;
    [extra: string]: unknown;
}

// Lezen is publiek; instellen alleen voor beheerders (sessiecookie, vereis_admin)
const organisatieBeheer = axios.create({
    baseURL: '/api/organisatie',
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
});

export const organisatieAPI = {
    get: () => publicApi.get<Organisatie>('/organisatie'),
    zet: (data: OrganisatieInvoer) => organisatieBeheer.put<Organisatie>('', data),
    themas: () => organisatieBeheer.get<ThemaInfo[]>('/themas'),
    logos: () => organisatieBeheer.get<string[]>('/logos'),
    exporteer: () => organisatieBeheer.get<OrganisatieExport>('/export'),
    importeer: (data: unknown) => organisatieBeheer.post<Organisatie>('/import', data),
};

// Gemeenten en gebieden via PostgREST (/api/data), zoals de hoofdapp.
// Response wordt omgezet naar de eerdere vorm { gemeenten|gebieden, totaal }.
export const gebiedenAPI = {
    getGemeenten: async () => {
        const res = await publicApi.get<{ code: string; naam: string; provincie?: string }[]>('/data/gemeenten', {
            params: { order: 'naam.asc' }
        });
        return { ...res, data: { gemeenten: res.data, totaal: res.data.length } };
    },
    zoekGebieden: async (q: string) => {
        // Tekens die de PostgREST or-filter syntax breken weglaten
        const term = q.replace(/[,()*"\\]/g, ' ').trim();
        const res = await publicApi.get<{ id: string; naam: string; gemeente_code: string | null; gebiedstype_id: string | null }[]>('/data/gebieden', {
            params: {
                select: 'id,naam,gemeente_code,gebiedstype_id',
                or: `(naam.ilike.*${term}*,id.ilike.*${term}*)`,
                order: 'naam.asc',
                limit: 20
            }
        });
        const gebieden: import('../types').GebiedListItem[] = res.data.map(g => ({
            id: g.id,
            naam: g.naam,
            type: g.gebiedstype_id ?? ''
        }));
        return { ...res, data: { gebieden, totaal: gebieden.length } };
    },
};

export const aiAPI = {
    searchKompas: (q: string, limit: number = 5) =>
        publicApi.get<any[]>('/ai/kompas/search', { params: { q, limit } }),
};

export default api;
