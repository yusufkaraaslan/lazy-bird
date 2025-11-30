/**
 * BlockContainer Component
 *
 * Container for modular blocks with drag-and-drop reordering
 * Displays blocks based on current tab and view
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Plus, GripVertical, X, Settings } from 'lucide-react';
import { useDashboardStore } from '../store';
import type { BlockConfig } from '../store';
import { useThemeStore } from '../store';
import { getAvailableBlocks, getBlockDefinition } from '../config/blockRegistry';

interface SortableBlockProps {
  block: BlockConfig;
  onRemove: () => void;
  onConfigure: () => void;
}

function SortableBlock({ block, onRemove, onConfigure }: SortableBlockProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: block.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const blockDefinition = getBlockDefinition(block.type);

  if (!blockDefinition) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-sm text-red-600 dark:text-red-400">
          Block type "{block.type}" not found in registry
        </p>
      </div>
    );
  }

  const BlockComponent = blockDefinition.component;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        group relative bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700
        shadow-card hover:shadow-card-hover transition-shadow duration-200
        ${isDragging ? 'opacity-50 z-50' : ''}
      `}
    >
      {/* Header with drag handle and controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <GripVertical className="w-4 h-4 text-gray-400" />
          </button>
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {blockDefinition.name}
          </h3>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onConfigure}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Configure block"
          >
            <Settings className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>
          <button
            onClick={onRemove}
            className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
            title="Remove block"
          >
            <X className="w-4 h-4 text-red-500 dark:text-red-400" />
          </button>
        </div>
      </div>

      {/* Block content */}
      <div className="p-4">
        <BlockComponent
          blockId={block.id}
          config={block.config}
          onRemove={onRemove}
          onConfigChange={(newConfig) => {
            // Will be wired up via store
            console.log('Config change:', block.id, newConfig);
          }}
        />
      </div>
    </div>
  );
}

export function BlockContainer() {
  const activeTab = useDashboardStore((state) => state.activeTab);
  const currentView = useDashboardStore((state) => state.currentView);
  const visibleBlocks = useDashboardStore((state) => state.visibleBlocks);
  const addBlock = useDashboardStore((state) => state.addBlock);
  const removeBlock = useDashboardStore((state) => state.removeBlock);
  const reorderBlocks = useDashboardStore((state) => state.reorderBlocks);
  const animationsEnabled = useThemeStore((state) => state.animationsEnabled);

  const [addBlockMenuOpen, setAddBlockMenuOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Get available blocks for current tab/view
  const availableBlocks = getAvailableBlocks(activeTab, currentView);

  // Filter visible blocks to show only those visible in current context
  const displayedBlocks = visibleBlocks
    .filter((block) => block.visible)
    .sort((a, b) => a.order - b.order);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = displayedBlocks.findIndex((b) => b.id === active.id);
      const newIndex = displayedBlocks.findIndex((b) => b.id === over.id);

      const reordered = arrayMove(displayedBlocks, oldIndex, newIndex);
      reorderBlocks(reordered.map((b) => b.id));
    }
  };

  return (
    <div className="p-6 space-y-4">
      {/* Blocks */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={displayedBlocks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
        >
          {displayedBlocks.map((block) => (
            <SortableBlock
              key={block.id}
              block={block}
              onRemove={() => removeBlock(block.id)}
              onConfigure={() => {
                // TODO: Open configuration modal
                console.log('Configure block:', block.id);
              }}
            />
          ))}
        </SortableContext>
      </DndContext>

      {/* Empty state */}
      {displayedBlocks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
          <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <Plus className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
            No blocks yet
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Add your first block to get started
          </p>
        </div>
      )}

      {/* Add Block Button */}
      <div className="relative">
        <button
          onClick={() => setAddBlockMenuOpen(!addBlockMenuOpen)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-primary-400 dark:hover:border-primary-500 hover:text-primary-600 dark:hover:text-primary-400 transition-colors duration-200 w-full justify-center"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm font-medium">Add Block</span>
        </button>

        {/* Add Block Menu */}
        {addBlockMenuOpen && availableBlocks.length > 0 && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-10"
              onClick={() => setAddBlockMenuOpen(false)}
            />

            {/* Menu */}
            <motion.div
              initial={animationsEnabled ? { opacity: 0, y: -10 } : {}}
              animate={animationsEnabled ? { opacity: 1, y: 0 } : {}}
              className="absolute left-0 right-0 mt-2 rounded-lg bg-white dark:bg-gray-700 shadow-lg border border-gray-200 dark:border-gray-600 z-20 max-h-96 overflow-y-auto"
            >
              <div className="py-1">
                {availableBlocks.map((blockDef) => {
                  const Icon = blockDef.icon;
                  return (
                    <button
                      key={blockDef.id}
                      onClick={() => {
                        addBlock(blockDef.id);
                        setAddBlockMenuOpen(false);
                      }}
                      className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors duration-150"
                    >
                      <Icon className="w-5 h-5 text-primary-500 mt-0.5" />
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {blockDef.name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {blockDef.description}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}

        {addBlockMenuOpen && availableBlocks.length === 0 && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setAddBlockMenuOpen(false)}
            />
            <motion.div
              initial={animationsEnabled ? { opacity: 0, y: -10 } : {}}
              animate={animationsEnabled ? { opacity: 1, y: 0 } : {}}
              className="absolute left-0 right-0 mt-2 rounded-lg bg-white dark:bg-gray-700 shadow-lg border border-gray-200 dark:border-gray-600 z-20 p-4"
            >
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                No blocks available for this view
              </p>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
