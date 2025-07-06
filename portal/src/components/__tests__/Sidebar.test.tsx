import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import Sidebar from '../Sidebar'

describe('Sidebar', () => {
  const renderWithRouter = (ui: ReactElement) => {
    return render(ui, { wrapper: BrowserRouter })
  }

  it('renders all navigation items', () => {
    renderWithRouter(<Sidebar />)
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Repositories')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
  })

  it('renders navigation links with correct hrefs', () => {
    renderWithRouter(<Sidebar />)
    
    expect(screen.getByText('Dashboard').closest('a')).toHaveAttribute('href', '/dashboard')
    expect(screen.getByText('Repositories').closest('a')).toHaveAttribute('href', '/repositories')
    expect(screen.getByText('Search').closest('a')).toHaveAttribute('href', '/search')
    expect(screen.getByText('Knowledge Graph').closest('a')).toHaveAttribute('href', '/graph')
    expect(screen.getByText('Analytics').closest('a')).toHaveAttribute('href', '/analytics')
  })

  it('renders sidebar header with logo', () => {
    renderWithRouter(<Sidebar />)
    
    expect(screen.getByText('Semantic Web')).toBeInTheDocument()
    expect(screen.getByText('Semantic Web').closest('.logo')).toBeInTheDocument()
  })

  it('renders navigation menu structure', () => {
    renderWithRouter(<Sidebar />)
    
    const navMenu = screen.getByText('Dashboard').closest('.nav-menu')
    expect(navMenu).toBeInTheDocument()
    
    const navItems = navMenu?.querySelectorAll('li')
    expect(navItems).toHaveLength(5) // 5 navigation items
  })
}) 