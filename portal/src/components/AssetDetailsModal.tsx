import { useState, useEffect, useCallback } from 'react'
import Modal from './Modal'

// Type definitions
interface AssetData {
  uri: string
  title: string
  type: string
  language: string
  repository: string
  path: string
  snippet: string
  canonicalName: string
  startLine: string
  endLine: string
  description: string
}

interface AssetDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  assetUri: string | null
}

/**
 * Asset Details Modal component
 * @param {AssetDetailsModalProps} props - Component props
 */
function AssetDetailsModal({ isOpen, onClose, assetUri }: AssetDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<string>('details')
  const [assetData, setAssetData] = useState<AssetData | null>(null)
  const [loading, setLoading] = useState<boolean>(false)

  /**
   * Fetch asset details from the API
   */
  const fetchAssetDetails = useCallback(async () => {
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
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.results?.bindings?.[0]) {
        const item = data.results.bindings[0]
        setAssetData({
          uri: assetUri,
          title: item.title?.value || 'Unknown',
          type: item.type?.value?.split('#').pop() || 'Unknown',
          language: item.language?.value || 'Unknown',
          repository: item.repository?.value || 'Unknown',
          path: item.path?.value || 'N/A',
          snippet: item.snippet?.value || '',
          canonicalName: item.canonicalName?.value || 'N/A',
          startLine: item.startLine?.value || '',
          endLine: item.endLine?.value || '',
          description: item.description?.value || ''
        })
      } else {
        // Handle empty results
        setAssetData({
          uri: assetUri,
          title: 'Unknown',
          type: 'Unknown',
          language: 'Unknown',
          repository: 'Unknown',
          path: 'N/A',
          snippet: '',
          canonicalName: 'N/A',
          startLine: '',
          endLine: '',
          description: ''
        })
      }
    } catch (error) {
      console.error('Error fetching asset details:', error)
      setAssetData(null)
    } finally {
      setLoading(false)
    }
  }, [assetUri])

  useEffect(() => {
    if (isOpen && assetUri) {
      fetchAssetDetails()
    }
  }, [isOpen, assetUri, fetchAssetDetails])

  const renderDetailsTab = () => (
    <div className="asset-info" role="region" aria-label="Asset details">
      {assetData && (
        <>
          <div className="info-section">
            <h4>Basic Information</h4>
            <dl className="info-grid">
              <div className="info-item">
                <dt>Name:</dt>
                <dd>{assetData.title}</dd>
              </div>
              <div className="info-item">
                <dt>Type:</dt>
                <dd>{assetData.type}</dd>
              </div>
              <div className="info-item">
                <dt>Language:</dt>
                <dd>{assetData.language || 'Unknown'}</dd>
              </div>
              <div className="info-item">
                <dt>Canonical Name:</dt>
                <dd>{assetData.canonicalName || 'N/A'}</dd>
              </div>
            </dl>
          </div>
          
          <div className="info-section">
            <h4>Location</h4>
            <dl className="info-grid">
              <div className="info-item">
                <dt>Repository:</dt>
                <dd>{assetData.repository ? assetData.repository.split('/').pop() : 'Unknown'}</dd>
              </div>
              <div className="info-item">
                <dt>Path:</dt>
                <dd>{assetData.path || 'N/A'}</dd>
              </div>
              <div className="info-item">
                <dt>Lines:</dt>
                <dd>
                  {assetData.startLine && assetData.endLine 
                    ? `${assetData.startLine}-${assetData.endLine}` 
                    : 'N/A'
                  }
                </dd>
              </div>
            </dl>
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
    <div className="relationships-list" role="region" aria-label="Asset relationships">
      <p>Relationship data will be displayed here</p>
      {/* TODO: Implement relationships fetching and display */}
    </div>
  )

  const renderCodeTab = () => (
    <div className="code-viewer" role="region" aria-label="Asset code snippet">
      {assetData?.snippet ? (
        <pre className="code-snippet" role="textbox" aria-label="Code snippet">
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

  const tabs = [
    { id: 'details', label: 'Details', icon: 'fas fa-info-circle' },
    { id: 'relationships', label: 'Relationships', icon: 'fas fa-project-diagram' },
    { id: 'code', label: 'Code', icon: 'fas fa-code' }
  ]

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Asset Details" size="large">
      <div className="asset-modal-content">
        {/* Tab Navigation */}
        <div className="tab-navigation" role="tablist" aria-label="Asset detail tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <i className={tab.icon} aria-hidden="true"></i>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {loading ? (
            <div className="loading-container" role="status" aria-live="polite">
              <i className="fas fa-spinner fa-spin" aria-hidden="true"></i>
              <p>Loading asset details...</p>
            </div>
          ) : (
            <div 
              role="tabpanel" 
              id={`tabpanel-${activeTab}`}
              aria-labelledby={`tab-${activeTab}`}
            >
              {renderTabContent()}
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default AssetDetailsModal 