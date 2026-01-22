/**
 * ProcessGradeView Component
 * Displays APQP meeting process quality grade with detailed breakdown
 */

import { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Award,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  Users,
  Target,
  ClipboardList,
  Shield,
} from 'lucide-react';

// Dimension info for display
const DIMENSION_INFO = {
  discussion_coverage: {
    label: 'Discussion Coverage',
    description: 'Were all critical APQP topics discussed?',
    icon: ClipboardList,
  },
  stakeholder_participation: {
    label: 'Stakeholder Participation',
    description: 'Did all parties contribute meaningfully?',
    icon: Users,
  },
  decision_quality: {
    label: 'Decision Quality',
    description: 'Were decisions clear and documented?',
    icon: Target,
  },
  action_assignment: {
    label: 'Action Assignment',
    description: 'Were tasks assigned with owners/dates?',
    icon: CheckCircle,
  },
  risk_discussion: {
    label: 'Risk Discussion',
    description: 'Were risks identified and addressed?',
    icon: Shield,
  },
};

// Grade badge component
function GradeBadge({ grade, score }) {
  const getGradeStyle = (grade) => {
    switch (grade) {
      case 'Excellent':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Good':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Acceptable':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Needs Work':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-red-100 text-red-800 border-red-200';
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${getGradeStyle(grade)}`}>
      <Award className="h-5 w-5" />
      <span className="font-bold text-lg">{score}/100</span>
      <span className="font-medium">{grade}</span>
    </div>
  );
}

GradeBadge.propTypes = {
  grade: PropTypes.string.isRequired,
  score: PropTypes.number.isRequired,
};

// Dimension score bar component
function DimensionScoreBar({ dimensionKey, score, maxScore = 20 }) {
  const info = DIMENSION_INFO[dimensionKey];
  const Icon = info?.icon || CheckCircle;
  const percentage = (score / maxScore) * 100;

  const getBarColor = (pct) => {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <Icon className="h-4 w-4 text-gray-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-900">{info?.label || dimensionKey}</span>
          <span className="text-sm font-bold text-gray-700">{score}/{maxScore}</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${getBarColor(percentage)}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-0.5">{info?.description}</p>
      </div>
    </div>
  );
}

DimensionScoreBar.propTypes = {
  dimensionKey: PropTypes.string.isRequired,
  score: PropTypes.number.isRequired,
  maxScore: PropTypes.number,
};

// Topics checklist component
function TopicsSection({ title, topics, isPositive }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!topics || topics.length === 0) return null;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <span className="font-medium text-sm">{title}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {topics.length}
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="p-3 space-y-2">
          {topics.map((topic, index) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              {isPositive ? (
                <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
              )}
              <span className="text-gray-700">{topic}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

TopicsSection.propTypes = {
  title: PropTypes.string.isRequired,
  topics: PropTypes.arrayOf(PropTypes.string),
  isPositive: PropTypes.bool,
};

// Feedback list component
function FeedbackList({ title, items, icon: Icon, colorClass }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!items || items.length === 0) return null;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <Icon className={`h-4 w-4 ${colorClass}`} />
          <span className="font-medium text-sm">{title}</span>
        </div>
      </button>
      {isExpanded && (
        <ul className="p-3 space-y-2">
          {items.map((item, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
              <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${colorClass.replace('text-', 'bg-')}`} />
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

FeedbackList.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.string),
  icon: PropTypes.elementType.isRequired,
  colorClass: PropTypes.string.isRequired,
};

// Main component
export default function ProcessGradeView({ grade }) {
  if (!grade) {
    return null;
  }

  const {
    overall_score,
    dimension_scores,
    grade: gradeLabel,
    strengths,
    improvements,
    topics_discussed,
    topics_missing,
  } = grade;

  return (
    <div className="space-y-6">
      {/* Header with overall grade */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Meeting Process Quality</h3>
            <p className="text-sm text-gray-500">APQP meeting effectiveness assessment</p>
          </div>
          <GradeBadge grade={gradeLabel} score={overall_score} />
        </div>

        {/* Dimension scores */}
        <div className="space-y-4">
          {Object.entries(dimension_scores).map(([key, score]) => (
            <DimensionScoreBar key={key} dimensionKey={key} score={score} />
          ))}
        </div>
      </div>

      {/* Topics section */}
      <div className="grid grid-cols-2 gap-4">
        <TopicsSection
          title="Topics Discussed"
          topics={topics_discussed}
          isPositive={true}
        />
        <TopicsSection
          title="Topics Missing"
          topics={topics_missing}
          isPositive={false}
        />
      </div>

      {/* Strengths and improvements */}
      <div className="grid grid-cols-2 gap-4">
        <FeedbackList
          title="Strengths"
          items={strengths}
          icon={TrendingUp}
          colorClass="text-green-500"
        />
        <FeedbackList
          title="Areas for Improvement"
          items={improvements}
          icon={AlertTriangle}
          colorClass="text-yellow-500"
        />
      </div>
    </div>
  );
}

ProcessGradeView.propTypes = {
  grade: PropTypes.shape({
    overall_score: PropTypes.number.isRequired,
    dimension_scores: PropTypes.object.isRequired,
    grade: PropTypes.string.isRequired,
    strengths: PropTypes.arrayOf(PropTypes.string),
    improvements: PropTypes.arrayOf(PropTypes.string),
    topics_discussed: PropTypes.arrayOf(PropTypes.string),
    topics_missing: PropTypes.arrayOf(PropTypes.string),
  }),
};
