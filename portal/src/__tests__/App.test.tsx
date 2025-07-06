import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import App from '../App'

// Remove all view component mocks

describe('App', () => {
  const renderApp = (ui: ReactElement) => {
    return render(ui)
  }

  it('renders the app container', () => {
    renderApp(<App />)
    expect(screen.getByRole('heading', { name: 'System Overview' })).toBeInTheDocument()
  })

  it('shows dashboard by default', () => {
    renderApp(<App />)
    expect(screen.getByRole('heading', { name: 'System Overview' })).toBeInTheDocument()
  })

  it('renders sidebar with navigation items', () => {
    renderApp(<App />)
    expect(screen.getByRole('menuitem', { name: 'Repositories' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Search' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Knowledge Graph' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Analytics' })).toBeInTheDocument()
  })

  it('renders header with page title', () => {
    renderApp(<App />)
    expect(screen.getByRole('heading', { name: 'System Overview' })).toBeInTheDocument()
  })

  it('changes view when sidebar item is clicked', async () => {
    renderApp(<App />)
    
    // Click on the sidebar link for Repositories
    const repoLinks = screen.getAllByText('Repositories')
    const repoSidebarLink = repoLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/repositories')
    if (!repoSidebarLink) throw new Error('Sidebar link for Repositories not found')
    fireEvent.click(repoSidebarLink.closest('a')!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Repository Management', level: 2 })).toBeInTheDocument()
    })
  })

  it('shows Knowledge Search heading when Search is clicked', async () => {
    renderApp(<App />)
    
    // Click on the sidebar link for Search
    const searchLinks = screen.getAllByText('Search')
    const searchSidebarLink = searchLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/search')
    if (!searchSidebarLink) throw new Error('Sidebar link for Search not found')
    fireEvent.click(searchSidebarLink.closest('a')!)
    
    // Wait for the navigation to complete and heading to update
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Knowledge Search', level: 2 })).toBeInTheDocument()
    })
  })

  it('navigates to different routes', async () => {
    renderApp(<App />)
    
    // Click on the sidebar link for Repositories
    const repoLinks = screen.getAllByText('Repositories')
    const repoSidebarLink = repoLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/repositories')
    if (!repoSidebarLink) throw new Error('Sidebar link for Repositories not found')
    fireEvent.click(repoSidebarLink.closest('a')!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Repository Management', level: 2 })).toBeInTheDocument()
    })
    
    // Click on the sidebar link for Search
    const searchLinks = screen.getAllByText('Search')
    const searchSidebarLink = searchLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/search')
    if (!searchSidebarLink) throw new Error('Sidebar link for Search not found')
    fireEvent.click(searchSidebarLink.closest('a')!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Knowledge Search', level: 2 })).toBeInTheDocument()
    })
    
    // Click on the sidebar link for Knowledge Graph
    const graphLinks = screen.getAllByText('Knowledge Graph')
    const graphSidebarLink = graphLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/graph')
    if (!graphSidebarLink) throw new Error('Sidebar link for Knowledge Graph not found')
    fireEvent.click(graphSidebarLink.closest('a')!)
    await waitFor(() => {
      expect(screen.getAllByText('Knowledge Graph Visualization').length).toBeGreaterThan(0)
    })
    
    // Click on the sidebar link for Analytics
    const analyticsLinks = screen.getAllByText('Analytics')
    const analyticsSidebarLink = analyticsLinks.find(el => el.closest('a') && el.closest('a')?.getAttribute('href') === '/analytics')
    if (!analyticsSidebarLink) throw new Error('Sidebar link for Analytics not found')
    fireEvent.click(analyticsSidebarLink.closest('a')!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Analytics', level: 2 })).toBeInTheDocument()
    })
  })
}) 