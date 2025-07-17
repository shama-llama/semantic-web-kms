import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const files = formData.getAll("files") as File[]
    
    if (!files || files.length === 0) {
      return NextResponse.json({ error: "No files provided" }, { status: 400 })
    }

    // Forward the request to the backend upload API
    const backendUrl = buildApiUrl("/api/upload/organization")
    const backendFormData = new FormData()
    
    files.forEach((file) => {
      backendFormData.append("files", file)
    })

    const response = await fetch(backendUrl, {
      method: "POST",
      body: backendFormData,
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error uploading files:", error)
    return NextResponse.json({ error: "Failed to upload files" }, { status: 500 })
  }
} 