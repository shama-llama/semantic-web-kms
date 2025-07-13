"use client"

import { useState, useCallback } from "react"
import { graphApi } from "@/lib/api"
import type { GraphData } from "@/lib/api"

export function useKnowledgeGraph(organizationId: string) {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadGraph = useCallback(
    async (options?: {
      layout?: "force-directed" | "hierarchical" | "circular" | "grid"
      filter?: "all" | "classes" | "functions" | "components"
      maxNodes?: number
    }) => {
      setIsLoading(true)
      setError(null)

      try {
        const data = await graphApi.getData(organizationId, options)
        setGraphData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load graph")
      } finally {
        setIsLoading(false)
      }
    },
    [organizationId],
  )

  const exportGraph = useCallback(
    async (format: "json" | "graphml" | "gexf") => {
      try {
        const blob = await graphApi.export(organizationId, format)
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `knowledge-graph.${format}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Export failed")
      }
    },
    [organizationId],
  )

  return {
    graphData,
    isLoading,
    error,
    loadGraph,
    exportGraph,
  }
}
