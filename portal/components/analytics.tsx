"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Code, Shield, FileText, Users, Target, BarChart3, Database } from "lucide-react"
import { analyticsApi } from "@/lib/api"
import type { AnalyticsData } from "@/lib/api"
import { useOrganization } from "@/components/organization-provider"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export function Analytics() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { organization } = useOrganization()

  // Debug logging
  console.log("Analytics component - organization:", organization)
  console.log("Analytics component - analyticsData:", analyticsData)

  useEffect(() => {
    if (organization) {
      loadAnalyticsData()
    }
  }, [organization])

  const loadAnalyticsData = async () => {
    if (!organization) return

    setIsLoading(true)
    try {
      const data = await analyticsApi.getData(organization.id)
      setAnalyticsData(data)
    } catch (error) {
      console.error("Failed to load analytics data:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Check if we have meaningful data
  const hasData = analyticsData && (
    (analyticsData.codebaseMetrics?.totalFiles || 0) > 0 ||
    (analyticsData.entityDistribution?.functions || 0) > 0 ||
    (analyticsData.entityDistribution?.classes || 0) > 0 ||
    (analyticsData.languageDistribution?.length || 0) > 0
  )

  // Show placeholder when no organization or no data
  if (!organization) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Deep insights into code quality and patterns</p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Analytics</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Data Available</h3>
                <p className="text-muted-foreground">
                  Analytics and insights will be available once you add and analyze repositories.
                </p>
              </div>
              <Link href="/">
                <Button>Back to Dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Loading analytics data...</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-8 bg-muted rounded w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  // Show placeholder when no meaningful data
  if (!hasData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Comprehensive analysis of {organization.name} codebase quality and patterns
          </p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Analytics</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Analytics Data</h3>
                <p className="text-muted-foreground">
                  Analytics and insights will be available once repositories are analyzed.
                </p>
              </div>
              <Link href="/">
                <Button>Back to Dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Ensure we have the expected data structure
  if (!analyticsData || !analyticsData.codebaseMetrics || !analyticsData.entityDistribution) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Comprehensive analysis of {organization.name} codebase quality and patterns
          </p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Analytics</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">Data Structure Error</h3>
                <p className="text-muted-foreground">
                  Analytics data is not in the expected format. Please try refreshing the page.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Comprehensive analysis of {organization.name} codebase quality and patterns
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Lines</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((analyticsData.complexityMetrics || {}).totalLinesOfCode || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Across {((analyticsData.codebaseMetrics || {}).totalFiles || 0)} files</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Functions</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((analyticsData.entityDistribution || {}).functions || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Total functions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Complexity</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((analyticsData.complexityMetrics || {}).averageCyclomaticComplexity || 0)}</div>
            <p className="text-xs text-muted-foreground">Average complexity</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Documentation</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((analyticsData.documentationMetrics || {}).totalDocumentationEntities || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Documentation entities</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="entities">Entities</TabsTrigger>
          <TabsTrigger value="languages">Languages</TabsTrigger>
          <TabsTrigger value="quality">Documentation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Codebase Metrics</CardTitle>
                <CardDescription>Overall codebase statistics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Total Files</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).totalFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Source Files</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).sourceCodeFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Documentation</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).documentationFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Repositories</span>
                    </div>
                    <div className="text-2xl font-bold">{((analyticsData.codebaseMetrics || {}).totalRepositories || 0).toLocaleString()}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Complexity Metrics</CardTitle>
                <CardDescription>Code complexity analysis</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Average Complexity</span>
                    <span className="text-sm text-muted-foreground">
                      {((analyticsData.complexityMetrics || {}).averageCyclomaticComplexity || 0)}
                    </span>
                  </div>
                  <Progress value={((analyticsData.complexityMetrics || {}).averageCyclomaticComplexity || 0) * 10} />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">High Complexity Functions</span>
                    <span className="text-sm text-muted-foreground">
                      {((analyticsData.complexityMetrics || {}).highComplexityFunctions || 0)}
                    </span>
                  </div>
                  <Progress value={(((analyticsData.complexityMetrics || {}).highComplexityFunctions || 0) / ((analyticsData.entityDistribution || {}).functions || 1)) * 100} />
                </div>
                <div className="text-sm text-muted-foreground">
                  {((analyticsData.complexityMetrics || {}).highComplexityFunctions || 0)} functions have high complexity
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="entities" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Entity Distribution</CardTitle>
                <CardDescription>WDO ontology entity types</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Functions</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.entityDistribution || {}).functions || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Classes</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.entityDistribution || {}).classes || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Interfaces</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.entityDistribution || {}).interfaces || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Imports</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {/* Placeholder for Imports, as it's not in the data yet */}
                      0
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>File Types</CardTitle>
                <CardDescription>Digital information carriers</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Code className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Source Files</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).sourceCodeFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Documentation</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).documentationFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Assets</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).assetFiles || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Total Files</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {((analyticsData.codebaseMetrics || {}).totalFiles || 0).toLocaleString()}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="languages" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Language Distribution</CardTitle>
              <CardDescription>Programming languages used across the codebase</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(analyticsData.languageDistribution || []).map((lang) => (
                <div key={lang.language} className="space-y-2">
                  <div className="flex justify-between">
                    <span className="font-medium">{lang.language}</span>
                    <span className="text-sm text-muted-foreground">
                      {lang.percentage || 0}% ({(lang.entities || 0).toLocaleString()} files)
                    </span>
                  </div>
                  <Progress value={lang.percentage || 0} />
                </div>
              )) || (
                <div className="text-center text-muted-foreground">
                  No language data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="quality" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Documentation Metrics</CardTitle>
                <CardDescription>Documentation coverage and quality</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">

                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Total Documentation</span>
                    <span className="text-sm text-muted-foreground">
                      {((analyticsData.documentationMetrics || {}).totalDocumentationEntities || 0)}
                    </span>
                  </div>
                  <Progress value={(((analyticsData.documentationMetrics || {}).totalDocumentationEntities || 0) / ((analyticsData.entityDistribution || {}).functions || 1)) * 100} />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">README Files</span>
                    <span className="text-sm text-muted-foreground">{((analyticsData.documentationMetrics || {}).readmeFiles || 0)}</span>
                  </div>
                  <Progress value={(((analyticsData.documentationMetrics || {}).readmeFiles || 0) / ((analyticsData.codebaseMetrics || {}).totalFiles || 1)) * 100} />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Code Comments</span>
                    <span className="text-sm text-muted-foreground">{((analyticsData.documentationMetrics || {}).codeComments || 0)}</span>
                  </div>
                  <Progress value={(((analyticsData.documentationMetrics || {}).codeComments || 0) / ((analyticsData.entityDistribution || {}).functions || 1)) * 100} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Development Activity</CardTitle>
                <CardDescription>Development metrics and trends</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="text-sm text-muted-foreground">
                    Total Commits: {((analyticsData.developmentMetrics || {}).totalCommits || 0)}
                  </div>

                  <div className="text-sm text-muted-foreground">
                    Total Issues: {((analyticsData.developmentMetrics || {}).totalIssues || 0)}
                  </div>

                  <div className="text-sm text-muted-foreground">
                    Contributors: {((analyticsData.developmentMetrics || {}).totalContributors || 0)}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>


      </Tabs>
    </div>
  )
}
