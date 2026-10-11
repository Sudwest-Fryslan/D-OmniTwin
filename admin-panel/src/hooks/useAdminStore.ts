import { create } from 'zustand';
import type { Indicator, ColorSchema, HierarchyNode, Polariteit } from '../types';
import type { AuthConfig, AuthUser } from '../services/api';

// Zonder antwoord van /api/admin/auth/config: lokaal inloggen, zoals vóór Keycloak
export const STANDAARD_AUTH_CONFIG: AuthConfig = {
    oidc: false, lokaal: true, noodtoegang: false, gebruikersbeheer_url: null, account_url: null, demo: false,
};

interface AdminStore {
    // Auth
    isAuthenticated: boolean;
    user: AuthUser | null;
    setAuthenticated: (status: boolean, user?: AuthUser) => void;
    logout: () => void;
    authConfig: AuthConfig;
    setAuthConfig: (config: AuthConfig) => void;

    // Data
    selectedIndicator: Indicator | null;
    setSelectedIndicator: (indicator: Indicator | null) => void;

    colorSchemas: ColorSchema[];
    setColorSchemas: (schemas: ColorSchema[]) => void;

    polariteiten: Polariteit[];
    setPolariteiten: (lijst: Polariteit[]) => void;

    hierarchyTree: HierarchyNode[];
    setHierarchyTree: (tree: HierarchyNode[]) => void;

    // UI State
    sidebarOpen: boolean;
    toggleSidebar: () => void;

    // Data Kwaliteit State
    deduplicatieKandidaten: any[] | null;
    setDeduplicatieKandidaten: (kandidaten: any[] | null) => void;
}

export const useAdminStore = create<AdminStore>((set) => ({
    // Auth - Initieel false, wordt door App.tsx/getMe gecontroleerd
    isAuthenticated: false,
    user: null,
    setAuthenticated: (status, user) => set({ isAuthenticated: status, user: user || null }),
    logout: () => set({ isAuthenticated: false, user: null }),
    authConfig: STANDAARD_AUTH_CONFIG,
    setAuthConfig: (authConfig) => set({ authConfig }),

    // Data
    selectedIndicator: null,
    setSelectedIndicator: (indicator) => set({ selectedIndicator: indicator }),

    colorSchemas: [],
    setColorSchemas: (schemas) => set({ colorSchemas: schemas }),

    polariteiten: [],
    setPolariteiten: (lijst) => set({ polariteiten: lijst }),

    hierarchyTree: [],
    setHierarchyTree: (tree) => set({ hierarchyTree: tree }),

    // UI State
    sidebarOpen: true,
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

    // Data Kwaliteit State
    deduplicatieKandidaten: null,
    setDeduplicatieKandidaten: (k) => set({ deduplicatieKandidaten: k }),
}));
