"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, Filter, Code, FileText, Lightbulb, ExternalLink, Database } from "lucide-react"
import { searchApi } from "@/lib/api"
import type { SearchResult } from "@/lib/api"
import { useOrganization } from "@/components/organization-provider"
import Link from "next/link"

export function SemanticSearch() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedType, setSelectedType] = useState<string>("all")
  const [selectedRepo, setSelectedRepo] = useState<string>("all")
  const [suggestions, setSuggestions] = useState<{ query: string; category: string }[]>([])
  const { organization } = useOrganization()

  const loadSuggestions = useCallback(async () => {
    if (!organization) return
    try {
      const suggestionData = await searchApi.suggestions()
      setSuggestions(suggestionData)
    } catch (error) {
      console.error("Failed to load suggestions:", error)
    }
  }, [organization])

  useEffect(() => {
    if (organization) {
      loadSuggestions()
    }
  }, [organization, loadSuggestions])

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim() || !organization) return

    setIsLoading(true)
    try {
      const searchResults = await searchApi.semantic(organization.id, searchQuery, {
        filters: {
          entityType: selectedType !== "all" ? selectedType : undefined,
          repository: selectedRepo !== "all" ? selectedRepo : undefined,
        },
      })
      setResults(searchResults)
    } catch (error) {
      console.error("Search failed:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    handleSearch(suggestion)
  }

  const getEntityIcon = (type: string) => {
    switch (type) {
      case "function":
        return <Code className="h-4 w-4" />
      case "class":
        return <FileText className="h-4 w-4" />
      case "component":
        return <Code className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "bg-green-500"
    if (confidence >= 0.6) return "bg-yellow-500"
    return "bg-red-500"
  }

  // Show placeholder when no organization or no data
  if (!organization) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Semantic Search</h1>
          <p className="text-muted-foreground">Search through your codebase using natural language</p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Search className="h-5 w-5" />
              <span>Semantic Search</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Data Available</h3>
                <p className="text-muted-foreground">
                  Semantic search functionality will be available once you add and analyze repositories.
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
        <h1 className="text-3xl font-bold">Semantic Search</h1>
        <p className="text-muted-foreground">Search through {organization.name} using natural language queries</p>
      </div>

      {/* Search Interface */}
      <Card>
        <CardHeader>
          <CardTitle>Search Query</CardTitle>
          <CardDescription>Use natural language to find code patterns, functions, and concepts</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="e.g., authentication functions, React components for user management"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button onClick={() => handleSearch()} disabled={!query.trim() || isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </Button>
          </div>

          {/* Filters */}
          <div className="flex space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Entity Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="function">Functions</SelectItem>
                  <SelectItem value="class">Classes</SelectItem>
                  <SelectItem value="component">Components</SelectItem>
                  <SelectItem value="interface">Interfaces</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Select value={selectedRepo} onValueChange={setSelectedRepo}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Repository" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Repositories</SelectItem>
                {organization.repositories.map((repo) => (
                  <SelectItem key={repo.id} value={repo.name}>
                    {repo.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Suggestions */}
      {suggestions.length > 0 && !results && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Lightbulb className="h-5 w-5" />
              <span>Suggested Queries</span>
            </CardTitle>
            <CardDescription>Try these popular search patterns</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="justify-start h-auto p-3 bg-transparent"
                  onClick={() => handleSuggestionClick(suggestion.query)}
                >
                  <div className="text-left">
                    <div className="font-medium">{suggestion.query}</div>
                    <div className="text-xs text-muted-foreground">{suggestion.category}</div>
                  </div>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search Results */}
      {results && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search Results</CardTitle>
              <CardDescription>
                Found {results.totalCount} entities with {Math.round(results.semanticInsights.confidence * 100)}%
                confidence
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="entities" className="w-full">
                <TabsList>
                  <TabsTrigger value="entities">Entities</TabsTrigger>
                  <TabsTrigger value="insights">Insights</TabsTrigger>
                </TabsList>

                <TabsContent value="entities" className="space-y-4">
                  {results.entities.map((entity) => (
                    <Card key={entity.id} className="hover:shadow-md transition-shadow">
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          <div className="flex items-start justify-between">
                            <div className="space-y-1">
                              <div className="flex items-center space-x-2">
                                {getEntityIcon(entity.type)}
                                <span className="font-medium">{entity.name}</span>
                                <Badge variant="outline">{entity.type}</Badge>
                                <Badge variant="outline">{entity.repository}</Badge>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {entity.enrichedDescription ? (
                                  <span dangerouslySetInnerHTML={{ __html: entity.enrichedDescription }} />
                                ) : (
                                  entity.description
                                )}
                              </p>
                            </div>
                            <div className="flex items-center space-x-2">
                              <div className="flex items-center space-x-1">
                                <div className={`w-2 h-2 rounded-full ${getConfidenceColor(entity.confidence)}`} />
                                <span className="text-xs text-muted-foreground">
                                  {Math.round(entity.confidence * 100)}%
                                </span>
                              </div>
                              <Button variant="ghost" size="sm">
                                <ExternalLink className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>

                          <div className="bg-muted rounded-md p-3">
                            <code className="text-sm">{entity.snippet}</code>
                          </div>

                          <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                            <span>{entity.file}</span>
                            <span>Line {entity.line}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </TabsContent>

                <TabsContent value="insights" className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Related Concepts</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {results.semanticInsights.relatedConcepts.map((concept, index) => (
                            <Badge
                              key={index}
                              variant="secondary"
                              className="cursor-pointer hover:bg-secondary/80"
                              onClick={() => handleSuggestionClick(concept)}
                            >
                              {concept}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Suggested Queries</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {results.semanticInsights.suggestedQueries.map((suggestion, index) => (
                            <Button
                              key={index}
                              variant="ghost"
                              className="justify-start h-auto p-2 w-full"
                              onClick={() => handleSuggestionClick(suggestion)}
                            >
                              <Search className="h-3 w-3 mr-2" />
                              {suggestion}
                            </Button>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
