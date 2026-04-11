import { create } from 'zustand';
import type { Indicator, ColorSchema, HierarchyNode, ScoreType } from '../types';

interface AdminStore {
    // Auth
    isAuthenticated: boolean;
    user: { id: string; username: string; is_admin: boolean } | null;
    setAuthenticated: (status: boolean, user?: { id: string; username: string; is_admin: boolean }) => void;
    logout: () => void;

    // Data
    selectedIndicator: Indicator | null;
    setSelectedIndicator: (indicator: Indicator | null) => void;

    colorSchemas: ColorSchema[];
    setColorSchemas: (schemas: ColorSchema[]) => void;

    scoreTypes: ScoreType[];
    setScoreTypes: (types: ScoreType[]) => void;

    hierarchyTree: HierarchyNode[];
    setHierarchyTree: (tree: HierarchyNode[]) => void;

    // UI State
    sidebarOpen: boolean;
    toggleSidebar: () => void;
}

export const useAdminStore = create<AdminStore>((set) => ({
    // Auth - Initieel false, wordt door App.tsx/getMe gecontroleerd
    isAuthenticated: false,
    user: null,
    setAuthenticated: (status, user) => set({ isAuthenticated: status, user: user || null }),
    logout: () => set({ isAuthenticated: false, user: null }),

    // Data
    selectedIndicator: null,
    setSelectedIndicator: (indicator) => set({ selectedIndicator: indicator }),

    colorSchemas: [],
    setColorSchemas: (schemas) => set({ colorSchemas: schemas }),

    scoreTypes: [],
    setScoreTypes: (types) => set({ scoreTypes: types }),

    hierarchyTree: [],
    setHierarchyTree: (tree) => set({ hierarchyTree: tree }),

    // UI State
    sidebarOpen: true,
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
