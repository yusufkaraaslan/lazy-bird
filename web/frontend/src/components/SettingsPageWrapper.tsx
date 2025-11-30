/**
 * SettingsPageWrapper Component
 *
 * Wrapper for settings pages to provide consistent layout
 */

import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

interface SettingsPageWrapperProps {
  children: ReactNode;
  showBackButton?: boolean;
}

export function SettingsPageWrapper({ children, showBackButton = true }: SettingsPageWrapperProps) {
  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {showBackButton && (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-3">
          <Link
            to="/"
            onClick={(e) => {
              e.preventDefault();
              window.history.back();
            }}
            className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Back</span>
          </Link>
        </div>
      )}
      <div className="flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
