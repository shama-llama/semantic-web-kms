"use client"

import { createContext, useContext, useState, ReactNode, useEffect } from "react"

interface ProcessingStage {
  status: "pending" | "processing" | "completed" | "error"
  progress: number
  message?: string
}

interface Repository {
  id: string
  name: string
  description: string
  lastUpdated: string
  complexity: { total: string; average: string }
  entities: number
  language: string
  contributors: string
  coverage?: number
}

interface OrganizationData {
  id: string
  name: string
  totalEntities: number
  totalFiles: number
  totalRelations: number
  repositories: Repository[]
}

interface OrganizationContextType {
  organization: OrganizationData | null
  processingStages: Record<string, ProcessingStage>
  isLoading: boolean
  error: string | null
  inputDirectory: string | null
  analyzeOrganization: (name: string) => Promise<void>
  refreshStatus: () => Promise<void>
  clearError: () => void
  getInputDirectory: () => Promise<void>
  initializeOrganization: () => Promise<void>
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined)

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const [organization, setOrganization] = useState<OrganizationData | null>(null)
  const [processingStages, setProcessingStages] = useState<Record<string, ProcessingStage>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [inputDirectory, setInputDirectory] = useState<string | null>(null)

  // Initialize organization on mount
  useEffect(() => {
    initializeOrganization()
  }, [])

  const analyzeOrganization = async (name: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch("/api/organizations/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      })

      if (!response.ok) {
        throw new Error("Failed to analyze organization")
      }

      const data = await response.json()
      setCurrentJobId(data.job_id)

      // Create a mock organization for now
      // In a real implementation, this would come from the backend
      const mockOrganization: OrganizationData = {
        id: data.job_id,
        name: name,
        totalEntities: 0,
        totalFiles: 0,
        totalRelations: 0,
        repositories: [],
      }
      setOrganization(mockOrganization)

      // Start polling for status updates
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const refreshStatus = async () => {
    if (!currentJobId) return

    try {
      const response = await fetch(`/api/progress/${currentJobId}`)
      if (response.ok) {
        const jobStatus = await response.json()
        setProcessingStages(jobStatus.stages)
        
        // If job is complete, fetch organization data
        if (jobStatus.status === "completed") {
          await fetchOrganizationData()
        }
      }
    } catch (err) {
      console.error("Failed to refresh status:", err)
    }
  }

  const fetchOrganizationData = async () => {
    if (!organization) return

    try {
      // Properly encode the organization ID for use as URL parameters
      const encodedOrgId = encodeURIComponent(organization.id)
      
      // First, get the organization details
      const orgResponse = await fetch(`/api/organizations/${encodedOrgId}`)
      if (orgResponse.ok) {
        setOrganization({ ...(await orgResponse.json()), totalFiles: organization.totalFiles || 0 })
        
        // Fetch repositories for this organization
        const reposResponse = await fetch(`/api/repositories?organization=${encodedOrgId}`)
        if (reposResponse.ok) {
          const repositories = await reposResponse.json()
          
          // Fetch dashboard stats for this organization
          const statsResponse = await fetch(`/api/dashboard_stats?organization=${encodedOrgId}`)
          if (statsResponse.ok) {
            const stats = await statsResponse.json()
            
            setOrganization(prev => prev ? {
              ...prev,
              totalEntities: stats.totalEntities || 0,
              totalFiles: stats.totalFiles || 0,
              totalRelations: stats.totalRelationships || 0,
              repositories: repositories || [],
            } : null)
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch organization data:", err)
    }
  }

  const clearError = () => {
    setError(null)
  }

  const getInputDirectory = async () => {
    try {
      const response = await fetch('/api/input-directory')
      if (response.ok) {
        const data = await response.json()
        setInputDirectory(data.input_directory)
      }
    } catch (err) {
      console.error("Failed to get input directory:", err)
    }
  }

  const initializeOrganization = async () => {
    try {
      // Get the first available organization
      const response = await fetch('/api/organizations')
      if (response.ok) {
        const organizations = await response.json()
        if (organizations.length > 0) {
          const firstOrg = organizations[0]
          // Properly encode the organization ID for use as a URL parameter
          const encodedOrgId = encodeURIComponent(firstOrg.id)
          const orgDetailsResponse = await fetch(`/api/organizations/${encodedOrgId}`)
          if (orgDetailsResponse.ok) {
            const orgDetails = await orgDetailsResponse.json()
            setOrganization({ ...orgDetails, totalFiles: orgDetails.totalFiles || 0 })
          }
        }
      }
    } catch (err) {
      console.error("Failed to initialize organization:", err)
    }
  }

  return (
    <OrganizationContext.Provider
      value={{
        organization,
        processingStages,
        isLoading,
        error,
        inputDirectory,
        analyzeOrganization,
        refreshStatus,
        clearError,
        getInputDirectory,
        initializeOrganization,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  )
}

export function useOrganization() {
  const context = useContext(OrganizationContext)
  if (context === undefined) {
    throw new Error("useOrganization must be used within an OrganizationProvider")
  }
  return context
}
