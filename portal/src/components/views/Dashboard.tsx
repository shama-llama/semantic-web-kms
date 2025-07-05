import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

// Type definitions for dashboard data
interface DashboardStats {
  totalRepos: number
  totalFiles: number
  totalEntities: number
  totalRelationships: number
}

interface ActivityItem {
  id: number
  type: string
  title: string
  description: string
  time: string
  icon: string
  status: 'success' | 'warning' | 'error' | 'info'
}

type QuickAction = 'add-repository' | 'search' | 'graph' | 'analytics'

/**
 * Dashboard component with overview stats, recent activity, and quick actions
 */
function Dashboard(): React.JSX.Element {
  const navigate = useNavigate()
  
  const [stats, setStats] = useState<DashboardStats>({
    totalRepos: 0,
    totalFiles: 0,
    totalEntities: 0,
    totalRelationships: 0
  })
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    updateDashboardStats()
    updateRecentActivity()
  }, [])

  /**
   * Fetch and update dashboard statistics from the API
   */
  const updateDashboardStats = async (): Promise<void> => {
    try {
      const response = await fetch('/api/dashboard_stats')
      if (!response.ok) throw new Error('Failed to fetch dashboard stats')
      const data = await response.json()
      setStats({
        totalRepos: data.totalRepos ?? 0,
        totalFiles: data.totalFiles ?? 0,
        totalEntities: data.totalEntities ?? 0,
        totalRelationships: data.totalRelationships ?? 0
      })
    } catch (error) {
      console.error('Error fetching dashboard stats:', error)
      setStats({
        totalRepos: 0,
        totalFiles: 0,
        totalEntities: 0,
        totalRelationships: 0
      })
    } finally {
      setLoading(false)
    }
  }

  /**
   * Fetch recent activity data
   */
  const updateRecentActivity = async (): Promise<void> => {
    try {
      // TODO: Implement actual activity API
      // For now, using mock data
      const mockActivity: ActivityItem[] = [
        {
          id: 1,
          type: 'repository_added',
          title: 'Repository added',
          description: 'semantic-web-kms',
          time: '2 hours ago',
          icon: 'fas fa-plus-circle',
          status: 'success'
        },
        {
          id: 2,
          type: 'search_performed',
          title: 'Knowledge search performed',
          description: 'Found 15 entities',
          time: '4 hours ago',
          icon: 'fas fa-search',
          status: 'info'
        },
        {
          id: 3,
          type: 'graph_updated',
          title: 'Graph visualization updated',
          description: 'Added 23 new relationships',
          time: '1 day ago',
          icon: 'fas fa-project-diagram',
          status: 'success'
        },
        {
          id: 4,
          type: 'analysis_completed',
          title: 'Analysis completed',
          description: 'Processed 45 files',
          time: '2 days ago',
          icon: 'fas fa-cog',
          status: 'success'
        }
      ]
      setRecentActivity(mockActivity)
    } catch (error) {
      console.error('Error fetching recent activity:', error)
      setRecentActivity([])
    }
  }

  const handleQuickAction = (action: QuickAction): void => {
    switch (action) {
      case 'add-repository':
        navigate('/repositories')
        break
      case 'search':
        navigate('/search')
        break
      case 'graph':
        navigate('/graph')
        break
      case 'analytics':
        navigate('/analytics')
        break
      default:
        break
    }
  }

  const getStatusColor = (status: ActivityItem['status']): string => {
    switch (status) {
      case 'success':
        return 'var(--success-500)'
      case 'warning':
        return 'var(--warning-500)'
      case 'error':
        return 'var(--error-500)'
      default:
        return 'var(--primary-500)'
    }
  }

  const getStatusBg = (status: ActivityItem['status']): string => {
    switch (status) {
      case 'success':
        return 'var(--success-50)'
      case 'warning':
        return 'var(--warning-50)'
      case 'error':
        return 'var(--error-50)'
      default:
        return 'var(--primary-50)'
    }
  }

  return (
    <div className="dashboard-main-wrapper">
      <div className="dashboard-header-spacer" />
      <div className="dashboard-content-centered">
        {/* Stats Overview */}
        <div className="card stats-overview-card mb-8">
          <div className="card-header">
            <h3>
              <i className="fas fa-chart-line"></i>
              System Overview
            </h3>
          </div>
          <div className="card-content">
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-number">
                  {loading ? (
                    <div className="loading-skeleton" style={{ height: '2rem', width: '60%' }}></div>
                  ) : (
                    stats.totalRepos
                  )}
                </div>
                <div className="stat-label">Repositories</div>
              </div>
              <div className="stat-item">
                <div className="stat-number">
                  {loading ? (
                    <div className="loading-skeleton" style={{ height: '2rem', width: '70%' }}></div>
                  ) : (
                    stats.totalFiles
                  )}
                </div>
                <div className="stat-label">Files Analyzed</div>
              </div>
              <div className="stat-item">
                <div className="stat-number">
                  {loading ? (
                    <div className="loading-skeleton" style={{ height: '2rem', width: '50%' }}></div>
                  ) : (
                    stats.totalEntities
                  )}
                </div>
                <div className="stat-label">Entities</div>
              </div>
              <div className="stat-item">
                <div className="stat-number">
                  {loading ? (
                    <div className="loading-skeleton" style={{ height: '2rem', width: '80%' }}></div>
                  ) : (
                    stats.totalRelationships
                  )}
                </div>
                <div className="stat-label">Relationships</div>
              </div>
            </div>
          </div>
        </div>

        <div className="dashboard-grid">
          {/* Recent Activity */}
          <div className="card recent-activity">
            <div className="card-header">
              <h3>
                <i className="fas fa-clock"></i>
                Recent Activity
              </h3>
            </div>
            <div className="card-scrollable" tabIndex={0} role="region" aria-label="Recent activity list">
              <div className="activity-list">
                {recentActivity.length > 0 ? (
                  recentActivity.map((activity: ActivityItem) => (
                    <div key={activity.id} className="activity-item">
                      <div 
                        className="activity-icon"
                        style={{
                          backgroundColor: getStatusBg(activity.status),
                          color: getStatusColor(activity.status)
                        }}
                      >
                        <i className={activity.icon}></i>
                      </div>
                      <div className="activity-content">
                        <div className="activity-title">{activity.title}</div>
                        <div className="activity-desc">{activity.description}</div>
                        <div className="activity-time">{activity.time}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <i className="fas fa-inbox"></i>
                    <h3>No recent activity</h3>
                    <p>Start by adding a repository or performing a search</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card quick-actions">
            <div className="card-header">
              <h3>
                <i className="fas fa-bolt"></i>
                Quick Actions
              </h3>
            </div>
            <div className="card-content">
              <div className="action-buttons action-buttons-grid">
                <button 
                  className="btn btn-primary"
                  onClick={() => handleQuickAction('add-repository')}
                >
                  <i className="fas fa-plus"></i>
                  Add Repository
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => handleQuickAction('search')}
                >
                  <i className="fas fa-search"></i>
                  Search Knowledge
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => handleQuickAction('graph')}
                >
                  <i className="fas fa-project-diagram"></i>
                  View Graph
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => handleQuickAction('analytics')}
                >
                  <i className="fas fa-chart-bar"></i>
                  View Analytics
                </button>
              </div>
            </div>
          </div>

          {/* System Health */}
          <div className="card system-health">
            <div className="card-header">
              <h3>
                <i className="fas fa-heartbeat"></i>
                System Health
              </h3>
            </div>
            <div className="card-content">
              <div className="health-item">
                <div className="health-label">API Status</div>
                <div className="status-indicator status-active">
                  <i className="fas fa-check-circle"></i>
                  <span>Online</span>
                </div>
              </div>
              <div className="health-item">
                <div className="health-label">Database</div>
                <div className="status-indicator status-active">
                  <i className="fas fa-check-circle"></i>
                  <span>Connected</span>
                </div>
              </div>
              <div className="health-item">
                <div className="health-label">Processing Queue</div>
                <div className="status-indicator status-active">
                  <i className="fas fa-check-circle"></i>
                  <span>Idle</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard 