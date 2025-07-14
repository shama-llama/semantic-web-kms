import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

// Define a local type for entity transformation
interface Entity {
  id: string;
  name: string;
  type: "function" | "class" | "component" | "interface" | "variable";
  repository: string;
  description?: string;
  editorialNote?: string;
  enrichedDescription?: string;
  confidence: number;
  snippet: string;
  file: string;
  line: number;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get("query") || ""
    const type = searchParams.get("type")
    const repository = searchParams.get("repository")
    const limit = searchParams.get("limit") || "50"

    if (!query) {
      return NextResponse.json({ error: "Query parameter is required" }, { status: 400 })
    }

    // Build backend URL with query parameters
    const backendUrl = new URL(buildApiUrl("/api/search"))
    backendUrl.searchParams.set("query", query)
    if (type) backendUrl.searchParams.set("type", type)
    if (repository) backendUrl.searchParams.set("repository", repository)
    backendUrl.searchParams.set("limit", limit)

    const response = await fetch(backendUrl.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(30000),
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    
    // Transform backend data to match frontend interface
    const result = {
      entities: data.entities.map((entity: Entity) => ({
        id: entity.id,
        name: entity.name,
        type: entity.type as "function" | "class" | "component" | "interface" | "variable",
        repository: entity.repository,
        description: entity.description,
        editorialNote: entity.editorialNote,
        enrichedDescription: entity.enrichedDescription,
        confidence: entity.confidence,
        snippet: entity.snippet,
        file: entity.file,
        line: entity.line,
      })),
      totalCount: data.totalCount,
      semanticInsights: data.semanticInsights,
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error("Error performing search:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackResult = {
      entities: [],
      totalCount: 0,
      semanticInsights: {
        relatedConcepts: [],
        suggestedQueries: [],
        confidence: 0,
      },
    }
    
    return NextResponse.json(fallbackResult, { status: 503 })
  }
}
