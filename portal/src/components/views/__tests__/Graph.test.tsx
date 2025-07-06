import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import Graph from '../Graph'

// Mock fetch
const mockFetch = vi.fn()
globalThis.fetch = mockFetch as unknown as typeof fetch

// Mock alert
const mockAlert = vi.fn()
globalThis.alert = mockAlert as unknown as typeof alert

describe('Graph', () => {
  beforeEach(() => {
    mockFetch.mockClear()
    mockAlert.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders graph interface', () => {
    render(<Graph />)
    
    expect(screen.getAllByText('Knowledge Graph Visualization').length).toBeGreaterThan(0)
    expect(screen.getByText('Export Data')).toBeInTheDocument()
    expect(screen.getByText('Reset View')).toBeInTheDocument()
    expect(screen.getByText('Graph Statistics')).toBeInTheDocument()
  })

  it('displays graph statistics', async () => {
    const mockStatsData = {
      results: {
        bindings: [
          {
            nodeCount: { value: '10' },
            edgeCount: { value: '25' }
          }
        ]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatsData
    })

    await act(async () => {
      render(<Graph />)
    })

    await waitFor(() => {
      expect(screen.getByText('Nodes:')).toBeInTheDocument()
      expect(screen.getByText('Edges:')).toBeInTheDocument()
    })
  })

  it('handles export functionality', () => {
    render(<Graph />)
    
    const exportButton = screen.getByText('Export Data')
    fireEvent.click(exportButton)
    
    expect(mockAlert).toHaveBeenCalledWith('Exporting graph...')
  })

  it('handles reset functionality', () => {
    render(<Graph />)
    
    const resetButton = screen.getByText('Reset View')
    fireEvent.click(resetButton)
    
    // Should not throw errors
    expect(resetButton).toBeInTheDocument()
  })

  it('displays placeholder content', () => {
    render(<Graph />)
    
    expect(screen.getByText('Graph visualization coming soon...')).toBeInTheDocument()
  })

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    await act(async () => {
      render(<Graph />)
    })

    // Should handle error gracefully and still render
    expect(screen.getByText('Graph Statistics')).toBeInTheDocument()
  })
}) 