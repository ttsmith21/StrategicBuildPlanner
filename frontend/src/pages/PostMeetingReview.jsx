/**
 * PostMeetingReview Page
 * Phase 2 workflow for reviewing meeting transcripts against plans
 */

import { useState, useCallback } from 'react';
import {
  FileSearch,
  FileText,
  GitCompare,
  CheckSquare,
  ClipboardCheck,
  FileOutput,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';

import ConfluenceSearch from '../components/ConfluenceSearch';
import TranscriptUpload from '../components/TranscriptUpload';
import TranscriptComparisonView from '../components/TranscriptComparisonView';
import ProcessGradeView from '../components/ProcessGradeView';
import ReviewSummary from '../components/ReviewSummary';

import {
  compareTranscriptToPlan,
  gradeAPQPProcess,
  gradePlan,
  getConfluencePageText,
} from '../services/api';

const WORKFLOW_STEPS = [
  { id: 'select', label: 'Select Plan', icon: FileSearch },
  { id: 'transcript', label: 'Upload Notes', icon: FileText },
  { id: 'compare', label: 'Compare', icon: GitCompare },
  { id: 'grade-process', label: 'Grade Process', icon: CheckSquare },
  { id: 'grade-plan', label: 'Grade Plan', icon: ClipboardCheck },
  { id: 'summary', label: 'Summary', icon: FileOutput },
];

export default function PostMeetingReview() {
  // Workflow state
  const [currentStep, setCurrentStep] = useState('select');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Data state
  const [selectedConfluencePage, setSelectedConfluencePage] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [meetingType, setMeetingType] = useState('kickoff');
  const [comparison, setComparison] = useState(null);
  const [processGrade, setProcessGrade] = useState(null);
  const [planGrade, setPlanGrade] = useState(null);
  const [planContent, setPlanContent] = useState(null);

  // Get step status for styling
  const getStepStatus = (stepId) => {
    const stepOrder = WORKFLOW_STEPS.map((s) => s.id);
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(stepId);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'current';
    return 'upcoming';
  };

  // Handle step click (backward navigation only)
  const handleStepClick = (stepId) => {
    const stepOrder = WORKFLOW_STEPS.map((s) => s.id);
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(stepId);

    if (stepIndex < currentIndex) {
      setCurrentStep(stepId);
    }
  };

  // Handle page selection
  const handlePageSelect = useCallback(async (page) => {
    setSelectedConfluencePage(page);
    setError(null);

    // Fetch page content for later use
    if (page?.id) {
      try {
        const content = await getConfluencePageText(page.id);
        setPlanContent(content);
      } catch (err) {
        console.warn('Could not fetch page content:', err);
      }
    }
  }, []);

  // Handle transcript ready
  const handleTranscriptReady = useCallback((text) => {
    setTranscript(text);
  }, []);

  // Proceed from select to transcript step
  const handleSelectContinue = useCallback(() => {
    if (!selectedConfluencePage) {
      setError('Please select a Confluence page first');
      return;
    }
    setCurrentStep('transcript');
  }, [selectedConfluencePage]);

  // Proceed from transcript to compare step and run comparison
  const handleTranscriptContinue = useCallback(async () => {
    if (!transcript) {
      setError('Please upload or paste a transcript first');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await compareTranscriptToPlan(
        transcript,
        selectedConfluencePage.id,
        meetingType
      );
      setComparison(result);
      setCurrentStep('compare');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to compare transcript');
    } finally {
      setIsLoading(false);
    }
  }, [transcript, selectedConfluencePage, meetingType]);

  // Proceed to process grading
  const handleCompareContinue = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await gradeAPQPProcess(transcript, meetingType);
      setProcessGrade(result);
      setCurrentStep('grade-process');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to grade process');
    } finally {
      setIsLoading(false);
    }
  }, [transcript, meetingType]);

  // Proceed to plan grading
  const handleProcessGradeContinue = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // For plan grading, we need the plan JSON
      // Since we're comparing against Confluence content, we'll grade what we have
      // In a real implementation, this would parse the Confluence content to JSON
      // For now, we'll use the comparison results as a proxy
      const mockPlanJson = {
        project_name: selectedConfluencePage?.title || 'Unknown',
        content: planContent,
      };

      const result = await gradePlan(mockPlanJson);
      setPlanGrade(result);
      setCurrentStep('grade-plan');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to grade plan');
    } finally {
      setIsLoading(false);
    }
  }, [selectedConfluencePage, planContent]);

  // Proceed to summary
  const handlePlanGradeContinue = useCallback(() => {
    setCurrentStep('summary');
  }, []);

  // Reset workflow
  const handleReset = useCallback(() => {
    setCurrentStep('select');
    setSelectedConfluencePage(null);
    setTranscript(null);
    setComparison(null);
    setProcessGrade(null);
    setPlanGrade(null);
    setPlanContent(null);
    setError(null);
  }, []);

  // Calculate word count for display
  const transcriptWordCount = transcript
    ? transcript.trim().split(/\s+/).filter(Boolean).length
    : 0;

  return (
    <div className="space-y-6">
      {/* Progress Steps */}
      <div className="bg-white border-b border-gray-200 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-4">
        <nav className="flex items-center justify-center flex-wrap gap-2">
          {WORKFLOW_STEPS.map((step, index) => {
            const status = getStepStatus(step.id);
            return (
              <div key={step.id} className="flex items-center">
                <button
                  onClick={() => handleStepClick(step.id)}
                  disabled={status === 'upcoming'}
                  className={`
                    flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium
                    transition-colors
                    ${status === 'completed' ? 'text-green-700 bg-green-50 hover:bg-green-100 cursor-pointer' : ''}
                    ${status === 'current' ? 'text-primary-700 bg-primary-50' : ''}
                    ${status === 'upcoming' ? 'text-gray-400 cursor-not-allowed' : ''}
                  `}
                >
                  {status === 'completed' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <step.icon className="h-4 w-4" />
                  )}
                  <span className="hidden sm:inline">{step.label}</span>
                </button>
                {index < WORKFLOW_STEPS.length - 1 && (
                  <ArrowRight className="h-4 w-4 mx-1 text-gray-300" />
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      )}

      {/* Step: Select Plan */}
      {currentStep === 'select' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Step 1: Select Plan to Review
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Search for the project's Confluence page that you want to review against the meeting transcript.
          </p>

          <ConfluenceSearch onPageSelect={handlePageSelect} />

          {selectedConfluencePage && (
            <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-medium text-green-800">
                  Selected: {selectedConfluencePage.title}
                </span>
              </div>
            </div>
          )}

          <button
            onClick={handleSelectContinue}
            disabled={!selectedConfluencePage}
            className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue to Upload Transcript
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      )}

      {/* Step: Upload Transcript */}
      {currentStep === 'transcript' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Step 2: Upload Meeting Transcript
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Upload the meeting notes or transcript to compare against the plan.
          </p>

          {/* Meeting type selector */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Meeting Type
            </label>
            <select
              value={meetingType}
              onChange={(e) => setMeetingType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="kickoff">Kickoff Meeting</option>
              <option value="review">Design Review</option>
              <option value="customer">Customer Meeting</option>
              <option value="internal">Internal Discussion</option>
            </select>
          </div>

          <TranscriptUpload
            onTranscriptReady={handleTranscriptReady}
            disabled={isLoading}
          />

          <button
            onClick={handleTranscriptContinue}
            disabled={!transcript || isLoading}
            className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                Compare Transcript to Plan
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Step: Compare */}
      {currentStep === 'compare' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Step 3: Comparison Results
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Review what was captured in the plan and what might be missing from the meeting discussion.
            </p>

            <TranscriptComparisonView comparison={comparison} />

            <button
              onClick={handleCompareContinue}
              disabled={isLoading}
              className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Grading Process...
                </>
              ) : (
                <>
                  Grade Meeting Process
                  <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step: Grade Process */}
      {currentStep === 'grade-process' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Step 4: Meeting Process Quality
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Evaluate how effective the APQP meeting was based on the transcript.
            </p>

            <ProcessGradeView grade={processGrade} />

            <button
              onClick={handleProcessGradeContinue}
              disabled={isLoading}
              className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Grading Plan...
                </>
              ) : (
                <>
                  Grade Plan Quality
                  <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step: Grade Plan */}
      {currentStep === 'grade-plan' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Step 5: Plan Output Quality
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Evaluate the quality of the Strategic Build Plan itself.
            </p>

            {planGrade && (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm text-gray-500">Overall Score</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {planGrade.overall_score}/100
                    </p>
                  </div>
                  <div className={`px-4 py-2 rounded-lg font-medium ${
                    planGrade.grade === 'Excellent' ? 'bg-green-100 text-green-800' :
                    planGrade.grade === 'Good' ? 'bg-blue-100 text-blue-800' :
                    planGrade.grade === 'Acceptable' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {planGrade.grade}
                  </div>
                </div>

                {planGrade.strengths && planGrade.strengths.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Strengths</h4>
                    <ul className="space-y-1">
                      {planGrade.strengths.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {planGrade.improvements && planGrade.improvements.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Areas for Improvement</h4>
                    <ul className="space-y-1">
                      {planGrade.improvements.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <AlertCircle className="h-4 w-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={handlePlanGradeContinue}
              className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700"
            >
              View Summary
              <ArrowRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Summary */}
      {currentStep === 'summary' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Review Summary
                </h2>
                <p className="text-sm text-gray-600">
                  Complete assessment of the meeting and plan quality.
                </p>
              </div>
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Start New Review
              </button>
            </div>

            <ReviewSummary
              confluencePage={selectedConfluencePage}
              transcriptWordCount={transcriptWordCount}
              comparison={comparison}
              processGrade={processGrade}
              planGrade={planGrade}
            />
          </div>
        </div>
      )}
    </div>
  );
}
