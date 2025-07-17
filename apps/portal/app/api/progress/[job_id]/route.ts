import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ job_id: string }> }
) {
  try {
    const { job_id } = await params

    if (!job_id) {
      return NextResponse.json({ error: "Job ID is required" }, { status: 400 })
    }

    // Forward the request to the backend progress API
    const backendUrl = buildApiUrl(`/api/progress/${job_id}`)
    const response = await fetch(backendUrl)

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error getting progress:", error)
    return NextResponse.json({ error: "Failed to get progress" }, { status: 500 })
  }
} 