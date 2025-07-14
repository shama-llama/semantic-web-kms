// API Types
export interface ProcessingStage {
  status: "pending" | "processing" | "completed" | "error"
  progress: number
  message?: string
}

/**
 * Repository metadata returned by the backend.
 */
export interface Repository {
  id: string;
  name: string;
  lastUpdated: string;
  complexity: {
    total: string;
    average: string;
  };
  entities: number;
  language: string;
  contributors: number;
  status?: string;
}

export interface DashboardStats {
  totalEntities: number;
  totalRelationships: number;
  totalImports: number;
  totalRepositories: number;
  totalFiles: number;
  totalLines: number;
  averageComplexity: number;
  recentActivity: {
    lastUpdated: string;
    newEntities: number;
    newRelationships: number;
  };
  topLanguages: Array<{
    language: string;
    percentage: number;
    entities: number;
  }>;
  processingStatus: {
    status: string;
    lastProcessed: string;
    nextScheduled: string;
  };
}

export interface OrganizationData {
  id: string
  name: string
  repositories: Repository[]
  totalEntities: number
  totalRelations: number
  processingStatus: "pending" | "processing" | "completed" | "error"
  createdAt: string
  updatedAt: string
}

export interface KnowledgeEntity {
  id: string
  name: string
  type: "class" | "function" | "component" | "interface" | "variable"
  repository: string
  description: string
  editorialNote?: string
  enrichedDescription?: string
  confidence: number
  snippet: string
  file: string
  line: number
}

export interface SearchResult {
  entities: KnowledgeEntity[]
  totalCount: number
  semanticInsights: {
    relatedConcepts: string[]
    suggestedQueries: string[]
    confidence: number
  }
}

export interface GraphNode {
  id: string
  name: string
  type: "repository" | "file" | "function" | "class" | "concept"
  size: number
  color: string
  repository?: string
  language?: string
}

export interface GraphEdge {
  source: string
  target: string
  type: "depends_on" | "imports" | "calls" | "extends" | "implements" | "contains" | "defines"
  weight: number
}

export interface GraphCluster {
  id: string
  name: string
  nodes: string[]
  color: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  clusters: GraphCluster[]
}

export interface AnalyticsData {
  codebaseMetrics?: {
    totalRepositories?: number
    totalFiles?: number
    sourceCodeFiles?: number
    documentationFiles?: number
    assetFiles?: number
  }
  entityDistribution?: {
    functions?: number
    classes?: number
    interfaces?: number
    attributes?: number
    variables?: number
    parameters?: number
  }
  languageDistribution?: Array<{
    language: string
    entities?: number
    percentage?: number
  }>
  complexityMetrics?: {
    averageCyclomaticComplexity?: number
    highComplexityFunctions?: number
    totalLinesOfCode?: number
  }
  documentationMetrics?: {
    totalDocumentationEntities?: number
    readmeFiles?: number
    codeComments?: number
    apiDocumentation?: number
  }
  developmentMetrics?: {
    totalCommits?: number
    totalIssues?: number
    totalContributors?: number
  }
  assetMetrics?: {
    imageFiles?: number
    audioFiles?: number
    videoFiles?: number
    fontFiles?: number
  }
  trends?: {
    complexity?: {
      timestamps?: string[]
      values?: number[]
    }
    documentation?: {
      timestamps?: string[]
      values?: number[]
    }
  }
}

// Error handling
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

// API client functions
export const searchApi = {
  semantic: async (
    organizationId: string,
    query: string,
    options?: {
      searchType?: "semantic" | "exact" | "pattern"
      filters?: {
        entityType?: string
        repository?: string
        confidenceThreshold?: number
      }
      limit?: number
      offset?: number
    },
  ): Promise<SearchResult> => {
    const params = new URLSearchParams({ query })
    if (options?.filters?.entityType) params.set("type", options.filters.entityType)
    if (options?.filters?.repository) params.set("repository", options.filters.repository)
    if (options?.limit) params.set("limit", options.limit.toString())

    const response = await fetch(`/api/search?${params}`)
    if (!response.ok) {
      throw new ApiError(`Search failed: ${response.statusText}`, response.status)
    }
    return response.json()
  },

  suggestions: async (): Promise<{ query: string; category: string }[]> => {
    // Mock suggestions for now - could be enhanced with backend integration
    return [
      { query: "authentication patterns", category: "Security" },
      { query: "state management in React", category: "Frontend" },
      { query: "database optimization techniques", category: "Backend" },
      { query: "error handling strategies", category: "Architecture" },
      { query: "testing patterns and practices", category: "Quality" },
      { query: "API design principles", category: "Architecture" },
    ]
  },
}

export const graphApi = {
  getData: async (
    options?: {
      layout?: "force-directed" | "hierarchical" | "circular" | "grid"
      filter?: "all" | "classes" | "functions" | "components"
      maxNodes?: number
    },
  ): Promise<GraphData> => {
    const params = new URLSearchParams()
    if (options?.layout) params.set("layout", options.layout)
    if (options?.filter) params.set("filter", options.filter)
    if (options?.maxNodes) params.set("maxNodes", options.maxNodes.toString())

    const response = await fetch(`/api/graph?${params}`)
    if (!response.ok) {
      throw new ApiError(`Failed to load graph: ${response.statusText}`, response.status)
    }
    return response.json()
  },

  getClusterDetails: async (clusterId: string): Promise<GraphCluster> => {
    // Mock cluster details for now
    return {
      id: clusterId,
      name: "Authentication Module",
      nodes: ["file1", "class1"],
      color: "#3b82f6",
    }
  },

  export: async (format: "json" | "graphml" | "gexf"): Promise<Blob> => {
    const response = await fetch(`/api/graph/export?format=${format}`)
    if (!response.ok) {
      throw new ApiError(`Export failed: ${response.statusText}`, response.status)
    }
    return response.blob()
  },
}

export const analyticsApi = {
  getData: async (): Promise<AnalyticsData> => {
    const response = await fetch("/api/analytics")
    if (!response.ok) {
      throw new ApiError(`Failed to load analytics: ${response.statusText}`, response.status)
    }
    return response.json()
  },
}

// Legacy functions - now use the new API routes
export async function getRepositories(): Promise<Repository[]> {
  const response = await fetch("/api/repositories")
  if (!response.ok) {
    throw new ApiError(`Failed to load repositories: ${response.statusText}`, response.status)
  }
  return response.json()
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch("/api/dashboard_stats")
  if (!response.ok) {
    throw new ApiError(`Failed to load dashboard stats: ${response.statusText}`, response.status)
  }
  return response.json()
}

export async function runSparqlQuery(query: string): Promise<unknown> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"
  const res = await fetch(`${baseUrl}/api/sparql`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  })

  if (!res.ok) {
    throw new ApiError(`SPARQL query failed: ${res.statusText}`, res.status)
  }

  return res.json()
}
