/**
 * Theme Configuration
 *
 * Central theme constants and utilities
 */

// Animation durations (all 200-300ms for snappy feel)
export const ANIMATION_DURATION = {
  fast: 200,
  normal: 250,
  slow: 300,
} as const;

// Color palette (matches Tailwind config)
export const COLORS = {
  primary: {
    main: '#6366f1', // primary-500
    light: '#a5b4fc', // primary-300
    dark: '#4338ca', // primary-700
  },
  accent: {
    main: '#3b82f6', // accent-500
    light: '#93c5fd', // accent-300
    dark: '#1d4ed8', // accent-700
  },
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
} as const;

// Z-index layers
export const Z_INDEX = {
  base: 1,
  dropdown: 10,
  sticky: 20,
  modal: 30,
  popover: 40,
  tooltip: 50,
  toast: 100,
} as const;

// Breakpoints (matches Tailwind defaults)
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

// Layout constants
export const LAYOUT = {
  sidebarWidth: 240,
  headerHeight: 64,
  tabBarHeight: 48,
  viewSelectorHeight: 40,
  blockGap: 16,
  blockPadding: 24,
} as const;

// Animation variants for Framer Motion
export const MOTION_VARIANTS = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: ANIMATION_DURATION.fast / 1000 },
  },
  slideIn: {
    initial: { y: -10, opacity: 0 },
    animate: { y: 0, opacity: 1 },
    exit: { y: -10, opacity: 0 },
    transition: { duration: ANIMATION_DURATION.normal / 1000 },
  },
  scaleIn: {
    initial: { scale: 0.95, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
    exit: { scale: 0.95, opacity: 0 },
    transition: { duration: ANIMATION_DURATION.fast / 1000 },
  },
} as const;

// Theme utility functions
export function getThemeClass(isDark: boolean): string {
  return isDark ? 'dark' : 'light';
}

export function shouldReduceMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
