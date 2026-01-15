/**
 * Strategic Build Planner - Main App
 * Two-phase APQP workflow application
 */

import { useState } from 'react';
import { FileSearch, FileCheck } from 'lucide-react';
import PreMeetingPrep from './pages/PreMeetingPrep';
import PlanBuilder from './pages/PlanBuilder';

const PHASES = [
  {
    id: 'phase1',
    label: 'Phase 1: Pre-Meeting Prep',
    description: 'Generate checklist from specs',
    icon: FileSearch,
    component: PreMeetingPrep,
  },
  {
    id: 'phase2',
    label: 'Phase 2: Post-Meeting Review',
    description: 'Analyze transcript & grade',
    icon: FileCheck,
    component: PlanBuilder,
  },
];

function App() {
  const [activePhase, setActivePhase] = useState('phase1');

  const ActiveComponent = PHASES.find((p) => p.id === activePhase)?.component || PreMeetingPrep;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Phase Selector Tab Bar */}
      <div className="bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-4">
            {PHASES.map((phase) => (
              <button
                key={phase.id}
                onClick={() => setActivePhase(phase.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                  ${
                    activePhase === phase.id
                      ? 'border-primary-500 text-white'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
                  }
                `}
              >
                <phase.icon className="h-4 w-4" />
                <span>{phase.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active Phase Content */}
      <ActiveComponent />
    </div>
  );
}

export default App;
