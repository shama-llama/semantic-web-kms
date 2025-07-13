import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    const backendUrl = buildApiUrl("/api/metrics/code-complexity")
    
    const response = await fetch(backendUrl, {
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
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error loading code complexity metrics:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackData = {
      averageComplexity: 0,
      highComplexityFiles: 0,
      totalFiles: 0,
      files: [],
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
} 