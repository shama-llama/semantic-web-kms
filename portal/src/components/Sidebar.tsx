import React from 'react'
import { NavLink } from 'react-router-dom'

/**
 * Sidebar component with navigation menu using React Router
 */
function Sidebar(): React.JSX.Element {
  const navItems = [
    { id: 'dashboard', path: '/dashboard', icon: 'fas fa-tachometer-alt', label: 'Dashboard' },
    { id: 'repositories', path: '/repositories', icon: 'fas fa-folder', label: 'Repositories' },
    { id: 'search', path: '/search', icon: 'fas fa-search', label: 'Search' },
    { id: 'graph', path: '/graph', icon: 'fas fa-project-diagram', label: 'Knowledge Graph' },
    { id: 'analytics', path: '/analytics', icon: 'fas fa-chart-bar', label: 'Analytics' }
  ]

  return (
    <nav className="sidebar" id="navigation" role="navigation" aria-label="Main navigation">
      <div className="sidebar-header">
        <div className="logo">
          <i className="fas fa-network-wired" aria-hidden="true"></i>
          <span>Semantic Web</span>
        </div>
      </div>
      
      <ul className="nav-menu" role="menubar">
        {navItems.map((item) => (
          <li key={item.id} role="none">
            <NavLink
              to={item.path}
              className={({ isActive }: { isActive: boolean }) => `nav-item ${isActive ? 'active' : ''}`}
              role="menuitem"
            >
              <i className={item.icon} aria-hidden="true"></i>
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export default Sidebar 