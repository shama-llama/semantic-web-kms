import { NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET() {
  try {
    const backendUrl = buildApiUrl("/api/relationships")
    
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
    console.error("Error loading relationships:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackData = {
      relationships: [],
      totalRelationships: 0,
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
} 