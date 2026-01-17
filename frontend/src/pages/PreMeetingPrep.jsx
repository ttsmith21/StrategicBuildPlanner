/**
 * PreMeetingPrep Page (Phase 1)
 * Upload specs, generate checklist, compare with vendor quote, publish to Confluence
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  FileUp,
  ListChecks,
  Upload as PublishIcon,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  FileText,
  GitCompare,
  SkipForward,
} from 'lucide-react';

import UploadZone from '../components/UploadZone';
import ChecklistPreview from '../components/ChecklistPreview';
import QuoteUpload from '../components/QuoteUpload';
import ComparisonView from '../components/ComparisonView';
import ConfluenceSearch from '../components/ConfluenceSearch';
import {
  ingestDocuments,
  generateChecklist,
  publishChecklist,
  updateTemplateWithChecklist,
  compareQuoteWithChecklist,
  generateMergePreview,
  resolveConflicts,
} from '../services/api';

const WORKFLOW_STEPS = [
  { id: 'upload', label: 'Upload Specs', icon: FileUp },
  { id: 'checklist', label: 'Generate Checklist', icon: ListChecks },
  { id: 'quote', label: 'Upload Quote', icon: FileText },
  { id: 'compare', label: 'Compare', icon: GitCompare },
  { id: 'publish', label: 'Publish', icon: PublishIcon },
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
  const checklistRef = useRef(null); // Ref to always have latest checklist for publish
  const [uploadProgress, setUploadProgress] = useState(0);
  const [confluenceUrl, setConfluenceUrl] = useState(null);

  // Keep ref in sync with state - ensures handlePublish always has latest checklist
  useEffect(() => {
    checklistRef.current = checklist;
  }, [checklist]);

  // Quote comparison state
  const [quoteAssumptions, setQuoteAssumptions] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [mergePreview, setMergePreview] = useState(null);

  // Conflict resolution state
  const [resolutions, setResolutions] = useState({});
  const [isApplyingResolutions, setIsApplyingResolutions] = useState(false);
  const [actionItemsCreated, setActionItemsCreated] = useState([]);

  // Confluence parent page selection
  const [selectedConfluencePage, setSelectedConfluencePage] = useState(null);

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
      setCurrentStep('quote'); // Go to quote upload step
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate checklist');
    } finally {
      setIsLoading(false);
    }
  }, [vectorStoreId, projectName, customerName]);

  // Handle quote extraction complete
  const handleQuoteExtracted = useCallback((quote) => {
    setQuoteAssumptions(quote);
  }, []);

  // Handle quote comparison
  const handleCompareQuote = useCallback(async () => {
    if (!quoteAssumptions || !checklist) {
      setError('Need both checklist and quote to compare');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await compareQuoteWithChecklist(quoteAssumptions, checklist);
      setComparison(result);
      setCurrentStep('compare');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to compare quote');
    } finally {
      setIsLoading(false);
    }
  }, [quoteAssumptions, checklist]);

  // Skip quote comparison
  const handleSkipQuote = useCallback(() => {
    setCurrentStep('publish');
  }, []);

  // Generate merge preview
  const handleGenerateMergePreview = useCallback(async () => {
    if (!checklist || !quoteAssumptions || !comparison) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await generateMergePreview(checklist, quoteAssumptions, comparison);
      setMergePreview(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate merge preview');
    } finally {
      setIsLoading(false);
    }
  }, [checklist, quoteAssumptions, comparison]);

  // Handle individual conflict resolution
  const handleResolve = useCallback((resolutionData) => {
    setResolutions((prev) => ({
      ...prev,
      [resolutionData.conflict_index]: resolutionData,
    }));
  }, []);

  // Handle applying all resolutions
  const handleApplyResolutions = useCallback(async () => {
    if (!checklist || !comparison || Object.keys(resolutions).length === 0) {
      return;
    }

    setIsApplyingResolutions(true);
    setError(null);

    try {
      // Convert resolutions object to array
      const resolutionsList = Object.values(resolutions);

      const result = await resolveConflicts(checklist, comparison, resolutionsList);

      // Update checklist with resolved version
      setChecklist(result.updated_checklist);

      // Track any action items created
      if (result.action_items?.length > 0) {
        setActionItemsCreated(result.action_items);
      }

      // Show success and proceed to publish
      setCurrentStep('publish');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to apply resolutions');
    } finally {
      setIsApplyingResolutions(false);
    }
  }, [checklist, comparison, resolutions]);

  // Proceed to publish after comparison - apply any resolutions first
  const handleProceedToPublish = useCallback(async () => {
    // If there are any resolutions, apply them before proceeding
    if (checklist && comparison && Object.keys(resolutions).length > 0) {
      setIsApplyingResolutions(true);
      setError(null);

      try {
        const resolutionsList = Object.values(resolutions);
        console.log('Applying resolutions:', resolutionsList.length, 'resolutions');
        const result = await resolveConflicts(checklist, comparison, resolutionsList);
        console.log('Resolution result:', result);
        console.log('Updated checklist has resolutions_applied:', result.updated_checklist?.resolutions_applied);
        console.log('Resolution summary:', result.updated_checklist?.resolution_summary);

        // Update checklist with resolved version - this is critical!
        // Update both state AND ref immediately to ensure publish gets the right data
        setChecklist(result.updated_checklist);
        checklistRef.current = result.updated_checklist; // Immediate ref update

        // Track any action items created
        if (result.action_items?.length > 0) {
          setActionItemsCreated(result.action_items);
        }
      } catch (err) {
        console.error('Failed to apply resolutions:', err);
        // Continue to publish even if resolution fails
      } finally {
        setIsApplyingResolutions(false);
      }
    }

    setCurrentStep('publish');
  }, [checklist, comparison, resolutions]);

  // Handle Confluence page selection - auto-populate project and customer names
  const handleConfluencePageSelect = useCallback((page) => {
    setSelectedConfluencePage(page);

    // Auto-populate project name from page title
    if (page?.title) {
      setProjectName(page.title);
    }

    // Auto-populate customer name from ancestors
    // Hierarchy: Customer → Family of Parts → Project
    // Ancestors array from Confluence: [root/space, ..., customer, family_of_parts]
    // So customer is the second-to-last ancestor (grandparent)
    if (page?.ancestors && page.ancestors.length >= 2) {
      // Get the grandparent (Customer level)
      const customer = page.ancestors[page.ancestors.length - 2];
      if (customer?.title) {
        setCustomerName(customer.title);
      }
    } else if (page?.ancestors && page.ancestors.length === 1) {
      // Only one ancestor - use it as customer
      const customer = page.ancestors[0];
      if (customer?.title) {
        setCustomerName(customer.title);
      }
    }
  }, []);

  // Handle publish to Confluence
  const handlePublish = useCallback(async () => {
    // Use ref to get the most current checklist (avoids stale closure issues)
    const currentChecklist = checklistRef.current;

    if (!currentChecklist) {
      setError('No checklist to publish');
      return;
    }

    // Debug logging to verify checklist state
    console.log('Publishing checklist - resolutions_applied:', currentChecklist.resolutions_applied);
    console.log('Publishing checklist - resolution_summary:', currentChecklist.resolution_summary);
    console.log('Selected page for update:', selectedConfluencePage?.id, selectedConfluencePage?.title);

    setIsLoading(true);
    setError(null);

    try {
      let result;

      // If a Confluence page is selected, use template update mode
      if (selectedConfluencePage?.id) {
        console.log('Using template update mode for page:', selectedConfluencePage.id);

        // Extract quote assumptions from comparison data
        const quoteAssumptions = [];
        if (comparison?.quote_only_items) {
          comparison.quote_only_items.forEach(item => {
            if (item.quote_assumption) {
              quoteAssumptions.push(item.quote_assumption);
            }
          });
        }
        // Also add assumptions from conflicts
        if (comparison?.conflicts) {
          comparison.conflicts.forEach(conflict => {
            if (conflict.quote_assumption) {
              quoteAssumptions.push(conflict.quote_assumption);
            }
          });
        }

        console.log('Quote assumptions to add:', quoteAssumptions.length);

        result = await updateTemplateWithChecklist(
          currentChecklist,
          selectedConfluencePage.id,
          quoteAssumptions
        );
      } else {
        // No page selected - create a new page (old behavior)
        console.log('Creating new Confluence page');
        result = await publishChecklist(currentChecklist, null);
      }

      setConfluenceUrl(result.page_url);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to publish to Confluence';
      // Provide helpful error message for credential issues
      if (detail.includes('not permitted') || detail.includes('not configured')) {
        setError('Confluence credentials not configured. Please check your .env file has CONFLUENCE_URL, CONFLUENCE_EMAIL, and CONFLUENCE_API_TOKEN set correctly.');
      } else {
        setError(detail);
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedConfluencePage, comparison]); // Using ref for checklist, so no dependency needed

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
    // Reset quote state
    setQuoteAssumptions(null);
    setComparison(null);
    setMergePreview(null);
    // Reset resolution state
    setResolutions({});
    setIsApplyingResolutions(false);
    setActionItemsCreated([]);
    // Reset Confluence selection
    setSelectedConfluencePage(null);
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
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Step 1: Select Confluence Page */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Step 1: Select Project Page
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Search for the existing Confluence page for this project. This will auto-fill the project and customer names.
              </p>

              <ConfluenceSearch
                onPageSelect={handleConfluencePageSelect}
                disabled={isLoading}
              />

              {selectedConfluencePage && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle className="h-4 w-4" />
                    <span className="text-sm font-medium">Page selected</span>
                  </div>
                  <p className="text-sm text-green-600 mt-1">
                    Project: <strong>{selectedConfluencePage.title}</strong>
                  </p>
                  {selectedConfluencePage.ancestors?.length > 0 && (
                    <p className="text-xs text-green-600 mt-1">
                      Path: {selectedConfluencePage.ancestors.map(a => a.title).reverse().join(' → ')} → {selectedConfluencePage.title}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Step 2: Upload Documents */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Step 2: Upload Specification Documents
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Upload customer specs, drawings, and quotes. The AI will analyze
                them against 40+ APQP checklist items.
              </p>

              {/* Project Name - auto-filled but editable */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project Name *
                  {selectedConfluencePage && <span className="text-xs text-gray-500 ml-2">(from Confluence)</span>}
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Select a page above or enter manually"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={isLoading}
                />
              </div>

              {/* Customer Name - auto-filled but editable */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Customer Name
                  {selectedConfluencePage?.ancestors?.length > 0 && <span className="text-xs text-gray-500 ml-2">(from Confluence)</span>}
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Auto-filled from Confluence parent"
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

        {/* Step: Upload Quote */}
        {currentStep === 'quote' && (
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Quote Upload */}
              <div>
                <QuoteUpload
                  projectName={projectName}
                  onQuoteExtracted={handleQuoteExtracted}
                  disabled={isLoading}
                />

                {/* Compare Button */}
                {quoteAssumptions && (
                  <button
                    onClick={handleCompareQuote}
                    disabled={isLoading}
                    className="mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Comparing...
                      </>
                    ) : (
                      <>
                        <GitCompare className="h-5 w-5" />
                        Compare Quote vs. Checklist
                      </>
                    )}
                  </button>
                )}

                {/* Skip Button */}
                <button
                  onClick={handleSkipQuote}
                  disabled={isLoading}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 text-gray-600 font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <SkipForward className="h-4 w-4" />
                  Skip Quote Comparison
                </button>
              </div>

              {/* Checklist Preview (collapsed) */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Generated Checklist
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  {checklist?.statistics?.requirements_found || 0} requirements found from customer documents
                </p>
                <div className="max-h-80 overflow-y-auto border border-gray-100 rounded-lg">
                  <ChecklistPreview
                    checklist={checklist}
                    onChecklistChange={setChecklist}
                    isLoading={false}
                    compact={true}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step: Comparison Results */}
        {currentStep === 'compare' && (
          <div className="max-w-5xl mx-auto space-y-6">
            <ComparisonView
              comparison={comparison}
              mergePreview={mergePreview}
              resolutions={resolutions}
              onResolve={handleResolve}
              onApplyResolutions={handleApplyResolutions}
              onRequestMerge={handleGenerateMergePreview}
              isLoading={isLoading}
              isApplying={isApplyingResolutions}
            />

            {/* Action Buttons */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setCurrentStep('quote')}
                disabled={isLoading || isApplyingResolutions}
                className="px-4 py-2 text-gray-600 font-medium border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Back to Quote
              </button>
              {/* Show skip button only if there are no conflicts or conflicts aren't all resolved */}
              {(!comparison?.conflicts?.length || Object.keys(resolutions).length < comparison?.conflicts?.length) && (
                <button
                  onClick={handleProceedToPublish}
                  disabled={isLoading || isApplyingResolutions}
                  className="flex items-center gap-2 px-6 py-3 bg-gray-500 text-white font-medium rounded-lg hover:bg-gray-600 disabled:opacity-50"
                >
                  <SkipForward className="h-5 w-5" />
                  Skip to Publish
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step: Publish */}
        {currentStep === 'publish' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Pre-Meeting Checklist: {projectName}
                </h2>
                {customerName && (
                  <p className="text-sm text-gray-500">Customer: {customerName}</p>
                )}
                {comparison && (
                  <p className="text-sm text-gray-500">
                    Quote compared: {comparison.vendor_name || 'Unknown vendor'}
                    {comparison.statistics?.total_conflicts > 0 && (
                      <span className="text-red-600 ml-2">
                        ({comparison.statistics.total_conflicts} conflicts)
                      </span>
                    )}
                  </p>
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

            {/* Confluence Page Selection */}
            {!confluenceUrl && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Select Parent Page in Confluence (Optional)
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  Search for an existing page to publish under, or leave empty to create at the root of the space.
                </p>
                <ConfluenceSearch
                  onPageSelect={handleConfluencePageSelect}
                  disabled={isLoading}
                />
                {selectedConfluencePage && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-green-700">
                    <CheckCircle className="h-4 w-4" />
                    Will publish under: <strong>{selectedConfluencePage.title}</strong>
                  </div>
                )}
              </div>
            )}

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

            {/* Show action items created from resolutions */}
            {actionItemsCreated.length > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-orange-700 mb-3">
                  Action Items Created ({actionItemsCreated.length})
                </h3>
                <p className="text-sm text-orange-600 mb-3">
                  The following action items need to be discussed with the vendor:
                </p>
                <div className="space-y-2">
                  {actionItemsCreated.map((item, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-lg border border-orange-100">
                      <p className="font-medium text-gray-900">{item.title}</p>
                      {item.description && (
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">{item.description}</p>
                      )}
                      <div className="mt-2 flex gap-3 text-xs text-gray-500">
                        {item.assignee_hint && <span>Assignee: {item.assignee_hint}</span>}
                        {item.due_date_hint && <span>Due: {item.due_date_hint}</span>}
                        <span className={`px-2 py-0.5 rounded ${
                          item.priority === 'high' ? 'bg-red-100 text-red-700' :
                          item.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {item.priority}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Show comparison summary if we did comparison */}
            {comparison && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Comparison Summary
                </h3>
                <div className="grid grid-cols-4 gap-3 text-sm">
                  <div className="p-2 bg-green-50 rounded text-center">
                    <p className="text-lg font-bold text-green-700">{comparison.statistics?.total_matches || 0}</p>
                    <p className="text-xs text-green-600">Matches</p>
                  </div>
                  <div className="p-2 bg-red-50 rounded text-center">
                    <p className="text-lg font-bold text-red-700">{comparison.statistics?.total_conflicts || 0}</p>
                    <p className="text-xs text-red-600">Conflicts</p>
                  </div>
                  <div className="p-2 bg-blue-50 rounded text-center">
                    <p className="text-lg font-bold text-blue-700">{comparison.statistics?.quote_only_count || 0}</p>
                    <p className="text-xs text-blue-600">Quote Only</p>
                  </div>
                  <div className="p-2 bg-orange-50 rounded text-center">
                    <p className="text-lg font-bold text-orange-700">{comparison.statistics?.checklist_only_count || 0}</p>
                    <p className="text-xs text-orange-600">Unaddressed</p>
                  </div>
                </div>
              </div>
            )}

            <ChecklistPreview
              checklist={checklist}
              onChecklistChange={setChecklist}
              isLoading={isLoading && !checklist}
            />
          </div>
        )}
      </main>
    </div>
  );
}
