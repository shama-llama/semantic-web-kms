import { NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET() {
  try {
    // Forward the request to the backend input directory API
    const backendUrl = buildApiUrl("/api/input-directory")
    const response = await fetch(backendUrl)
    
    if (!response.ok) {
      console.error(`Backend responded with status ${response.status}: ${response.statusText}`)
      return NextResponse.json({ error: "Failed to get input directory" }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error getting input directory:", error)
    return NextResponse.json({ error: "Failed to get input directory" }, { status: 500 })
  }
} 