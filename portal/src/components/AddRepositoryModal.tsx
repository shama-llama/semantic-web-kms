import React, { useState } from 'react'
import Modal from './Modal'

// Type definitions
interface AnalysisOptions {
  analyzeCode: boolean
  analyzeDocs: boolean
  generateOntology: boolean
}

interface RepositoryData {
  type: 'github' | 'local'
  url: string
  analysisOptions: AnalysisOptions
}

interface AddRepositoryModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (repoData: RepositoryData) => Promise<void>
}

/**
 * Add Repository Modal component
 * @param {AddRepositoryModalProps} props - Component props
 */
function AddRepositoryModal({ isOpen, onClose, onAdd }: AddRepositoryModalProps) {
  const [repoType, setRepoType] = useState<'github' | 'local'>('github')
  const [githubUrl, setGithubUrl] = useState<string>('')
  const [localPath, setLocalPath] = useState<string>('')
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisOptions>({
    analyzeCode: true,
    analyzeDocs: true,
    generateOntology: true
  })
  const [loading, setLoading] = useState<boolean>(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    
    if (repoType === 'github' && !githubUrl.trim()) {
      alert('Please enter a GitHub repository URL')
      return
    }
    
    if (repoType === 'local' && !localPath.trim()) {
      alert('Please enter a local directory path')
      return
    }

    setLoading(true)
    
    try {
      const repoData: RepositoryData = {
        type: repoType,
        url: repoType === 'github' ? githubUrl : localPath,
        analysisOptions
      }
      
      await onAdd(repoData)
      onClose()
      
      // Reset form
      setGithubUrl('')
      setLocalPath('')
    } catch (error) {
      console.error('Error adding repository:', error)
      alert('Failed to add repository. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleOptionChange = (option: keyof AnalysisOptions) => {
    setAnalysisOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }))
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Repository">
      <form onSubmit={handleSubmit} role="form" aria-label="Add repository form">
        <fieldset>
          <legend className="sr-only">Repository Type</legend>
          <div className="form-group">
            <label htmlFor="repo-type-label">Repository Type</label>
            <div className="radio-group" role="radiogroup" aria-labelledby="repo-type-label">
              <label className="radio-option">
                <input
                  type="radio"
                  name="repo-type"
                  value="github"
                  checked={repoType === 'github'}
                  onChange={(e) => setRepoType(e.target.value as 'github')}
                  aria-describedby="github-description"
                />
                <span>GitHub Repository</span>
              </label>
              <span id="github-description" className="sr-only">
                Add a GitHub repository by providing its URL
              </span>
              <label className="radio-option">
                <input
                  type="radio"
                  name="repo-type"
                  value="local"
                  checked={repoType === 'local'}
                  onChange={(e) => setRepoType(e.target.value as 'local')}
                  aria-describedby="local-description"
                />
                <span>Local Directory</span>
              </label>
              <span id="local-description" className="sr-only">
                Add a local directory by providing its file path
              </span>
            </div>
          </div>
        </fieldset>
        
        {repoType === 'github' && (
          <div className="form-group">
            <label htmlFor="github-url">GitHub Repository URL</label>
            <input
              id="github-url"
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
              aria-describedby="github-url-help"
              required
            />
            <span id="github-url-help" className="sr-only">
              Enter the full URL of the GitHub repository you want to add
            </span>
          </div>
        )}
        
        {repoType === 'local' && (
          <div className="form-group">
            <label htmlFor="local-path">Local Directory Path</label>
            <input
              id="local-path"
              type="text"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="/path/to/your/project"
              aria-describedby="local-path-help"
              required
            />
            <span id="local-path-help" className="sr-only">
              Enter the full file path to the local directory you want to add
            </span>
          </div>
        )}
        
        <fieldset>
          <legend>Analysis Options</legend>
          <div className="form-group">
            <label htmlFor="analysis-options-label">Analysis Options</label>
            <div className="checkbox-group" role="group" aria-labelledby="analysis-options-label">
              <label className="checkbox-option">
                <input
                  type="checkbox"
                  checked={analysisOptions.analyzeCode}
                  onChange={() => handleOptionChange('analyzeCode')}
                  aria-describedby="analyze-code-description"
                />
                <span>Analyze Code Structure</span>
              </label>
              <span id="analyze-code-description" className="sr-only">
                Extract and analyze the structure of code files in the repository
              </span>
              <label className="checkbox-option">
                <input
                  type="checkbox"
                  checked={analysisOptions.analyzeDocs}
                  onChange={() => handleOptionChange('analyzeDocs')}
                  aria-describedby="analyze-docs-description"
                />
                <span>Analyze Documentation</span>
              </label>
              <span id="analyze-docs-description" className="sr-only">
                Extract and analyze documentation files in the repository
              </span>
              <label className="checkbox-option">
                <input
                  type="checkbox"
                  checked={analysisOptions.generateOntology}
                  onChange={() => handleOptionChange('generateOntology')}
                  aria-describedby="generate-ontology-description"
                />
                <span>Generate Ontology</span>
              </label>
              <span id="generate-ontology-description" className="sr-only">
                Generate semantic ontology from the repository content
              </span>
            </div>
          </div>
        </fieldset>
        
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={loading}
            aria-describedby={loading ? 'loading-description' : undefined}
          >
            {loading ? 'Adding...' : 'Add Repository'}
          </button>
          {loading && (
            <span id="loading-description" className="sr-only">
              Repository is being added, please wait
            </span>
          )}
        </div>
      </form>
    </Modal>
  )
}

export default AddRepositoryModal 