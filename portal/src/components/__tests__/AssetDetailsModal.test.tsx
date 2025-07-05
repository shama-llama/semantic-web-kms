import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AssetDetailsModal from '../AssetDetailsModal'

// Mock Modal component
vi.mock('../Modal', () => ({
  default: ({ children, isOpen, onClose, title }: { children: React.ReactNode; isOpen: boolean; onClose: () => void; title: string }) => 
    isOpen ? (
      <div data-testid="modal">
        <div data-testid="modal-title">{title}</div>
        <button onClick={onClose} data-testid="modal-close">Close</button>
        {children}
      </div>
    ) : null
}))

describe('AssetDetailsModal', () => {
  const mockFetch = vi.fn()
  let mockConsoleError: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    mockConsoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when not open', () => {
    render(
      <AssetDetailsModal 
        isOpen={false} 
        onClose={vi.fn()} 
        assetUri={null} 
      />
    )
    
    expect(screen.queryByTestId('modal')).not.toBeInTheDocument()
  })

  it('renders modal when open', () => {
    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )
    
    expect(screen.getByTestId('modal')).toBeInTheDocument()
    expect(screen.getByTestId('modal-title')).toHaveTextContent('Asset Details')
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => 
      new Promise(() => {}) // Never resolves
    )

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )
    
    expect(screen.getByText('Loading asset details...')).toBeInTheDocument()
  })

  it('fetches asset details when opened', async () => {
    const mockAssetData = {
      results: {
        bindings: [{
          title: { value: 'Test Asset' },
          type: { value: 'http://example.com/Class' },
          language: { value: 'JavaScript' },
          repository: { value: 'http://example.com/repo' },
          path: { value: '/src/test.js' },
          snippet: { value: 'console.log("test");' },
          canonicalName: { value: 'TestAsset' },
          startLine: { value: '10' },
          endLine: { value: '15' },
          description: { value: 'Test description' }
        }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.stringContaining('SELECT')
      })
    })
  })

  it('displays asset details when fetch succeeds', async () => {
    const mockAssetData = {
      results: {
        bindings: [{
          title: { value: 'Test Asset' },
          type: { value: 'http://example.com/Class' },
          language: { value: 'JavaScript' },
          repository: { value: 'http://example.com/repo' },
          path: { value: '/src/test.js' },
          snippet: { value: 'console.log("test");' },
          canonicalName: { value: 'TestAsset' },
          startLine: { value: '10' },
          endLine: { value: '15' },
          description: { value: 'Test description' }
        }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Test Asset')).toBeInTheDocument()
      expect(screen.getByText('http://example.com/Class')).toBeInTheDocument()
      expect(screen.getByText('JavaScript')).toBeInTheDocument()
      expect(screen.getByText('TestAsset')).toBeInTheDocument()
      expect(screen.getByText('repo')).toBeInTheDocument()
      expect(screen.getByText('/src/test.js')).toBeInTheDocument()
      expect(screen.getByText('10-15')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toBeInTheDocument()
    })
  })

  it('handles missing optional fields gracefully', async () => {
    const mockAssetData = {
      results: {
        bindings: [{
          title: { value: 'Test Asset' }
          // Missing optional fields
        }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Test Asset')).toBeInTheDocument()
      // Check for specific labels to avoid ambiguity
      const typeLabel = screen.getByText('Type:').closest('.info-item')
      expect(typeLabel).toHaveTextContent('Unknown')
      const languageLabel = screen.getByText('Language:').closest('.info-item')
      expect(languageLabel).toHaveTextContent('Unknown')
      const canonicalLabel = screen.getByText('Canonical Name:').closest('.info-item')
      expect(canonicalLabel).toHaveTextContent('N/A')
      const repoLabel = screen.getByText('Repository:').closest('.info-item')
      expect(repoLabel).toHaveTextContent('Unknown')
      const pathLabel = screen.getByText('Path:').closest('.info-item')
      expect(pathLabel).toHaveTextContent('N/A')
      const linesLabel = screen.getByText('Lines:').closest('.info-item')
      expect(linesLabel).toHaveTextContent('N/A')
    })
  })

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(mockConsoleError).toHaveBeenCalledWith('Error fetching asset details:', expect.any(Error))
    })
  })

  it('handles non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(mockConsoleError).toHaveBeenCalledWith('Error fetching asset details:', expect.any(Error))
    })
  })

  it('handles empty results', async () => {
    const mockAssetData = {
      results: {
        bindings: []
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      // Check for specific labels to avoid ambiguity
      const nameLabel = screen.getByText('Name:').closest('.info-item')
      expect(nameLabel).toHaveTextContent('Unknown')
    })
  })

  it('switches between tabs', async () => {
    const mockAssetData = {
      results: {
        bindings: [{
          title: { value: 'Test Asset' },
          snippet: { value: 'console.log("test");' }
        }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Test Asset')).toBeInTheDocument()
    })

    // Switch to relationships tab
    const relationshipsTab = screen.getByText('Relationships')
    fireEvent.click(relationshipsTab)
    expect(screen.getByText('Relationship data will be displayed here')).toBeInTheDocument()

    // Switch to code tab
    const codeTab = screen.getByText('Code')
    fireEvent.click(codeTab)
    expect(screen.getByText('console.log("test");')).toBeInTheDocument()

    // Switch back to details tab
    const detailsTab = screen.getByText('Details')
    fireEvent.click(detailsTab)
    expect(screen.getByText('Test Asset')).toBeInTheDocument()
  })

  it('shows no code snippet message when snippet is missing', async () => {
    const mockAssetData = {
      results: {
        bindings: [{
          title: { value: 'Test Asset' }
          // No snippet
        }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAssetData
    })

    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Test Asset')).toBeInTheDocument()
    })

    // Switch to code tab
    const codeTab = screen.getByText('Code')
    fireEvent.click(codeTab)
    expect(screen.getByText('No code snippet available for this entity.')).toBeInTheDocument()
  })

  it('calls onClose when modal close button is clicked', () => {
    const onClose = vi.fn()
    
    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={onClose} 
        assetUri="http://example.com/asset1" 
      />
    )
    
    const closeButton = screen.getByTestId('modal-close')
    fireEvent.click(closeButton)
    
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not fetch when assetUri is null', () => {
    render(
      <AssetDetailsModal 
        isOpen={true} 
        onClose={vi.fn()} 
        assetUri={null} 
      />
    )
    
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('does not fetch when modal is not open', () => {
    render(
      <AssetDetailsModal 
        isOpen={false} 
        onClose={vi.fn()} 
        assetUri="http://example.com/asset1" 
      />
    )
    
    expect(mockFetch).not.toHaveBeenCalled()
  })
}) 