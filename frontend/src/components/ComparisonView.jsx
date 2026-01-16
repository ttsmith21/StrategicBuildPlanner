/**
 * ComparisonView Component
 * Display comparison results between quote assumptions and checklist requirements
 */

import { useState } from 'react';
import {
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  FileQuestion,
  ListTodo,
  ChevronDown,
  ChevronRight,
  Merge,
} from 'lucide-react';

// Severity badge colors
const SEVERITY_COLORS = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

export default function ComparisonView({
  comparison,
  mergePreview,
  onRequestMerge,
  isLoading = false,
  disabled = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    conflicts: true,
    matches: false,
    quoteOnly: false,
    checklistOnly: false,
  });

  if (!comparison) {
    return null;
  }

  const { statistics } = comparison;

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const renderSection = (
    id,
    title,
    icon,
    items,
    bgColor,
    borderColor,
    renderItem
  ) => {
    const isExpanded = expandedSections[id];
    const count = items?.length || 0;

    return (
      <div className={`border rounded-lg overflow-hidden ${borderColor}`}>
        <button
          onClick={() => toggleSection(id)}
          className={`w-full flex items-center gap-3 px-4 py-3 ${bgColor} hover:opacity-90 transition-opacity`}
        >
          {icon}
          <span className="font-medium flex-1 text-left">{title}</span>
          <span className="text-sm font-semibold px-2 py-0.5 rounded-full bg-white/50">
            {count}
          </span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>

        {isExpanded && items && items.length > 0 && (
          <div className="divide-y divide-gray-100 bg-white">
            {items.map((item, index) => (
              <div key={index} className="p-4">
                {renderItem(item)}
              </div>
            ))}
          </div>
        )}

        {isExpanded && (!items || items.length === 0) && (
          <div className="p-4 text-center text-sm text-gray-500 bg-white">
            No items in this category
          </div>
        )}
      </div>
    );
  };

  // Render conflict item
  const renderConflict = (conflict) => (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded border ${
            SEVERITY_COLORS[conflict.severity] || SEVERITY_COLORS.medium
          }`}
        >
          {conflict.severity?.toUpperCase()}
        </span>
        <span className="text-xs text-gray-500 uppercase tracking-wider">
          {conflict.category}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-red-50 rounded-lg border border-red-100">
          <p className="text-xs font-medium text-red-600 mb-1">Quote Says:</p>
          <p className="text-sm text-red-900">{conflict.quote_assumption}</p>
        </div>
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
          <p className="text-xs font-medium text-blue-600 mb-1">Customer Requires:</p>
          <p className="text-sm text-blue-900">{conflict.checklist_requirement}</p>
        </div>
      </div>

      <div className="p-3 bg-gray-50 rounded-lg">
        <p className="text-xs font-medium text-gray-600 mb-1">Conflict:</p>
        <p className="text-sm text-gray-800">{conflict.conflict_description}</p>
      </div>

      {conflict.resolution_suggestion && (
        <div className="p-3 bg-green-50 rounded-lg border border-green-100">
          <p className="text-xs font-medium text-green-600 mb-1">Suggested Resolution:</p>
          <p className="text-sm text-green-800">{conflict.resolution_suggestion}</p>
        </div>
      )}
    </div>
  );

  // Render match item
  const renderMatch = (match) => (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{match.category}</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-medium text-gray-600 mb-1">Quote:</p>
          <p className="text-sm text-gray-800">{match.quote_assumption}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-600 mb-1">Requirement:</p>
          <p className="text-sm text-gray-800">{match.checklist_requirement}</p>
        </div>
      </div>
      {match.alignment_notes && (
        <p className="text-xs text-green-600 italic">{match.alignment_notes}</p>
      )}
    </div>
  );

  // Render quote-only item
  const renderQuoteOnly = (item) => (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{item.category}</p>
      <p className="text-sm text-gray-800">{item.assumption}</p>
      {item.recommendation && (
        <p className="text-xs text-blue-600 italic">
          Recommendation: {item.recommendation}
        </p>
      )}
    </div>
  );

  // Render checklist-only item
  const renderChecklistOnly = (item) => (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{item.category}</p>
      <p className="text-sm text-gray-800">{item.requirement}</p>
      {item.action_needed && (
        <p className="text-xs text-orange-600 italic">
          Action: {item.action_needed}
        </p>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Comparison Results
            </h3>
            <p className="text-sm text-gray-500">
              {comparison.vendor_name && `Vendor: ${comparison.vendor_name}`}
              {comparison.quote_number && ` • Quote #${comparison.quote_number}`}
            </p>
          </div>

          {onRequestMerge && (
            <button
              onClick={onRequestMerge}
              disabled={disabled || isLoading || statistics?.total_conflicts > 0}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg font-medium
                ${
                  statistics?.total_conflicts > 0
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }
                disabled:opacity-50
              `}
            >
              <Merge className="h-4 w-4" />
              {statistics?.total_conflicts > 0
                ? 'Resolve Conflicts First'
                : 'Generate Merge Preview'}
            </button>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-red-50 border border-red-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold text-red-700">
                {statistics?.total_conflicts || 0}
              </span>
            </div>
            <p className="text-sm text-red-600 mt-1">Conflicts</p>
            {statistics?.high_severity_conflicts > 0 && (
              <p className="text-xs text-red-500 mt-1">
                {statistics.high_severity_conflicts} high severity
              </p>
            )}
          </div>

          <div className="p-4 rounded-lg bg-green-50 border border-green-200">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-2xl font-bold text-green-700">
                {statistics?.total_matches || 0}
              </span>
            </div>
            <p className="text-sm text-green-600 mt-1">Matches</p>
          </div>

          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
            <div className="flex items-center gap-2">
              <FileQuestion className="h-5 w-5 text-blue-500" />
              <span className="text-2xl font-bold text-blue-700">
                {statistics?.quote_only_count || 0}
              </span>
            </div>
            <p className="text-sm text-blue-600 mt-1">Quote Only</p>
          </div>

          <div className="p-4 rounded-lg bg-orange-50 border border-orange-200">
            <div className="flex items-center gap-2">
              <ListTodo className="h-5 w-5 text-orange-500" />
              <span className="text-2xl font-bold text-orange-700">
                {statistics?.checklist_only_count || 0}
              </span>
            </div>
            <p className="text-sm text-orange-600 mt-1">Unaddressed</p>
          </div>
        </div>

        {/* High Severity Warning */}
        {statistics?.high_severity_conflicts > 0 && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">
                {statistics.high_severity_conflicts} High Severity Conflict
                {statistics.high_severity_conflicts > 1 ? 's' : ''} Found
              </p>
              <p className="text-xs text-red-600 mt-1">
                These must be resolved with the vendor before proceeding.
                Review the conflicts below for details.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Detailed Sections */}
      <div className="space-y-3">
        {/* Conflicts - Always show first if any */}
        {renderSection(
          'conflicts',
          'Conflicts',
          <AlertCircle className="h-5 w-5 text-red-600" />,
          comparison.conflicts,
          'bg-red-50',
          'border-red-200',
          renderConflict
        )}

        {/* Matches */}
        {renderSection(
          'matches',
          'Matches',
          <CheckCircle className="h-5 w-5 text-green-600" />,
          comparison.matches,
          'bg-green-50',
          'border-green-200',
          renderMatch
        )}

        {/* Quote Only */}
        {renderSection(
          'quoteOnly',
          'Quote-Only Assumptions',
          <FileQuestion className="h-5 w-5 text-blue-600" />,
          comparison.quote_only,
          'bg-blue-50',
          'border-blue-200',
          renderQuoteOnly
        )}

        {/* Checklist Only */}
        {renderSection(
          'checklistOnly',
          'Unaddressed Requirements',
          <ListTodo className="h-5 w-5 text-orange-600" />,
          comparison.checklist_only,
          'bg-orange-50',
          'border-orange-200',
          renderChecklistOnly
        )}
      </div>

      {/* Merge Preview */}
      {mergePreview && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Merge Preview
          </h3>

          <div className="p-4 bg-green-50 border border-green-200 rounded-lg mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <p className="font-medium text-green-700">
                {mergePreview.merge_summary?.ready_to_merge
                  ? 'Ready to publish - no conflicts!'
                  : 'Review required before publishing'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500">Total Matches</p>
              <p className="font-semibold text-gray-900">
                {mergePreview.merge_summary?.total_matches || 0}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500">Quote Additions</p>
              <p className="font-semibold text-gray-900">
                {mergePreview.merge_summary?.quote_additions || 0}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
