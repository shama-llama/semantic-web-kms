import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AddRepositoryModal from '../AddRepositoryModal'

describe('AddRepositoryModal', () => {
  const mockOnClose = vi.fn()
  const mockOnAdd = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders when isOpen is true', () => {
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    expect(screen.getByRole('heading', { name: 'Add Repository' })).toBeInTheDocument()
    expect(screen.getAllByText('Repository Type')).toHaveLength(2)
    expect(screen.getByText('GitHub Repository')).toBeInTheDocument()
    expect(screen.getByText('Local Directory')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(
      <AddRepositoryModal isOpen={false} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    expect(screen.queryByText('Add Repository')).not.toBeInTheDocument()
  })

  it('shows GitHub URL input when GitHub is selected', () => {
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    expect(screen.getByPlaceholderText('https://github.com/username/repository')).toBeInTheDocument()
  })

  it('shows local path input when Local Directory is selected', async () => {
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    const localRadio = screen.getByLabelText('Local Directory')
    fireEvent.click(localRadio)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText('/path/to/your/project')).toBeInTheDocument()
    })
  })

  it('calls onClose when cancel button is clicked', () => {
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('validates GitHub URL before submission', async () => {
    const user = userEvent.setup()
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    const submitButton = screen.getByRole('button', { name: 'Add Repository' })
    await user.click(submitButton)
    
    // Should show alert for empty GitHub URL
    expect(mockOnAdd).not.toHaveBeenCalled()
  })

  it('validates local path before submission', async () => {
    const user = userEvent.setup()
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    // Switch to local directory
    const localRadio = screen.getByLabelText('Local Directory')
    await user.click(localRadio)
    
    const submitButton = screen.getByRole('button', { name: 'Add Repository' })
    await user.click(submitButton)
    
    // Should show alert for empty local path
    expect(mockOnAdd).not.toHaveBeenCalled()
  })

  it('submits form with correct data for GitHub repository', async () => {
    const user = userEvent.setup()
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    const urlInput = screen.getByPlaceholderText('https://github.com/username/repository')
    await user.type(urlInput, 'https://github.com/test/repo')
    
    const submitButton = screen.getByRole('button', { name: 'Add Repository' })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(mockOnAdd).toHaveBeenCalledWith({
        type: 'github',
        url: 'https://github.com/test/repo',
        analysisOptions: {
          analyzeCode: true,
          analyzeDocs: true,
          generateOntology: true
        }
      })
    })
  })

  it('toggles analysis options', async () => {
    const user = userEvent.setup()
    render(
      <AddRepositoryModal isOpen={true} onClose={mockOnClose} onAdd={mockOnAdd} />
    )
    
    const analyzeCodeCheckbox = screen.getByLabelText('Analyze Code Structure')
    const analyzeDocsCheckbox = screen.getByLabelText('Analyze Documentation')
    const generateOntologyCheckbox = screen.getByLabelText('Generate Ontology')
    
    // All should be checked by default
    expect(analyzeCodeCheckbox).toBeChecked()
    expect(analyzeDocsCheckbox).toBeChecked()
    expect(generateOntologyCheckbox).toBeChecked()
    
    // Toggle one option
    await user.click(analyzeDocsCheckbox)
    expect(analyzeDocsCheckbox).not.toBeChecked()
  })
}) 