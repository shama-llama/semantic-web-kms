"use client"

import type React from "react"

import { useEffect, useRef, useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ZoomIn, ZoomOut, RotateCcw, Download, Filter, Settings, Info, Network, Eye, EyeOff } from "lucide-react"
import type { KnowledgeGraphNode, GraphData } from "@/lib/sparql"
import { GraphProcessor, type GraphFilter, type GraphLayout } from "@/lib/graph-processing"

interface InteractiveGraphProps {
  data: GraphData | null
  isLoading: boolean
  onNodeClick?: (node: KnowledgeGraphNode) => void
  onExport?: (format: string) => void
  className?: string
}

export function InteractiveGraph({
  data,
  isLoading,
  onNodeClick,
  onExport,
  className,
}: InteractiveGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const animationRef = useRef<number | undefined>(undefined)

  const [processor, setProcessor] = useState<GraphProcessor | null>(null)
  const [filteredData, setFilteredData] = useState<GraphData | null>(null)
  const [selectedNode, setSelectedNode] = useState<KnowledgeGraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<KnowledgeGraphNode | null>(null)
  const [isNodeDialogOpen, setIsNodeDialogOpen] = useState(false)

  // Graph controls
  const [zoom, setZoom] = useState(1)
  const [panX, setPanX] = useState(0)
  const [panY, setPanY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // Layout and filtering
  const [currentLayout, setCurrentLayout] = useState<GraphLayout>({
    name: "force",
    algorithm: "force",
    parameters: { width: 800, height: 600, iterations: 100 },
  })

  const [filter, setFilter] = useState<GraphFilter>({
    nodeTypes: [],
    edgeTypes: [],
    clusters: [],
    minCentrality: 0,
    maxNodes: 1000,
    searchTerm: "",
  })

  const [showEdges, setShowEdges] = useState(true)
  const [showLabels, setShowLabels] = useState(true)
  const [nodeSize, setNodeSize] = useState(1)
  const [selectedLayout, setSelectedLayout] = useState("force-directed")

  // Initialize processor when data changes
  useEffect(() => {
    if (data) {
      const newProcessor = new GraphProcessor(data)
      setProcessor(newProcessor)

      // Apply initial filter
      const filtered = newProcessor.applyFilter(filter)
      setFilteredData(filtered)
    }
  }, [data, filter])

  // Apply filter when filter changes
  useEffect(() => {
    if (processor) {
      const filtered = processor.applyFilter(filter)
      setFilteredData(filtered)
    }
  }, [processor, filter])

  // Apply layout when layout or filtered data changes
  useEffect(() => {
    if (processor && filteredData && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      const layoutParams = {
        ...currentLayout.parameters,
        width: rect.width,
        height: rect.height,
      }

      const layoutData = { ...filteredData }
      layoutData.nodes = processor.applyLayout({ ...currentLayout, parameters: layoutParams }, layoutData.nodes)

      setFilteredData(layoutData)
    }
  }, [currentLayout, filteredData, processor])

  // Canvas drawing
  const drawGraph = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !filteredData) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio
    canvas.height = rect.height * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height)

    // Apply transformations
    ctx.save()
    ctx.translate(panX, panY)
    ctx.scale(zoom, zoom)

    // Draw edges first
    if (showEdges) {
      ctx.strokeStyle = "#e2e8f0"
      ctx.lineWidth = 1

      filteredData.edges.forEach((edge) => {
        const sourceNode = filteredData.nodes.find((n) => n.id === edge.source)
        const targetNode = filteredData.nodes.find((n) => n.id === edge.target)

        if (sourceNode && targetNode && sourceNode.x !== undefined && targetNode.x !== undefined) {
          ctx.beginPath()
          ctx.moveTo(sourceNode.x, sourceNode.y!)
          ctx.lineTo(targetNode.x, targetNode.y!)
          ctx.stroke()

          // Draw arrow
          const angle = Math.atan2(targetNode.y! - sourceNode.y!, targetNode.x! - sourceNode.x!)
          const arrowLength = 10
          const arrowAngle = Math.PI / 6

          ctx.beginPath()
          ctx.moveTo(
            targetNode.x! - arrowLength * Math.cos(angle - arrowAngle),
            targetNode.y! - arrowLength * Math.sin(angle - arrowAngle),
          )
          ctx.lineTo(targetNode.x!, targetNode.y!)
          ctx.lineTo(
            targetNode.x! - arrowLength * Math.cos(angle + arrowAngle),
            targetNode.y! - arrowLength * Math.sin(angle + arrowAngle),
          )
          ctx.stroke()
        }
      })
    }

    // Draw nodes
    filteredData.nodes.forEach((node) => {
      if (node.x === undefined || node.y === undefined) return

      const radius = node.size * nodeSize
      const isSelected = selectedNode?.id === node.id
      const isHovered = hoveredNode?.id === node.id

      // Node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
      ctx.fillStyle = isSelected ? "#3b82f6" : isHovered ? "#60a5fa" : node.color
      ctx.fill()

      if (isSelected || isHovered) {
        ctx.strokeStyle = "#1e40af"
        ctx.lineWidth = 2
        ctx.stroke()
      }

      // Node label
      if (showLabels && zoom > 0.5) {
        ctx.fillStyle = "#1f2937"
        ctx.font = `${Math.max(10, 12 * zoom)}px sans-serif`
        ctx.textAlign = "center"
        ctx.fillText(node.label, node.x, node.y + radius + 15)
      }
    })

    ctx.restore()
  }, [filteredData, zoom, panX, panY, selectedNode, hoveredNode, showEdges, showLabels, nodeSize])

  // Animation loop
  useEffect(() => {
    const animate = () => {
      drawGraph()
      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [drawGraph])

  // Mouse event handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return

      const x = (e.clientX - rect.left - panX) / zoom
      const y = (e.clientY - rect.top - panY) / zoom

      // Check if clicking on a node
      const clickedNode = filteredData?.nodes.find((node) => {
        if (node.x === undefined || node.y === undefined) return false
        const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
        return distance <= node.size * nodeSize
      })

      if (clickedNode) {
        setSelectedNode(clickedNode)
        setIsNodeDialogOpen(true)
        onNodeClick?.(clickedNode)
      } else {
        setIsDragging(true)
        setDragStart({ x: e.clientX - panX, y: e.clientY - panY })
      }
    },
    [filteredData, zoom, panX, panY, nodeSize, onNodeClick],
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return

      if (isDragging) {
        setPanX(e.clientX - dragStart.x)
        setPanY(e.clientY - dragStart.y)
      } else {
        // Check for hover
        const x = (e.clientX - rect.left - panX) / zoom
        const y = (e.clientY - rect.top - panY) / zoom

        const hoveredNode = filteredData?.nodes.find((node) => {
          if (node.x === undefined || node.y === undefined) return false
          const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
          return distance <= node.size * nodeSize
        })

        setHoveredNode(hoveredNode || null)
      }
    },
    [isDragging, dragStart, filteredData, zoom, panX, panY, nodeSize],
  )

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
    setZoom((prev) => Math.max(0.1, Math.min(5, prev * zoomFactor)))
  }, [])

  // Control functions
  const handleExport = (format: string) => {
    if (processor) {
      const exportData = processor.exportGraph(format as 'json' | 'gexf' | 'graphml' | 'cytoscape')
      const blob = new Blob([exportData], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `knowledge-graph.${format}`
      a.click()
      URL.revokeObjectURL(url)
    }
    onExport?.(format)
  }

  const getUniqueValues = (key: keyof KnowledgeGraphNode) => {
    if (!data) return []
    return Array.from(new Set(data.nodes.map((node) => node[key] as string).filter(Boolean)))
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-96">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto animate-pulse">
              <Network className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h3 className="font-medium">Loading Knowledge Graph</h3>
              <p className="text-sm text-muted-foreground">Processing graph data...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || !filteredData) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-96">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Network className="w-8 h-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-medium">No Graph Data</h3>
              <p className="text-sm text-muted-foreground">No knowledge graph data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Graph Controls */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                Interactive Knowledge Graph
              </CardTitle>
              <CardDescription>
                {filteredData.statistics.totalNodes} nodes, {filteredData.statistics.totalEdges} edges
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Select value={selectedLayout} onValueChange={setSelectedLayout}>
                <SelectTrigger className="w-32 sm:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="force-directed">Force Directed</SelectItem>
                  <SelectItem value="hierarchical">Hierarchical</SelectItem>
                  <SelectItem value="circular">Circular</SelectItem>
                  <SelectItem value="grid">Grid</SelectItem>
                  <SelectItem value="cluster">Cluster</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" aria-label="Zoom in" onClick={() => setZoom((prev) => Math.min(5, prev * 1.2))}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" aria-label="Zoom out" onClick={() => setZoom((prev) => Math.max(0.1, prev / 1.2))}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" aria-label="Reset view" onClick={() => { setZoom(1); setPanX(0); setPanY(0); }}>
                <RotateCcw className="h-4 w-4" />
              </Button>
              <Select onValueChange={handleExport}>
                <SelectTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4" />
                  </Button>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">Export JSON</SelectItem>
                  <SelectItem value="gexf">Export GEXF</SelectItem>
                  <SelectItem value="graphml">Export GraphML</SelectItem>
                  <SelectItem value="cytoscape">Export Cytoscape</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Graph Visualization */}
        <div className="lg:col-span-3">
          <Card className="h-[400px] sm:h-[500px] lg:h-[700px]">
            <CardContent className="p-0 h-full">
              <div
                ref={containerRef}
                className="relative w-full h-full overflow-hidden rounded-lg"
                role="img"
                aria-label="Interactive knowledge graph visualization"
              >
                <canvas
                  ref={canvasRef}
                  className="w-full h-full cursor-grab active:cursor-grabbing focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  onWheel={handleWheel}
                  tabIndex={0}
                  role="application"
                  aria-label="Knowledge graph canvas - use arrow keys to navigate, enter to select nodes"
                  onKeyDown={(e) => {
                    // Add keyboard navigation
                    if (e.key === "ArrowLeft") setPanX((prev) => prev + 20)
                    if (e.key === "ArrowRight") setPanX((prev) => prev - 20)
                    if (e.key === "ArrowUp") setPanY((prev) => prev + 20)
                    if (e.key === "ArrowDown") setPanY((prev) => prev - 20)
                    if (e.key === "Enter" && hoveredNode) {
                      setSelectedNode(hoveredNode)
                      setIsNodeDialogOpen(true)
                    }
                  }}
                />

                {/* Zoom indicator */}
                <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-sm rounded-lg px-3 py-2 text-sm">
                  Zoom: {(zoom * 100).toFixed(0)}%
                </div>

                {/* Node hover info */}
                {hoveredNode && (
                  <div className="absolute top-4 right-4 bg-background/90 backdrop-blur-sm rounded-lg p-3 max-w-xs">
                    <h4 className="font-medium">{hoveredNode.label}</h4>
                    <p className="text-sm text-muted-foreground">{hoveredNode.type}</p>
                    <div className="flex gap-2 mt-2">
                      <Badge variant="outline">Centrality: {hoveredNode.centrality.toFixed(2)}</Badge>
                      <Badge variant="outline">Degree: {hoveredNode.inDegree + hoveredNode.outDegree}</Badge>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Controls Panel */}
        <div className="space-y-4">
          <Tabs defaultValue="filter" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="filter" aria-label="Filter options">
                <Filter className="h-4 w-4" />
                <span className="sr-only">Filter</span>
              </TabsTrigger>
              <TabsTrigger value="layout" aria-label="Layout options">
                <Settings className="h-4 w-4" />
                <span className="sr-only">Layout</span>
              </TabsTrigger>
              <TabsTrigger value="view" aria-label="View options">
                <Eye className="h-4 w-4" />
                <span className="sr-only">View</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="filter" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Filters</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Search</label>
                    <Input
                      placeholder="Search nodes..."
                      value={filter.searchTerm}
                      onChange={(e) => setFilter((prev) => ({ ...prev, searchTerm: e.target.value }))}
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Node Types</label>
                    <Select
                      value={filter.nodeTypes.join(",")}
                      onValueChange={(value) =>
                        setFilter((prev) => ({
                          ...prev,
                          nodeTypes: value ? value.split(",") : [],
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All types" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        {getUniqueValues("type").map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Max Nodes: {filter.maxNodes}</label>
                    <Slider
                      value={[filter.maxNodes]}
                      onValueChange={([value]) => setFilter((prev) => ({ ...prev, maxNodes: value }))}
                      max={5000}
                      min={100}
                      step={100}
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Min Centrality: {filter.minCentrality.toFixed(2)}
                    </label>
                    <Slider
                      value={[filter.minCentrality]}
                      onValueChange={([value]) => setFilter((prev) => ({ ...prev, minCentrality: value }))}
                      max={1}
                      min={0}
                      step={0.01}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="layout" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Layout</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Algorithm</label>
                    <Select
                      value={currentLayout.algorithm}
                      onValueChange={(value: string) =>
                        setCurrentLayout((prev) => ({
                          ...prev,
                          algorithm: value as GraphLayout["algorithm"],
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="force">Force Directed</SelectItem>
                        <SelectItem value="hierarchical">Hierarchical</SelectItem>
                        <SelectItem value="circular">Circular</SelectItem>
                        <SelectItem value="grid">Grid</SelectItem>
                        <SelectItem value="cluster">Cluster</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button onClick={() => setCurrentLayout((prev) => ({ ...prev }))} className="w-full">
                    Apply Layout
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="view" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">View Options</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">Show Edges</label>
                    <Button variant="outline" size="sm" onClick={() => setShowEdges(!showEdges)}>
                      {showEdges ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    </Button>
                  </div>

                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">Show Labels</label>
                    <Button variant="outline" size="sm" onClick={() => setShowLabels(!showLabels)}>
                      {showLabels ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    </Button>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Node Size: {nodeSize.toFixed(1)}x</label>
                    <Slider
                      value={[nodeSize]}
                      onValueChange={([value]) => setNodeSize(value)}
                      max={3}
                      min={0.5}
                      step={0.1}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Graph Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Nodes:</span>
                <span>{filteredData.statistics.totalNodes}</span>
              </div>
              <div className="flex justify-between">
                <span>Edges:</span>
                <span>{filteredData.statistics.totalEdges}</span>
              </div>
              <div className="flex justify-between">
                <span>Clusters:</span>
                <span>{filteredData.statistics.clusters}</span>
              </div>
              <div className="flex justify-between">
                <span>Density:</span>
                <span>{(filteredData.statistics.density * 100).toFixed(1)}%</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Node Details Dialog */}
      <Dialog open={isNodeDialogOpen} onOpenChange={setIsNodeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              {selectedNode?.label}
            </DialogTitle>
            <DialogDescription>Detailed information about this knowledge entity</DialogDescription>
          </DialogHeader>

          {selectedNode && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Basic Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Type:</span>
                      <Badge variant="outline">{selectedNode.type}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span>URI:</span>
                      <code className="text-xs bg-muted px-1 rounded">{selectedNode.uri}</code>
                    </div>
                    <div className="flex justify-between">
                      <span>Cluster:</span>
                      <span>{selectedNode.cluster || "None"}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Graph Metrics</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Centrality:</span>
                      <span>{selectedNode.centrality.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>In Degree:</span>
                      <span>{selectedNode.inDegree}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Out Degree:</span>
                      <span>{selectedNode.outDegree}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-2">Properties</h4>
                <ScrollArea className="h-32">
                  <div className="space-y-1 text-sm">
                    {Object.entries(selectedNode.properties).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="font-medium">{key}:</span>
                        <span className="text-muted-foreground">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>

              {processor && (
                <div>
                  <h4 className="font-medium mb-2">Connected Nodes</h4>
                  <div className="flex flex-wrap gap-1">
                    {processor
                      .getNodeNeighbors(selectedNode.id, 1)
                      .slice(0, 10)
                      .map((neighbor) => (
                        <Badge
                          key={neighbor.id}
                          variant="secondary"
                          className="cursor-pointer"
                          onClick={() => {
                            setSelectedNode(neighbor)
                          }}
                        >
                          {neighbor.label}
                        </Badge>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
