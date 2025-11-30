/**
 * Block Registry
 *
 * Central registry for all plugin blocks.
 * This enables the modular plugin/card system.
 */

import type { ComponentType } from 'react';
import type { LucideIcon } from 'lucide-react';

export interface BlockDefinition {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  component: ComponentType<BlockProps>;
  defaultConfig?: Record<string, any>;
  availableIn: ('dashboard' | 'analytics' | 'settings')[];
  requiresView?: 'overall' | 'project' | 'agent';
}

export interface BlockProps {
  blockId: string;
  config?: Record<string, any>;
  onRemove?: () => void;
  onConfigChange?: (config: Record<string, any>) => void;
}

/**
 * Block Registry
 *
 * To add a new block:
 * 1. Create your block component in src/components/blocks/YourBlock.tsx
 * 2. Import it here
 * 3. Register it in the BLOCK_REGISTRY object below
 * 4. It will automatically appear in the "Add Block" dropdown!
 */
export const BLOCK_REGISTRY: Record<string, BlockDefinition> = {
  // Dashboard blocks will be added as they're implemented
  // Example:
  // 'system-status': {
  //   id: 'system-status',
  //   name: 'System Status',
  //   description: 'Shows queue depth, active agents, system health',
  //   icon: Activity,
  //   component: SystemStatusBlock,
  //   availableIn: ['dashboard'],
  //   requiresView: 'overall',
  // },
};

/**
 * Get blocks available for a specific tab and view
 */
export function getAvailableBlocks(
  tab: 'dashboard' | 'analytics' | 'settings',
  view?: 'overall' | 'project' | 'agent'
): BlockDefinition[] {
  return Object.values(BLOCK_REGISTRY).filter(block => {
    const isAvailableInTab = block.availableIn.includes(tab);
    const matchesView = !block.requiresView || !view || block.requiresView === view;
    return isAvailableInTab && matchesView;
  });
}

/**
 * Get block definition by ID
 */
export function getBlockDefinition(blockId: string): BlockDefinition | undefined {
  return BLOCK_REGISTRY[blockId];
}
