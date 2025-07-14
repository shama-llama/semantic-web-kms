import { NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET() {
  try {
    const backendUrl = buildApiUrl("/api/organizations")
    console.log("Frontend API: Calling backend URL:", backendUrl)
    
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(10000), // 10 seconds timeout
    })

    console.log("Frontend API: Backend response status:", response.status)

    if (!response.ok) {
      console.error("Frontend API: Backend error:", response.status, response.statusText)
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    console.log("Frontend API: Backend data:", data)
    return NextResponse.json(data)
  } catch (error) {
    console.error("Frontend API: Error loading organizations:", error)
    
    // Return empty array if backend is unavailable
    return NextResponse.json([], { status: 503 })
  }
} 