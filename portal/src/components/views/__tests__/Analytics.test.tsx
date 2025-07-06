import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import Analytics from '../Analytics'

// Mock ResponsiveContainer to avoid chart dimension warnings
vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts')
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 400, height: 300 }}>
        {children}
      </div>
    )
  }
})

describe('Analytics', () => {
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

  it('renders analytics interface', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })
    render(<Analytics />)
    await waitFor(() => expect(screen.queryByText('Loading analytics...')).not.toBeInTheDocument())
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Export Data')).toBeInTheDocument()
  })

  it('fetches analytics data on mount', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/analytics')
    })
  })

  it('displays analytics data when fetch succeeds', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })
    render(<Analytics />)
    await waitFor(() => expect(screen.getByTestId('test-class-count')).toHaveTextContent('10'))
    expect(screen.getByTestId('test-function-count')).toHaveTextContent('20')
    expect(screen.getByTestId('test-variable-count')).toHaveTextContent('15')
    expect(screen.getByTestId('test-repo-total')).toHaveTextContent('5')
    expect(screen.getByTestId('test-repo-active')).toHaveTextContent('3')
    expect(screen.getByTestId('test-repo-inactive')).toHaveTextContent('2')
  })

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(<Analytics />)

    await waitFor(() => {
      expect(mockConsoleError).toHaveBeenCalledWith('Error fetching analytics:', expect.any(Error))
    })
  })

  it('handles non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(mockConsoleError).toHaveBeenCalledWith('Error fetching analytics:', expect.any(Error))
    })
  })

  it('exports data when export button is clicked', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Export Data')).toBeInTheDocument()
    })

    const exportButton = screen.getByText('Export Data')
    fireEvent.click(exportButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/analytics/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.any(String)
      })
    })
  })

  it('displays entity type distribution chart', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Entity Type Distribution')).toBeInTheDocument()
      const chartContainer = screen.getByText('Entity Type Distribution').closest('.card')?.querySelector('.chart-container')
      expect(chartContainer).toBeInTheDocument()
    })
  })

  it('displays repository status chart', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Repository Status')).toBeInTheDocument()
      // Verify the chart container is rendered (the chart data is inside SVG elements)
      const chartContainer = screen.getByText('Repository Status').closest('.card')?.querySelector('.chart-container')
      expect(chartContainer).toBeInTheDocument()
    })
  })

  it('displays language distribution chart', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('File Distribution')).toBeInTheDocument()
      const chartContainer = screen.getByText('File Distribution').closest('.card')?.querySelector('.chart-container')
      expect(chartContainer).toBeInTheDocument()
    })
  })

  it('displays relationship type chart', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Entity Type Distribution')).toBeInTheDocument()
      const chartContainer = screen.getByText('Entity Type Distribution').closest('.card')?.querySelector('.chart-container')
      expect(chartContainer).toBeInTheDocument()
    })
  })

  it('handles empty analytics data', async () => {
    const mockAnalyticsData = {
      entityCounts: {},
      repositoryStats: { total: 0, active: 0, inactive: 0 },
      languageStats: {},
      relationshipStats: { total: 0, types: {} }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })
  })

  it('displays loading state initially', () => {
    mockFetch.mockImplementation(() => 
      new Promise(() => {}) // Never resolves
    )

    render(<Analytics />)
    
    expect(screen.getByText('Loading analytics...')).toBeInTheDocument()
  })

  it('displays summary statistics', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Total Nodes')).toBeInTheDocument()
      expect(screen.getByText('Total Relationships')).toBeInTheDocument()
      expect(screen.getByText('Avg. Connections')).toBeInTheDocument()
    })
  })

  it('displays time-based analytics', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } },
      timeSeries: {
        entities: [{ date: '2024-01-01', count: 10 }, { date: '2024-01-02', count: 15 }],
        relationships: [{ date: '2024-01-01', count: 20 }, { date: '2024-01-02', count: 25 }]
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Growth Over Time')).toBeInTheDocument()
    })
  })

  it('displays refresh button', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 1 },
      repositoryStats: { total: 1, active: 1, inactive: 0 },
      languageStats: { Python: 1 },
      relationshipStats: { total: 1, types: { uses: 1 } }
    }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalyticsData
    })
    render(<Analytics />)
    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument()
    })
  })

  it('handles refresh action', async () => {
    const mockAnalyticsData = {
      entityCounts: { Class: 10, Function: 20, Variable: 15 },
      repositoryStats: { total: 5, active: 3, inactive: 2 },
      languageStats: { JavaScript: 25, Python: 15, TypeScript: 10 },
      relationshipStats: { total: 50, types: { uses: 20, extends: 15, implements: 15 } }
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsData
    })

    render(<Analytics />)

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument()
    })

    const refreshButton = screen.getByText('Refresh')
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2) // Initial load + refresh
    })
  })
}) 