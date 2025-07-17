"use client"

import { useEffect, useState } from "react"
import { getRepositories, Repository } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Database, GitBranch, Clock } from "lucide-react"
import Link from "next/link"

// Extend Repository to include optional fields that may be present in backend data
interface RepositoryWithExtras extends Repository {
  description?: string;
  files?: number;
}

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<RepositoryWithExtras[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRepos = async () => {
      setLoading(true)
      setError(null)
      try {
        const repos = await getRepositories()
        setRepositories(repos)
      } catch (err) {
        const errorMsg = (err instanceof Error) ? err.message : "Failed to load repositories"
        setError(errorMsg)
      } finally {
        setLoading(false)
      }
    }
    fetchRepos()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Repositories</h1>
          <p className="text-muted-foreground">Loading repository data...</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
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
          <h1 className="text-3xl font-bold">Repositories</h1>
          <p className="text-muted-foreground">Error loading repositories</p>
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

  if (!repositories || repositories.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Repositories</h1>
          <p className="text-muted-foreground">Repository analysis and management</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5" />
              <span>Repository Analysis</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Data Available</h3>
                <p className="text-muted-foreground">
                  Repository analysis and management will be available once you add and analyze repositories.
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

  // Set a min height for the header to align all cards, and use flex-col for vertical alignment
  const HEADER_MIN_HEIGHT = "4.5rem"; // Adjust as needed for 1-2 lines of title+badge

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Repositories</h1>
        <p className="text-muted-foreground">Repository analysis and management</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {repositories.map((repo) => (
          <Card key={repo.id}>
            <CardHeader className="flex flex-col justify-start" style={{ minHeight: HEADER_MIN_HEIGHT }}>
              <div className="flex items-start gap-2 min-h-[2.5rem]">
                <GitBranch className="h-4 w-4 mt-1" />
                <div className="flex-1">
                  <CardTitle className="text-lg font-bold leading-tight break-words">
                    {repo.name}
                  </CardTitle>
                </div>
                <Badge variant="outline" className="shrink-0 mt-1">{repo.language}</Badge>
              </div>
              <CardDescription className="mt-1 text-sm text-muted-foreground break-words">
                {repo.description || "No description"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-2 gap-4 text-sm mb-2">
                <div>
                  <p className="text-muted-foreground">Entities</p>
                  <p className="font-medium break-words">{repo.entities ?? 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Contributors</p>
                  <p className="font-medium break-words">{repo.contributors ?? 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Files</p>
                  <p className="font-medium break-words">{repo.files ?? "-"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Complexity</p>
                  <p className="font-medium break-words">{repo.complexity?.average ?? "-"}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
                <Clock className="h-3 w-3" />
                <span className="break-words">Last updated: {repo.lastUpdated ? new Date(repo.lastUpdated).toLocaleString() : "-"}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
