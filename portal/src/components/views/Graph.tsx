import { useState, useEffect } from 'react'

// Type definitions
interface GraphStats {
  nodeCount: number
  edgeCount: number
}

interface SelectedNode {
  id: string
  name: string
  type: string
  description: string
  file: string
  connections: number
}

/**
 * Graph component for knowledge graph visualization
 */
function Graph() {
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null)
  const [graphStats, setGraphStats] = useState<GraphStats>({
    nodeCount: 0,
    edgeCount: 0
  })

  useEffect(() => {
    let isMounted = true
    const safeUpdateGraphStats = async () => {
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
        if (isMounted) {
          if (data.results?.bindings?.[0]) {
            const binding = data.results.bindings[0]
            setGraphStats({
              nodeCount: parseInt(binding.nodeCount?.value || '0'),
              edgeCount: parseInt(binding.edgeCount?.value || '0')
            })
          } else {
            setGraphStats({ nodeCount: 0, edgeCount: 0 })
          }
        }
      } catch (error) {
        if (isMounted) {
          console.error('Error fetching graph stats:', error)
          setGraphStats({ nodeCount: 0, edgeCount: 0 })
        }
      }
    }
    safeUpdateGraphStats()
    return () => { isMounted = false }
  }, [])

  const exportGraph = () => {
    // TODO: Implement graph export functionality
    alert('Exporting graph...')
  }

  const resetGraph = () => {
    // TODO: Implement graph reset functionality
    setSelectedNode(null)
    console.log('Resetting graph...')
  }

  const focusOnNode = (nodeId: string) => {
    // TODO: Implement focus on node functionality
    console.log('Focusing on node:', nodeId)
  }

  const expandNode = (nodeId: string) => {
    // TODO: Implement expand node functionality
    console.log('Expanding node:', nodeId)
  }

  return (
    <div className="graph-container">
      <div className="graph-header">
        <h2>Knowledge Graph Visualization</h2>
        <div className="graph-controls">
          <div className="graph-controls-right">
            <button className="btn btn-primary" onClick={resetGraph}>
              <i className="fas fa-home"></i>
              Reset View
            </button>
            <button className="btn btn-success" onClick={exportGraph}>
              <i className="fas fa-download"></i>
              Export Data
            </button>
          </div>
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