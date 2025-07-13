import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl, handleApiError } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    // Forward organization query parameter if present
    const { searchParams } = new URL(request.url)
    const organization = searchParams.get("organization")
    let backendUrl = buildApiUrl("/api/dashboard_stats")
    if (organization) {
      backendUrl += `?organization=${encodeURIComponent(organization)}`
    }

    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      // Reduced timeout for better UX
      signal: AbortSignal.timeout(15000), // 15 seconds instead of 30
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    
    // Transform backend data to match frontend interface
    const dashboardStats = {
      totalEntities: data.totalEntities || 0,
      totalRelationships: data.totalRelationships || 0,
      totalImports: data.totalImports || 0,
      totalRepositories: data.totalRepos || 0,
      totalFiles: data.totalFiles || 0,
      totalLines: 0, // Not provided by backend yet
      averageComplexity: data.averageComplexity || 0,
      recentActivity: {
        lastUpdated: new Date().toISOString(),
        newEntities: 0,
        newRelationships: 0,
      },
      topLanguages: data.topLanguages || [],
      processingStatus: {
        status: "completed",
        lastProcessed: new Date().toISOString(),
        nextScheduled: new Date().toISOString(),
      },
    }

    return NextResponse.json(dashboardStats)
  } catch (error) {
    console.error("Error loading dashboard stats:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackStats = {
      totalEntities: 0,
      totalRelationships: 0,
      totalImports: 0,
      totalRepositories: 0,
      totalFiles: 0,
      totalLines: 0,
      averageComplexity: 0,
      recentActivity: {
        lastUpdated: new Date().toISOString(),
        newEntities: 0,
        newRelationships: 0,
      },
      topLanguages: [],
      processingStatus: {
        status: "error",
        lastProcessed: new Date().toISOString(),
        nextScheduled: new Date().toISOString(),
      },
    }
    
    return NextResponse.json(fallbackStats, { status: 503 })
  }
} 