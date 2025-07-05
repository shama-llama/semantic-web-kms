import React, { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts'

/**
 * Analytics component for displaying insights and metrics
 */
function Analytics() {
  const [analyticsData, setAnalyticsData] = useState({
    totalNodes: 0,
    totalEdges: 0,
    nodeTypes: [],
    centralityScores: [],
    topEntities: [],
    fileDistribution: [],
    entityTypes: [],
    repoActivity: []
  })
  const [loading, setLoading] = useState(true)
  const [showAllEntities, setShowAllEntities] = useState(false)
  const [showAllCentrality, setShowAllCentrality] = useState(false)

  useEffect(() => {
    updateAnalytics()
  }, [])

  /**
   * Fetch analytics data from the API
   */
  const updateAnalytics = async () => {
    setLoading(true)
    
    try {
      // Fetch analytics data from the backend API
      const [fileDistResponse, entityTypesResponse, repoActivityResponse] = await Promise.all([
        fetch('/api/analytics/file_distribution'),
        fetch('/api/analytics/entity_types'),
        fetch('/api/analytics/repo_activity')
      ])

      const fileDistData = await fileDistResponse.json()
      const entityTypesData = await entityTypesResponse.json()
      const repoActivityData = await repoActivityResponse.json()

      // Get total counts
      const totalNodes = entityTypesData.types?.reduce((sum, type) => sum + type.count, 0) || 0
      const totalEdges = fileDistData.totalRelationships || 0

      // Process node types for pie chart
      const nodeTypes = entityTypesData.types?.map(type => ({
        type: type.type,
        count: type.count,
        percentage: totalNodes > 0 ? Math.round((type.count / totalNodes) * 1000) / 10 : 0
      })) || []

      // Process file distribution
      const fileDistribution = fileDistData.distribution?.map(file => ({
        extension: file.extension,
        count: file.count,
        percentage: file.percentage
      })) || []

      // Process repository activity
      const repoActivity = repoActivityData.repositories?.map(repo => ({
        repo: repo.name,
        files: repo.fileCount,
        entities: repo.entityCount,
        lastActivity: repo.lastActivity
      })) || []

      setAnalyticsData({
        totalNodes,
        totalEdges,
        nodeTypes,
        centralityScores: [], // TODO: Implement centrality calculation
        topEntities: [], // TODO: Implement top entities calculation
        fileDistribution,
        entityTypes: entityTypesData.types || [],
        repoActivity
      })
    } catch (error) {
      console.error('Error fetching analytics:', error)
      // Fallback to mock data if API fails
      setAnalyticsData({
        totalNodes: 0,
        totalEdges: 0,
        nodeTypes: [],
        centralityScores: [],
        topEntities: [],
        fileDistribution: [],
        entityTypes: [],
        repoActivity: []
      })
    } finally {
      setLoading(false)
    }
  }

  const getInsights = () => {
    const avgConnections = analyticsData.totalNodes > 0 ? 
      Math.round((analyticsData.totalEdges / analyticsData.totalNodes) * 100) / 100 : 0
    
    const topEntity = analyticsData.topEntities[0]
    const functionPercentage = analyticsData.nodeTypes.find(t => t.type === 'Function')?.percentage || 0
    
    return [
      {
        icon: 'fas fa-lightbulb',
        title: 'High Connectivity',
        description: `The ${topEntity?.name || 'main'} function has the highest centrality score (${topEntity?.centrality || 0.95}), indicating it's a critical component in your codebase.`
      },
      {
        icon: 'fas fa-chart-line',
        title: 'Function Dominance',
        description: `Functions make up ${functionPercentage}% of all entities, suggesting a functional programming approach.`
      },
      {
        icon: 'fas fa-link',
        title: 'Strong Coupling',
        description: `Average of ${avgConnections} connections per node indicates good integration between components.`
      },
      {
        icon: 'fas fa-code',
        title: 'Python Focus',
        description: `${analyticsData.fileDistribution[0]?.percentage || 52.9}% of files are Python, showing a backend-heavy architecture.`
      }
    ]
  }

  // Gruvbox-light high-contrast palette
  const pieColors = [
    '#b57614', // orange
    '#98971a', // green
    '#458588', // blue
    '#cc241d', // red
    '#d79921', // yellow
    '#8ec07c', // aqua
    '#d65d0e'  // bright orange
  ]
  const barColors = [
    '#b57614', // orange
    '#98971a', // green
    '#458588', // blue
    '#cc241d', // red
    '#d79921', // yellow
    '#8ec07c'  // aqua
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div className="loading-spinner"></div>
        <p>Loading analytics...</p>
      </div>
    )
  }

  return (
    <div className="analytics-grid">
      <div className="card">
        <div className="card-header">
          <h3>Graph Overview</h3>
        </div>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-number">{analyticsData.totalNodes}</div>
            <div className="stat-label">Total Nodes</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">{analyticsData.totalEdges}</div>
            <div className="stat-label">Total Relationships</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">
              {analyticsData.totalNodes > 0 ? 
                Math.round((analyticsData.totalEdges / analyticsData.totalNodes) * 100) / 100 : 0
              }
            </div>
            <div className="stat-label">Avg. Connections</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Node Types Distribution</h3>
        </div>
        <div className="chart-container" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={analyticsData.nodeTypes}
                dataKey="count"
                nameKey="type"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
              >
                {analyticsData.nodeTypes.map((entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={pieColors[idx % pieColors.length]} />
                ))}
              </Pie>
              <RechartsTooltip formatter={(value, name) => [`${value} nodes`, name]} />
              <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 16, fontSize: '1rem', color: '#3c3836' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>File Distribution</h3>
        </div>
        <div className="chart-container" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analyticsData.fileDistribution} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="extension" />
              <YAxis />
              <RechartsTooltip formatter={(value) => `${value} files`} />
              <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 16, fontSize: '1rem', color: '#3c3836' }} />
              <Bar dataKey="count" name="Files" fill="#b57614">
                {analyticsData.fileDistribution.map((entry, idx) => (
                  <Cell key={`bar-cell-${idx}`} fill={barColors[idx % barColors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Centrality Analysis</h3>
        </div>
        <div className="card-scrollable">
          <div className="centrality-bar-list">
            {(showAllCentrality ? analyticsData.centralityScores : analyticsData.centralityScores.slice(0, 3)).map((item, idx) => (
              <div key={idx} className="centrality-bar-row">
                <span className="entity-name">{item.entity}</span>
                <span className="entity-type">{item.type}</span>
                <div className="centrality-bar-bg">
                  <div className="centrality-bar-fill" style={{ width: `${item.score * 100}%` }}></div>
                </div>
                <span className="centrality-score">{item.score.toFixed(2)}</span>
              </div>
            ))}
            {analyticsData.centralityScores.length > 3 && (
              <button 
                className="btn btn-secondary" 
                style={{ marginTop: 12, fontSize: '1rem', padding: '0.75rem 1.25rem' }} 
                aria-label={showAllCentrality ? 'Show less centrality scores' : 'Show all centrality scores'}
                onClick={() => setShowAllCentrality(v => !v)}>
                {showAllCentrality ? 'Show Less' : 'Show All'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Most Connected Entities</h3>
        </div>
        <div className="card-scrollable">
          <div className="top-entities-list">
            {(showAllEntities ? analyticsData.topEntities : analyticsData.topEntities.slice(0, 3)).map((entity, idx) => (
              <div key={idx} className="entity-list-row">
                <span className="entity-name">{entity.name}</span>
                <span className="entity-type">{entity.type}</span>
                <span className="entity-connections">{entity.connections} connections</span>
                <span className="entity-centrality">Centrality: {entity.centrality}</span>
              </div>
            ))}
            {analyticsData.topEntities.length > 3 && (
              <button 
                className="btn btn-secondary" 
                style={{ marginTop: 12, fontSize: '1rem', padding: '0.75rem 1.25rem' }} 
                aria-label={showAllEntities ? 'Show less connected entities' : 'Show all connected entities'}
                onClick={() => setShowAllEntities(v => !v)}>
                {showAllEntities ? 'Show Less' : 'Show All'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Repository Activity</h3>
        </div>
        <div className="card-scrollable">
          <table className="analytics-table" aria-label="Repository Activity">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Files</th>
                <th>Entities</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {analyticsData.repoActivity.map((repo, index) => (
                <tr key={index} className="analytics-row">
                  <td className="repo-name">{repo.repo}</td>
                  <td className="repo-files">{repo.files}</td>
                  <td className="repo-entities">{repo.entities}</td>
                  <td className="repo-last-activity">
                    <i className="fas fa-clock" aria-hidden="true" style={{ marginRight: 6, color: '#b57614' }}></i>
                    {repo.lastActivity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Insights</h3>
        </div>
        <div className="insights-content">
          {getInsights().map((insight, index) => (
            <div key={index} className="insight-section">
              <i className={insight.icon}></i>
              <div className="insight-text">
                <strong>{insight.title}:</strong> {insight.description}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Analytics 