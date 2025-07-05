import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Header component with page title, search bar, user menu, and theme toggle
 */
function Header(): React.JSX.Element {
  const navigate = useNavigate()
  
  // Theme state is managed at the document level for global effect
  const [dark, setDark] = useState(false)
  const [quickSearchQuery, setQuickSearchQuery] = useState('')

  const handleThemeToggle = () => {
    setDark((prev) => {
      const next = !prev
      if (next) {
        document.documentElement.classList.add('theme-dark')
      } else {
        document.documentElement.classList.remove('theme-dark')
      }
      return next
    })
  }

  const handleQuickSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (quickSearchQuery.trim()) {
      // Navigate to search page with query
      navigate(`/search?q=${encodeURIComponent(quickSearchQuery.trim())}`)
    }
  }

  const handleQuickSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleQuickSearch(e as React.FormEvent)
    }
  }

  return (
    <div className="page-container">
      <header className="header" role="banner">
        <div className="header-left">
          <form className="search-bar" onSubmit={handleQuickSearch} role="search">
            <i className="fas fa-search" aria-hidden="true"></i>
            <input 
              type="text" 
              placeholder="Quick search..." 
              value={quickSearchQuery}
              onChange={(e) => setQuickSearchQuery(e.target.value)}
              onKeyDown={handleQuickSearchKeyDown}
              aria-label="Quick search"
              aria-describedby="search-description"
            />
            <span id="search-description" className="sr-only">
              Press Enter to search or navigate to the search page
            </span>
          </form>
        </div>
        <div className="header-right">
          <button
            className="btn btn-secondary"
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            onClick={handleThemeToggle}
            type="button"
          >
            <i className={dark ? 'fas fa-moon' : 'fas fa-sun'} aria-hidden="true"></i>
            {dark ? 'Dark' : 'Light'}
          </button>
        </div>
      </header>
    </div>
  )
}

export default Header 