/**
 * ConfluenceSearch Component
 * Search for existing Confluence pages by job number or browse hierarchy
 */

import { useState, useCallback } from 'react';
import {
  Search,
  FolderTree,
  FileText,
  ChevronRight,
  ChevronDown,
  Loader2,
  Building2,
  Package,
  Wrench,
  ExternalLink,
} from 'lucide-react';

import {
  searchConfluencePages,
  getConfluenceHierarchy,
  getConfluencePage,
} from '../services/api';

// Icons for different page types
const TYPE_ICONS = {
  customer: Building2,
  family: Package,
  project: Wrench,
  page: FileText,
};

export default function ConfluenceSearch({ onPageSelect, disabled = false }) {
  const [mode, setMode] = useState('search'); // 'search' or 'browse'
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Browse state
  const [hierarchy, setHierarchy] = useState([]);
  const [expandedNodes, setExpandedNodes] = useState({});
  const [loadingNodes, setLoadingNodes] = useState({});

  // Selected page
  const [selectedPage, setSelectedPage] = useState(null);

  // Handle search
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setError(null);
    setSearchResults([]);

    try {
      const results = await searchConfluencePages(searchQuery);
      setSearchResults(results);

      if (results.length === 0) {
        setError('No pages found matching your search');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to search Confluence');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery]);

  // Load root hierarchy
  const loadRootHierarchy = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const results = await getConfluenceHierarchy(null);
      setHierarchy(results);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load Confluence hierarchy');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Toggle node expansion
  const toggleNode = useCallback(async (pageId) => {
    if (expandedNodes[pageId]) {
      // Collapse
      setExpandedNodes((prev) => ({ ...prev, [pageId]: false }));
      return;
    }

    // Expand and load children
    setLoadingNodes((prev) => ({ ...prev, [pageId]: true }));

    try {
      const children = await getConfluenceHierarchy(pageId);

      // Update hierarchy with children
      const updateHierarchy = (nodes) => {
        return nodes.map((node) => {
          if (node.id === pageId) {
            return { ...node, children };
          }
          if (node.children) {
            return { ...node, children: updateHierarchy(node.children) };
          }
          return node;
        });
      };

      setHierarchy(updateHierarchy(hierarchy));
      setExpandedNodes((prev) => ({ ...prev, [pageId]: true }));
    } catch (err) {
      setError(`Failed to load children: ${err.message}`);
    } finally {
      setLoadingNodes((prev) => ({ ...prev, [pageId]: false }));
    }
  }, [expandedNodes, hierarchy]);

  // Select a page
  const handleSelectPage = useCallback(async (page) => {
    setSelectedPage(page);

    if (onPageSelect) {
      // Load full page data with ancestors
      try {
        const fullPage = await getConfluencePage(page.id);
        onPageSelect(fullPage);
      } catch (err) {
        // Still pass the basic page info
        onPageSelect(page);
      }
    }
  }, [onPageSelect]);

  // Switch mode
  const handleModeChange = (newMode) => {
    setMode(newMode);
    setError(null);

    if (newMode === 'browse' && hierarchy.length === 0) {
      loadRootHierarchy();
    }
  };

  // Render a tree node
  const renderTreeNode = (node, depth = 0) => {
    const isExpanded = expandedNodes[node.id];
    const isLoadingNode = loadingNodes[node.id];
    const isSelected = selectedPage?.id === node.id;
    const Icon = TYPE_ICONS[node.type] || FileText;

    return (
      <div key={node.id}>
        <div
          className={`
            flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer
            transition-colors duration-150
            ${isSelected ? 'bg-primary-100 text-primary-700' : 'hover:bg-gray-100'}
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
          style={{ paddingLeft: `${depth * 20 + 12}px` }}
          onClick={() => !disabled && handleSelectPage(node)}
        >
          {node.has_children ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (!disabled) toggleNode(node.id);
              }}
              className="p-0.5 hover:bg-gray-200 rounded"
              disabled={disabled}
            >
              {isLoadingNode ? (
                <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
              ) : isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}

          <Icon className={`h-4 w-4 ${isSelected ? 'text-primary-600' : 'text-gray-500'}`} />

          <span className={`text-sm flex-1 truncate ${isSelected ? 'font-medium' : ''}`}>
            {node.title}
          </span>

          {node.url && (
            <a
              href={node.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100"
            >
              <ExternalLink className="h-3 w-3 text-gray-400" />
            </a>
          )}
        </div>

        {isExpanded && node.children && (
          <div>
            {node.children.map((child) => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Mode Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => handleModeChange('search')}
          className={`
            flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium
            transition-colors duration-150 border-b-2
            ${mode === 'search'
              ? 'text-primary-600 border-primary-600 bg-primary-50'
              : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
            }
          `}
          disabled={disabled}
        >
          <Search className="h-4 w-4" />
          Search by Job #
        </button>
        <button
          onClick={() => handleModeChange('browse')}
          className={`
            flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium
            transition-colors duration-150 border-b-2
            ${mode === 'browse'
              ? 'text-primary-600 border-primary-600 bg-primary-50'
              : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
            }
          `}
          disabled={disabled}
        >
          <FolderTree className="h-4 w-4" />
          Browse Hierarchy
        </button>
      </div>

      <div className="p-4">
        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Search Mode */}
        {mode === 'search' && (
          <div>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Enter job number (e.g., F12345)"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={disabled || isLoading}
              />
              <button
                onClick={handleSearch}
                disabled={disabled || isLoading || !searchQuery.trim()}
                className="px-4 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Search className="h-5 w-5" />
                )}
              </button>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100">
                {searchResults.map((page) => {
                  const isSelected = selectedPage?.id === page.id;
                  return (
                    <div
                      key={page.id}
                      onClick={() => !disabled && handleSelectPage(page)}
                      className={`
                        flex items-center gap-3 p-3 cursor-pointer transition-colors
                        ${isSelected ? 'bg-primary-50' : 'hover:bg-gray-50'}
                        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                      `}
                    >
                      <FileText className={`h-5 w-5 ${isSelected ? 'text-primary-600' : 'text-gray-400'}`} />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm truncate ${isSelected ? 'font-medium text-primary-700' : 'text-gray-900'}`}>
                          {page.title}
                        </p>
                        {page.ancestors && page.ancestors.length > 0 && (
                          <p className="text-xs text-gray-500 truncate">
                            {page.ancestors.map((a) => a.title).join(' > ')}
                          </p>
                        )}
                      </div>
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 hover:bg-gray-200 rounded"
                      >
                        <ExternalLink className="h-4 w-4 text-gray-400" />
                      </a>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Browse Mode */}
        {mode === 'browse' && (
          <div className="max-h-80 overflow-y-auto">
            {isLoading && hierarchy.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                <span className="ml-2 text-sm text-gray-500">Loading hierarchy...</span>
              </div>
            ) : hierarchy.length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-500">
                No pages found in Confluence
              </div>
            ) : (
              <div className="space-y-0.5">
                {hierarchy.map((node) => renderTreeNode(node))}
              </div>
            )}
          </div>
        )}

        {/* Selected Page Info */}
        {selectedPage && (
          <div className="mt-4 p-3 bg-primary-50 border border-primary-200 rounded-lg">
            <p className="text-sm font-medium text-primary-700">Selected Page</p>
            <p className="text-sm text-primary-600">{selectedPage.title}</p>
          </div>
        )}
      </div>
    </div>
  );
}
