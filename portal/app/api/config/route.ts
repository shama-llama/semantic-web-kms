import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    const backendUrl = buildApiUrl("/api/config")
    
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
    console.error("Error loading config:", error)
    
    // Return fallback config if backend is unavailable
    const fallbackData = {
      backend: {
        version: "1.0.0",
        environment: "development",
        debug: true,
      },
      database: {
        type: "AllegroGraph",
        url: null,
        repository: null,
        connected: false,
      },
      features: {
        sparql_endpoint: true,
        progress_tracking: true,
        file_upload: true,
        analytics: true,
        export: true,
      },
      paths: {
        input_directory: "~/downloads/repos/Thinkster/",
        output_directory: "output",
        logs_directory: "logs",
      },
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
} 