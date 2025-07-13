import type { KnowledgeGraphNode, KnowledgeGraphEdge, GraphData } from "./sparql"

export interface GraphLayout {
  name: string
  algorithm: "force" | "hierarchical" | "circular" | "grid" | "cluster"
  parameters: Record<string, any>
}

export interface GraphFilter {
  nodeTypes: string[]
  edgeTypes: string[]
  clusters: string[]
  minCentrality: number
  maxNodes: number
  searchTerm?: string
}

export class GraphProcessor {
  private nodes: Map<string, KnowledgeGraphNode> = new Map()
  private edges: Map<string, KnowledgeGraphEdge> = new Map()
  private clusters: Map<string, Set<string>> = new Map()

  constructor(private data: GraphData) {
    this.processData()
  }

  private processData() {
    // Process nodes
    this.data.nodes.forEach((node) => {
      this.nodes.set(node.id, node)

      // Group by clusters
      if (node.cluster) {
        if (!this.clusters.has(node.cluster)) {
          this.clusters.set(node.cluster, new Set())
        }
        this.clusters.get(node.cluster)!.add(node.id)
      }
    })

    // Process edges
    this.data.edges.forEach((edge) => {
      this.edges.set(edge.id, edge)
    })

    // Calculate additional metrics
    this.calculateMetrics()
  }

  private calculateMetrics() {
    // Calculate degree centrality
    const inDegree = new Map<string, number>()
    const outDegree = new Map<string, number>()

    this.data.edges.forEach((edge) => {
      outDegree.set(edge.source, (outDegree.get(edge.source) || 0) + 1)
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
    })

    // Update node metrics
    this.nodes.forEach((node, id) => {
      node.inDegree = inDegree.get(id) || 0
      node.outDegree = outDegree.get(id) || 0
      node.size = Math.max(5, Math.min(20, (node.inDegree + node.outDegree) * 2))
    })
  }

  applyFilter(filter: GraphFilter): GraphData {
    let filteredNodes = Array.from(this.nodes.values())
    let filteredEdges = Array.from(this.edges.values())

    // Filter by node types
    if (filter.nodeTypes.length > 0) {
      filteredNodes = filteredNodes.filter((node) => filter.nodeTypes.includes(node.type))
    }

    // Filter by clusters
    if (filter.clusters.length > 0) {
      filteredNodes = filteredNodes.filter((node) => node.cluster && filter.clusters.includes(node.cluster))
    }

    // Filter by centrality
    filteredNodes = filteredNodes.filter((node) => node.centrality >= filter.minCentrality)

    // Filter by search term
    if (filter.searchTerm) {
      const searchLower = filter.searchTerm.toLowerCase()
      filteredNodes = filteredNodes.filter(
        (node) => node.label.toLowerCase().includes(searchLower) || node.type.toLowerCase().includes(searchLower),
      )
    }

    // Limit nodes
    if (filteredNodes.length > filter.maxNodes) {
      // Sort by centrality and take top nodes
      filteredNodes = filteredNodes.sort((a, b) => b.centrality - a.centrality).slice(0, filter.maxNodes)
    }

    // Filter edges to only include those between filtered nodes
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    filteredEdges = filteredEdges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))

    // Filter by edge types
    if (filter.edgeTypes.length > 0) {
      filteredEdges = filteredEdges.filter((edge) => filter.edgeTypes.includes(edge.type))
    }

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      statistics: {
        totalNodes: filteredNodes.length,
        totalEdges: filteredEdges.length,
        clusters: new Set(filteredNodes.map((n) => n.cluster).filter(Boolean)).size,
        density:
          filteredNodes.length > 1
            ? (2 * filteredEdges.length) / (filteredNodes.length * (filteredNodes.length - 1))
            : 0,
      },
    }
  }

  applyLayout(layout: GraphLayout, nodes: KnowledgeGraphNode[]): KnowledgeGraphNode[] {
    switch (layout.algorithm) {
      case "force":
        return this.applyForceLayout(nodes, layout.parameters)
      case "hierarchical":
        return this.applyHierarchicalLayout(nodes, layout.parameters)
      case "circular":
        return this.applyCircularLayout(nodes, layout.parameters)
      case "grid":
        return this.applyGridLayout(nodes, layout.parameters)
      case "cluster":
        return this.applyClusterLayout(nodes, layout.parameters)
      default:
        return nodes
    }
  }

  private applyForceLayout(nodes: KnowledgeGraphNode[], params: any): KnowledgeGraphNode[] {
    // Simplified force-directed layout
    const width = params.width || 800
    const height = params.height || 600
    const iterations = params.iterations || 100

    // Initialize positions randomly
    nodes.forEach((node) => {
      if (!node.x) node.x = Math.random() * width
      if (!node.y) node.y = Math.random() * height
    })

    // Simple force simulation
    for (let i = 0; i < iterations; i++) {
      // Repulsion between all nodes
      for (let j = 0; j < nodes.length; j++) {
        for (let k = j + 1; k < nodes.length; k++) {
          const dx = nodes[k].x! - nodes[j].x!
          const dy = nodes[k].y! - nodes[j].y!
          const distance = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 1000 / (distance * distance)

          nodes[j].x! -= (dx / distance) * force
          nodes[j].y! -= (dy / distance) * force
          nodes[k].x! += (dx / distance) * force
          nodes[k].y! += (dy / distance) * force
        }
      }

      // Attraction along edges
      this.data.edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source)
        const target = nodes.find((n) => n.id === edge.target)

        if (source && target) {
          const dx = target.x! - source.x!
          const dy = target.y! - source.y!
          const distance = Math.sqrt(dx * dx + dy * dy) || 1
          const force = distance * 0.01

          source.x! += (dx / distance) * force
          source.y! += (dy / distance) * force
          target.x! -= (dx / distance) * force
          target.y! -= (dy / distance) * force
        }
      })

      // Keep nodes within bounds
      nodes.forEach((node) => {
        node.x = Math.max(50, Math.min(width - 50, node.x!))
        node.y = Math.max(50, Math.min(height - 50, node.y!))
      })
    }

    return nodes
  }

  private applyHierarchicalLayout(nodes: KnowledgeGraphNode[], params: any): KnowledgeGraphNode[] {
    const width = params.width || 800
    const height = params.height || 600

    // Group nodes by type for hierarchical layout
    const typeGroups = new Map<string, KnowledgeGraphNode[]>()
    nodes.forEach((node) => {
      if (!typeGroups.has(node.type)) {
        typeGroups.set(node.type, [])
      }
      typeGroups.get(node.type)!.push(node)
    })

    const types = Array.from(typeGroups.keys())
    const levelHeight = height / types.length

    types.forEach((type, levelIndex) => {
      const levelNodes = typeGroups.get(type)!
      const nodeWidth = width / levelNodes.length

      levelNodes.forEach((node, nodeIndex) => {
        node.x = (nodeIndex + 0.5) * nodeWidth
        node.y = (levelIndex + 0.5) * levelHeight
      })
    })

    return nodes
  }

  private applyCircularLayout(nodes: KnowledgeGraphNode[], params: any): KnowledgeGraphNode[] {
    const centerX = (params.width || 800) / 2
    const centerY = (params.height || 600) / 2
    const radius = Math.min(centerX, centerY) * 0.8

    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length
      node.x = centerX + radius * Math.cos(angle)
      node.y = centerY + radius * Math.sin(angle)
    })

    return nodes
  }

  private applyGridLayout(nodes: KnowledgeGraphNode[], params: any): KnowledgeGraphNode[] {
    const width = params.width || 800
    const height = params.height || 600
    const cols = Math.ceil(Math.sqrt(nodes.length))
    const rows = Math.ceil(nodes.length / cols)
    const cellWidth = width / cols
    const cellHeight = height / rows

    nodes.forEach((node, index) => {
      const col = index % cols
      const row = Math.floor(index / cols)
      node.x = (col + 0.5) * cellWidth
      node.y = (row + 0.5) * cellHeight
    })

    return nodes
  }

  private applyClusterLayout(nodes: KnowledgeGraphNode[], params: any): KnowledgeGraphNode[] {
    const width = params.width || 800
    const height = params.height || 600

    // Group nodes by cluster
    const clusterGroups = new Map<string, KnowledgeGraphNode[]>()
    nodes.forEach((node) => {
      const cluster = node.cluster || "default"
      if (!clusterGroups.has(cluster)) {
        clusterGroups.set(cluster, [])
      }
      clusterGroups.get(cluster)!.push(node)
    })

    const clusters = Array.from(clusterGroups.keys())
    const clusterCols = Math.ceil(Math.sqrt(clusters.length))
    const clusterRows = Math.ceil(clusters.length / clusterCols)
    const clusterWidth = width / clusterCols
    const clusterHeight = height / clusterRows

    clusters.forEach((cluster, clusterIndex) => {
      const clusterNodes = clusterGroups.get(cluster)!
      const clusterCol = clusterIndex % clusterCols
      const clusterRow = Math.floor(clusterIndex / clusterCols)
      const clusterCenterX = (clusterCol + 0.5) * clusterWidth
      const clusterCenterY = (clusterRow + 0.5) * clusterHeight
      const clusterRadius = Math.min(clusterWidth, clusterHeight) * 0.4

      // Arrange nodes in cluster in a circle
      clusterNodes.forEach((node, nodeIndex) => {
        if (clusterNodes.length === 1) {
          node.x = clusterCenterX
          node.y = clusterCenterY
        } else {
          const angle = (2 * Math.PI * nodeIndex) / clusterNodes.length
          node.x = clusterCenterX + clusterRadius * Math.cos(angle)
          node.y = clusterCenterY + clusterRadius * Math.sin(angle)
        }
      })
    })

    return nodes
  }

  getNodesByCluster(clusterId: string): KnowledgeGraphNode[] {
    const nodeIds = this.clusters.get(clusterId) || new Set()
    return Array.from(nodeIds)
      .map((id) => this.nodes.get(id)!)
      .filter(Boolean)
  }

  getNodeNeighbors(nodeId: string, depth = 1): KnowledgeGraphNode[] {
    const visited = new Set<string>()
    const queue: Array<{ id: string; currentDepth: number }> = [{ id: nodeId, currentDepth: 0 }]
    const neighbors: KnowledgeGraphNode[] = []

    while (queue.length > 0) {
      const { id, currentDepth } = queue.shift()!

      if (visited.has(id) || currentDepth > depth) continue
      visited.add(id)

      if (currentDepth > 0) {
        const node = this.nodes.get(id)
        if (node) neighbors.push(node)
      }

      if (currentDepth < depth) {
        // Find connected nodes
        this.data.edges.forEach((edge) => {
          if (edge.source === id && !visited.has(edge.target)) {
            queue.push({ id: edge.target, currentDepth: currentDepth + 1 })
          }
          if (edge.target === id && !visited.has(edge.source)) {
            queue.push({ id: edge.source, currentDepth: currentDepth + 1 })
          }
        })
      }
    }

    return neighbors
  }

  exportGraph(format: "json" | "gexf" | "graphml" | "cytoscape"): string {
    switch (format) {
      case "json":
        return JSON.stringify(this.data, null, 2)
      case "gexf":
        return this.exportGEXF()
      case "graphml":
        return this.exportGraphML()
      case "cytoscape":
        return this.exportCytoscape()
      default:
        return JSON.stringify(this.data, null, 2)
    }
  }

  private exportGEXF(): string {
    // GEXF format implementation
    let gexf = `<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
  <graph mode="static" defaultedgetype="directed">
    <nodes>`

    this.data.nodes.forEach((node) => {
      gexf += `
      <node id="${node.id}" label="${node.label}">
        <attvalues>
          <attvalue for="type" value="${node.type}"/>
          <attvalue for="centrality" value="${node.centrality}"/>
        </attvalues>
      </node>`
    })

    gexf += `
    </nodes>
    <edges>`

    this.data.edges.forEach((edge) => {
      gexf += `
      <edge id="${edge.id}" source="${edge.source}" target="${edge.target}" label="${edge.label}" weight="${edge.weight}"/>`
    })

    gexf += `
    </edges>
  </graph>
</gexf>`

    return gexf
  }

  private exportGraphML(): string {
    // GraphML format implementation
    let graphml = `<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="label" for="node" attr.name="label" attr.type="string"/>
  <key id="type" for="node" attr.name="type" attr.type="string"/>
  <key id="centrality" for="node" attr.name="centrality" attr.type="double"/>
  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>
  <graph id="G" edgedefault="directed">`

    this.data.nodes.forEach((node) => {
      graphml += `
    <node id="${node.id}">
      <data key="label">${node.label}</data>
      <data key="type">${node.type}</data>
      <data key="centrality">${node.centrality}</data>
    </node>`
    })

    this.data.edges.forEach((edge) => {
      graphml += `
    <edge source="${edge.source}" target="${edge.target}">
      <data key="weight">${edge.weight}</data>
    </edge>`
    })

    graphml += `
  </graph>
</graphml>`

    return graphml
  }

  private exportCytoscape(): string {
    const cytoscapeData = {
      elements: {
        nodes: this.data.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            centrality: node.centrality,
          },
        })),
        edges: this.data.edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            weight: edge.weight,
          },
        })),
      },
    }

    return JSON.stringify(cytoscapeData, null, 2)
  }
}
