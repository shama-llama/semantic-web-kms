import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ format: string }> }
) {
  try {
    const { format } = await params

    if (!format) {
      return NextResponse.json({ error: "Export format is required" }, { status: 400 })
    }

    const backendUrl = buildApiUrl(`/api/export/${format}`)
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(60000), // Longer timeout for exports
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    // Handle different content types
    const contentType = response.headers.get("content-type")
    
    if (contentType?.includes("text/csv")) {
      const csvData = await response.text()
      return new NextResponse(csvData, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="knowledge-base.${format}"`,
        },
      })
    } else if (contentType?.includes("text/turtle")) {
      const ttlData = await response.text()
      return new NextResponse(ttlData, {
        headers: {
          "Content-Type": "text/turtle",
          "Content-Disposition": `attachment; filename="knowledge-base.${format}"`,
        },
      })
    } else if (contentType?.includes("application/rdf+xml")) {
      const rdfData = await response.text()
      return new NextResponse(rdfData, {
        headers: {
          "Content-Type": "application/rdf+xml",
          "Content-Disposition": `attachment; filename="knowledge-base.${format}"`,
        },
      })
    } else {
      // JSON response
      const data = await response.json()
      return NextResponse.json(data)
    }
  } catch (error) {
    console.error("Error exporting data:", error)
    return NextResponse.json({ error: "Failed to export data" }, { status: 500 })
  }
} 