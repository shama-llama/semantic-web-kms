import React, { useState, useEffect } from 'react'

/**
 * Graph component for knowledge graph visualization
 */
function Graph() {
  const [graphSearchQuery, setGraphSearchQuery] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphStats, setGraphStats] = useState({
    nodeCount: 0,
    edgeCount: 0
  })
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    updateGraphStats()
  }, [])

  /**
   * Update graph statistics
   */
  const updateGraphStats = async () => {
    try {
      const query = `
        SELECT (COUNT(DISTINCT ?entity) AS ?nodeCount) (COUNT(?rel) AS ?edgeCount)
        WHERE {
          ?entity a ?type .
          OPTIONAL { ?entity ?rel ?target }
        }
      `
      
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      
      const data = await response.json()
      
      if (data.results?.bindings?.[0]) {
        const binding = data.results.bindings[0]
        setGraphStats({
          nodeCount: parseInt(binding.nodeCount?.value || '0'),
          edgeCount: parseInt(binding.edgeCount?.value || '0')
        })
      } else {
        setGraphStats({ nodeCount: 0, edgeCount: 0 })
      }
    } catch (error) {
      console.error('Error fetching graph stats:', error)
      setGraphStats({ nodeCount: 0, edgeCount: 0 })
    }
  }

  const searchInGraph = async () => {
    if (!graphSearchQuery.trim()) {
      alert('Please enter a search query')
      return
    }

    setLoading(true)
    
    try {
      const query = `
        SELECT ?entity ?title ?type
        WHERE {
          ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?title .
          OPTIONAL { ?entity a ?type }
          FILTER(CONTAINS(LCASE(?title), LCASE("${graphSearchQuery}")))
        }
        LIMIT 10
      `
      
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      
      const data = await response.json()
      
      if (data.results?.bindings) {
        const results = data.results.bindings.map((item, idx) => ({
          id: idx + 1,
          uri: item.entity?.value || '',
          title: item.title?.value || '',
          type: item.type?.value?.split('#').pop() || 'Unknown'
        }))
        setSearchResults(results)
      } else {
        setSearchResults([])
      }
    } catch (error) {
      console.error('Error searching in graph:', error)
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  const filterGraphByType = (type) => {
    // TODO: Implement graph filtering by type
    console.log('Filtering by type:', type)
  }

  const exportGraph = () => {
    // TODO: Implement graph export functionality
    alert('Exporting graph...')
  }

  const resetGraph = () => {
    // TODO: Implement graph reset functionality
    setSelectedNode(null)
    setSearchResults([])
    setGraphSearchQuery('')
    console.log('Resetting graph...')
  }

  const showNodeDetails = (nodeId) => {
    // TODO: Implement node details fetching
    setSelectedNode({
      id: nodeId,
      name: 'Sample Node',
      type: 'Function',
      description: 'This is a sample node description.',
      file: 'src/components/Graph.jsx',
      connections: 15
    })
  }

  const focusOnNode = (nodeId) => {
    // TODO: Implement focus on node functionality
    console.log('Focusing on node:', nodeId)
  }

  const expandNode = (nodeId) => {
    // TODO: Implement expand node functionality
    console.log('Expanding node:', nodeId)
  }

  return (
    <div className="graph-container">
      <div className="graph-header">
        <h2>Knowledge Graph Visualization</h2>
        <div className="graph-controls">
          <div className="graph-search">
            <input
              type="text"
              value={graphSearchQuery}
              onChange={(e) => setGraphSearchQuery(e.target.value)}
              placeholder="Search entities..."
            />
            <button className="btn btn-sm btn-primary" onClick={searchInGraph} disabled={loading}>
              <i className="fas fa-search"></i>
            </button>
          </div>
          <select 
            id="graph-filter" 
            onChange={(e) => filterGraphByType(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="FunctionDefinition">Functions</option>
            <option value="ClassDefinition">Classes</option>
            <option value="InterfaceDefinition">Interfaces</option>
            <option value="AttributeDeclaration">Attributes</option>
            <option value="VariableDeclaration">Variables</option>
            <option value="ImportDeclaration">Imports</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={exportGraph}>
            <i className="fas fa-download"></i>
            Export
          </button>
          <button className="btn btn-secondary btn-sm" onClick={resetGraph}>
            <i className="fas fa-home"></i>
            Reset View
          </button>
        </div>
      </div>
      
      <div className="graph-main">
        <div className="graph-canvas">
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%',
            color: '#64748b',
            fontSize: '1.125rem'
          }}>
            <div style={{ textAlign: 'center' }}>
              <i className="fas fa-project-diagram" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
              <p>Knowledge Graph Visualization</p>
              <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                Graph visualization coming soon...
              </p>
            </div>
          </div>
        </div>
        
        <div className="graph-sidebar">
          <div className="sidebar-section">
            <h4>Graph Statistics</h4>
            <div className="graph-stats">
              <div className="stat">
                <span className="stat-label">Nodes:</span>
                <span className="stat-value">{graphStats.nodeCount}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Edges:</span>
                <span className="stat-value">{graphStats.edgeCount}</span>
              </div>
            </div>
          </div>
          
          <div className="sidebar-section">
            <h4>Search Results</h4>
            <div className="search-results">
              {loading ? (
                <p>Searching...</p>
              ) : searchResults.length > 0 ? (
                searchResults.map((result) => (
                  <div key={result.id} className="search-result-item">
                    <div className="result-header">
                      <div className="result-label">{result.title}</div>
                      <div className="result-type">{result.type}</div>
                    </div>
                    <button 
                      className="btn btn-sm btn-secondary"
                      onClick={() => showNodeDetails(result.uri)}
                    >
                      View Details
                    </button>
                  </div>
                ))
              ) : (
                <p>Search for entities to see results here</p>
              )}
            </div>
          </div>
          
          {selectedNode && (
            <div className="sidebar-section">
              <h4>Node Details</h4>
              <div className="node-details-content">
                <div className="node-header">
                  <h5>{selectedNode.name}</h5>
                  <div className="node-type">{selectedNode.type}</div>
                </div>
                <div className="node-description">
                  <p>{selectedNode.description}</p>
                </div>
                <div className="node-file">
                  <strong>File:</strong> {selectedNode.file}
                </div>
                <div className="node-connections">
                  <strong>Connections:</strong> {selectedNode.connections}
                </div>
                <div className="node-actions">
                  <button 
                    className="btn btn-sm btn-primary"
                    onClick={() => focusOnNode(selectedNode.id)}
                  >
                    <i className="fas fa-eye"></i>
                    Focus
                  </button>
                  <button 
                    className="btn btn-sm btn-secondary"
                    onClick={() => expandNode(selectedNode.id)}
                  >
                    <i className="fas fa-expand"></i>
                    Expand
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Graph 