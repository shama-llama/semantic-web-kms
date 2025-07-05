import { useState } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './components/views/Dashboard'
import Repositories from './components/views/Repositories'
import Search from './components/views/Search'
import Graph from './components/views/Graph'
import Analytics from './components/views/Analytics'

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [pageTitle, setPageTitle] = useState('Dashboard')

  const handleViewChange = (viewName) => {
    setCurrentView(viewName)
    const titles = {
      dashboard: 'Dashboard',
      repositories: 'Repositories',
      search: 'Search',
      graph: 'Knowledge Graph',
      analytics: 'Analytics'
    }
    setPageTitle(titles[viewName] || 'Dashboard')
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard onViewChange={handleViewChange} />
      case 'repositories':
        return <Repositories />
      case 'search':
        return <Search />
      case 'graph':
        return <Graph />
      case 'analytics':
        return <Analytics />
      default:
        return <Dashboard onViewChange={handleViewChange} />
    }
  }

  return (
    <div className="app-container">
      <Sidebar currentView={currentView} onViewChange={handleViewChange} />
      <main className="main-content">
        <Header pageTitle={pageTitle} />
        <div className="content-area">
          {renderCurrentView()}
        </div>
      </main>
    </div>
  )
}

export default App
