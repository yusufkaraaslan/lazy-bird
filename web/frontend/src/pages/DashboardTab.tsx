/**
 * DashboardTab Page
 *
 * Main dashboard with modular blocks
 * Supports Overall, Project, and Agent views
 */

import { ViewSelector } from '../components/ViewSelector';
import { BlockContainer } from '../components/BlockContainer';

export function DashboardTab() {
  return (
    <div className="flex flex-col h-full">
      <ViewSelector />
      <div className="flex-1 overflow-y-auto">
        <BlockContainer />
      </div>
    </div>
  );
}
