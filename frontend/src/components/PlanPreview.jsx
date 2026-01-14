/**
 * PlanPreview Component
 * Displays the generated Strategic Build Plan with tabs for JSON and Markdown views
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileJson, FileText, Copy, CheckCircle, Download } from 'lucide-react';

export default function PlanPreview({ planJson, planMarkdown, grade }) {
  const [activeTab, setActiveTab] = useState('preview');
  const [copied, setCopied] = useState(false);

  const handleCopy = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = (content, filename, type) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getGradeColor = (score) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 80) return 'text-blue-600 bg-blue-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    if (score >= 60) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };

  const tabs = [
    { id: 'preview', label: 'Preview', icon: FileText },
    { id: 'json', label: 'JSON', icon: FileJson },
  ];

  if (!planJson && !planMarkdown) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <FileText className="mx-auto h-12 w-12 text-gray-300" />
        <p className="mt-4 text-gray-500">No plan generated yet</p>
        <p className="mt-1 text-sm text-gray-400">
          Upload documents and click Generate to create a Strategic Build Plan
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header with tabs and grade */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50">
        <div className="flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px
                ${activeTab === tab.id
                  ? 'text-primary-600 border-primary-500 bg-white'
                  : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-100'
                }
              `}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {grade && (
          <div className="px-4">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(grade.overall_score)}`}>
              Score: {grade.overall_score}/100 ({grade.grade})
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'preview' && planMarkdown && (
          <div className="prose prose-sm max-w-none">
            <div className="flex justify-end gap-2 mb-4">
              <button
                onClick={() => handleCopy(planMarkdown)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                {copied ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={() => handleDownload(planMarkdown, `${planJson?.project_name || 'plan'}.md`, 'text/markdown')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                <Download className="h-4 w-4" />
                Download MD
              </button>
            </div>
            <ReactMarkdown>{planMarkdown}</ReactMarkdown>
          </div>
        )}

        {activeTab === 'json' && planJson && (
          <div>
            <div className="flex justify-end gap-2 mb-4">
              <button
                onClick={() => handleCopy(JSON.stringify(planJson, null, 2))}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                {copied ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={() => handleDownload(JSON.stringify(planJson, null, 2), `${planJson?.project_name || 'plan'}.json`, 'application/json')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                <Download className="h-4 w-4" />
                Download JSON
              </button>
            </div>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto text-sm max-h-[600px]">
              {JSON.stringify(planJson, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Grade Details */}
      {grade && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <h4 className="font-medium text-gray-700 mb-3">Quality Assessment</h4>

          {/* Dimension Scores */}
          <div className="grid grid-cols-5 gap-2 mb-4">
            {Object.entries(grade.dimension_scores || {}).map(([key, value]) => (
              <div key={key} className="text-center">
                <div className="text-lg font-semibold text-gray-800">{value}/20</div>
                <div className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</div>
              </div>
            ))}
          </div>

          {/* Strengths */}
          {grade.strengths?.length > 0 && (
            <div className="mb-3">
              <h5 className="text-sm font-medium text-green-700 mb-1">Strengths</h5>
              <ul className="text-sm text-gray-600 space-y-1">
                {grade.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Improvements */}
          {grade.improvements?.length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-yellow-700 mb-1">Suggested Improvements</h5>
              <ul className="text-sm text-gray-600 space-y-1">
                {grade.improvements.map((imp, i) => (
                  <li key={i}>• {imp}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Critical Gaps */}
          {grade.critical_gaps?.length > 0 && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
              <h5 className="text-sm font-medium text-red-700 mb-1">Critical Gaps</h5>
              <ul className="text-sm text-red-600 space-y-1">
                {grade.critical_gaps.map((gap, i) => (
                  <li key={i}>⚠️ {gap}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
