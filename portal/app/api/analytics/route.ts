import { type NextRequest, NextResponse } from "next/server"
import { buildApiUrl } from "@/lib/config"

export async function GET(request: NextRequest) {
  try {
    const backendUrl = buildApiUrl("/api/analytics")
    
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
    
    // Transform backend data to match frontend interface
    const analyticsData = {
      codebaseMetrics: {
        totalRepositories: data.codebaseMetrics?.totalRepositories || 0,
        totalFiles: data.codebaseMetrics?.totalFiles || 0,
        sourceCodeFiles: data.codebaseMetrics?.sourceCodeFiles || 0,
        documentationFiles: data.codebaseMetrics?.documentationFiles || 0,
        assetFiles: data.codebaseMetrics?.assetFiles || 0,
      },
      entityDistribution: {
        functions: data.entityDistribution?.functions || 0,
        classes: data.entityDistribution?.classes || 0,
        interfaces: data.entityDistribution?.interfaces || 0,
        attributes: data.entityDistribution?.attributes || 0,
        variables: data.entityDistribution?.variables || 0,
        parameters: data.entityDistribution?.parameters || 0,
      },
      languageDistribution: data.languageDistribution?.map((lang: any) => ({
        language: lang.language,
        entities: lang.entities,
        percentage: lang.percentage,
      })) || [],
      complexityMetrics: {
        averageCyclomaticComplexity: data.complexityMetrics?.averageCyclomaticComplexity || 0,
        highComplexityFunctions: data.complexityMetrics?.highComplexityFunctions || 0,
        totalLinesOfCode: data.complexityMetrics?.totalLinesOfCode || 0,
      },
      documentationMetrics: {
        totalDocumentationEntities: data.documentationMetrics?.totalDocumentationEntities || 0,
        readmeFiles: data.documentationMetrics?.readmeFiles || 0,
        codeComments: data.documentationMetrics?.codeComments || 0,
        apiDocumentation: data.documentationMetrics?.apiDocumentation || 0,
      },
      developmentMetrics: {
        totalCommits: data.developmentMetrics?.totalCommits || 0,
        totalIssues: data.developmentMetrics?.totalIssues || 0,
        totalContributors: data.developmentMetrics?.totalContributors || 0,
      },
      assetMetrics: {
        imageFiles: data.assetMetrics?.imageFiles || 0,
        audioFiles: data.assetMetrics?.audioFiles || 0,
        videoFiles: data.assetMetrics?.videoFiles || 0,
        fontFiles: data.assetMetrics?.fontFiles || 0,
      },
      trends: {
        complexity: {
          timestamps: data.trends?.complexity?.timestamps || [],
          values: data.trends?.complexity?.values || [],
        },
        documentation: {
          timestamps: data.trends?.documentation?.timestamps || [],
          values: data.trends?.documentation?.values || [],
        },
      },
    }

    return NextResponse.json(analyticsData)
  } catch (error) {
    console.error("Error loading analytics:", error)
    
    // Return fallback data if backend is unavailable
    const fallbackData = {
      codebaseMetrics: {
        totalRepositories: 0,
        totalFiles: 0,
        sourceCodeFiles: 0,
        documentationFiles: 0,
        assetFiles: 0,
      },
      entityDistribution: {
        functions: 0,
        classes: 0,
        interfaces: 0,
        attributes: 0,
        variables: 0,
        parameters: 0,
      },
      languageDistribution: [],
      complexityMetrics: {
        averageCyclomaticComplexity: 0,
        highComplexityFunctions: 0,
        totalLinesOfCode: 0,
      },
      documentationMetrics: {
        totalDocumentationEntities: 0,
        readmeFiles: 0,
        codeComments: 0,
        apiDocumentation: 0,
      },
      developmentMetrics: {
        totalCommits: 0,
        totalIssues: 0,
        totalContributors: 0,
      },
      assetMetrics: {
        imageFiles: 0,
        audioFiles: 0,
        videoFiles: 0,
        fontFiles: 0,
      },
      trends: {
        complexity: { timestamps: [], values: [] },
        documentation: { timestamps: [], values: [] },
      },
    }
    
    return NextResponse.json(fallbackData, { status: 503 })
  }
}
