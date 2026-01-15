/**
 * PreMeetingPrep Page (Phase 1)
 * Upload specs, generate checklist, publish to Confluence
 */

import { useState, useCallback } from 'react';
import {
  FileUp,
  ListChecks,
  Upload as PublishIcon,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';

import UploadZone from '../components/UploadZone';
import ChecklistPreview from '../components/ChecklistPreview';
import { ingestDocuments, generateChecklist, publishChecklist } from '../services/api';

const WORKFLOW_STEPS = [
  { id: 'upload', label: 'Upload Specs', icon: FileUp },
  { id: 'checklist', label: 'Generate Checklist', icon: ListChecks },
  { id: 'publish', label: 'Publish to Confluence', icon: PublishIcon },
];

export default function PreMeetingPrep() {
  // Workflow state
  const [currentStep, setCurrentStep] = useState('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Data state
  const [projectName, setProjectName] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [files, setFiles] = useState([]);
  const [vectorStoreId, setVectorStoreId] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [confluenceUrl, setConfluenceUrl] = useState(null);

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
      setCurrentStep('checklist');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload documents');
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  }, [projectName, files]);

  // Handle checklist generation
  const handleGenerateChecklist = useCallback(async () => {
    if (!vectorStoreId) {
      setError('No documents uploaded. Please upload documents first.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await generateChecklist(vectorStoreId, projectName, customerName);
      setChecklist(result);
      setCurrentStep('publish');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate checklist');
    } finally {
      setIsLoading(false);
    }
  }, [vectorStoreId, projectName, customerName]);

  // Handle publish to Confluence
  const handlePublish = useCallback(async () => {
    if (!checklist) {
      setError('No checklist to publish');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await publishChecklist(checklist);
      setConfluenceUrl(result.page_url);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to publish to Confluence');
    } finally {
      setIsLoading(false);
    }
  }, [checklist]);

  // Reset workflow
  const handleReset = () => {
    setCurrentStep('upload');
    setProjectName('');
    setCustomerName('');
    setFiles([]);
    setVectorStoreId(null);
    setChecklist(null);
    setConfluenceUrl(null);
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
                Pre-Meeting Prep
              </h1>
              <p className="text-sm text-gray-500">
                Phase 1: Generate APQP checklist from specifications
              </p>
            </div>
            {(checklist || vectorStoreId) && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Start New
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
                Upload Specification Documents
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Upload customer specs, drawings, and quotes. The AI will analyze
                them against 40+ APQP checklist items.
              </p>

              {/* Project Name */}
              <div className="mb-4">
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

              {/* Customer Name */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Customer Name
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="e.g., ACME Corporation"
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

        {/* Step: Generate Checklist */}
        {currentStep === 'checklist' && !checklist && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                <ListChecks className="h-8 w-8 text-primary-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Ready to Generate Checklist
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Documents processed successfully. Click below to run the APQP
                checklist analysis using AI.
              </p>

              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-700">
                  <strong>Project:</strong> {projectName}
                </p>
                {customerName && (
                  <p className="text-sm text-gray-700">
                    <strong>Customer:</strong> {customerName}
                  </p>
                )}
                <p className="text-sm text-gray-700">
                  <strong>Documents:</strong> {files.length} file(s) uploaded
                </p>
              </div>

              <button
                onClick={handleGenerateChecklist}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Generating Checklist...
                  </>
                ) : (
                  <>
                    <ListChecks className="h-5 w-5" />
                    Generate Pre-Meeting Checklist
                  </>
                )}
              </button>

              {isLoading && (
                <p className="mt-4 text-sm text-gray-500">
                  Running 40+ prompts in parallel. This may take 30-60 seconds...
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step: Review Checklist */}
        {(currentStep === 'checklist' && checklist) || currentStep === 'publish' ? (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Pre-Meeting Checklist: {projectName}
                </h2>
                {customerName && (
                  <p className="text-sm text-gray-500">Customer: {customerName}</p>
                )}
              </div>
              <div className="flex gap-3">
                {!confluenceUrl ? (
                  <button
                    onClick={handlePublish}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <PublishIcon className="h-4 w-4" />
                    )}
                    Publish to Confluence
                  </button>
                ) : (
                  <a
                    href={confluenceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700"
                  >
                    <CheckCircle className="h-4 w-4" />
                    View in Confluence
                  </a>
                )}
              </div>
            </div>

            {confluenceUrl && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium text-green-800">
                    Published Successfully!
                  </p>
                  <p className="text-sm text-green-700">
                    The pre-meeting checklist has been published to Confluence.
                    Share this with your team before the kickoff meeting.
                  </p>
                </div>
              </div>
            )}

            <ChecklistPreview
              checklist={checklist}
              onChecklistChange={setChecklist}
              isLoading={isLoading && !checklist}
            />
          </div>
        ) : null}
      </main>
    </div>
  );
}
