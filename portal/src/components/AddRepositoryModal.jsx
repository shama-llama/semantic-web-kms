import React, { useState } from 'react'
import Modal from './Modal'

/**
 * Add Repository Modal component
 * @param {boolean} isOpen - Whether the modal is open
 * @param {function} onClose - Function to close the modal
 * @param {function} onAdd - Function to add repository
 */
function AddRepositoryModal({ isOpen, onClose, onAdd }) {
  const [repoType, setRepoType] = useState('github')
  const [githubUrl, setGithubUrl] = useState('')
  const [localPath, setLocalPath] = useState('')
  const [analysisOptions, setAnalysisOptions] = useState({
    analyzeCode: true,
    analyzeDocs: true,
    generateOntology: true
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
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
      const repoData = {
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

  const handleOptionChange = (option) => {
    setAnalysisOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }))
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Repository">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Repository Type</label>
          <div className="radio-group">
            <label className="radio-option">
              <input
                type="radio"
                name="repo-type"
                value="github"
                checked={repoType === 'github'}
                onChange={(e) => setRepoType(e.target.value)}
              />
              <span>GitHub Repository</span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="repo-type"
                value="local"
                checked={repoType === 'local'}
                onChange={(e) => setRepoType(e.target.value)}
              />
              <span>Local Directory</span>
            </label>
          </div>
        </div>
        
        {repoType === 'github' && (
          <div className="form-group">
            <label>GitHub Repository URL</label>
            <input
              type="text"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
            />
          </div>
        )}
        
        {repoType === 'local' && (
          <div className="form-group">
            <label>Local Directory Path</label>
            <input
              type="text"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="/path/to/your/project"
            />
          </div>
        )}
        
        <div className="form-group">
          <label>Analysis Options</label>
          <div className="checkbox-group">
            <label className="checkbox-option">
              <input
                type="checkbox"
                checked={analysisOptions.analyzeCode}
                onChange={() => handleOptionChange('analyzeCode')}
              />
              <span>Analyze Code Structure</span>
            </label>
            <label className="checkbox-option">
              <input
                type="checkbox"
                checked={analysisOptions.analyzeDocs}
                onChange={() => handleOptionChange('analyzeDocs')}
              />
              <span>Analyze Documentation</span>
            </label>
            <label className="checkbox-option">
              <input
                type="checkbox"
                checked={analysisOptions.generateOntology}
                onChange={() => handleOptionChange('generateOntology')}
              />
              <span>Generate Ontology</span>
            </label>
          </div>
        </div>
        
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Adding...' : 'Add Repository'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default AddRepositoryModal 