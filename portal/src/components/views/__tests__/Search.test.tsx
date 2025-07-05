import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import Search from '../Search'

interface AssetDetailsModalProps {
  isOpen: boolean;
  assetUri: string | null;
  onClose: () => void;
}

// Mock AssetDetailsModal
vi.mock('../AssetDetailsModal', () => ({
  default: ({ isOpen, onClose }: AssetDetailsModalProps) => 
    isOpen ? (
      <div data-testid="asset-modal">
        <div data-testid="modal-title">Asset Details</div>
        <button data-testid="modal-close" onClick={onClose}>Close</button>
        <div className="asset-tabs">
          <button className="tab-btn active">Details</button>
          <button className="tab-btn">Relationships</button>
          <button className="tab-btn">Code</button>
        </div>
        <div className="tab-content">
          <div className="asset-info">
            <div className="info-section">
              <h4>Basic Information</h4>
              <div className="info-grid">
                <div className="info-item">
                  <label>Name:</label>
                  <span>Test Asset</span>
                </div>
                <div className="info-item">
                  <label>Type:</label>
                  <span>http://example.com/Class</span>
                </div>
                <div className="info-item">
                  <label>Language:</label>
                  <span>JavaScript</span>
                </div>
                <div className="info-item">
                  <label>Canonical Name:</label>
                  <span>TestAsset</span>
                </div>
              </div>
            </div>
            <div className="info-section">
              <h4>Location</h4>
              <div className="info-grid">
                <div className="info-item">
                  <label>Repository:</label>
                  <span>repo</span>
                </div>
                <div className="info-item">
                  <label>Path:</label>
                  <span>/src/test.js</span>
                </div>
                <div className="info-item">
                  <label>Lines:</label>
                  <span>10-15</span>
                </div>
              </div>
            </div>
            <div className="info-section">
              <h4>Description</h4>
              <p>Test description</p>
            </div>
          </div>
        </div>
      </div>
    ) : null
}))

describe('Search', () => {
  const renderWithRouter = (ui: ReactElement) => {
    return render(ui, { wrapper: BrowserRouter })
  }

  let mockFetch: ReturnType<typeof vi.fn>
  let mockAlert: ReturnType<typeof vi.fn>
  let localStorageMock: {
    getItem: ReturnType<typeof vi.fn>
    setItem: ReturnType<typeof vi.fn>
    removeItem: ReturnType<typeof vi.fn>
    clear: ReturnType<typeof vi.fn>
  }

  beforeEach(() => {
    mockFetch = vi.fn((url: string) => {
      if (typeof url === 'string' && url.includes('/api/search')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ 
            results: [
              {
                uri: 'http://example.com/Class',
                name: 'Test Entity',
                type: 'Class',
                description: 'Test description',
                repository: 'Test Repo',
                language: 'JavaScript',
                path: '/src/test.js',
                lines: '10-15'
              }
            ] 
          })
        })
      } else if (typeof url === 'string' && url.includes('/api/search/suggestions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            suggestions: [
              { title: 'Test Suggestion', type: 'Class' }
            ]
          })
        })
      } else if (typeof url === 'string' && url.includes('/api/sparql')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            results: {
              bindings: [
                {
                  repository: { value: 'http://example.com/repo1' },
                  name: { value: 'Test Repo' }
                }
              ]
            }
          })
        })
      }
      return Promise.resolve({ ok: false })
    })
    
    mockAlert = vi.fn()
    globalThis.fetch = mockFetch as unknown as typeof fetch
    globalThis.alert = mockAlert as unknown as typeof alert
    
    localStorageMock = {
      getItem: vi.fn().mockReturnValue('[]'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    }
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders search form', () => {
    renderWithRouter(<Search />)
    
    expect(screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
  })

  it('handles search input changes', () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    
    expect(searchInput).toHaveValue('test query')
  })

  it('performs search on form submission', async () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test' } })
    fireEvent.submit(searchForm!)
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/search', expect.any(Object))
    })
  })

  it('shows loading state during search', async () => {
    // Mock a delayed response
    mockFetch.mockImplementationOnce(() => 
      new Promise(resolve => 
        setTimeout(() => resolve({
          ok: true,
          json: async () => ({ results: [] })
        }), 100)
      )
    )
    
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test' } })
    fireEvent.submit(searchForm!)
    
    // Should show loading state
    expect(screen.getByText((_, element) => {
      if (!element) return false;
      return element.tagName === 'P' && typeof element.textContent === 'string' && element.textContent.toLowerCase().includes('searching');
    })).toBeInTheDocument()
  })

  it('displays search results', async () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test' } })
    fireEvent.submit(searchForm!)
    
    // Wait for results to appear
    await waitFor(() => {
      expect(screen.getByText('Class')).toBeInTheDocument()
    })
    
    // Check that we have search results with the expected content
    expect(screen.getByText('Class')).toBeInTheDocument()
    expect(screen.getByText('/src/test.js')).toBeInTheDocument()
    expect(screen.getByText((_, element) => {
      return element?.textContent?.includes('Test description') ?? false
    }, { selector: '.result-description' })).toBeInTheDocument()
    
    // Check for JavaScript in the result specifically (not the dropdown)
    const resultLanguage = screen.getByText('JavaScript', { selector: '.result-language' })
    expect(resultLanguage).toBeInTheDocument()
  })

  it('shows alert for empty search query', () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.submit(searchForm!)
    
    expect(mockAlert).toHaveBeenCalledWith('Please enter a search query')
  })

  it('handles search error gracefully', async () => {
    // Mock fetch to throw an error
    mockFetch.mockImplementationOnce(() => 
      Promise.reject(new Error('Search error'))
    )
    
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test' } })
    fireEvent.submit(searchForm!)
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })
  })

  it('clears search results', () => {
    renderWithRouter(<Search />)
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    fireEvent.change(searchInput, { target: { value: 'test' } })
    const clearButton = document.querySelector('.clear-btn') as HTMLElement
    fireEvent.click(clearButton)
    expect(searchInput).toHaveValue('')
  })

  it('switches to advanced search mode', () => {
    renderWithRouter(<Search />)
    
    const advancedButton = screen.getByText((content) => content.includes('Advanced'))
    fireEvent.click(advancedButton)
    
    expect(advancedButton).toHaveClass('active')
  })

  it('shows asset details modal when result is clicked', async () => {
    renderWithRouter(<Search />)
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    fireEvent.change(searchInput, { target: { value: 'test' } })
    fireEvent.submit(searchForm!)

    // Wait for the result to appear and click the "View Details" button
    const viewDetailsButton = await screen.findByText('View Details')
    fireEvent.click(viewDetailsButton)

    // Wait for the modal to appear (look for unique string in the mock modal)
    await waitFor(() => {
      expect(screen.getByText(/Asset Details/i)).toBeInTheDocument()
    })
  })

  it('filters results by type', () => {
    renderWithRouter(<Search />)
    
    const typeFilter = screen.getByDisplayValue('All Types')
    fireEvent.change(typeFilter, { target: { value: 'ClassDefinition' } })
    
    expect(typeFilter).toHaveValue('ClassDefinition')
  })

  it('filters results by language', () => {
    renderWithRouter(<Search />)
    
    const languageFilter = screen.getByDisplayValue('All Languages')
    fireEvent.change(languageFilter, { target: { value: 'javascript' } })
    
    expect(languageFilter).toHaveValue('javascript')
  })

  it('saves search to history', async () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    fireEvent.submit(searchForm!)
    
    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith('recentSearches', expect.any(String))
    })
  })

  it('loads recent searches on mount', () => {
    localStorageMock.getItem.mockReturnValue(JSON.stringify(['recent query 1', 'recent query 2']))
    
    renderWithRouter(<Search />)
    
    expect(localStorageMock.getItem).toHaveBeenCalledWith('recentSearches')
  })

  it('handles suggestions', async () => {
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    fireEvent.change(searchInput, { target: { value: 'test' } })
    
    // Wait for suggestions to appear
    await waitFor(() => {
      // Check that mockFetch was called with the suggestions endpoint at least once
      expect(mockFetch.mock.calls.some((call: unknown[]) => Array.isArray(call) && call[0] === '/api/search/suggestions?q=test')).toBe(true)
    })
  })

  it('handles suggestion errors gracefully', async () => {
    // Mock fetch to throw an error for suggestions
    mockFetch.mockImplementationOnce(() => 
      Promise.reject(new Error('Suggestions error'))
    )
    
    renderWithRouter(<Search />)
    
    const searchInput = screen.getByPlaceholderText('Search for functions, classes, APIs, or concepts...')
    fireEvent.change(searchInput, { target: { value: 'test' } })
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })
  })
}) 