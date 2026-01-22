/**
 * TranscriptComparisonView Component
 * Displays comparison results between meeting transcript and plan
 */

import { useState } from 'react';
import PropTypes from 'prop-types';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  FileText,
  Target,
} from 'lucide-react';

// Coverage score gauge component
function CoverageGauge({ score }) {
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Good Coverage';
    if (score >= 60) return 'Partial Coverage';
    return 'Low Coverage';
  };

  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="48"
            cy="48"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx="48"
            cy="48"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            className={getScoreColor(score)}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: strokeDashoffset,
              transition: 'stroke-dashoffset 0.5s ease',
            }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${getScoreColor(score)}`}>
            {Math.round(score)}%
          </span>
        </div>
      </div>
      <p className={`mt-2 text-sm font-medium ${getScoreColor(score)}`}>
        {getScoreLabel(score)}
      </p>
    </div>
  );
}

CoverageGauge.propTypes = {
  score: PropTypes.number.isRequired,
};

// Missing item card component
function MissingItemCard({ item }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getImportanceStyle = (importance) => {
    switch (importance) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'important':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'decision':
        return <Target className="h-4 w-4" />;
      case 'action_item':
        return <CheckCircle className="h-4 w-4" />;
      case 'requirement':
        return <FileText className="h-4 w-4" />;
      case 'risk':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  return (
    <div className={`border rounded-lg p-3 ${getImportanceStyle(item.importance)}`}>
      <div className="flex items-start gap-2">
        <div className="mt-0.5">{getCategoryIcon(item.category)}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium uppercase">{item.category.replace('_', ' ')}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              item.importance === 'critical' ? 'bg-red-200' :
              item.importance === 'important' ? 'bg-yellow-200' : 'bg-gray-200'
            }`}>
              {item.importance}
            </span>
          </div>
          <p className="text-sm font-medium">{item.content}</p>
          {item.transcript_excerpt && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-2 flex items-center gap-1 text-xs opacity-70 hover:opacity-100"
            >
              {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              View transcript excerpt
            </button>
          )}
          {isExpanded && item.transcript_excerpt && (
            <blockquote className="mt-2 pl-3 border-l-2 border-current text-xs italic opacity-80">
              "{item.transcript_excerpt}"
            </blockquote>
          )}
        </div>
      </div>
    </div>
  );
}

MissingItemCard.propTypes = {
  item: PropTypes.shape({
    category: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired,
    transcript_excerpt: PropTypes.string,
    importance: PropTypes.string.isRequired,
  }).isRequired,
};

// Discrepancy card component
function DiscrepancyCard({ discrepancy }) {
  return (
    <div className={`border rounded-lg p-3 ${
      discrepancy.severity === 'major' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'
    }`}>
      <div className="flex items-start gap-2">
        <AlertTriangle className={`h-5 w-5 flex-shrink-0 ${
          discrepancy.severity === 'major' ? 'text-red-500' : 'text-yellow-500'
        }`} />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-gray-900">{discrepancy.topic}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              discrepancy.severity === 'major' ? 'bg-red-200 text-red-800' : 'bg-yellow-200 text-yellow-800'
            }`}>
              {discrepancy.severity}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500 mb-1">Transcript says:</p>
              <p className="text-gray-700">{discrepancy.transcript_says}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Plan says:</p>
              <p className="text-gray-700">{discrepancy.plan_says}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

DiscrepancyCard.propTypes = {
  discrepancy: PropTypes.shape({
    topic: PropTypes.string.isRequired,
    transcript_says: PropTypes.string.isRequired,
    plan_says: PropTypes.string.isRequired,
    severity: PropTypes.string.isRequired,
  }).isRequired,
};

// Captured item card component
function CapturedItemCard({ item }) {
  return (
    <div className="border border-green-200 bg-green-50 rounded-lg p-3">
      <div className="flex items-start gap-2">
        <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">{item.topic}</p>
          <p className="text-xs text-gray-500 mt-1">
            Found in: {item.plan_location}
          </p>
        </div>
        <div className="text-xs text-green-600 font-medium">
          {Math.round(item.confidence * 100)}%
        </div>
      </div>
    </div>
  );
}

CapturedItemCard.propTypes = {
  item: PropTypes.shape({
    topic: PropTypes.string.isRequired,
    plan_location: PropTypes.string.isRequired,
    confidence: PropTypes.number.isRequired,
  }).isRequired,
};

// Main component
export default function TranscriptComparisonView({ comparison }) {
  const [activeSection, setActiveSection] = useState('missing');

  if (!comparison) {
    return null;
  }

  const { coverage_score, missing_items, discrepancies, captured_items, summary } = comparison;

  // Count items by importance
  const criticalCount = missing_items.filter(i => i.importance === 'critical').length;
  const majorDiscrepancyCount = discrepancies.filter(d => d.severity === 'major').length;

  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-start gap-6">
          <CoverageGauge score={coverage_score} />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Comparison Summary</h3>
            <p className="text-sm text-gray-600 mb-4">{summary}</p>

            {/* Quick stats */}
            <div className="flex gap-4">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
                criticalCount > 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
              }`}>
                <XCircle className="h-4 w-4" />
                <span>{missing_items.length} missing items</span>
                {criticalCount > 0 && (
                  <span className="text-xs">({criticalCount} critical)</span>
                )}
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
                majorDiscrepancyCount > 0 ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
              }`}>
                <AlertTriangle className="h-4 w-4" />
                <span>{discrepancies.length} discrepancies</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm bg-green-100 text-green-700">
                <CheckCircle className="h-4 w-4" />
                <span>{captured_items.length} captured</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveSection('missing')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            activeSection === 'missing'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Missing Items ({missing_items.length})
        </button>
        <button
          onClick={() => setActiveSection('discrepancies')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            activeSection === 'discrepancies'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Discrepancies ({discrepancies.length})
        </button>
        <button
          onClick={() => setActiveSection('captured')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            activeSection === 'captured'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Captured ({captured_items.length})
        </button>
      </div>

      {/* Section content */}
      <div className="space-y-3">
        {activeSection === 'missing' && (
          <>
            {missing_items.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                <p>All items from the transcript are captured in the plan!</p>
              </div>
            ) : (
              missing_items.map((item, index) => (
                <MissingItemCard key={index} item={item} />
              ))
            )}
          </>
        )}

        {activeSection === 'discrepancies' && (
          <>
            {discrepancies.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                <p>No discrepancies found between transcript and plan!</p>
              </div>
            ) : (
              discrepancies.map((discrepancy, index) => (
                <DiscrepancyCard key={index} discrepancy={discrepancy} />
              ))
            )}
          </>
        )}

        {activeSection === 'captured' && (
          <>
            {captured_items.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <AlertCircle className="h-12 w-12 mx-auto mb-3 text-yellow-500" />
                <p>No matching items found in the plan.</p>
              </div>
            ) : (
              captured_items.map((item, index) => (
                <CapturedItemCard key={index} item={item} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}

TranscriptComparisonView.propTypes = {
  comparison: PropTypes.shape({
    coverage_score: PropTypes.number.isRequired,
    missing_items: PropTypes.arrayOf(PropTypes.object).isRequired,
    discrepancies: PropTypes.arrayOf(PropTypes.object).isRequired,
    captured_items: PropTypes.arrayOf(PropTypes.object).isRequired,
    summary: PropTypes.string.isRequired,
  }),
};
