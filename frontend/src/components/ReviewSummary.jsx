/**
 * ReviewSummary Component
 * Final summary combining all post-meeting review results
 */

import PropTypes from 'prop-types';
import {
  FileText,
  ExternalLink,
  Award,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ClipboardCheck,
} from 'lucide-react';

// Grade card component
function GradeCard({ title, score, grade, icon: Icon, dimensions }) {
  const getGradeColor = (grade) => {
    switch (grade) {
      case 'Excellent':
        return 'border-green-200 bg-green-50';
      case 'Good':
        return 'border-blue-200 bg-blue-50';
      case 'Acceptable':
        return 'border-yellow-200 bg-yellow-50';
      case 'Needs Work':
        return 'border-orange-200 bg-orange-50';
      default:
        return 'border-red-200 bg-red-50';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className={`border rounded-lg p-4 ${getGradeColor(grade)}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-gray-600" />
          <h4 className="font-medium text-gray-900">{title}</h4>
        </div>
        <div className="text-right">
          <span className={`text-2xl font-bold ${getScoreColor(score)}`}>{score}</span>
          <span className="text-sm text-gray-500">/100</span>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className={`text-sm font-medium ${getScoreColor(score)}`}>{grade}</span>
        {dimensions && (
          <div className="flex gap-1">
            {Object.values(dimensions).map((dim, i) => (
              <div
                key={i}
                className={`w-2 h-6 rounded ${
                  dim >= 16 ? 'bg-green-400' :
                  dim >= 12 ? 'bg-yellow-400' : 'bg-red-400'
                }`}
                title={`${dim}/20`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

GradeCard.propTypes = {
  title: PropTypes.string.isRequired,
  score: PropTypes.number.isRequired,
  grade: PropTypes.string.isRequired,
  icon: PropTypes.elementType.isRequired,
  dimensions: PropTypes.object,
};

// Stats item component
function StatItem({ icon: Icon, label, value, color = 'text-gray-600' }) {
  return (
    <div className="flex items-center gap-2">
      <Icon className={`h-4 w-4 ${color}`} />
      <span className="text-sm text-gray-600">{label}:</span>
      <span className={`text-sm font-medium ${color}`}>{value}</span>
    </div>
  );
}

StatItem.propTypes = {
  icon: PropTypes.elementType.isRequired,
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  color: PropTypes.string,
};

// Main component
export default function ReviewSummary({
  confluencePage,
  transcriptWordCount,
  comparison,
  processGrade,
  planGrade,
}) {
  // Calculate overall assessment
  const getOverallAssessment = () => {
    const scores = [];
    if (comparison) scores.push(comparison.coverage_score);
    if (processGrade) scores.push(processGrade.overall_score);
    if (planGrade) scores.push(planGrade.overall_score);

    if (scores.length === 0) return null;

    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;

    if (avgScore >= 80) {
      return {
        status: 'success',
        message: 'Meeting and plan are well documented. Ready to proceed.',
        icon: CheckCircle,
        color: 'text-green-600 bg-green-50 border-green-200',
      };
    } else if (avgScore >= 60) {
      return {
        status: 'warning',
        message: 'Some gaps identified. Review missing items before proceeding.',
        icon: AlertTriangle,
        color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      };
    } else {
      return {
        status: 'error',
        message: 'Significant gaps found. Plan update recommended before proceeding.',
        icon: XCircle,
        color: 'text-red-600 bg-red-50 border-red-200',
      };
    }
  };

  const assessment = getOverallAssessment();

  return (
    <div className="space-y-6">
      {/* Overall assessment banner */}
      {assessment && (
        <div className={`border rounded-lg p-4 flex items-start gap-3 ${assessment.color}`}>
          <assessment.icon className="h-6 w-6 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold">Overall Assessment</h3>
            <p className="text-sm mt-1">{assessment.message}</p>
          </div>
        </div>
      )}

      {/* Page info */}
      {confluencePage && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-500 mb-2">Reviewed Page</h4>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-gray-400" />
              <span className="font-medium text-gray-900">{confluencePage.title}</span>
            </div>
            {confluencePage.url && (
              <a
                href={confluencePage.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
              >
                View in Confluence
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
          {confluencePage.ancestors && confluencePage.ancestors.length > 0 && (
            <p className="text-xs text-gray-500 mt-2">
              Path: {confluencePage.ancestors.map(a => a.title).join(' > ')}
            </p>
          )}
        </div>
      )}

      {/* Review stats */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-500 mb-3">Review Statistics</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {transcriptWordCount && (
            <StatItem
              icon={FileText}
              label="Transcript"
              value={`${transcriptWordCount.toLocaleString()} words`}
            />
          )}
          {comparison && (
            <>
              <StatItem
                icon={comparison.missing_items.length > 0 ? XCircle : CheckCircle}
                label="Missing items"
                value={comparison.missing_items.length}
                color={comparison.missing_items.length > 0 ? 'text-red-600' : 'text-green-600'}
              />
              <StatItem
                icon={comparison.discrepancies.length > 0 ? AlertTriangle : CheckCircle}
                label="Discrepancies"
                value={comparison.discrepancies.length}
                color={comparison.discrepancies.length > 0 ? 'text-yellow-600' : 'text-green-600'}
              />
              <StatItem
                icon={CheckCircle}
                label="Coverage"
                value={`${Math.round(comparison.coverage_score)}%`}
                color={comparison.coverage_score >= 80 ? 'text-green-600' : 'text-yellow-600'}
              />
            </>
          )}
        </div>
      </div>

      {/* Grade cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {processGrade && (
          <GradeCard
            title="Meeting Process Quality"
            score={processGrade.overall_score}
            grade={processGrade.grade}
            icon={ClipboardCheck}
            dimensions={processGrade.dimension_scores}
          />
        )}
        {planGrade && (
          <GradeCard
            title="Plan Output Quality"
            score={planGrade.overall_score}
            grade={planGrade.grade}
            icon={Award}
            dimensions={planGrade.dimension_scores}
          />
        )}
      </div>

      {/* Action items summary */}
      {comparison && comparison.missing_items.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Recommended Actions ({comparison.missing_items.filter(i => i.importance === 'critical').length} critical)
          </h4>
          <ul className="space-y-2">
            {comparison.missing_items
              .filter(item => item.importance === 'critical')
              .slice(0, 5)
              .map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <XCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <span className="text-gray-700">{item.content}</span>
                </li>
              ))}
            {comparison.missing_items.filter(i => i.importance === 'critical').length > 5 && (
              <li className="text-sm text-gray-500 pl-6">
                +{comparison.missing_items.filter(i => i.importance === 'critical').length - 5} more critical items
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

ReviewSummary.propTypes = {
  confluencePage: PropTypes.shape({
    id: PropTypes.string,
    title: PropTypes.string,
    url: PropTypes.string,
    ancestors: PropTypes.array,
  }),
  transcriptWordCount: PropTypes.number,
  comparison: PropTypes.shape({
    coverage_score: PropTypes.number,
    missing_items: PropTypes.array,
    discrepancies: PropTypes.array,
  }),
  processGrade: PropTypes.shape({
    overall_score: PropTypes.number,
    grade: PropTypes.string,
    dimension_scores: PropTypes.object,
  }),
  planGrade: PropTypes.shape({
    overall_score: PropTypes.number,
    grade: PropTypes.string,
    dimension_scores: PropTypes.object,
  }),
};
