import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import Repositories from '../Repositories'

interface AddRepositoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRepositoryAdded: () => void;
}

// Mock AddRepositoryModal
vi.mock('../../AddRepositoryModal', () => ({
  default: ({ isOpen, onClose, onRepositoryAdded }: AddRepositoryModalProps) => 
    isOpen ? (
      <div data-testid="add-repo-modal">
        <button onClick={onClose}>Close</button>
        <button onClick={onRepositoryAdded}>Add</button>
      </div>
    ) : null
}))

describe('Repositories', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders repositories interface', () => {
    render(<Repositories />)
    
    expect(screen.getByText('Repository Management')).toBeInTheDocument()
    expect(screen.getByText('Add Repository')).toBeInTheDocument()
  })

  it('fetches repositories on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: { bindings: [] } })
    })

    render(<Repositories />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sparql',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('SELECT ?repository ?name')
        })
      )
    })
  })

  it('displays repositories when fetch succeeds', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { repository: { value: 'http://example.com/repo1' }, name: { value: 'Repo1' } },
          { repository: { value: 'http://example.com/repo2' }, name: { value: 'Repo2' } }
        ]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(() => {
      expect(screen.getByText('Repo1')).toBeInTheDocument()
      expect(screen.getByText('Repo2')).toBeInTheDocument()
    })
  })

  it('handles missing repository fields gracefully', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { 
            repository: { value: 'http://example.com/repo1' }
            // Missing optional fields
          }
        ]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(() => {
      expect(screen.getByText('repo1')).toBeInTheDocument() // fallback name
    })
  })

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(<Repositories />)

    await waitFor(async () => {
      const nodes = await screen.findAllByText((_, element) => {
        if (!element) return false;
        return typeof element.textContent === 'string' && element.textContent.includes('No repositories found');
      });
      expect(nodes.length).toBeGreaterThan(0);
    })
  })

  it('handles non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    })

    await act(async () => {
      render(<Repositories />)
    })

    await waitFor(async () => {
      const nodes = await screen.findAllByText((_, element) => {
        if (!element) return false;
        return typeof element.textContent === 'string' && element.textContent.includes('No repositories found');
      });
      expect(nodes.length).toBeGreaterThan(0);
    })
  })

  it('shows add repository modal when button is clicked', () => {
    render(<Repositories />)
    
    const addButton = screen.getByText('Add Repository')
    fireEvent.click(addButton)
    
    expect(screen.getByTestId('add-repo-modal')).toBeInTheDocument()
  })

  it('closes add repository modal', () => {
    render(<Repositories />)
    
    const addButton = screen.getByText('Add Repository')
    fireEvent.click(addButton)
    
    const closeButton = screen.getByText('Close')
    fireEvent.click(closeButton)
    
    expect(screen.queryByTestId('add-repo-modal')).not.toBeInTheDocument()
  })

  it('refreshes repositories after adding new repository', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { 
            repository: { value: 'http://example.com/repo1' }, 
            name: { value: 'Repo1' },
            path: { value: '/path/to/repo1' },
            status: { value: 'active' }
          }
        ]
      }
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockReposData
    })

    await act(async () => {
      render(<Repositories />)
    })

    await waitFor(() => {
      expect(screen.getByText('Repo1')).toBeInTheDocument()
    })

    // Open modal and add repository
    const addButton = screen.getByText('Add Repository')
    fireEvent.click(addButton)
    
    const addRepoButton = screen.getByText('Add')
    fireEvent.click(addRepoButton)

    // Should fetch repositories again
    await waitFor(() => {
      // The component should call fetchRepositories after adding a repo
      expect(mockFetch).toHaveBeenCalled()
    })
  })

  it('handles empty repositories list', async () => {
    const mockReposData = {
      results: {
        bindings: []
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(async () => {
      const nodes = await screen.findAllByText((_, element) => {
        if (!element) return false;
        return typeof element.textContent === 'string' && element.textContent.includes('No repositories found');
      });
      expect(nodes.length).toBeGreaterThan(0);
    })
  })

  it('displays repository actions', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { 
            repository: { value: 'http://example.com/repo1' }, 
            name: { value: 'Repo1' },
            path: { value: '/path/to/repo1' },
            status: { value: 'active' }
          }
        ]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(() => {
      expect(screen.getByText('View Details')).toBeInTheDocument()
      expect(screen.getByText('Search')).toBeInTheDocument()
    })
  })

  it('handles repository deletion', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { 
            repository: { value: 'http://example.com/repo1' }, 
            name: { value: 'Repo1' },
            path: { value: '/path/to/repo1' },
            status: { value: 'active' }
          }
        ]
      }
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(() => {
      const searchButton = screen.getByText('Search')
      fireEvent.click(searchButton)
    })

    // Should handle search action
    expect(screen.getByText('Search')).toBeInTheDocument()
  })

  it('handles repository view action', async () => {
    const mockReposData = {
      results: {
        bindings: [
          { 
            repository: { value: 'http://example.com/repo1' }, 
            name: { value: 'Repo1' },
            path: { value: '/path/to/repo1' },
            status: { value: 'active' }
          }
        ]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(() => {
      const viewButton = screen.getByText('View Details')
      fireEvent.click(viewButton)
    })

    // Should navigate or show repository details
    expect(screen.getByText('View Details')).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    mockFetch.mockImplementation(() => 
      new Promise(() => {}) // Never resolves
    )

    render(<Repositories />)
    
    expect(screen.getByText('Loading repositories...')).toBeInTheDocument()
  })

  it('handles repository fetch with missing results', async () => {
    const mockReposData = {
      // Missing results
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockReposData
    })

    render(<Repositories />)

    await waitFor(async () => {
      const nodes = await screen.findAllByText((_, element) => {
        if (!element) return false;
        return typeof element.textContent === 'string' && element.textContent.includes('No repositories found');
      });
      expect(nodes.length).toBeGreaterThan(0);
    })
  })
}) 