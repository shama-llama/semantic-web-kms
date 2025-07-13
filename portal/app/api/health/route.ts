import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    const backendUrl = buildApiUrl("/api/health")
    
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(10000), // Shorter timeout for health checks
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error checking health:", error)
    
    // Return unhealthy status if backend is unavailable
    const fallbackData = {
      status: "unhealthy",
      error: "Backend not accessible",
      timestamp: new Date().toISOString(),
      services: {
        sparql_endpoint: false,
        filesystem: false,
        api_server: false,
      },
      system: {
        memory_usage: 0,
        disk_usage: 0,
      },
      version: "1.0.0",
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
} 