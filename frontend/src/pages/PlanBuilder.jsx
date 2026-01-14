/**
 * PlanBuilder Page
 * Main workflow for creating Strategic Build Plans
 */

import { useState, useCallback } from 'react';
import {
  FileUp,
  Wand2,
  ClipboardCheck,
  Upload as PublishIcon,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';

import UploadZone from '../components/UploadZone';
import PlanPreview from '../components/PlanPreview';
import { ingestDocuments, generateDraft, gradePlan } from '../services/api';

const WORKFLOW_STEPS = [
  { id: 'upload', label: 'Upload Documents', icon: FileUp },
  { id: 'generate', label: 'Generate Plan', icon: Wand2 },
  { id: 'review', label: 'Review & Grade', icon: ClipboardCheck },
  { id: 'publish', label: 'Publish', icon: PublishIcon },
];

export default function PlanBuilder() {
  // Workflow state
  const [currentStep, setCurrentStep] = useState('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Data state
  const [projectName, setProjectName] = useState('');
  const [files, setFiles] = useState([]);
  const [vectorStoreId, setVectorStoreId] = useState(null);
  const [planJson, setPlanJson] = useState(null);
  const [planMarkdown, setPlanMarkdown] = useState(null);
  const [grade, setGrade] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Handle file upload and ingestion
  const handleIngest = useCallback(async () => {
    if (!projectName.trim()) {
      setError('Please enter a project name');
      return;
    }
    if (files.length === 0) {
      setError('Please upload at least one document');
      return;
    }

    setIsLoading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const result = await ingestDocuments(projectName, files, setUploadProgress);
      setVectorStoreId(result.vector_store_id);
      setCurrentStep('generate');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload documents');
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  }, [projectName, files]);

  // Handle plan generation
  const handleGenerate = useCallback(async () => {
    if (!vectorStoreId) {
      setError('No documents uploaded. Please upload documents first.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await generateDraft(vectorStoreId, projectName);
      setPlanJson(result.plan_json);
      setPlanMarkdown(result.plan_markdown);
      setCurrentStep('review');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate plan');
    } finally {
      setIsLoading(false);
    }
  }, [vectorStoreId, projectName]);

  // Handle plan grading
  const handleGrade = useCallback(async () => {
    if (!planJson) {
      setError('No plan to grade');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await gradePlan(planJson);
      setGrade(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to grade plan');
    } finally {
      setIsLoading(false);
    }
  }, [planJson]);

  // Reset workflow
  const handleReset = () => {
    setCurrentStep('upload');
    setProjectName('');
    setFiles([]);
    setVectorStoreId(null);
    setPlanJson(null);
    setPlanMarkdown(null);
    setGrade(null);
    setError(null);
  };

  const getStepStatus = (stepId) => {
    const stepOrder = WORKFLOW_STEPS.map((s) => s.id);
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(stepId);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'current';
    return 'upcoming';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Strategic Build Planner
              </h1>
              <p className="text-sm text-gray-500">
                AI-powered APQP planning for Northern Manufacturing
              </p>
            </div>
            {(planJson || vectorStoreId) && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Start New Plan
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <nav className="flex items-center justify-center">
            {WORKFLOW_STEPS.map((step, index) => {
              const status = getStepStatus(step.id);
              return (
                <div key={step.id} className="flex items-center">
                  <div
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                      ${status === 'completed' ? 'text-green-700 bg-green-50' : ''}
                      ${status === 'current' ? 'text-primary-700 bg-primary-50' : ''}
                      ${status === 'upcoming' ? 'text-gray-400' : ''}
                    `}
                  >
                    {status === 'completed' ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <step.icon className="h-5 w-5" />
                    )}
                    {step.label}
                  </div>
                  {index < WORKFLOW_STEPS.length - 1 && (
                    <ArrowRight className="h-5 w-5 mx-2 text-gray-300" />
                  )}
                </div>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-500 hover:text-red-700"
            >
              ×
            </button>
          </div>
        )}

        {/* Step: Upload */}
        {currentStep === 'upload' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Upload Project Documents
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Upload quotes, drawings, specifications, and other manufacturing documents
                to generate a Strategic Build Plan.
              </p>

              {/* Project Name */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g., ACME-2025-Bracket-Assembly"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={isLoading}
                />
              </div>

              {/* File Upload */}
              <UploadZone onFilesChange={setFiles} disabled={isLoading} />

              {/* Upload Progress */}
              {isLoading && uploadProgress > 0 && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                    <span>Uploading and processing...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handleIngest}
                disabled={isLoading || !projectName.trim() || files.length === 0}
                className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Processing Documents...
                  </>
                ) : (
                  <>
                    <FileUp className="h-5 w-5" />
                    Upload & Continue
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step: Generate */}
        {currentStep === 'generate' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                <Wand2 className="h-8 w-8 text-primary-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Ready to Generate Plan
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Documents processed successfully. Click below to generate your
                Strategic Build Plan using AI analysis.
              </p>

              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-700">
                  <strong>Project:</strong> {projectName}
                </p>
                <p className="text-sm text-gray-700">
                  <strong>Documents:</strong> {files.length} file(s) uploaded
                </p>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Generating Plan...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-5 w-5" />
                    Generate Strategic Build Plan
                  </>
                )}
              </button>

              {isLoading && (
                <p className="mt-4 text-sm text-gray-500">
                  This may take 30-60 seconds depending on document complexity...
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step: Review */}
        {(currentStep === 'review' || currentStep === 'publish') && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Strategic Build Plan: {projectName}
              </h2>
              <div className="flex gap-3">
                {!grade && (
                  <button
                    onClick={handleGrade}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white font-medium rounded-lg hover:bg-yellow-600 disabled:opacity-50"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ClipboardCheck className="h-4 w-4" />
                    )}
                    Grade Plan
                  </button>
                )}
                <button
                  onClick={() => setCurrentStep('publish')}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700"
                >
                  <PublishIcon className="h-4 w-4" />
                  Publish to Confluence
                </button>
              </div>
            </div>

            <PlanPreview
              planJson={planJson}
              planMarkdown={planMarkdown}
              grade={grade}
            />
          </div>
        )}
      </main>
    </div>
  );
}
