/**
 * LessonsLearned Component
 * Display extracted lessons learned from historical Confluence pages
 * Allow users to accept/reject/modify each insight before publishing
 */

import { useState, useMemo } from 'react';
import {
  BookOpen,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Edit3,
  ChevronDown,
  ChevronRight,
  Loader2,
  Info,
  AlertCircle,
  Shield,
  MessageSquare,
  Settings,
  SkipForward,
  ArrowRight,
  FileText,
} from 'lucide-react';

// Category icon mapping
const CATEGORY_CONFIG = {
  'Quality Issue': {
    icon: AlertCircle,
    color: 'red',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    badgeBg: 'bg-red-100',
  },
  'Risk Warning': {
    icon: AlertTriangle,
    color: 'yellow',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-700',
    badgeBg: 'bg-yellow-100',
  },
  'Best Practice': {
    icon: CheckCircle,
    color: 'green',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-700',
    badgeBg: 'bg-green-100',
  },
  'Customer Feedback': {
    icon: MessageSquare,
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-700',
    badgeBg: 'bg-blue-100',
  },
  'Process Improvement': {
    icon: Settings,
    color: 'purple',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    textColor: 'text-purple-700',
    badgeBg: 'bg-purple-100',
  },
};

function InsightCard({
  insight,
  selection,
  onSelectionChange,
  disabled,
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(
    insight.recommendation || ''
  );

  const config = CATEGORY_CONFIG[insight.category] || CATEGORY_CONFIG['Best Practice'];
  const CategoryIcon = config.icon;

  const handleAccept = () => {
    onSelectionChange(insight.id, 'accepted', null);
    setIsEditing(false);
  };

  const handleReject = () => {
    onSelectionChange(insight.id, 'rejected', null);
    setIsEditing(false);
  };

  const handleSaveEdit = () => {
    onSelectionChange(insight.id, 'accepted', editedText);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedText(insight.recommendation || '');
    setIsEditing(false);
  };

  const getStatusBadge = () => {
    if (!selection) return null;

    if (selection.status === 'accepted') {
      return (
        <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
          <CheckCircle className="h-3 w-3" />
          Accepted
        </span>
      );
    }
    if (selection.status === 'rejected') {
      return (
        <span className="flex items-center gap-1 text-xs font-medium text-red-700 bg-red-100 px-2 py-0.5 rounded-full">
          <XCircle className="h-3 w-3" />
          Rejected
        </span>
      );
    }
    return null;
  };

  return (
    <div
      className={`
        border rounded-lg overflow-hidden transition-all
        ${config.borderColor}
        ${selection?.status === 'rejected' ? 'opacity-60' : ''}
      `}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full flex items-center gap-3 px-4 py-3 ${config.bgColor} hover:opacity-90 transition-opacity`}
      >
        <CategoryIcon className={`h-5 w-5 ${config.textColor}`} />
        <span className={`font-medium flex-1 text-left ${config.textColor}`}>
          {insight.title}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${config.badgeBg} ${config.textColor}`}>
          {insight.category}
        </span>
        {getStatusBadge()}
        <span className="text-xs text-gray-500">
          {Math.round(insight.relevance_score * 100)}% relevant
        </span>
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 bg-white space-y-4">
          {/* Description */}
          <div>
            <p className="text-sm text-gray-700">{insight.description}</p>
          </div>

          {/* Source excerpt */}
          {insight.source_excerpt && (
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-xs font-medium text-gray-500 mb-1">Source:</p>
              <p className="text-sm text-gray-600 italic">"{insight.source_excerpt}"</p>
            </div>
          )}

          {/* Recommendation */}
          <div className={`p-3 rounded-lg ${config.bgColor}`}>
            <p className="text-xs font-medium text-gray-500 mb-1">Recommendation:</p>
            {isEditing ? (
              <div className="space-y-2">
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  rows={3}
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={handleCancelEdit}
                    className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEdit}
                    className="px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700"
                  >
                    Save & Accept
                  </button>
                </div>
              </div>
            ) : (
              <p className={`text-sm ${config.textColor}`}>
                {selection?.modifiedText || insight.recommendation}
              </p>
            )}
          </div>

          {/* Action Buttons */}
          {!isEditing && (
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={handleReject}
                disabled={disabled}
                className={`
                  flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg
                  ${selection?.status === 'rejected'
                    ? 'bg-red-100 text-red-700'
                    : 'text-red-600 hover:bg-red-50 border border-red-200'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
              <button
                onClick={() => setIsEditing(true)}
                disabled={disabled}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Edit3 className="h-4 w-4" />
                Modify
              </button>
              <button
                onClick={handleAccept}
                disabled={disabled}
                className={`
                  flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg
                  ${selection?.status === 'accepted'
                    ? 'bg-green-600 text-white'
                    : 'bg-green-100 text-green-700 hover:bg-green-200'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <CheckCircle className="h-4 w-4" />
                Accept
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function LessonsLearned({
  lessonsData,
  selections = {},
  onSelectionChange,
  onProceed,
  onSkip,
  isLoading = false,
  disabled = false,
}) {
  // Calculate progress
  const progress = useMemo(() => {
    if (!lessonsData?.insights?.length) {
      return { accepted: 0, rejected: 0, pending: 0, total: 0, percentage: 0 };
    }

    const total = lessonsData.insights.length;
    let accepted = 0;
    let rejected = 0;

    Object.values(selections).forEach((sel) => {
      if (sel.status === 'accepted') accepted++;
      if (sel.status === 'rejected') rejected++;
    });

    const pending = total - accepted - rejected;
    const percentage = total > 0 ? Math.round(((accepted + rejected) / total) * 100) : 0;

    return { accepted, rejected, pending, total, percentage };
  }, [lessonsData, selections]);

  // Get accepted lessons for publishing
  const acceptedLessons = useMemo(() => {
    if (!lessonsData?.insights) return [];

    return lessonsData.insights
      .filter((insight) => selections[insight.id]?.status === 'accepted')
      .map((insight) => ({
        ...insight,
        recommendation: selections[insight.id]?.modifiedText || insight.recommendation,
      }));
  }, [lessonsData, selections]);

  // Handle skip
  if (lessonsData?.skipped) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
            <Info className="h-6 w-6 text-gray-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Lessons Available
          </h3>
          <p className="text-sm text-gray-600 mb-6">
            {lessonsData.skip_reason || 'Could not extract lessons from historical pages.'}
          </p>
          <button
            onClick={onSkip}
            disabled={disabled}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            <ArrowRight className="h-4 w-4" />
            Continue to Publish
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading && !lessonsData) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Extracting Lessons Learned
          </h3>
          <p className="text-sm text-gray-600">
            Analyzing historical projects, family documentation, and customer pages...
          </p>
        </div>
      </div>
    );
  }

  if (!lessonsData?.insights?.length) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-full mb-4">
            <AlertTriangle className="h-6 w-6 text-yellow-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Insights Found
          </h3>
          <p className="text-sm text-gray-600 mb-6">
            No relevant lessons were found in the historical documentation.
          </p>
          <button
            onClick={onSkip}
            disabled={disabled}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            <ArrowRight className="h-4 w-4" />
            Continue to Publish
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Summary */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <BookOpen className="h-6 w-6 text-yellow-700" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Lessons Learned
              </h3>
              <p className="text-sm text-gray-500">
                {lessonsData.insights.length} insights from historical projects
              </p>
            </div>
          </div>
        </div>

        {/* Source Pages */}
        <div className="p-4 bg-gray-50 rounded-lg mb-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Analyzed Pages:</p>
          <div className="flex flex-wrap gap-2">
            {lessonsData.sibling_pages_analyzed?.map((page) => (
              <span
                key={page.id}
                className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
              >
                <FileText className="h-3 w-3" />
                {page.title}
              </span>
            ))}
            {lessonsData.family_page && (
              <span className="flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                <FileText className="h-3 w-3" />
                {lessonsData.family_page.title} (Family)
              </span>
            )}
            {lessonsData.customer_page && (
              <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                <FileText className="h-3 w-3" />
                {lessonsData.customer_page.title} (Customer)
              </span>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-600">
              Review Progress: {progress.accepted + progress.rejected} of {progress.total}
            </span>
            <div className="flex gap-4 text-xs">
              <span className="text-green-600">{progress.accepted} accepted</span>
              <span className="text-red-600">{progress.rejected} rejected</span>
              <span className="text-gray-500">{progress.pending} pending</span>
            </div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-4 border-t border-gray-200">
          <button
            onClick={onSkip}
            disabled={disabled || isLoading}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <SkipForward className="h-4 w-4" />
            Skip Lessons
          </button>

          <div className="flex items-center gap-3">
            {progress.pending > 0 && (
              <span className="text-sm text-gray-500">
                {progress.pending} insights still need review
              </span>
            )}
            <button
              onClick={() => onProceed(acceptedLessons)}
              disabled={disabled || isLoading}
              className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <ArrowRight className="h-4 w-4" />
                  Proceed with {progress.accepted} Lesson{progress.accepted !== 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Insight Cards */}
      <div className="space-y-4">
        {lessonsData.insights.map((insight) => (
          <InsightCard
            key={insight.id}
            insight={insight}
            selection={selections[insight.id]}
            onSelectionChange={onSelectionChange}
            disabled={disabled || isLoading}
          />
        ))}
      </div>
    </div>
  );
}
