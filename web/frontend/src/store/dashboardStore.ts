/**
 * Dashboard Store
 *
 * Manages dashboard state: active tab, current view, visible blocks, and layout
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type TabType = 'dashboard' | 'analytics' | 'settings';
export type ViewType = 'overall' | 'project' | 'agent';

export interface BlockConfig {
  id: string;
  type: string;
  order: number;
  visible: boolean;
  config?: Record<string, any>;
}

interface DashboardState {
  // Current navigation
  activeTab: TabType;
  currentView: ViewType;
  selectedProjectId: string | null;

  // Block management
  visibleBlocks: BlockConfig[];

  // Actions
  setActiveTab: (tab: TabType) => void;
  setCurrentView: (view: ViewType) => void;
  setSelectedProjectId: (projectId: string | null) => void;

  // Block actions
  addBlock: (blockType: string) => void;
  removeBlock: (blockId: string) => void;
  reorderBlocks: (blockIds: string[]) => void;
  toggleBlockVisibility: (blockId: string) => void;
  updateBlockConfig: (blockId: string, config: Record<string, any>) => void;

  // Layout presets
  saveLayoutPreset: (name: string) => void;
  loadLayoutPreset: (name: string) => void;
  resetLayout: () => void;
}

// Default blocks - empty for now, will be populated as blocks are implemented in later issues
const defaultBlocks: BlockConfig[] = [];

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => ({
      // Initial state
      activeTab: 'dashboard',
      currentView: 'overall',
      selectedProjectId: null,
      visibleBlocks: defaultBlocks,

      // Tab/View navigation
      setActiveTab: (tab) => set({ activeTab: tab }),

      setCurrentView: (view) => set({ currentView: view }),

      setSelectedProjectId: (projectId) => set({ selectedProjectId: projectId }),

      // Block management
      addBlock: (blockType) => {
        const blocks = get().visibleBlocks;
        const maxOrder = blocks.length > 0 ? Math.max(...blocks.map(b => b.order)) : -1;
        const newBlock: BlockConfig = {
          id: `${blockType}-${Date.now()}`,
          type: blockType,
          order: maxOrder + 1,
          visible: true,
        };
        set({ visibleBlocks: [...blocks, newBlock] });
      },

      removeBlock: (blockId) => {
        set({
          visibleBlocks: get().visibleBlocks.filter(b => b.id !== blockId)
        });
      },

      reorderBlocks: (blockIds) => {
        const blocks = get().visibleBlocks;
        const reordered = blockIds.map((id, index) => {
          const block = blocks.find(b => b.id === id);
          return block ? { ...block, order: index } : null;
        }).filter(Boolean) as BlockConfig[];
        set({ visibleBlocks: reordered });
      },

      toggleBlockVisibility: (blockId) => {
        set({
          visibleBlocks: get().visibleBlocks.map(b =>
            b.id === blockId ? { ...b, visible: !b.visible } : b
          )
        });
      },

      updateBlockConfig: (blockId, config) => {
        set({
          visibleBlocks: get().visibleBlocks.map(b =>
            b.id === blockId ? { ...b, config: { ...b.config, ...config } } : b
          )
        });
      },

      // Layout presets (simplified for now)
      saveLayoutPreset: (name) => {
        const blocks = get().visibleBlocks;
        localStorage.setItem(`layout-preset-${name}`, JSON.stringify(blocks));
      },

      loadLayoutPreset: (name) => {
        const stored = localStorage.getItem(`layout-preset-${name}`);
        if (stored) {
          set({ visibleBlocks: JSON.parse(stored) });
        }
      },

      resetLayout: () => {
        set({ visibleBlocks: defaultBlocks });
      },
    }),
    {
      name: 'dashboard-storage', // LocalStorage key
      partialize: (state) => ({
        // Only persist these fields
        activeTab: state.activeTab,
        currentView: state.currentView,
        selectedProjectId: state.selectedProjectId,
        visibleBlocks: state.visibleBlocks,
      }),
    }
  )
);
