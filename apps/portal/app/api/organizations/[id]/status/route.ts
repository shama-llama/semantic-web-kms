import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params

    // Forward the request to the backend progress tracking API
    const backendUrl = buildApiUrl(`/api/progress/${id}`)
    const response = await fetch(backendUrl)
    
    if (!response.ok) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 })
    }

    const jobStatus = await response.json()
    return NextResponse.json(jobStatus.stages)
  } catch (error) {
    console.error("Error getting processing status:", error)
    return NextResponse.json({ error: "Failed to get processing status" }, { status: 500 })
  }
}
