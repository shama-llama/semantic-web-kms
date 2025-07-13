"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Search, Database, Code, AlertCircle, Play, Download, RefreshCw, Zap, Brain } from "lucide-react"
import { InteractiveGraph } from "./interactive-graph"
import { DataInputPanel } from "./data-input-panel"
import { useOrganization } from "@/components/organization-provider"
import type { KnowledgeGraphNode, SPARQLQuery } from "@/lib/sparql"
import { useSPARQLGraph } from "@/hooks/useSPARQLGraph"

interface EnhancedKnowledgeGraphProps {
  className?: string
}

export function EnhancedKnowledgeGraph({ className }: EnhancedKnowledgeGraphProps) {
  const [customQuery, setCustomQuery] = useState("")
  const [queryResults, setQueryResults] = useState<any>(null)
  const [isQueryDialogOpen, setIsQueryDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [searchResults, setSearchResults] = useState<KnowledgeGraphNode[]>([])

  // Organization management
  const {
    organization,
    processingStages,
    isLoading: isOrgLoading,
    error: orgError,
    analyzeOrganization,
    refreshStatus,
    clearError: clearOrgError,
  } = useOrganization()

  // SPARQL graph integration
  const {
    graphData,
    isLoading: isGraphLoading,
    error: graphError,
    nodeDetails,
    executeQuery,
    loadGraph,
    searchNodes,
    getNodeDetails,
    getNodeNeighbors,
    clearError: clearGraphError,
  } = useSPARQLGraph(organization?.id || null)

  // Handle GitHub organization analysis
  const handleGitHubSubmit = async (orgName: string) => {
    await analyzeOrganization(orgName)
  }

  // Handle local folder upload
  const handleFolderUpload = async (files: FileList) => {
    // Convert FileList to FormData for upload
    const formData = new FormData()
    Array.from(files).forEach((file) => {
      formData.append('files', file)
    })

    try {
      const response = await fetch('/api/upload/organization', {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Organization upload failed")
      }

      const result = await response.json()
      console.log("Organization upload successful:", result)
      
      // Start polling for progress if job_id is returned
      if (result.job_id) {
        // You can implement progress tracking here similar to DataInputPanel
        console.log("Analysis started with job ID:", result.job_id)
      }
    } catch (error) {
      console.error("Organization upload error:", error)
    }
  }

  // Handle node click in graph
  const handleNodeClick = async (node: KnowledgeGraphNode) => {
    await getNodeDetails(node.uri)
  }

  // Handle custom SPARQL query execution
  const handleExecuteQuery = async () => {
    if (!customQuery.trim()) return

    try {
      const query: SPARQLQuery = { query: customQuery }
      const result = await executeQuery(query)
      setQueryResults(result)
      setIsQueryDialogOpen(true)
    } catch (error) {
      console.error("Query execution failed:", error)
    }
  }

  // Handle semantic search
  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setSearchResults([])
      return
    }

    try {
      const results = await searchNodes(searchTerm)
      setSearchResults(results)
    } catch (error) {
      console.error("Search failed:", error)
    }
  }

  // Predefined SPARQL queries for web development
  const predefinedQueries = [
    {
      name: "React Components",
      description: "Find all React components and their relationships",
      query: `
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX web: <http://example.org/web#>
        
        SELECT ?component ?label ?props ?hooks WHERE {
          ?component rdf:type web:ReactComponent .
          ?component rdfs:label ?label .
          OPTIONAL { ?component web:hasProps ?props }
          OPTIONAL { ?component web:usesHook ?hooks }
        }
        ORDER BY ?label
      `,
    },
    {
      name: "API Endpoints",
      description: "Show REST API endpoints and their methods",
      query: `
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX web: <http://example.org/web#>
        
        SELECT ?endpoint ?method ?controller WHERE {
          ?endpoint rdf:type web:APIEndpoint .
          ?endpoint web:httpMethod ?method .
          ?endpoint web:handledBy ?controller .
        }
        ORDER BY ?endpoint
      `,
    },
    {
      name: "Frontend Dependencies",
      description: "Map frontend framework dependencies",
      query: `
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX web: <http://example.org/web#>
        
        SELECT ?package ?version ?dependents WHERE {
          ?package rdf:type web:NPMPackage .
          ?package web:version ?version .
          ?package web:usedBy ?dependents .
          FILTER(CONTAINS(?package, "react") || CONTAINS(?package, "vue") || CONTAINS(?package, "angular"))
        }
        ORDER BY DESC(?dependents)
      `,
    },
    {
      name: "Database Schemas",
      description: "Identify database models and relationships",
      query: `
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX web: <http://example.org/web#>
        
        SELECT ?model ?table ?fields WHERE {
          ?model rdf:type web:DatabaseModel .
          ?model rdfs:label ?table .
          ?model web:hasField ?fields .
        }
        ORDER BY ?table
      `,
    },
  ]

  return (
    <div className={`space-y-4 sm:space-y-6 ${className}`}>
      {/* Data Input Panel */}
      <DataInputPanel />

      {/* Error Alerts */}
      {graphError && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          <AlertDescription className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
            <span>{graphError}</span>
            <Button variant="ghost" size="sm" onClick={clearGraphError} aria-label="Clear graph error">
              Clear
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Interface */}
      {organization && (
        <div className="grid grid-cols-1 lg:grid-cols-4 xl:grid-cols-5 gap-4 lg:gap-6">
          {/* Graph Visualization */}
          <div className="lg:col-span-3 xl:col-span-4">
            <InteractiveGraph
              data={graphData}
              isLoading={isGraphLoading}
              onNodeClick={handleNodeClick}
              onExport={(format) => console.log(`Exporting web development graph as ${format}`)}
            />
          </div>

          {/* Control Panel */}
          <div className="space-y-4">
            <Tabs defaultValue="search" className="w-full">
              <TabsList className="grid w-full grid-cols-3" role="tablist">
                <TabsTrigger value="search" aria-label="Search web development entities" role="tab">
                  <Search className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">Search</span>
                </TabsTrigger>
                <TabsTrigger value="sparql" aria-label="Execute SPARQL queries" role="tab">
                  <Database className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">SPARQL</span>
                </TabsTrigger>
                <TabsTrigger value="analysis" aria-label="Web development analysis tools" role="tab">
                  <Brain className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">Analysis</span>
                </TabsTrigger>
              </TabsList>

              {/* Semantic Search */}
              <TabsContent value="search" className="space-y-4" role="tabpanel">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Web Development Search</CardTitle>
                    <CardDescription className="text-xs">Search through components, APIs, and patterns</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        placeholder="Search components, APIs, patterns..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                        aria-label="Search web development entities"
                        aria-describedby="search-help"
                      />
                      <Button size="sm" onClick={handleSearch} aria-label="Execute search">
                        <Search className="h-4 w-4" />
                      </Button>
                    </div>
                    <p id="search-help" className="text-xs text-muted-foreground">
                      Search for React components, API endpoints, database models, or design patterns.
                    </p>

                    {searchResults.length > 0 && (
                      <ScrollArea className="h-48">
                        <div className="space-y-2" role="list" aria-label="Search results">
                          {searchResults.map((node) => (
                            <div
                              key={node.id}
                              className="p-2 border rounded cursor-pointer hover:bg-muted/50 focus:bg-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
                              onClick={() => handleNodeClick(node)}
                              onKeyPress={(e) => e.key === "Enter" && handleNodeClick(node)}
                              tabIndex={0}
                              role="button"
                              aria-label={`View details for ${node.label}`}
                            >
                              <div className="font-medium text-sm">{node.label}</div>
                              <div className="text-xs text-muted-foreground">{node.type}</div>
                              <Badge variant="outline" className="text-xs mt-1">
                                Relevance: {node.centrality.toFixed(2)}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* SPARQL Queries */}
              <TabsContent value="sparql" className="space-y-4" role="tabpanel">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Web Development Queries</CardTitle>
                    <CardDescription className="text-xs">
                      Execute SPARQL queries for web development insights
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-xs font-medium" htmlFor="predefined-queries">
                        Predefined Web Development Queries
                      </label>
                      <div className="space-y-1" role="list" aria-labelledby="predefined-queries">
                        {predefinedQueries.map((query) => (
                          <Button
                            key={query.name}
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-xs bg-transparent"
                            onClick={() => setCustomQuery(query.query)}
                            aria-label={`Load ${query.name} query: ${query.description}`}
                          >
                            <Code className="h-3 w-3 mr-2" aria-hidden="true" />
                            {query.name}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs font-medium" htmlFor="custom-query">
                        Custom SPARQL Query
                      </label>
                      <Textarea
                        id="custom-query"
                        placeholder="Enter SPARQL query for web development analysis..."
                        value={customQuery}
                        onChange={(e) => setCustomQuery(e.target.value)}
                        className="text-xs font-mono"
                        rows={6}
                        aria-describedby="query-help"
                      />
                      <p id="query-help" className="text-xs text-muted-foreground">
                        Write SPARQL queries to analyze web development patterns, dependencies, and architectures.
                      </p>
                    </div>

                    <Button
                      onClick={handleExecuteQuery}
                      disabled={!customQuery.trim()}
                      className="w-full"
                      size="sm"
                      aria-label="Execute SPARQL query"
                    >
                      <Play className="h-4 w-4 mr-2" aria-hidden="true" />
                      Execute Query
                    </Button>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Analysis Tools */}
              <TabsContent value="analysis" className="space-y-4" role="tabpanel">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Web Development Analysis</CardTitle>
                    <CardDescription className="text-xs">
                      Advanced analysis tools for web development patterns
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full justify-start bg-transparent"
                      onClick={loadGraph}
                      aria-label="Refresh web development knowledge graph"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
                      Refresh Graph
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full justify-start bg-transparent"
                      onClick={() => {
                        setCustomQuery(predefinedQueries[0].query)
                        handleExecuteQuery()
                      }}
                      aria-label="Analyze React components"
                    >
                      <Zap className="h-4 w-4 mr-2" aria-hidden="true" />
                      Component Analysis
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full justify-start bg-transparent"
                      onClick={() => {
                        setCustomQuery(predefinedQueries[2].query)
                        handleExecuteQuery()
                      }}
                      aria-label="Analyze frontend dependencies"
                    >
                      <Brain className="h-4 w-4 mr-2" aria-hidden="true" />
                      Dependency Analysis
                    </Button>

                    {graphData && (
                      <div className="space-y-2 text-xs" role="region" aria-label="Graph statistics">
                        <h4 className="font-medium">Knowledge Graph Stats:</h4>
                        <div className="flex justify-between">
                          <span>Web Components:</span>
                          <span>{graphData.statistics.totalNodes}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Relationships:</span>
                          <span>{graphData.statistics.totalEdges}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Density:</span>
                          <span>{(graphData.statistics.density * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Pattern Clusters:</span>
                          <span>{graphData.statistics.clusters}</span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}

      {/* SPARQL Query Results Dialog */}
      <Dialog open={isQueryDialogOpen} onOpenChange={setIsQueryDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh]" role="dialog" aria-labelledby="query-results-title">
          <DialogHeader>
            <DialogTitle id="query-results-title">Web Development Query Results</DialogTitle>
            <DialogDescription>Results from your SPARQL query analysis</DialogDescription>
          </DialogHeader>

          {queryResults && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                <Badge variant="outline" role="status">
                  {queryResults.results.bindings.length} results found
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const dataStr = JSON.stringify(queryResults, null, 2)
                    const blob = new Blob([dataStr], { type: "application/json" })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement("a")
                    a.href = url
                    a.download = "web-dev-sparql-results.json"
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  aria-label="Export query results as JSON"
                >
                  <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                  Export Results
                </Button>
              </div>

              <ScrollArea className="h-96">
                <div className="space-y-2" role="list" aria-label="Query results">
                  {queryResults.results.bindings.map((binding: any, index: number) => (
                    <div key={index} className="p-3 border rounded-lg" role="listitem">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                        {Object.entries(binding).map(([key, value]: [string, any]) => (
                          <div key={key} className="flex justify-between">
                            <span className="font-medium">{key}:</span>
                            <span className="text-muted-foreground truncate ml-2" title={value?.value || "N/A"}>
                              {value?.value || "N/A"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
