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

// API client with auth header and cookie support
const api = axios.create({
    baseURL: '/api/admin',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add admin key to all requests
api.interceptors.request.use((config) => {
    const adminKey = localStorage.getItem('adminKey') || process.env.REACT_APP_ADMIN_KEY;
    if (adminKey) {
        config.headers['X-Admin-Key'] = adminKey;
    }
    return config;
});

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

// Visualisatie - uses /api/visualisatie endpoints (separate prefix from /api/admin)
const vizApi = axios.create({
    baseURL: '/api/visualisatie',
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
});

// Add admin key to viz requests
vizApi.interceptors.request.use((config) => {
    const adminKey = localStorage.getItem('adminKey') || process.env.REACT_APP_ADMIN_KEY;
    if (adminKey) {
        config.headers['X-Admin-Key'] = adminKey;
    }
    return config;
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

export const authAPI = {
    login: (formData: URLSearchParams) => authApiClient.post<{ message: string; user: { id: string; username: string } }>('/login', formData, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }),
    logout: () => authApiClient.post<{ message: string }>('/logout'),
    getMe: () => authApiClient.get<{ authenticated: boolean; user: { id: string; username: string; is_admin: boolean } | null }>('/me'),
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
    getMultiGebied: (payload: { gebied_ids: string[]; referentie: string; gemeente_code: string; deelgebied_naam?: string; thema?: string }) =>
        reportApiClient.post<any>('/multi-gebied', payload),
    getMultiGebiedGeoJSON: (payload: { gebied_ids: string[]; referentie: string; gemeente_code: string; thema?: string }) =>
        reportApiClient.post<any>('/multi-gebied/geojson', payload),
};

// Public API client — voor gebieden/gemeenten endpoint (geen auth nodig)
const publicApi = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
});

export const gebiedenAPI = {
    getGemeenten: () => publicApi.get<{ gemeenten: { code: string; naam: string; provincie?: string }[]; totaal: number }>('/gemeenten'),
    zoekGebieden: (q: string) =>
        publicApi.get<{ gebieden: import('../types').GebiedListItem[]; totaal: number }>('/gebieden/zoek', {
            params: { q }
        }),
};

export default api;
