import React from 'react'

/**
 * Sidebar component with navigation menu
 * @param {string} currentView - Currently active view
 * @param {function} onViewChange - Callback to change view
 */
function Sidebar({ currentView, onViewChange }) {
  const navItems = [
    { id: 'dashboard', icon: 'fas fa-tachometer-alt', label: 'Dashboard' },
    { id: 'repositories', icon: 'fas fa-folder', label: 'Repositories' },
    { id: 'search', icon: 'fas fa-search', label: 'Search' },
    { id: 'graph', icon: 'fas fa-project-diagram', label: 'Knowledge Graph' },
    { id: 'analytics', icon: 'fas fa-chart-bar', label: 'Analytics' }
  ]

  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <i className="fas fa-network-wired"></i>
          <span>Semantic KMS</span>
        </div>
      </div>
      
      <ul className="nav-menu">
        {navItems.map((item) => (
          <li
            key={item.id}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => onViewChange(item.id)}
          >
            <i className={item.icon}></i>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export default Sidebar 