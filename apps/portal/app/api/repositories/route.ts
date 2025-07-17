import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

// Define a local type for repository transformation
interface Repository {
  id: string;
  name?: string;
  lastUpdated?: string;
  complexity?: { total: number; average: number };
  files?: number;
  language?: string;
  contributors?: number;
  entities?: number;
  size?: number;
  description?: string;
  editorialNote?: string;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const organization = searchParams.get("organization")
    
    const backendUrl = buildApiUrl("/api/repositories") + 
      (organization ? `?organization=${encodeURIComponent(organization)}` : "")
    
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      // Reduced timeout for better UX
      signal: AbortSignal.timeout(10000), // 10 seconds instead of 30
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    
    // Transform backend data to match frontend interface
    const repositories = data.map((repo: Repository) => ({
      id: repo.id,
      name: repo.name || "Unnamed Repository",
      lastUpdated: repo.lastUpdated || "",
      complexity: repo.complexity || { total: 0, average: 0 },
      files: repo.files || 0,
      language: repo.language || "Unknown",
      contributors: repo.contributors || 0,
      entities: repo.entities || 0, // Include entity count from backend
      size: 0, // Not provided by backend yet
      description: repo.description || repo.editorialNote || "", // Pass through skos:editorialNote if present
    }))

    return NextResponse.json(repositories)
  } catch (error) {
    console.error("Error loading repositories:", error)
    
    // Return empty array if backend is unavailable
    return NextResponse.json([], { status: 503 })
  }
}
