import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import { ReactElement } from 'react'

// Mock for useNavigate hook
export const mockNavigate = vi.fn()

// Mock for useLocation hook
export const mockLocation = {
  pathname: '/dashboard',
  search: '',
  hash: '',
  state: null,
  key: 'default'
}

// Setup React Router mocks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation
  }
})

// Mock fetch for API calls
globalThis.fetch = vi.fn() as unknown as typeof fetch

// Mock window.alert
globalThis.alert = vi.fn() as unknown as typeof alert

// Mock ResizeObserver for chart components
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver as unknown as typeof ResizeObserver

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock document.getElementById for main.tsx testing
const mockRootElement = document.createElement('div')
mockRootElement.id = 'root'
document.body.appendChild(mockRootElement)

// Custom render function that includes React Router
export function renderWithRouter(ui: ReactElement, { route = '/' } = {}) {
  window.history.pushState({}, 'Test page', route)

  return render(ui, { wrapper: BrowserRouter })
} 