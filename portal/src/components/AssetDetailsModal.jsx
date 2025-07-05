import React, { useState, useEffect } from 'react'
import Modal from './Modal'

/**
 * Asset Details Modal component
 * @param {boolean} isOpen - Whether the modal is open
 * @param {function} onClose - Function to close the modal
 * @param {string} assetUri - URI of the asset to display
 */
function AssetDetailsModal({ isOpen, onClose, assetUri }) {
  const [activeTab, setActiveTab] = useState('details')
  const [assetData, setAssetData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen && assetUri) {
      fetchAssetDetails()
    }
  }, [isOpen, assetUri])

  /**
   * Fetch asset details from the API
   */
  const fetchAssetDetails = async () => {
    if (!assetUri) return

    setLoading(true)
    
    try {
      const query = `
        SELECT ?entity ?title ?type ?language ?repository ?path ?snippet ?canonicalName ?startLine ?endLine ?description
        WHERE {
          <${assetUri}> <http://www.w3.org/2000/01/rdf-schema#label> ?title .
          OPTIONAL { <${assetUri}> a ?type }
          OPTIONAL { <${assetUri}> <http://purl.org/dc/terms/language> ?language }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#isInRepository> ?repository }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasRelativePath> ?path }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasSourceCodeSnippet> ?snippet }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasCanonicalName> ?canonicalName }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#startsAtLine> ?startLine }
          OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#endsAtLine> ?endLine }
          OPTIONAL { <${assetUri}> <http://purl.org/dc/terms/description> ?description }
        }
      `
      
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      
      const data = await response.json()
      
      if (data.results?.bindings?.[0]) {
        const item = data.results.bindings[0]
        setAssetData({
          uri: assetUri,
          title: item.title?.value || 'Unknown',
          type: item.type?.value?.split('#').pop() || 'Unknown',
          language: item.language?.value || '',
          repository: item.repository?.value || '',
          path: item.path?.value || '',
          snippet: item.snippet?.value || '',
          canonicalName: item.canonicalName?.value || '',
          startLine: item.startLine?.value || '',
          endLine: item.endLine?.value || '',
          description: item.description?.value || ''
        })
      }
    } catch (error) {
      console.error('Error fetching asset details:', error)
      setAssetData(null)
    } finally {
      setLoading(false)
    }
  }

  const renderDetailsTab = () => (
    <div className="asset-info">
      {assetData && (
        <>
          <div className="info-section">
            <h4>Basic Information</h4>
            <div className="info-grid">
              <div className="info-item">
                <label>Name:</label>
                <span>{assetData.title}</span>
              </div>
              <div className="info-item">
                <label>Type:</label>
                <span>{assetData.type}</span>
              </div>
              <div className="info-item">
                <label>Language:</label>
                <span>{assetData.language || 'Unknown'}</span>
              </div>
              <div className="info-item">
                <label>Canonical Name:</label>
                <span>{assetData.canonicalName || 'N/A'}</span>
              </div>
            </div>
          </div>
          
          <div className="info-section">
            <h4>Location</h4>
            <div className="info-grid">
              <div className="info-item">
                <label>Repository:</label>
                <span>{assetData.repository ? assetData.repository.split('/').pop() : 'Unknown'}</span>
              </div>
              <div className="info-item">
                <label>Path:</label>
                <span>{assetData.path || 'N/A'}</span>
              </div>
              <div className="info-item">
                <label>Lines:</label>
                <span>
                  {assetData.startLine && assetData.endLine 
                    ? `${assetData.startLine}-${assetData.endLine}` 
                    : 'N/A'
                  }
                </span>
              </div>
            </div>
          </div>
          
          {assetData.description && (
            <div className="info-section">
              <h4>Description</h4>
              <p>{assetData.description}</p>
            </div>
          )}
        </>
      )}
    </div>
  )

  const renderRelationshipsTab = () => (
    <div className="relationships-list">
      <p>Relationship data will be displayed here</p>
      {/* TODO: Implement relationships fetching and display */}
    </div>
  )

  const renderCodeTab = () => (
    <div className="code-viewer">
      {assetData?.snippet ? (
        <pre className="code-snippet">
          <code>{assetData.snippet}</code>
        </pre>
      ) : (
        <p>No code snippet available for this entity.</p>
      )}
    </div>
  )

  const renderTabContent = () => {
    switch (activeTab) {
      case 'details':
        return renderDetailsTab()
      case 'relationships':
        return renderRelationshipsTab()
      case 'code':
        return renderCodeTab()
      default:
        return renderDetailsTab()
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Asset Details" size="large">
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div className="loading-spinner"></div>
          <p>Loading asset details...</p>
        </div>
      ) : (
        <>
          <div className="asset-tabs">
            <button 
              className={`tab-btn ${activeTab === 'details' ? 'active' : ''}`}
              onClick={() => setActiveTab('details')}
            >
              Details
            </button>
            <button 
              className={`tab-btn ${activeTab === 'relationships' ? 'active' : ''}`}
              onClick={() => setActiveTab('relationships')}
            >
              Relationships
            </button>
            <button 
              className={`tab-btn ${activeTab === 'code' ? 'active' : ''}`}
              onClick={() => setActiveTab('code')}
            >
              Code
            </button>
          </div>
          
          <div className="tab-content">
            {renderTabContent()}
          </div>
        </>
      )}
    </Modal>
  )
}

export default AssetDetailsModal 