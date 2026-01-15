/**
 * ChecklistPreview Component
 * Displays and allows editing of pre-meeting checklist items organized by category
 */

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Edit3,
  Save,
  X,
  FileText,
} from 'lucide-react';

const STATUS_CONFIG = {
  requirement_found: {
    icon: CheckCircle,
    color: 'text-green-500',
    bg: 'bg-green-50',
    label: 'Requirement Found',
  },
  no_requirement: {
    icon: XCircle,
    color: 'text-gray-400',
    bg: 'bg-gray-50',
    label: 'No Requirement',
  },
  error: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    label: 'Error',
  },
};

function ChecklistItem({ item, onUpdate }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedAnswer, setEditedAnswer] = useState(item.answer || '');

  const config = STATUS_CONFIG[item.status] || STATUS_CONFIG.error;
  const StatusIcon = config.icon;

  const handleSave = () => {
    onUpdate({
      ...item,
      answer: editedAnswer,
      status: editedAnswer.toLowerCase().includes('no requirements found')
        ? 'no_requirement'
        : 'requirement_found',
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedAnswer(item.answer || '');
    setIsEditing(false);
  };

  return (
    <div className={`p-4 rounded-lg border ${config.bg} border-gray-200`}>
      <div className="flex items-start gap-3">
        <StatusIcon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${config.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-medium text-gray-900">{item.question}</h4>
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
                title="Edit answer"
              >
                <Edit3 className="h-4 w-4" />
              </button>
            )}
          </div>

          {isEditing ? (
            <div className="mt-2">
              <textarea
                value={editedAnswer}
                onChange={(e) => setEditedAnswer(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                rows={3}
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700"
                >
                  <Save className="h-3 w-3" />
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  <X className="h-3 w-3" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="mt-1 text-sm text-gray-700">{item.answer}</p>
              {item.source && (
                <p className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  Source: {item.source}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CategorySection({ category, onUpdateItem }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const foundCount = category.items.filter(
    (i) => i.status === 'requirement_found'
  ).length;
  const totalCount = category.items.length;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 text-left"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-400" />
          )}
          <h3 className="font-semibold text-gray-900">{category.name}</h3>
        </div>
        <span className="text-sm text-gray-500">
          {foundCount} / {totalCount} requirements found
        </span>
      </button>

      {isExpanded && (
        <div className="p-4 pt-0 space-y-3">
          {category.items.map((item) => (
            <ChecklistItem
              key={item.prompt_id}
              item={item}
              onUpdate={(updated) => onUpdateItem(category.id, item.prompt_id, updated)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChecklistPreview({
  checklist,
  onChecklistChange,
  isLoading,
}) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4" />
          <p className="text-gray-600">Generating checklist...</p>
          <p className="text-sm text-gray-500 mt-1">
            Running {checklist?.statistics?.total_prompts || '~40'} prompts in parallel
          </p>
        </div>
      </div>
    );
  }

  if (!checklist) {
    return null;
  }

  const handleUpdateItem = (categoryId, promptId, updatedItem) => {
    const updatedCategories = checklist.categories.map((cat) => {
      if (cat.id === categoryId) {
        return {
          ...cat,
          items: cat.items.map((item) =>
            item.prompt_id === promptId ? updatedItem : item
          ),
        };
      }
      return cat;
    });

    // Recalculate statistics
    const allItems = updatedCategories.flatMap((c) => c.items);
    const stats = {
      total_prompts: allItems.length,
      requirements_found: allItems.filter((i) => i.status === 'requirement_found').length,
      no_requirements: allItems.filter((i) => i.status === 'no_requirement').length,
      errors: allItems.filter((i) => i.status === 'error').length,
      coverage_percentage: 0,
    };
    stats.coverage_percentage = Math.round(
      (stats.requirements_found / stats.total_prompts) * 100
    );

    onChecklistChange({
      ...checklist,
      categories: updatedCategories,
      statistics: stats,
    });
  };

  return (
    <div className="space-y-6">
      {/* Statistics Summary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">
              {checklist.statistics.total_prompts}
            </p>
            <p className="text-sm text-gray-500">Total Items</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">
              {checklist.statistics.requirements_found}
            </p>
            <p className="text-sm text-gray-500">Requirements Found</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-400">
              {checklist.statistics.no_requirements}
            </p>
            <p className="text-sm text-gray-500">No Requirements</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-red-500">
              {checklist.statistics.errors}
            </p>
            <p className="text-sm text-gray-500">Errors</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-primary-600">
              {checklist.statistics.coverage_percentage}%
            </p>
            <p className="text-sm text-gray-500">Coverage</p>
          </div>
        </div>
        {checklist.generation_time_seconds && (
          <p className="text-center text-xs text-gray-400 mt-2">
            Generated in {checklist.generation_time_seconds.toFixed(1)} seconds
          </p>
        )}
      </div>

      {/* Categories */}
      <div className="space-y-4">
        {checklist.categories.map((category) => (
          <CategorySection
            key={category.id}
            category={category}
            onUpdateItem={handleUpdateItem}
          />
        ))}
      </div>
    </div>
  );
}
