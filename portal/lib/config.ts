// Backend API Configuration
export const API_CONFIG = {
  // Backend API base URL - defaults to localhost:8000 (current backend port)
  BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  
  // API endpoints
  ENDPOINTS: {
    DASHBOARD_STATS: "/api/dashboard_stats",
    REPOSITORIES: "/api/repositories",
    SPARQL: "/api/sparql",
    PROGRESS: "/api/progress",
    ORGANIZATIONS: "/api/organizations",
    UPLOAD: "/api/upload/organization",
    INPUT_DIRECTORY: "/api/input-directory",
    ENTITIES: "/api/entities",
    RELATIONSHIPS: "/api/relationships",
    METRICS: "/api/metrics",
    HEALTH: "/api/health",
    CONFIG: "/api/config",
    EXPORT: "/api/export",
  },
  
  // Request timeout in milliseconds
  TIMEOUT: 30000,
  
  // Retry configuration
  RETRY: {
    MAX_ATTEMPTS: 3,
    DELAY: 1000,
  },
} as const

// Helper function to build full API URLs
export function buildApiUrl(endpoint: string): string {
  return `${API_CONFIG.BACKEND_URL}${endpoint}`
}

// Helper function to handle API errors
export function handleApiError(error: any, context: string): never {
  console.error(`API Error in ${context}:`, error)
  
  if (error instanceof Response) {
    throw new Error(`HTTP ${error.status}: ${error.statusText}`)
  }
  
  if (error instanceof Error) {
    throw error
  }
  
  throw new Error(`Unknown error in ${context}: ${String(error)}`)
} 