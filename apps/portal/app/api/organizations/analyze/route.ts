import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name } = body

    if (!name) {
      return NextResponse.json({ error: "Organization name is required" }, { status: 400 })
    }

    // Forward the request to the backend analyze API
    const backendUrl = buildApiUrl("/api/organizations/analyze")
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error analyzing organization:", error)
    return NextResponse.json({ error: "Failed to analyze organization" }, { status: 500 })
  }
}
