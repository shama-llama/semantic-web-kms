import { useState, useEffect } from 'react'
import AddRepositoryModal from '../AddRepositoryModal'

// Type definitions
interface Repository {
  uri: string
  name: string
  fileCount: number
  entityCount: number
  relationshipCount: number
}

interface SparqlBinding {
  repository: { value: string }
  name?: { value: string }
  fileCount?: { value: string }
  entityCount?: { value: string }
  relationshipCount?: { value: string }
}

interface RepositoryData {
  type: 'github' | 'local'
  url: string
  analysisOptions: {
    analyzeCode: boolean
    analyzeDocs: boolean
    generateOntology: boolean
  }
}

/**
 * Repositories component for managing and viewing repositories
 */
function Repositories() {
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [showAddModal, setShowAddModal] = useState<boolean>(false)

  useEffect(() => {
    fetchRepositories()
  }, [])

  /**
   * Fetch repositories from the API using SPARQL query
   */
  const fetchRepositories = async () => {
    const query = `
      SELECT ?repository ?name
        (COUNT(DISTINCT ?file) AS ?fileCount)
        (COALESCE(?entityCountSub, 0) AS ?entityCount)
        (COALESCE(?relationshipCountSub, 0) AS ?relationshipCount)
      WHERE {
        ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
        OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name }
        OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file }
        OPTIONAL {
          SELECT ?repository (COUNT(DISTINCT ?entity) AS ?entityCountSub)
          WHERE {
            ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file2 .
            ?entity <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file2 .
            ?entity a ?entityType .
            FILTER(?entityType IN (
              <http://semantic-web-kms.edu.et/wdo#SoftwareCode>,
              <http://semantic-web-kms.edu.et/wdo#FunctionDefinition>,
              <http://semantic-web-kms.edu.et/wdo#ClassDefinition>
            ))
          }
          GROUP BY ?repository
        }
        OPTIONAL {
          SELECT ?repository (COUNT(DISTINCT ?relationship) AS ?relationshipCountSub)
          WHERE {
            ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file3 .
            ?entityA <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file3 .
            ?entityB <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file3 .
            FILTER(?entityA != ?entityB)
            ?entityA ?relPred ?entityB .
            FILTER(?relPred IN (
              <http://semantic-web-kms.edu.et/wdo#invokes>,
              <http://semantic-web-kms.edu.et/wdo#callsFunction>,
              <http://semantic-web-kms.edu.et/wdo#extendsType>,
              <http://semantic-web-kms.edu.et/wdo#implementsInterface>,
              <http://semantic-web-kms.edu.et/wdo#declaresCode>,
              <http://semantic-web-kms.edu.et/wdo#hasField>,
              <http://semantic-web-kms.edu.et/wdo#hasMethod>,
              <http://semantic-web-kms.edu.et/wdo#isRelatedTo>,
              <http://semantic-web-kms.edu.et/wdo#usesFramework>,
              <http://semantic-web-kms.edu.et/wdo#tests>,
              <http://semantic-web-kms.edu.et/wdo#documentsEntity>,
              <http://semantic-web-kms.edu.et/wdo#modifies>,
              <http://semantic-web-kms.edu.et/wdo#imports>,
              <http://semantic-web-kms.edu.et/wdo#isImportedBy>,
              <http://semantic-web-kms.edu.et/wdo#conformsToGuideline>,
              <http://semantic-web-kms.edu.et/wdo#copiesFrom>,
              <http://semantic-web-kms.edu.et/wdo#embedsCode>,
              <http://semantic-web-kms.edu.et/wdo#generates>,
              <http://semantic-web-kms.edu.et/wdo#hasArgument>,
              <http://semantic-web-kms.edu.et/wdo#hasResource>,
              <http://semantic-web-kms.edu.et/wdo#isAbout>,
              <http://semantic-web-kms.edu.et/wdo#isAboutCode>,
              <http://semantic-web-kms.edu.et/wdo#isDependencyOf>,
              <http://semantic-web-kms.edu.et/wdo#specifiesDependency>,
              <http://semantic-web-kms.edu.et/wdo#styles>
            ))
            BIND(CONCAT(STR(?entityA), STR(?relPred), STR(?entityB)) AS ?relationship)
          }
          GROUP BY ?repository
        }
      }
      GROUP BY ?repository ?name ?entityCountSub ?relationshipCountSub
    `
    
    try {
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      const data = await response.json()
      
      const repos = (data.results?.bindings || []).map((item: SparqlBinding) => ({
        uri: item.repository.value,
        name: item.name ? item.name.value : item.repository.value.split('/').pop(),
        fileCount: item.fileCount ? parseInt(item.fileCount.value) : 0,
        entityCount: item.entityCount ? parseInt(item.entityCount.value) : 0,
        relationshipCount: item.relationshipCount ? parseInt(item.relationshipCount.value) : 0
      }))
      
      setRepositories(repos)
    } catch (error) {
      console.error('Error fetching repositories:', error)
      setRepositories([])
    } finally {
      setLoading(false)
    }
  }

  /**
   * Handle adding a new repository
   */
  const handleAddRepository = async (repoData: RepositoryData) => {
    try {
      // TODO: Implement actual API call to add repository
      console.log('Adding repository:', repoData)
      
      // For now, just refresh the repositories list
      await fetchRepositories()
      
      // Show success message
      alert('Repository added successfully!')
    } catch (error) {
      console.error('Error adding repository:', error)
      throw error
    }
  }

  const viewRepoDetails = (repoUri: string) => {
    // TODO: Implement repository details view
    alert(`View details for ${repoUri}`)
  }

  const searchInRepo = (repoUri: string) => {
    // TODO: Implement search in repository
    alert(`Search in ${repoUri}`)
  }

  return (
    <div>
      <div className="view-header">
        <h2>Repository Management</h2>
        <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          <i className="fas fa-plus"></i>
          Add Repository
        </button>
      </div>
      
      <div className="repositories-grid">
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
            Loading repositories...
          </div>
        ) : repositories.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
            No repositories found.
          </div>
        ) : (
          repositories.map((repo, index) => (
            <div key={index} className="repo-card">
              <div className="repo-header">
                <div className="repo-name">{repo.name}</div>
                <div className="repo-url">{repo.uri}</div>
              </div>
              <div className="repo-stats">
                <div className="repo-stat">
                  <div className="repo-stat-number">{repo.fileCount}</div>
                  <div className="repo-stat-label">Files</div>
                </div>
                <div className="repo-stat">
                  <div className="repo-stat-number">{repo.entityCount}</div>
                  <div className="repo-stat-label">Entities</div>
                </div>
                <div className="repo-stat">
                  <div className="repo-stat-number">{repo.relationshipCount}</div>
                  <div className="repo-stat-label">Relationships</div>
                </div>
              </div>
              <div className="repo-actions">
                <button 
                  className="btn btn-secondary" 
                  onClick={() => viewRepoDetails(repo.uri)}
                >
                  <i className="fas fa-eye"></i>
                  View Details
                </button>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => searchInRepo(repo.uri)}
                >
                  <i className="fas fa-search"></i>
                  Search
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <AddRepositoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddRepository}
      />
    </div>
  )
}

export default Repositories
