import React, { useState, useEffect, useCallback } from 'react'
import AssetDetailsModal from '../AssetDetailsModal'

// Type definitions
interface SearchResult {
  id: number
  entity: string
  title: string
  type: string
  language: string
  repository: string
  path: string
  snippet: string
  canonicalName: string
  startLine: string
  endLine: string
  description: string
  relevance: number
}

interface Suggestion {
  title: string
  type: string
}

interface Repository {
  uri: string
  name: string
}

interface Pagination {
  page: number
  total: number
  limit: number
}

interface SparqlBinding {
  value: string
  type: string
}

interface SparqlResult {
  repository: SparqlBinding
  name?: SparqlBinding
}

interface SparqlResponse {
  results?: {
    bindings: SparqlResult[]
  }
}

interface SearchApiItem {
  entity?: string
  title?: string
  type?: string
  language?: string
  repository?: string
  path?: string
  snippet?: string
  canonicalName?: string
  startLine?: string
  endLine?: string
  description?: string
  relevance?: number
}

interface SearchResponse {
  results?: SearchApiItem[]
  total?: number
}

interface SuggestionsResponse {
  suggestions?: Suggestion[]
}

/**
 * Enhanced Search component for knowledge search with advanced features
 */
function Search() {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [languageFilter, setLanguageFilter] = useState('')
  const [repositoryFilter, setRepositoryFilter] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [loading, setLoading] = useState(false)
  const [showAssetModal, setShowAssetModal] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchMode, setSearchMode] = useState('basic') // basic, advanced
  const [pagination, setPagination] = useState<Pagination>({ page: 1, total: 0, limit: 20 })
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  useEffect(() => {
    fetchRepositories()
    loadRecentSearches()
  }, [])

  // Debounced search suggestions
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.length > 2) {
        fetchSuggestions()
        // Add real-time search for better UX
        performRealTimeSearch()
      } else {
        setSuggestions([])
        setShowSuggestions(false)
        setSearchResults([])
      }
    }, 300) // 300ms debounce

    return () => clearTimeout(timer)
  }, [searchQuery]) // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * Load recent searches from localStorage
   */
  const loadRecentSearches = () => {
    try {
      const recent = JSON.parse(localStorage.getItem('recentSearches') || '[]')
      setRecentSearches(recent.slice(0, 5)) // Keep last 5 searches
    } catch (error) {
      console.error('Error loading recent searches:', error)
    }
  }

  /**
   * Save search to recent searches
   */
  const saveSearchToHistory = (query: string) => {
    try {
      const recent = JSON.parse(localStorage.getItem('recentSearches') || '[]')
      const updated = [query, ...recent.filter((q: string) => q !== query)].slice(0, 10)
      localStorage.setItem('recentSearches', JSON.stringify(updated))
      setRecentSearches(updated.slice(0, 5))
    } catch (error) {
      console.error('Error saving search history:', error)
    }
  }

  /**
   * Fetch search suggestions with improved relevance
   */
  const fetchSuggestions = useCallback(async () => {
    try {
      const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(searchQuery)}`)
      const data: SuggestionsResponse = await response.json()
      
      if (data.suggestions) {
        setSuggestions(data.suggestions)
        setShowSuggestions(data.suggestions.length > 0)
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error)
      setSuggestions([])
      setShowSuggestions(false)
    }
  }, [searchQuery])

  /**
   * Fetch repositories for the filter dropdown
   */
  const fetchRepositories = async () => {
    try {
      const query = `
        SELECT DISTINCT ?repository ?name
        WHERE {
          ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
          OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name }
        }
      `
      
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      
      const data: SparqlResponse = await response.json()
      
      const repos = (data.results?.bindings || []).map((item: SparqlResult) => ({
        uri: item.repository.value,
        name: item.name ? item.name.value : item.repository.value.split('/').pop() || ''
      }))
      
      setRepositories(repos)
    } catch (error) {
      console.error('Error fetching repositories:', error)
      setRepositories([])
    }
  }

  /**
   * Perform enhanced search with relevance scoring
   */
  const performSearch = useCallback(async (page = 1) => {
    if (!searchQuery.trim()) {
      alert('Please enter a search query')
      return
    }

    setLoading(true)
    
    try {
      const searchData = {
        query: searchQuery.trim(),
        filters: {
          type: typeFilter || undefined,
          language: languageFilter || undefined,
          repository: repositoryFilter || undefined
        },
        page: page,
        limit: pagination.limit
      }

      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchData)
      })
      
      const data: SearchResponse = await response.json()
      
      if (data.results) {
        const results: SearchResult[] = data.results.map((item: SearchApiItem, idx: number) => ({
          id: idx + 1,
          entity: item.entity || '',
          title: item.title || '',
          type: item.type || 'Unknown',
          language: item.language || '',
          repository: item.repository || '',
          path: item.path || '',
          snippet: item.snippet || '',
          canonicalName: item.canonicalName || '',
          startLine: item.startLine || '',
          endLine: item.endLine || '',
          description: item.description || '',
          relevance: item.relevance || 0
        }))
        
        setSearchResults(results)
        setPagination(prev => ({
          ...prev,
          page: page,
          total: data.total || results.length
        }))
        
        // Save to search history
        saveSearchToHistory(searchQuery.trim())
      } else {
        setSearchResults([])
      }
    } catch (error) {
      console.error('Error performing search:', error)
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }, [searchQuery, typeFilter, languageFilter, repositoryFilter, pagination.limit])

  /**
   * Perform advanced search with boolean operators
   */
  const performAdvancedSearch = async () => {
    if (!searchQuery.trim()) {
      alert('Please enter a search query')
      return
    }

    setLoading(true)
    
    try {
      const searchData = {
        query: searchQuery.trim(),
        fields: ['title', 'content', 'description'],
        operator: 'OR', // Can be made configurable
        filters: {
          type: typeFilter || undefined,
          language: languageFilter || undefined,
          repository: repositoryFilter || undefined
        }
      }

      const response = await fetch('/api/search/advanced', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchData)
      })
      
      const data: SearchResponse = await response.json()
      
      if (data.results) {
        const results: SearchResult[] = data.results.map((item: SearchApiItem, idx: number) => ({
          id: idx + 1,
          entity: item.entity || '',
          title: item.title || '',
          type: item.type || 'Unknown',
          language: item.language || '',
          repository: item.repository || '',
          path: item.path || '',
          snippet: item.snippet || '',
          description: item.description || '',
          canonicalName: item.canonicalName || '',
          startLine: item.startLine || '',
          endLine: item.endLine || '',
          relevance: item.relevance || 0
        }))
        
        setSearchResults(results)
        saveSearchToHistory(searchQuery.trim())
      } else {
        setSearchResults([])
      }
    } catch (error) {
      console.error('Error performing advanced search:', error)
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  /**
   * Perform real-time search for better UX
   */
  const performRealTimeSearch = useCallback(async () => {
    if (!searchQuery.trim() || searchQuery.length < 3) return
    
    try {
      const searchData = {
        query: searchQuery.trim(),
        filters: {
          type: typeFilter || undefined,
          language: languageFilter || undefined,
          repository: repositoryFilter || undefined
        },
        page: 1,
        limit: 10 // Show fewer results for real-time search
      }

      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchData)
      })
      
      const data: SearchResponse = await response.json()
      
      if (data.results) {
        const results: SearchResult[] = data.results.map((item: SearchApiItem, idx: number) => ({
          id: idx + 1,
          entity: item.entity || '',
          title: item.title || '',
          type: item.type || 'Unknown',
          language: item.language || '',
          repository: item.repository || '',
          path: item.path || '',
          snippet: item.snippet || '',
          canonicalName: item.canonicalName || '',
          startLine: item.startLine || '',
          endLine: item.endLine || '',
          description: item.description || '',
          relevance: item.relevance || 0
        }))
        
        setSearchResults(results)
        setPagination(prev => ({
          ...prev,
          page: 1,
          total: data.total || results.length
        }))
      }
    } catch (error) {
      console.error('Error performing real-time search:', error)
    }
  }, [searchQuery, typeFilter, languageFilter, repositoryFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPagination(prev => ({ ...prev, page: 1 }))
    if (searchMode === 'advanced') {
      performAdvancedSearch()
    } else {
      performSearch(1)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSearch(e)
    }
  }

  const handleSuggestionClick = (suggestion: Suggestion) => {
    setSearchQuery(suggestion.title)
    setShowSuggestions(false)
    // Auto-search when suggestion is clicked
    setTimeout(() => {
      setPagination(prev => ({ ...prev, page: 1 }))
      performSearch(1)
    }, 100)
  }

  const handleRecentSearchClick = (query: string) => {
    setSearchQuery(query)
    setPagination(prev => ({ ...prev, page: 1 }))
    performSearch(1)
  }

  const showAssetDetails = (assetUri: string) => {
    setSelectedAsset(assetUri)
    setShowAssetModal(true)
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    setPagination(prev => ({ ...prev, page: 1, total: 0 }))
  }

  const loadMoreResults = () => {
    const nextPage = pagination.page + 1
    performSearch(nextPage)
  }

  /**
   * Highlight search terms in text
   */
  const highlightSearchTerms = (text: string, query: string): string => {
    if (!text || !query) return text
    
    const regex = new RegExp(`(${query})`, 'gi')
    return text.replace(regex, '<mark>$1</mark>')
  }

  return (
    <div className="search-container">
      <div className="search-header">
        <div className="search-header-content">
          <h2>Knowledge Search</h2>
        </div>
        {/* Search Mode Toggle */}
        <div className="search-mode-toggle">
          <button 
            className={`mode-btn ${searchMode === 'basic' ? 'active' : ''}`}
            onClick={() => setSearchMode('basic')}
          >
            <i className="fas fa-search"></i>
            Basic Search
          </button>
          <button 
            className={`mode-btn ${searchMode === 'advanced' ? 'active' : ''}`}
            onClick={() => setSearchMode('advanced')}
          >
            <i className="fas fa-cogs"></i>
            Advanced Search
          </button>
        </div>
      </div>
      
      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-group">
          <i className="fas fa-search"></i>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setShowSuggestions(suggestions.length > 0)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onKeyPress={handleKeyPress}
            placeholder={searchMode === 'basic' 
              ? "Search for functions, classes, APIs, or concepts..." 
              : "Enter search terms with boolean operators (AND, OR)..."
            }
            className="search-input"
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Searching...
              </>
            ) : (
              <>
                Search
              </>
            )}
          </button>
          {searchQuery && (
            <button 
              type="button" 
              className="btn btn-secondary clear-btn"
              onClick={clearSearch}
            >
              <i className="fas fa-times"></i>
            </button>
          )}
          
          {/* Enhanced Suggestions */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="search-suggestions">
              <div className="suggestions-header">
                <i className="fas fa-lightbulb"></i>
                Suggestions
              </div>
              {suggestions.map((suggestion, index) => (
                <div 
                  key={index} 
                  className="suggestion-item"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  <span className="suggestion-title">{suggestion.title}</span>
                  <span className="suggestion-type">{suggestion.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Recent Searches */}
        {recentSearches.length > 0 && !searchQuery && (
          <div className="recent-searches">
            <h4>Recent Searches</h4>
            <div className="recent-tags">
              {recentSearches.map((query, index) => (
                <button
                  key={index}
                  className="recent-tag"
                  onClick={() => handleRecentSearchClick(query)}
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        )}
        
        <div className="search-filters">
          <select 
            value={typeFilter} 
            onChange={(e) => setTypeFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Types</option>
            <option value="FunctionDefinition">Functions</option>
            <option value="ClassDefinition">Classes</option>
            <option value="InterfaceDefinition">Interfaces</option>
            <option value="APIDocumentation">APIs</option>
            <option value="DocumentationFile">Documentation</option>
          </select>
          <select 
            value={languageFilter} 
            onChange={(e) => setLanguageFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Languages</option>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
          </select>
          <select 
            value={repositoryFilter} 
            onChange={(e) => setRepositoryFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Repositories</option>
            {repositories.map((repo, index) => (
              <option key={index} value={repo.uri}>
                {repo.name}
              </option>
            ))}
          </select>
        </div>
      </form>
      
      <div className="search-results">
        {loading && pagination.page === 1 ? (
          <div className="loading-container">
            <i className="fas fa-spinner fa-spin"></i>
            <p>Searching...</p>
          </div>
        ) : searchResults.length > 0 ? (
          <>
            <div className="search-results-header">
              <span className="results-count">
                Found {pagination.total} result{pagination.total !== 1 ? 's' : ''}
                {pagination.page > 1 && ` (Page ${pagination.page})`}
              </span>
              <div className="results-sort">
                <span>Sorted by relevance</span>
              </div>
            </div>
            
            <div className="results-list">
              {searchResults.map((result) => (
                <div key={result.id} className="result-item">
                  <div className="result-header">
                    <div className="result-title">
                      <span dangerouslySetInnerHTML={{ 
                        __html: highlightSearchTerms(result.title, searchQuery) 
                      }} />
                      {result.relevance && (
                        <span className="relevance-score">
                          <i className="fas fa-star"></i>
                          {result.relevance}
                        </span>
                      )}
                    </div>
                    <div className="result-type">{result.type}</div>
                  </div>
                  <div className="result-meta">
                    {result.language && (
                      <span className="result-language">{result.language}</span>
                    )}
                    {result.canonicalName && (
                      <span className="result-canonical">({result.canonicalName})</span>
                    )}
                  </div>
                  <div className="result-path">{result.path}</div>
                  {result.description && (
                    <div className="result-description" dangerouslySetInnerHTML={{ 
                      __html: highlightSearchTerms(result.description, searchQuery) 
                    }} />
                  )}
                  {result.snippet && (
                    <div className="result-snippet">
                      <pre><code>{result.snippet}</code></pre>
                    </div>
                  )}
                  <div className="result-actions">
                    <button 
                      className="btn btn-secondary btn-sm"
                      onClick={() => showAssetDetails(result.entity)}
                    >
                      <i className="fas fa-eye"></i>
                      View Details
                    </button>
                    {result.startLine && result.endLine && (
                      <span className="result-lines">
                        Lines {result.startLine}-{result.endLine}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {/* Pagination */}
            {pagination.total > pagination.limit && (
              <div className="pagination">
                <button 
                  className="btn btn-secondary"
                  onClick={loadMoreResults}
                  disabled={loading}
                >
                  {loading ? 'Loading...' : 'Load More Results'}
                </button>
              </div>
            )}
          </>
        ) : searchQuery && !loading ? (
          <div className="no-results">
            <i className="fas fa-search"></i>
            <h3>No results found for &quot;{searchQuery}&quot;</h3>
            <p>Try:</p>
            <ul>
              <li>Using different keywords</li>
              <li>Checking your spelling</li>
              <li>Using more general terms</li>
              <li>Removing some filters</li>
            </ul>
          </div>
        ) : null}
      </div>

      <AssetDetailsModal
        isOpen={showAssetModal}
        onClose={() => setShowAssetModal(false)}
        assetUri={selectedAsset}
      />
    </div>
  )
}

export default Search 