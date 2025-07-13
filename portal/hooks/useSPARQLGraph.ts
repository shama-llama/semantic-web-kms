"use client"

import { useState, useCallback, useEffect } from "react"
import {
  SPARQLClient,
  type SPARQLQuery,
  type SPARQLResult,
  type GraphData,
  type KnowledgeGraphNode,
  type KnowledgeGraphEdge,
} from "@/lib/sparql"
import { ApiError } from "@/lib/api"

interface UseSPARQLGraphReturn {
  graphData: GraphData | null
  isLoading: boolean
  error: string | null
  nodeDetails: Record<string, any> | null
  executeQuery: (query: SPARQLQuery) => Promise<SPARQLResult>
  loadGraph: () => Promise<void>
  searchNodes: (searchTerm: string) => Promise<KnowledgeGraphNode[]>
  getNodeDetails: (nodeUri: string) => Promise<void>
  getNodeNeighbors: (nodeUri: string, depth?: number) => Promise<KnowledgeGraphNode[]>
  clearError: () => void
}

export function useSPARQLGraph(organizationId: string | null): UseSPARQLGraphReturn {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nodeDetails, setNodeDetails] = useState<Record<string, any> | null>(null)
  const [sparqlClient, setSparqlClient] = useState<SPARQLClient | null>(null)

  // Initialize SPARQL client
  useEffect(() => {
    if (organizationId) {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
      const client = new SPARQLClient(`${baseUrl}/organizations/${organizationId}`)
      setSparqlClient(client)
    } else {
      setSparqlClient(null)
    }
  }, [organizationId])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const executeQuery = useCallback(
    async (query: SPARQLQuery): Promise<SPARQLResult> => {
      if (!sparqlClient) {
        throw new Error("SPARQL client not initialized")
      }

      try {
        return await sparqlClient.query(query)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "SPARQL query failed"
        setError(errorMessage)
        throw new ApiError(errorMessage, 500)
      }
    },
    [sparqlClient],
  )

  const loadGraph = useCallback(async () => {
    if (!sparqlClient) {
      setError("No organization selected")
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // Execute parallel queries for nodes and edges
      const [nodesResult, edgesResult] = await Promise.all([
        sparqlClient.query({ query: SPARQLClient.queries.getAllNodes }),
        sparqlClient.query({ query: SPARQLClient.queries.getAllEdges }),
      ])

      // Process nodes
      const nodes: KnowledgeGraphNode[] = nodesResult.results.bindings.map((binding, index) => {
        const nodeUri = binding.node?.value || `node_${index}`
        const label = binding.label?.value || `Node ${index}`
        const type = binding.type?.value || "Unknown"
        const cluster = binding.cluster?.value
        const centrality = Number.parseFloat(binding.centrality?.value || "0")

        // Generate color based on type
        const typeColors: Record<string, string> = {
          class: "#3b82f6",
          function: "#10b981",
          component: "#8b5cf6",
          service: "#f59e0b",
          interface: "#ef4444",
          module: "#06b6d4",
          variable: "#84cc16",
        }

        return {
          id: nodeUri,
          uri: nodeUri,
          label,
          type,
          properties: {
            uri: nodeUri,
            type,
            cluster,
            centrality,
          },
          size: Math.max(5, Math.min(20, centrality * 15 + 5)),
          color: typeColors[type.toLowerCase()] || "#6b7280",
          cluster,
          centrality,
          inDegree: 0,
          outDegree: 0,
        }
      })

      // Process edges
      const edges: KnowledgeGraphEdge[] = edgesResult.results.bindings.map((binding, index) => {
        const source = binding.source?.value || ""
        const target = binding.target?.value || ""
        const relation = binding.relation?.value || ""
        const weight = Number.parseFloat(binding.weight?.value || "1")

        return {
          id: `edge_${index}`,
          source,
          target,
          label: relation.split("#").pop() || relation.split("/").pop() || relation,
          type: relation,
          weight,
          properties: {
            relation,
            weight,
          },
        }
      })

      // Calculate degree centrality
      const inDegree = new Map<string, number>()
      const outDegree = new Map<string, number>()

      edges.forEach((edge) => {
        outDegree.set(edge.source, (outDegree.get(edge.source) || 0) + 1)
        inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
      })

      // Update node degrees
      nodes.forEach((node) => {
        node.inDegree = inDegree.get(node.id) || 0
        node.outDegree = outDegree.get(node.id) || 0
        // Update size based on degree if centrality is not available
        if (node.centrality === 0) {
          node.size = Math.max(5, Math.min(20, (node.inDegree + node.outDegree) * 2 + 5))
        }
      })

      const graphData: GraphData = {
        nodes,
        edges,
        statistics: {
          totalNodes: nodes.length,
          totalEdges: edges.length,
          clusters: new Set(nodes.map((n) => n.cluster).filter(Boolean)).size,
          density: nodes.length > 1 ? (2 * edges.length) / (nodes.length * (nodes.length - 1)) : 0,
        },
      }

      setGraphData(graphData)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to load graph: ${err.message}`)
      } else {
        setError("Failed to load knowledge graph from SPARQL endpoint")
      }
    } finally {
      setIsLoading(false)
    }
  }, [sparqlClient])

  const searchNodes = useCallback(
    async (searchTerm: string): Promise<KnowledgeGraphNode[]> => {
      if (!sparqlClient || !searchTerm.trim()) {
        return []
      }

      try {
        const result = await sparqlClient.query({
          query: SPARQLClient.queries.searchNodes(searchTerm),
        })

        return result.results.bindings.map((binding, index) => {
          const nodeUri = binding.node?.value || `search_${index}`
          const label = binding.label?.value || "Unknown"
          const type = binding.type?.value || "Unknown"
          const score = Number.parseFloat(binding.score?.value || "0")

          return {
            id: nodeUri,
            uri: nodeUri,
            label,
            type,
            properties: { uri: nodeUri, type, score },
            size: Math.max(5, score * 20 + 5),
            color: "#3b82f6",
            centrality: score,
            inDegree: 0,
            outDegree: 0,
          }
        })
      } catch (err) {
        setError(`Search failed: ${err instanceof Error ? err.message : "Unknown error"}`)
        return []
      }
    },
    [sparqlClient],
  )

  const getNodeDetails = useCallback(
    async (nodeUri: string) => {
      if (!sparqlClient) {
        setError("SPARQL client not available")
        return
      }

      try {
        const result = await sparqlClient.query({
          query: SPARQLClient.queries.getNodeDetails(nodeUri),
        })

        const details: Record<string, any> = {}
        result.results.bindings.forEach((binding) => {
          const property = binding.property?.value || ""
          const value = binding.value?.value || ""
          const propertyName = property.split("#").pop() || property.split("/").pop() || property

          details[propertyName] = value
        })

        setNodeDetails(details)
      } catch (err) {
        setError(`Failed to get node details: ${err instanceof Error ? err.message : "Unknown error"}`)
      }
    },
    [sparqlClient],
  )

  const getNodeNeighbors = useCallback(
    async (nodeUri: string, depth = 1): Promise<KnowledgeGraphNode[]> => {
      if (!sparqlClient) {
        return []
      }

      try {
        const result = await sparqlClient.query({
          query: SPARQLClient.queries.getNodeNeighbors(nodeUri, depth),
        })

        return result.results.bindings.map((binding, index) => {
          const neighborUri = binding.neighbor?.value || `neighbor_${index}`
          const label = binding.label?.value || "Unknown"
          const relation = binding.relation?.value || ""

          return {
            id: neighborUri,
            uri: neighborUri,
            label,
            type: "neighbor",
            properties: { uri: neighborUri, relation },
            size: 8,
            color: "#10b981",
            centrality: 0,
            inDegree: 0,
            outDegree: 0,
          }
        })
      } catch (err) {
        setError(`Failed to get neighbors: ${err instanceof Error ? err.message : "Unknown error"}`)
        return []
      }
    },
    [sparqlClient],
  )

  // Auto-load graph when organization changes
  useEffect(() => {
    if (organizationId && sparqlClient) {
      loadGraph()
    } else {
      setGraphData(null)
      setNodeDetails(null)
    }
  }, [organizationId, sparqlClient, loadGraph])

  return {
    graphData,
    isLoading,
    error,
    nodeDetails,
    executeQuery,
    loadGraph,
    searchNodes,
    getNodeDetails,
    getNodeNeighbors,
    clearError,
  }
}
