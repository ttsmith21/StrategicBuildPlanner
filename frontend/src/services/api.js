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

export default api;
