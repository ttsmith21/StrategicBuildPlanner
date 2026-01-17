/**
 * ConflictResolution Component
 * Interactive resolution interface for a single quote vs. checklist conflict
 */

import { useState } from 'react';
import {
  FileText,
  FileCheck,
  Lightbulb,
  ClipboardList,
  PenLine,
  Check,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react';

const RESOLUTION_OPTIONS = [
  {
    id: 'customer_spec',
    label: 'Keep Spec',
    description: 'Use customer requirement',
    icon: FileCheck,
    color: 'blue',
  },
  {
    id: 'quote',
    label: 'Accept Quote',
    description: 'Use vendor assumption',
    icon: FileText,
    color: 'purple',
  },
  {
    id: 'ai_suggestion',
    label: 'AI Suggestion',
    description: 'Use AI resolution',
    icon: Lightbulb,
    color: 'yellow',
  },
  {
    id: 'action_item',
    label: 'Action Item',
    description: 'Create task for vendor',
    icon: ClipboardList,
    color: 'orange',
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Enter your own',
    icon: PenLine,
    color: 'gray',
  },
];

const SEVERITY_STYLES = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

export default function ConflictResolution({
  conflict,
  index,
  resolution,
  onResolve,
  disabled = false,
}) {
  const [expanded, setExpanded] = useState(!resolution);
  const [selectedType, setSelectedType] = useState(resolution?.resolution_type || null);
  const [customText, setCustomText] = useState(resolution?.custom_text || '');
  const [actionItem, setActionItem] = useState(resolution?.action_item || {
    title: `Clarify: ${conflict.category}`,
    description: conflict.resolution_suggestion || '',
    assignee_hint: '',
    due_date_hint: '',
    priority: 'high',
  });
  const [notes, setNotes] = useState(resolution?.notes || '');

  const handleSelectType = (type) => {
    if (disabled) return;
    setSelectedType(type);

    // Auto-confirm for simple options
    if (type === 'customer_spec' || type === 'quote' || type === 'ai_suggestion') {
      confirmResolution(type);
    }
  };

  const confirmResolution = (type = selectedType) => {
    if (!type) return;

    const resolutionData = {
      conflict_index: index,
      resolution_type: type,
      notes: notes || undefined,
    };

    if (type === 'custom') {
      resolutionData.custom_text = customText;
    }

    if (type === 'action_item') {
      resolutionData.action_item = actionItem;
    }

    onResolve(resolutionData);
    setExpanded(false);
  };

  const getPreviewValue = () => {
    switch (selectedType) {
      case 'customer_spec':
        return conflict.checklist_requirement;
      case 'quote':
        return conflict.quote_assumption;
      case 'ai_suggestion':
        return conflict.resolution_suggestion;
      case 'custom':
        return customText || '(Enter custom text)';
      case 'action_item':
        return `[Action Item] ${actionItem.title}`;
      default:
        return null;
    }
  };

  const isResolved = !!resolution;

  return (
    <div className={`border rounded-lg overflow-hidden ${isResolved ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}`}>
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {/* Severity Badge */}
          <span className={`px-2 py-1 text-xs font-medium rounded border ${SEVERITY_STYLES[conflict.severity] || SEVERITY_STYLES.medium}`}>
            {conflict.severity?.toUpperCase()}
          </span>

          {/* Category */}
          <span className="text-sm font-medium text-gray-700">
            {conflict.category}
          </span>

          {/* Resolution Status */}
          {isResolved && (
            <span className="flex items-center gap-1 text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
              <Check className="h-3 w-3" />
              Resolved
            </span>
          )}
        </div>

        <button className="p-1 hover:bg-gray-100 rounded">
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </button>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-200 p-4 space-y-4">
          {/* Conflict Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-red-50 rounded-lg border border-red-100">
              <p className="text-xs font-medium text-red-600 mb-1">Quote Says:</p>
              <p className="text-sm text-gray-800">{conflict.quote_assumption}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-xs font-medium text-blue-600 mb-1">Customer Requires:</p>
              <p className="text-sm text-gray-800">{conflict.checklist_requirement}</p>
            </div>
          </div>

          {/* Conflict Description */}
          <div className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-100">
            <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-yellow-700 mb-1">Conflict:</p>
              <p className="text-sm text-gray-700">{conflict.conflict_description}</p>
            </div>
          </div>

          {/* AI Suggestion */}
          {conflict.resolution_suggestion && (
            <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
              <p className="text-xs font-medium text-purple-600 mb-1">AI Suggested Resolution:</p>
              <p className="text-sm text-gray-700">{conflict.resolution_suggestion}</p>
            </div>
          )}

          {/* Resolution Options */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-3">Choose Resolution:</p>
            <div className="grid grid-cols-5 gap-2">
              {RESOLUTION_OPTIONS.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedType === option.id;

                return (
                  <button
                    key={option.id}
                    onClick={() => handleSelectType(option.id)}
                    disabled={disabled}
                    className={`
                      flex flex-col items-center p-3 rounded-lg border-2 transition-all
                      ${isSelected
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }
                      ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                  >
                    <Icon className={`h-5 w-5 mb-1 ${isSelected ? 'text-primary-600' : 'text-gray-500'}`} />
                    <span className="text-xs font-medium text-center">{option.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Text Input */}
          {selectedType === 'custom' && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Custom Resolution Text:
              </label>
              <textarea
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                placeholder="Enter your custom resolution..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                rows={3}
                disabled={disabled}
              />
              <button
                onClick={() => confirmResolution('custom')}
                disabled={disabled || !customText.trim()}
                className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                Confirm Custom Resolution
              </button>
            </div>
          )}

          {/* Action Item Form */}
          {selectedType === 'action_item' && (
            <div className="space-y-3 p-4 bg-orange-50 rounded-lg border border-orange-200">
              <p className="text-sm font-medium text-orange-700">Action Item Details:</p>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
                <input
                  type="text"
                  value={actionItem.title}
                  onChange={(e) => setActionItem({ ...actionItem, title: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  disabled={disabled}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <textarea
                  value={actionItem.description}
                  onChange={(e) => setActionItem({ ...actionItem, description: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  rows={3}
                  disabled={disabled}
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Assignee</label>
                  <input
                    type="text"
                    value={actionItem.assignee_hint}
                    onChange={(e) => setActionItem({ ...actionItem, assignee_hint: e.target.value })}
                    placeholder="e.g., John Smith"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    disabled={disabled}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Due Date</label>
                  <input
                    type="text"
                    value={actionItem.due_date_hint}
                    onChange={(e) => setActionItem({ ...actionItem, due_date_hint: e.target.value })}
                    placeholder="e.g., Next Friday"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    disabled={disabled}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                  <select
                    value={actionItem.priority}
                    onChange={(e) => setActionItem({ ...actionItem, priority: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    disabled={disabled}
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <button
                onClick={() => confirmResolution('action_item')}
                disabled={disabled || !actionItem.title.trim()}
                className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 disabled:opacity-50"
              >
                Create Action Item
              </button>
            </div>
          )}

          {/* Preview of resolved value */}
          {selectedType && getPreviewValue() && (
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="text-xs font-medium text-green-600 mb-1">Resolution Preview:</p>
              <p className="text-sm text-gray-800">{getPreviewValue()}</p>
            </div>
          )}

          {/* Notes field */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Notes (optional):
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about this resolution..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              disabled={disabled}
            />
          </div>
        </div>
      )}
    </div>
  );
}
