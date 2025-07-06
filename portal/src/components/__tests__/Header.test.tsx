import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import Header from '../Header'
import { mockNavigate, mockLocation } from '../../test/setup'

describe('Header', () => {
  const renderWithRouter = (ui: ReactElement) => {
    return render(ui, { wrapper: BrowserRouter })
  }

  beforeEach(() => {
    // Reset document classes
    document.documentElement.classList.remove('theme-dark')
    vi.clearAllMocks()
    // Reset mock location to dashboard
    mockLocation.pathname = '/dashboard'
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the header container', () => {
    renderWithRouter(<Header />)
    const header = screen.getByRole('banner')
    expect(header).toBeInTheDocument()
  })

  it('renders search bar with placeholder', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    expect(searchInput).toBeInTheDocument()
    expect(searchInput).toHaveAttribute('aria-label', 'Quick search')
  })

  it('renders theme toggle button', () => {
    renderWithRouter(<Header />)
    const themeButton = screen.getByRole('button', { name: /switch to dark mode/i })
    expect(themeButton).toBeInTheDocument()
    expect(themeButton).toHaveTextContent('Light')
  })

  it('handles theme toggle from light to dark', () => {
    renderWithRouter(<Header />)
    const themeButton = screen.getByRole('button', { name: /switch to dark mode/i })
    
    fireEvent.click(themeButton)
    
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true)
    expect(themeButton).toHaveTextContent('Dark')
    expect(themeButton).toHaveAttribute('aria-label', 'Switch to light mode')
  })

  it('handles theme toggle from dark to light', () => {
    renderWithRouter(<Header />)
    const themeButton = screen.getByRole('button', { name: /switch to dark mode/i })
    
    // First click to dark mode
    fireEvent.click(themeButton)
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true)
    
    // Second click to light mode
    fireEvent.click(themeButton)
    expect(document.documentElement.classList.contains('theme-dark')).toBe(false)
    expect(themeButton).toHaveTextContent('Light')
    expect(themeButton).toHaveAttribute('aria-label', 'Switch to dark mode')
  })

  it('updates search query on input change', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    expect(searchInput).toHaveValue('test query')
  })

  it('handles search form submission with query', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    fireEvent.submit(searchForm!)
    
    expect(mockNavigate).toHaveBeenCalledWith('/search?q=test%20query')
  })

  it('handles search form submission with empty query', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.submit(searchForm!)
    
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('handles search form submission with whitespace-only query', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    const searchForm = searchInput.closest('form')
    
    fireEvent.change(searchInput, { target: { value: '   ' } })
    fireEvent.submit(searchForm!)
    
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('handles Enter key press on search input', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    fireEvent.keyDown(searchInput, { key: 'Enter', code: 'Enter' })
    
    expect(mockNavigate).toHaveBeenCalledWith('/search?q=test%20query')
  })

  it('does not submit on other key presses', () => {
    renderWithRouter(<Header />)
    const searchInput = screen.getByPlaceholderText('Quick search...')
    
    fireEvent.change(searchInput, { target: { value: 'test query' } })
    fireEvent.keyPress(searchInput, { key: 'Space' })
    
    expect(mockNavigate).not.toHaveBeenCalled()
  })
}) 