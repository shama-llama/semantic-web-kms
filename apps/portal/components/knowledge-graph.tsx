"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Network, Download, ZoomIn, ZoomOut, RotateCcw, Maximize2, Settings, Database } from "lucide-react"
import { graphApi } from "@/lib/api"
import type { GraphData } from "@/lib/api"
import { useOrganization } from "@/components/organization-provider"
import Link from "next/link"

export function KnowledgeGraph() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLayout, setSelectedLayout] = useState("force-directed")
  const [selectedFilter, setSelectedFilter] = useState("all")
  const [maxNodes, setMaxNodes] = useState([100])
  // Removed unused selectedNode state
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { organization } = useOrganization()

  const loadGraphData = useCallback(async (): Promise<void> => {
    if (!organization) return

    setIsLoading(true)
    try {
      const data = await graphApi.getData({
        layout: selectedLayout as "force-directed" | "hierarchical" | "circular" | "grid",
        filter: selectedFilter as "all" | "classes" | "functions" | "components",
        maxNodes: maxNodes[0],
      })
      setGraphData(data)
      renderGraph(data)
    } catch (error) {
      console.error("Failed to load graph data:", error)
    } finally {
      setIsLoading(false)
    }
  }, [organization, selectedLayout, selectedFilter, maxNodes])

  useEffect(() => {
    if (organization) {
      loadGraphData()
    }
  }, [organization, loadGraphData])

  const renderGraph = (data: GraphData) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Simple force-directed layout simulation
    const nodes = data.nodes.map((node) => ({
      ...node,
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: 0,
      vy: 0,
    }))

    // Render edges
    ctx.strokeStyle = "#e2e8f0"
    ctx.lineWidth = 1
    data.edges.forEach((edge) => {
      const sourceNode = nodes.find((n) => n.id === edge.source)
      const targetNode = nodes.find((n) => n.id === edge.target)
      if (sourceNode && targetNode) {
        ctx.beginPath()
        ctx.moveTo(sourceNode.x, sourceNode.y)
        ctx.lineTo(targetNode.x, targetNode.y)
        ctx.stroke()
      }
    })

    // Render nodes
    nodes.forEach((node) => {
      ctx.fillStyle = node.color
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.size, 0, 2 * Math.PI)
      ctx.fill()

      // Node labels
      ctx.fillStyle = "#1f2937"
      ctx.font = "12px sans-serif"
      ctx.textAlign = "center"
      ctx.fillText(node.name, node.x, node.y + node.size + 15)
    })
  }

  const handleExport = async (format: "json" | "graphml" | "gexf") => {
    if (!organization) return

    try {
      const blob = await graphApi.export(format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `knowledge-graph.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Export failed:", error)
    }
  }

  // Show placeholder when no organization or no data
  if (!organization) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Knowledge Graph</h1>
          <p className="text-muted-foreground">Interactive visualization of codebase relationships</p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Network className="h-5 w-5" />
              <span>Knowledge Graph</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <Database className="h-12 w-12 text-muted-foreground mx-auto" />
              <div>
                <h3 className="text-lg font-medium">No Data Available</h3>
                <p className="text-muted-foreground">
                  Knowledge graph visualization will be available once you add and analyze repositories.
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
        <h1 className="text-3xl font-bold">Knowledge Graph</h1>
        <p className="text-muted-foreground">Interactive visualization of {organization.name} codebase relationships</p>
      </div>

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>Graph Controls</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Layout</label>
              <Select value={selectedLayout} onValueChange={setSelectedLayout}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="force-directed">Force Directed</SelectItem>
                  <SelectItem value="hierarchical">Hierarchical</SelectItem>
                  <SelectItem value="circular">Circular</SelectItem>
                  <SelectItem value="grid">Grid</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Filter</label>
              <Select value={selectedFilter} onValueChange={setSelectedFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Entities</SelectItem>
                  <SelectItem value="classes">Classes Only</SelectItem>
                  <SelectItem value="functions">Functions Only</SelectItem>
                  <SelectItem value="components">Components Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Max Nodes: {maxNodes[0]}</label>
              <Slider value={maxNodes} onValueChange={setMaxNodes} max={500} min={50} step={25} className="w-full" />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Actions</label>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm" onClick={() => loadGraphData()}>
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Graph Visualization */}
      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Network className="h-5 w-5" />
                  <span>Graph Visualization</span>
                </div>
                <div className="flex space-x-2">
                  <Button variant="outline" size="sm" onClick={() => handleExport("json")}>
                    <Download className="h-4 w-4 mr-2" />
                    Export JSON
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExport("graphml")}>
                    <Download className="h-4 w-4 mr-2" />
                    Export GraphML
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <canvas
                  ref={canvasRef}
                  className="w-full h-96 border rounded-lg bg-background"
                  style={{ minHeight: "400px" }}
                />
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/80">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">Loading graph...</p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Graph Info Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Graph Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {graphData && (
                <>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Nodes</span>
                    <span className="font-medium">{graphData.nodes.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Edges</span>
                    <span className="font-medium">{graphData.edges.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Clusters</span>
                    <span className="font-medium">{graphData.clusters.length}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* selectedNode && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Selected Node</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="font-medium">{selectedNode.name}</span>
                  <Badge variant="outline" className="ml-2">
                    {selectedNode.type}
                  </Badge>
                </div>
                {selectedNode.repository && (
                  <div className="text-sm text-muted-foreground">Repository: {selectedNode.repository}</div>
                )}
                {selectedNode.language && (
                  <div className="text-sm text-muted-foreground">Language: {selectedNode.language}</div>
                )}
              </CardContent>
            </Card>
          ) */}

          {graphData && graphData.clusters.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Clusters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {graphData.clusters.map((cluster) => (
                  <div
                    key={cluster.id}
                    className="flex items-center space-x-2 p-2 rounded border cursor-pointer hover:bg-accent"
                  >
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cluster.color }} />
                    <span className="text-sm font-medium">{cluster.name}</span>
                    <Badge variant="secondary" className="ml-auto">
                      {cluster.nodes.length}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
