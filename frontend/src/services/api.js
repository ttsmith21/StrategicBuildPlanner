/**
 * API Service Layer for Strategic Build Planner
 * Handles all communication with the FastAPI backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Health check
 */
export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}

/**
 * Ingest documents and create vector store
 * @param {string} projectName - Name of the project
 * @param {File[]} files - Array of files to upload
 * @param {function} onProgress - Progress callback
 */
export async function ingestDocuments(projectName, files, onProgress) {
  const formData = new FormData();
  formData.append('project_name', projectName);

  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post('/api/ingest', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return response.data;
}

/**
 * Generate Strategic Build Plan draft
 * @param {string} vectorStoreId - Vector store ID from ingest
 * @param {string} projectName - Project name
 * @param {object} options - Additional options
 */
export async function generateDraft(vectorStoreId, projectName, options = {}) {
  const response = await api.post('/api/draft', {
    vector_store_id: vectorStoreId,
    project_name: projectName,
    include_markdown: options.includeMarkdown ?? true,
  });

  return response.data;
}

/**
 * Grade a Strategic Build Plan
 * @param {object} planJson - The plan JSON to grade
 */
export async function gradePlan(planJson) {
  const response = await api.post('/api/qa/grade', {
    plan_json: planJson,
  });

  return response.data;
}

/**
 * Get QA grading rubric
 */
export async function getGradingRubric() {
  const response = await api.get('/api/qa/rubric');
  return response.data;
}

/**
 * Apply meeting transcript to plan
 * @param {object} planJson - Current plan JSON
 * @param {string} transcript - Meeting transcript text
 * @param {object} options - Additional options
 */
export async function applyMeetingTranscript(planJson, transcript, options = {}) {
  const response = await api.post('/api/meeting/apply', {
    plan_json: planJson,
    transcript: transcript,
    create_asana_tasks: options.createAsanaTasks ?? false,
  });

  return response.data;
}

/**
 * Publish plan to Confluence
 * @param {object} planJson - Plan JSON to publish
 * @param {string} title - Page title
 * @param {string} parentPageTitle - Parent page title (Family of Parts)
 */
export async function publishToConfluence(planJson, title, parentPageTitle) {
  const response = await api.post('/api/publish', {
    plan_json: planJson,
    title: title,
    parent_page_title: parentPageTitle,
    auto_find_parent: true,
  });

  return response.data;
}

/**
 * Search Confluence pages
 * @param {string} query - CQL search query
 */
export async function searchConfluence(query) {
  const response = await api.get('/api/publish/search', {
    params: { query },
  });

  return response.data;
}

/**
 * Generate pre-meeting checklist
 * @param {string} vectorStoreId - Vector store ID from ingest
 * @param {string} projectName - Project name
 * @param {string} customer - Optional customer name
 * @param {string[]} categoryIds - Optional category filter
 */
export async function generateChecklist(vectorStoreId, projectName, customer = null, categoryIds = null) {
  const response = await api.post('/api/checklist', {
    vector_store_id: vectorStoreId,
    project_name: projectName,
    customer: customer,
    category_ids: categoryIds,
  });

  return response.data;
}

/**
 * Get checklist prompts
 */
export async function getChecklistPrompts() {
  const response = await api.get('/api/checklist/prompts');
  return response.data;
}

/**
 * Get active checklist prompts
 */
export async function getActivePrompts() {
  const response = await api.get('/api/checklist/prompts/active');
  return response.data;
}

/**
 * Publish checklist to Confluence
 * @param {object} checklist - The checklist object to publish
 * @param {string} parentPageId - Optional parent page ID in Confluence
 */
export async function publishChecklist(checklist, parentPageId = null) {
  const response = await api.post('/api/checklist/publish', {
    checklist: checklist,
    parent_page_id: parentPageId,
  });

  return response.data;
}

/**
 * Update an existing Confluence template page with checklist data
 * This preserves the template structure and injects checklist items into appropriate sections
 * @param {object} checklist - The checklist data to publish
 * @param {string} pageId - The ID of the existing page to update
 * @param {string[]} quoteAssumptions - List of quote assumptions to add
 * @returns {Promise<object>} - Published page info with page_url
 */
export async function updateTemplateWithChecklist(checklist, pageId, quoteAssumptions = []) {
  const response = await api.post('/api/checklist/publish/template', {
    checklist: checklist,
    page_id: pageId,
    quote_assumptions: quoteAssumptions,
  });

  return response.data;
}

// ============================================================================
// Confluence Navigation API
// ============================================================================

/**
 * Search Confluence pages by job number (e.g., F12345)
 * @param {string} query - Job number or search term
 * @param {string} space - Confluence space key (default: KB)
 */
export async function searchConfluencePages(query, space = 'KB') {
  const response = await api.get('/api/confluence/search', {
    params: { q: query, space },
  });
  return response.data;
}

/**
 * Get Confluence page hierarchy for browsing
 * @param {string} parentId - Parent page ID (null for root)
 * @param {string} space - Confluence space key
 */
export async function getConfluenceHierarchy(parentId = null, space = 'KB') {
  const response = await api.get('/api/confluence/hierarchy', {
    params: { parent_id: parentId, space },
  });
  return response.data;
}

/**
 * Get a Confluence page with its ancestors
 * @param {string} pageId - Page ID
 */
export async function getConfluencePage(pageId) {
  const response = await api.get(`/api/confluence/page/${pageId}`);
  return response.data;
}

/**
 * Get Confluence page content as plain text
 * @param {string} pageId - Page ID
 */
export async function getConfluencePageText(pageId) {
  const response = await api.get(`/api/confluence/page/${pageId}/text`);
  return response.data;
}

/**
 * Get full context for a Confluence page (page + ancestors + children)
 * @param {string} pageId - Page ID
 */
export async function getConfluencePageContext(pageId) {
  const response = await api.get(`/api/confluence/page/${pageId}/context`);
  return response.data;
}

// ============================================================================
// Quote Comparison API
// ============================================================================

/**
 * Extract assumptions from a vendor quote PDF
 * @param {File} file - Quote PDF file
 * @param {string} projectName - Project name for context
 * @param {function} onProgress - Upload progress callback
 */
export async function extractQuoteAssumptions(file, projectName, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  if (projectName) {
    formData.append('project_name', projectName);
  }

  const response = await api.post('/api/quote/extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return response.data;
}

/**
 * Compare quote assumptions against checklist requirements
 * @param {object} quoteAssumptions - Output from extractQuoteAssumptions
 * @param {object} checklist - Checklist from generateChecklist
 */
export async function compareQuoteWithChecklist(quoteAssumptions, checklist) {
  const response = await api.post('/api/quote/compare', {
    quote_assumptions: quoteAssumptions,
    checklist: checklist,
  });

  return response.data;
}

/**
 * Generate merge preview with conflict highlights
 * @param {object} checklist - Original checklist
 * @param {object} quoteAssumptions - Extracted quote assumptions
 * @param {object} comparison - Comparison results
 */
export async function generateMergePreview(checklist, quoteAssumptions, comparison) {
  const response = await api.post('/api/quote/merge-preview', {
    checklist: checklist,
    quote_assumptions: quoteAssumptions,
    comparison: comparison,
  });

  return response.data;
}

/**
 * Run full quote comparison workflow in one call
 * @param {File} quoteFile - Quote PDF file
 * @param {object} checklist - Checklist to compare against
 * @param {string} projectName - Project name
 * @param {function} onProgress - Upload progress callback
 */
export async function fullQuoteWorkflow(quoteFile, checklist, projectName, onProgress) {
  const formData = new FormData();
  formData.append('quote_file', quoteFile);
  formData.append('checklist', JSON.stringify(checklist));
  if (projectName) {
    formData.append('project_name', projectName);
  }

  const response = await api.post('/api/quote/full-workflow', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return response.data;
}

/**
 * Apply conflict resolutions and update checklist
 * @param {object} checklist - Original checklist
 * @param {object} comparison - Comparison results with conflicts
 * @param {object[]} resolutions - Array of resolution decisions
 * @returns {object} - { updated_checklist, action_items, resolution_summary }
 */
export async function resolveConflicts(checklist, comparison, resolutions) {
  const response = await api.post('/api/quote/resolve-conflicts', {
    checklist: checklist,
    comparison: comparison,
    resolutions: resolutions,
  });

  return response.data;
}

export default api;
