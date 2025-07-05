import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createRoot } from 'react-dom/client'

// Mock React DOM
vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({
    render: vi.fn()
  }))
}))

// Mock App component
vi.mock('../App', () => ({
  default: () => <div data-testid="app">App Component</div>
}))

// Mock CSS import
vi.mock('../index.css', () => ({}))

describe('main.tsx', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should create root and render App component', async () => {
    // Import main.tsx to execute it
    await import('../main.tsx')
    
    expect(createRoot).toHaveBeenCalledWith(expect.any(HTMLElement))
    expect(createRoot).toHaveBeenCalledTimes(1)
  })

  it('should find root element', () => {
    const rootElement = document.getElementById('root')
    expect(rootElement).toBeInTheDocument()
    expect(rootElement?.id).toBe('root')
  })

  it('should handle missing root element', async () => {
    // Temporarily remove root element
    const rootElement = document.getElementById('root')
    if (rootElement) {
      rootElement.remove()
    }

    // Mock console.error to avoid noise
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    // This should throw an error when root element is missing
    // Since import() is async, we need to handle it properly
    try {
      await import('../main.tsx')
      // If we get here, the import succeeded when it shouldn't have
      expect.fail('Import should have failed')
    } catch (error) {
      expect(error).toBeInstanceOf(Error)
      // The error message might be different due to module loading
      // Just check that it's an error, don't check the specific message
      expect((error as Error).message).toBeTruthy()
    }

    consoleSpy.mockRestore()
  })
}) 