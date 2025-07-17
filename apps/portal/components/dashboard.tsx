"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { BarChart3, Database, GitBranch, Network, Search, TrendingUp, Users, Clock, FileText, BarChart } from "lucide-react"
import Link from "next/link"
import { useOrganization } from "@/components/organization-provider"
import React, { type JSX } from "react";
import {
  SiPython,
  SiJavascript,
  SiTypescript,
  SiGo,
  SiRust,
  SiRuby,
  SiPhp,
  SiC,
  SiGnubash,
  SiSwift,
  SiLua,
  SiScala,
  SiHtml5,
  SiCss3,
  SiSass
} from "react-icons/si";
import { formatDistanceToNow, format, parseISO, isValid } from "date-fns"

interface DashboardStats {
  totalEntities: number
  totalRelationships: number
  totalImports: number
  totalRepositories: number
  totalFiles: number
  totalLines: number
  averageComplexity: number
  recentActivity: {
    lastUpdated: string
    newEntities: number
    newRelationships: number
  }
  topLanguages: Array<{
    language: string
    percentage: number
    entities: number
  }>
  processingStatus: {
    status: string
    lastProcessed: string
    nextScheduled: string
  }
}

// Update the Repository interface
type RepoComplexity = number | { average: number }

interface Repository {
  id: string
  name: string
  language: string
  entities: number
  complexity: RepoComplexity
  contributors: number
  lastUpdated: string
  files: number
}

function getRepoAverageComplexity(complexity: RepoComplexity): number | string {
  if (typeof complexity === "object" && complexity !== null && "average" in complexity) {
    return complexity.average
  }
  if (typeof complexity === "number") {
    return complexity
  }
  return "-"
}

const LANGUAGE_DISPLAY_MAP: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  tsx: "TypeScript (TSX)",
  java: "Java",
  go: "Go",
  rust: "Rust",
  ruby: "Ruby",
  php: "PHP",
  c: "C",
  cpp: "C++",
  c_sharp: "C#",
  bash: "Bash",
  swift: "Swift",
  lua: "Lua",
  scala: "Scala",
  html: "HTML",
  css: "CSS",
  scss: "SCSS",
};

const LANGUAGE_ICON_MAP: Record<string, JSX.Element> = {
  python: <SiPython />,
  javascript: <SiJavascript />,
  typescript: <SiTypescript />,
  tsx: <SiTypescript />,
  go: <SiGo />,
  rust: <SiRust />,
  ruby: <SiRuby />,
  php: <SiPhp />,
  c: <SiC />,
  c_sharp: <SiC />,
  bash: <SiGnubash />,
  swift: <SiSwift />,
  lua: <SiLua />,
  scala: <SiScala />,
  html: <SiHtml5 />,
  css: <SiCss3 />,
  scss: <SiSass />,
};

function normalizeLanguage(lang: string): string {
  return LANGUAGE_DISPLAY_MAP[lang.toLowerCase()] || lang;
}

function getLanguageIcon(lang: string): JSX.Element | null {
  return LANGUAGE_ICON_MAP[lang.toLowerCase()] || null;
}

// Utility to format ISO date strings in a user-friendly way
function formatUserFriendlyDate(dateString: string): string {
  if (!dateString) return "N/A"
  let date: Date
  // Try parsing as ISO, fallback to Date constructor
  try {
    date = parseISO(dateString)
    if (!isValid(date)) {
      date = new Date(dateString)
    }
  } catch {
    date = new Date(dateString)
  }
  if (!isValid(date)) return dateString
  const now = new Date()
  // If within 7 days, show relative, else show short date
  const diff = Math.abs(now.getTime() - date.getTime())
  const sevenDays = 7 * 24 * 60 * 60 * 1000
  if (diff < sevenDays) {
    return formatDistanceToNow(date, { addSuffix: true })
  }
  return format(date, "MMM d, yyyy")
}

export function Dashboard() {
  const { processingStages } = useOrganization()
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        // Fetch dashboard stats
        const statsResponse = await fetch("/api/dashboard_stats")
        if (!statsResponse.ok) {
          throw new Error("Failed to load dashboard statistics")
        }
        const stats = await statsResponse.json()
        setDashboardStats(stats)

        // Fetch repositories
        const reposResponse = await fetch("/api/repositories")
        if (!reposResponse.ok) {
          throw new Error("Failed to load repositories")
        }
        const repos = await reposResponse.json()
        setRepositories(repos)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  // Check if we have meaningful data (not just zeros)
  const hasData = dashboardStats && (
    dashboardStats.totalEntities > 0 ||
    dashboardStats.totalRelationships > 0 ||
    dashboardStats.totalRepositories > 0 ||
    repositories.length > 0
  )

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Loading dashboard data...</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-8 bg-muted rounded w-1/2" />
                  <div className="h-3 bg-muted rounded w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Error loading dashboard data</p>
        </div>
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <div className="text-center space-y-4">
              <p className="text-red-600">{error}</p>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show placeholder when no data is available
  if (!hasData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Overview of semantic knowledge analysis</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart className="h-5 w-5" />
              <span>Dashboard Overview</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Data Available</h3>
                <p className="text-muted-foreground">
                  Dashboard metrics and analytics will be displayed here once you add and analyze repositories.
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of semantic knowledge analysis - Last updated {formatUserFriendlyDate(dashboardStats.recentActivity.lastUpdated)}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Files</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardStats.totalFiles.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Files analyzed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Entities</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardStats.totalEntities.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Entities extracted</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Relationships</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardStats.totalRelationships.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Relationships in knowledge graph</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Complexity</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardStats.averageComplexity}</div>
            <p className="text-xs text-muted-foreground">Cyclomatic complexity</p>
          </CardContent>
        </Card>
      </div>

      {/* Processing Status */}
      {Object.keys(processingStages).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Status</CardTitle>
            <CardDescription>Current analysis pipeline status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(processingStages).map(([stage, status]) => (
              <div key={stage} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{stage.replace(/([A-Z])/g, " $1").trim()}</span>
                  <Badge variant={status.status === "completed" ? "default" : "secondary"}>{status.status}</Badge>
                </div>
                <Progress value={status.progress} className="h-2" />
                {status.message && <p className="text-xs text-muted-foreground">{status.message}</p>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      
      {/* Language Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Language Distribution</CardTitle>
          <CardDescription>Entities by programming language</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {dashboardStats.topLanguages.map((lang) => (
              <div key={lang.language} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getLanguageIcon(lang.language)}
                  <span className="text-sm font-medium">{normalizeLanguage(lang.language)}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-muted-foreground">{lang.entities} files</span>
                  <span className="text-sm font-medium">{lang.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="cursor-pointer hover:shadow-md transition-shadow">
          <Link href="/search">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Search className="h-5 w-5" />
                <span>Semantic Search</span>
              </CardTitle>
              <CardDescription>Search through your codebase using natural language</CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow">
          <Link href="/knowledge-graph">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Network className="h-5 w-5" />
                <span>Knowledge Graph</span>
              </CardTitle>
              <CardDescription>Visualize relationships between code entities</CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow">
          <Link href="/analytics">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>Analytics</span>
              </CardTitle>
              <CardDescription>Deep insights into code quality and patterns</CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>
      
      {/* Repository Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Repository Overview</CardTitle>
          <CardDescription>{dashboardStats.totalRepositories} repositories analyzed</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {repositories.slice(0, 5).map((repo) => (
              <div key={repo.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{repo.name}</span>
                    <Badge variant="outline">{repo.language}</Badge>
                  </div>
                </div>
                <div className="text-right space-y-1">
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <span className="flex items-center space-x-1">
                      <FileText className="h-3 w-3" />
                      <span>{repo.files}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Users className="h-3 w-3" />
                      <span>{repo.contributors}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <TrendingUp className="h-3 w-3" />
                      <span>{getRepoAverageComplexity(repo.complexity)}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatUserFriendlyDate(repo.lastUpdated)}</span>
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {repositories.length > 5 && (
              <div className="text-center">
                <Link href="/repositories">
                  <Button variant="outline">View All {repositories.length} Repositories</Button>
                </Link>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

    </div>
  )
}
