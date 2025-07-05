import React, { useState } from 'react'

/**
 * Header component with page title, search bar, user menu, and theme toggle
 * @param {string} pageTitle - Current page title to display
 */
function Header({ pageTitle }) {
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

  const handleQuickSearch = (e) => {
    e.preventDefault()
    if (quickSearchQuery.trim()) {
      // Navigate to search page with query
      window.location.href = `/search?q=${encodeURIComponent(quickSearchQuery.trim())}`
    }
  }

  const handleQuickSearchKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleQuickSearch(e)
    }
  }

  return (
    <div className="page-container">
      <header className="header">
        <div className="header-left">
          <h1>{pageTitle}</h1>
        </div>
        <div className="header-right">
          <form className="search-bar" onSubmit={handleQuickSearch}>
            <i className="fas fa-search"></i>
            <input 
              type="text" 
              placeholder="Quick search..." 
              value={quickSearchQuery}
              onChange={(e) => setQuickSearchQuery(e.target.value)}
              onKeyPress={handleQuickSearchKeyPress}
              aria-label="Quick search"
            />
          </form>
          <button
            className="btn btn-secondary"
            style={{ marginLeft: 16 }}
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            onClick={handleThemeToggle}
          >
            <i className={dark ? 'fas fa-moon' : 'fas fa-sun'}></i>
            {dark ? 'Dark' : 'Light'}
          </button>
          <div className="user-menu">
            <i className="fas fa-user-circle"></i>
          </div>
        </div>
      </header>
    </div>
  )
}

export default Header 