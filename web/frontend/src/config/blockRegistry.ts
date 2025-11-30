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

// Import blocks
import { Activity, FolderOpen, ListTodo, Bot, Clock, DollarSign } from 'lucide-react';
import { SystemStatusBlock } from '../components/blocks/SystemStatusBlock';
import { ActiveProjectsBlock } from '../components/blocks/ActiveProjectsBlock';
import { QueueOverviewBlock } from '../components/blocks/QueueOverviewBlock';
import { AgentStatusBlock } from '../components/blocks/AgentStatusBlock';
import { RecentActivityBlock } from '../components/blocks/RecentActivityBlock';
import { CostTrackerBlock } from '../components/blocks/CostTrackerBlock';

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
  'system-status': {
    id: 'system-status',
    name: 'System Status',
    description: 'Queue depth, active agents, system health, and uptime',
    icon: Activity,
    component: SystemStatusBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
  'active-projects': {
    id: 'active-projects',
    name: 'Active Projects',
    description: 'List of enabled projects with status and issue counts',
    icon: FolderOpen,
    component: ActiveProjectsBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
  'queue-overview': {
    id: 'queue-overview',
    name: 'Queue Overview',
    description: 'All tasks across projects with status breakdown',
    icon: ListTodo,
    component: QueueOverviewBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
  'agent-status': {
    id: 'agent-status',
    name: 'Agent Status',
    description: 'List of agents with current tasks and resource usage',
    icon: Bot,
    component: AgentStatusBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
  'recent-activity': {
    id: 'recent-activity',
    name: 'Recent Activity',
    description: 'Timeline of recent events across all projects',
    icon: Clock,
    component: RecentActivityBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
  'cost-tracker': {
    id: 'cost-tracker',
    name: 'Cost Tracker',
    description: 'Spending metrics and budget progress',
    icon: DollarSign,
    component: CostTrackerBlock,
    availableIn: ['dashboard'],
    requiresView: 'overall',
  },
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
