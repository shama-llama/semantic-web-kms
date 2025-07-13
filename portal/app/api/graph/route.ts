import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const layout = searchParams.get("layout") || "force-directed"
    const filter = searchParams.get("filter") || "all"
    const maxNodes = searchParams.get("maxNodes") || "100"

    // Build backend URL with query parameters
    const backendUrl = new URL(buildApiUrl("/api/graph"))
    backendUrl.searchParams.set("layout", layout)
    backendUrl.searchParams.set("filter", filter)
    backendUrl.searchParams.set("maxNodes", maxNodes)

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
      nodes: data.nodes.map((node: any) => ({
        id: node.id,
        name: node.name,
        type: node.type as "repository" | "file" | "function" | "class" | "concept",
        size: node.size,
        color: node.color,
        repository: node.repository,
        language: node.language,
      })),
      edges: data.edges.map((edge: any) => ({
        source: edge.source,
        target: edge.target,
        type: edge.type as "depends_on" | "imports" | "calls" | "extends" | "implements" | "contains" | "defines",
        weight: edge.weight,
      })),
      clusters: data.clusters.map((cluster: any) => ({
        id: cluster.id,
        name: cluster.name,
        nodes: cluster.nodes,
        color: cluster.color,
      })),
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error("Error loading graph data:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackData = {
      nodes: [
        {
          id: "fallback-1",
          name: "No graph data available",
          type: "concept" as const,
          size: 10,
          color: "#6b7280",
          repository: "",
          language: "",
        },
      ],
      edges: [],
      clusters: [],
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
}
