/**
 * Theme Store
 *
 * Manages theme state: dark/light mode, animations enabled
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeState {
  // Theme settings
  mode: ThemeMode;
  animationsEnabled: boolean;

  // Actions
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
  toggleAnimations: () => void;

  // Computed
  isDark: () => boolean;
}

// Check system preference
const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // Initial state
      mode: 'system',
      animationsEnabled: true,

      // Actions
      setMode: (mode) => {
        set({ mode });

        // Apply theme to document
        if (typeof window !== 'undefined') {
          const isDark = mode === 'dark' || (mode === 'system' && getSystemTheme() === 'dark');
          document.documentElement.classList.toggle('dark', isDark);
        }
      },

      toggleMode: () => {
        const current = get().mode;
        const next: ThemeMode = current === 'light' ? 'dark' : current === 'dark' ? 'system' : 'light';
        get().setMode(next);
      },

      toggleAnimations: () => {
        set({ animationsEnabled: !get().animationsEnabled });
      },

      // Computed
      isDark: () => {
        const mode = get().mode;
        return mode === 'dark' || (mode === 'system' && getSystemTheme() === 'dark');
      },
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({
        mode: state.mode,
        animationsEnabled: state.animationsEnabled,
      }),
      onRehydrateStorage: () => (state) => {
        // Apply theme on hydration
        if (state) {
          const isDark = state.mode === 'dark' || (state.mode === 'system' && getSystemTheme() === 'dark');
          document.documentElement.classList.toggle('dark', isDark);
        }
      },
    }
  )
);

// Listen to system theme changes
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const state = useThemeStore.getState();
    if (state.mode === 'system') {
      state.setMode('system'); // Re-apply to update DOM
    }
  });
}
