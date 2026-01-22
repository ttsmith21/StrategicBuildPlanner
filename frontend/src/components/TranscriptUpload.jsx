/**
 * TranscriptUpload Component
 * Handles text transcript file upload for post-meeting review
 */

import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  FileText,
  Upload,
  X,
  FileUp,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';

const ACCEPTED_TYPES = {
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
};

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export default function TranscriptUpload({ onTranscriptReady, disabled = false }) {
  const [file, setFile] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [isReading, setIsReading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const validateFile = useCallback((file) => {
    // Check file type
    const validTypes = Object.keys(ACCEPTED_TYPES).flatMap(type => ACCEPTED_TYPES[type]);
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validTypes.includes(ext)) {
      return `Invalid file type. Please upload a .txt or .md file.`;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size is 5MB.`;
    }

    return null;
  }, []);

  const readFile = useCallback(async (file) => {
    setIsReading(true);
    setError(null);

    try {
      const text = await file.text();
      setTranscript(text);
      setFile(file);
      if (onTranscriptReady) {
        onTranscriptReady(text);
      }
    } catch (err) {
      setError(`Failed to read file: ${err.message}`);
    } finally {
      setIsReading(false);
    }
  }, [onTranscriptReady]);

  const handleFileSelect = useCallback((selectedFile) => {
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    readFile(selectedFile);
  }, [validateFile, readFile]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);

    if (disabled) return;

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      handleFileSelect(droppedFiles[0]);
    }
  }, [disabled, handleFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback((e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  }, [handleFileSelect]);

  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setTranscript('');
    setError(null);
    if (onTranscriptReady) {
      onTranscriptReady(null);
    }
  }, [onTranscriptReady]);

  const handleTextChange = useCallback((e) => {
    const text = e.target.value;
    setTranscript(text);
    if (onTranscriptReady) {
      onTranscriptReady(text || null);
    }
  }, [onTranscriptReady]);

  // Word count for display
  const wordCount = transcript ? transcript.trim().split(/\s+/).filter(Boolean).length : 0;

  return (
    <div className="space-y-4">
      {/* Error display */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-500 hover:text-red-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* File upload zone */}
      {!file && !transcript && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center transition-colors
            ${isDragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-gray-400'}
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <input
            type="file"
            accept=".txt,.md"
            onChange={handleInputChange}
            disabled={disabled}
            className="hidden"
            id="transcript-upload"
          />
          <label
            htmlFor="transcript-upload"
            className={`flex flex-col items-center ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
              {isReading ? (
                <Loader2 className="h-6 w-6 text-gray-400 animate-spin" />
              ) : (
                <Upload className="h-6 w-6 text-gray-400" />
              )}
            </div>
            <p className="text-sm font-medium text-gray-900 mb-1">
              {isReading ? 'Reading file...' : 'Upload meeting transcript'}
            </p>
            <p className="text-xs text-gray-500">
              Drag and drop or click to browse
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Supports .txt and .md files (max 5MB)
            </p>
          </label>
        </div>
      )}

      {/* File uploaded display */}
      {file && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {wordCount.toLocaleString()} words
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              disabled={disabled}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Or paste text */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">or paste transcript</span>
        </div>
      </div>

      {/* Text area for manual input */}
      <div>
        <textarea
          value={transcript}
          onChange={handleTextChange}
          disabled={disabled}
          placeholder="Paste your meeting transcript here..."
          rows={10}
          className={`
            w-full px-4 py-3 border border-gray-300 rounded-lg
            focus:ring-2 focus:ring-primary-500 focus:border-primary-500
            resize-y min-h-[200px]
            ${disabled ? 'bg-gray-50 cursor-not-allowed' : ''}
          `}
        />
        {transcript && (
          <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
            <span>{wordCount.toLocaleString()} words</span>
            <span>{transcript.length.toLocaleString()} characters</span>
          </div>
        )}
      </div>
    </div>
  );
}

TranscriptUpload.propTypes = {
  onTranscriptReady: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};
