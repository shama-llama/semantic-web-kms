import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const orgId = decodeURIComponent(id)
    
    // Handle both URI and simple name formats
    let backendUrl: string
    if (orgId.startsWith('http')) {
      // Full URI - encode properly
      backendUrl = buildApiUrl(`/api/organizations/${encodeURIComponent(orgId)}`)
    } else {
      // Simple name - try to find the full URI first
      const orgsResponse = await fetch(buildApiUrl('/api/organizations'))
      if (orgsResponse.ok) {
        const orgs = await orgsResponse.json()
        const org = orgs.find((o: any) => o.name === orgId || o.id.endsWith(orgId))
        if (org) {
          backendUrl = buildApiUrl(`/api/organizations/${encodeURIComponent(org.id)}`)
        } else {
          throw new Error('Organization not found')
        }
      } else {
        throw new Error('Failed to fetch organizations')
      }
    }
    
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(10000), // 10 seconds timeout
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error loading organization:", error)
    
    // Return error response
    return NextResponse.json(
      { error: "Failed to load organization" },
      { status: 503 }
    )
  }
} 