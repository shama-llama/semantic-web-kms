import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './components/views/Dashboard'
import Repositories from './components/views/Repositories'
import Search from './components/views/Search'
import Graph from './components/views/Graph'
import Analytics from './components/views/Analytics'



function App(): React.JSX.Element {
  return (
    <Router>
      <div className="app-container">
        {/* Skip links for keyboard navigation */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <a href="#navigation" className="skip-link">
          Skip to navigation
        </a>
        
        <Sidebar />
        <main className="main-content" id="main-content" role="main">
          <Header />
          <div className="content-area">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/repositories" element={<Repositories />} />
              <Route path="/search" element={<Search />} />
              <Route path="/graph" element={<Graph />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
