/**
 * QuoteUpload Component
 * Upload vendor quote PDF and extract assumptions for comparison
 */

import { useState, useCallback, useRef } from 'react';
import {
  FileUp,
  FileText,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  ListChecks,
} from 'lucide-react';

import { extractQuoteAssumptions } from '../services/api';

export default function QuoteUpload({
  projectName,
  onQuoteExtracted,
  disabled = false,
}) {
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [extractedQuote, setExtractedQuote] = useState(null);

  const fileInputRef = useRef(null);

  // Handle file selection
  const handleFileSelect = useCallback((event) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    // Validate file type
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please upload a PDF, DOCX, or TXT file');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setExtractedQuote(null);
  }, []);

  // Handle drag and drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
      if (!validTypes.includes(droppedFile.type)) {
        setError('Please upload a PDF, DOCX, or TXT file');
        return;
      }
      setFile(droppedFile);
      setError(null);
      setExtractedQuote(null);
    }
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  // Remove file
  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setExtractedQuote(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Extract assumptions from quote
  const handleExtract = useCallback(async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const result = await extractQuoteAssumptions(file, projectName, setUploadProgress);
      setExtractedQuote(result);

      if (onQuoteExtracted) {
        onQuoteExtracted(result);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to extract quote assumptions');
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  }, [file, projectName, onQuoteExtracted]);

  // Format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="h-5 w-5 text-primary-600" />
        <h3 className="text-lg font-semibold text-gray-900">Upload Vendor Quote</h3>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        Upload the vendor's quote PDF to extract their "Important Notes and Assumptions" for comparison.
      </p>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* File Upload Zone */}
      {!file && !extractedQuote && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => !disabled && fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${disabled ? 'border-gray-200 bg-gray-50 cursor-not-allowed' : 'border-gray-300 hover:border-primary-400 hover:bg-primary-50'}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileSelect}
            className="hidden"
            disabled={disabled}
          />
          <FileUp className={`h-10 w-10 mx-auto mb-3 ${disabled ? 'text-gray-300' : 'text-gray-400'}`} />
          <p className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
            Drop vendor quote here or click to browse
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Supports PDF, DOCX, TXT
          </p>
        </div>
      )}

      {/* Selected File */}
      {file && !extractedQuote && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <FileText className="h-8 w-8 text-primary-600" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
              <p className="text-xs text-gray-500">{formatSize(file.size)}</p>
            </div>
            {!isLoading && (
              <button
                onClick={handleRemoveFile}
                className="p-1 hover:bg-gray-200 rounded"
                disabled={disabled}
              >
                <X className="h-4 w-4 text-gray-500" />
              </button>
            )}
          </div>

          {/* Upload Progress */}
          {isLoading && uploadProgress > 0 && (
            <div>
              <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                <span>Uploading and analyzing...</span>
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

          {/* Extract Button */}
          <button
            onClick={handleExtract}
            disabled={disabled || isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Extracting Assumptions...
              </>
            ) : (
              <>
                <ListChecks className="h-5 w-5" />
                Extract Quote Assumptions
              </>
            )}
          </button>
        </div>
      )}

      {/* Extracted Quote Summary */}
      {extractedQuote && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-700">Quote Analyzed Successfully</p>
              <p className="text-xs text-green-600">
                {extractedQuote.assumptions?.length || 0} assumptions extracted
              </p>
            </div>
            <button
              onClick={handleRemoveFile}
              className="text-sm text-green-600 hover:text-green-800 font-medium"
              disabled={disabled}
            >
              Change Quote
            </button>
          </div>

          {/* Vendor Info */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs uppercase tracking-wider">Vendor</p>
              <p className="font-medium text-gray-900">
                {extractedQuote.vendor_name || 'Unknown'}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs uppercase tracking-wider">Quote #</p>
              <p className="font-medium text-gray-900">
                {extractedQuote.quote_number || 'N/A'}
              </p>
            </div>
          </div>

          {/* Assumptions Preview */}
          {extractedQuote.assumptions && extractedQuote.assumptions.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Extracted Assumptions ({extractedQuote.assumptions.length})
              </p>
              <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100">
                {extractedQuote.assumptions.slice(0, 5).map((assumption, index) => (
                  <div key={index} className="p-3">
                    <p className="text-xs font-medium text-primary-600 uppercase tracking-wider mb-1">
                      {assumption.category_name?.split(' - ')[0] || assumption.category_id}
                    </p>
                    <p className="text-sm text-gray-700">{assumption.text}</p>
                  </div>
                ))}
                {extractedQuote.assumptions.length > 5 && (
                  <div className="p-2 text-center text-xs text-gray-500 bg-gray-50">
                    +{extractedQuote.assumptions.length - 5} more assumptions
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
