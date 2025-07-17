"use client"

import { useState, useCallback } from "react"
import { searchApi } from "@/lib/api"
import type { SearchResult } from "@/lib/api"

export function useSemanticSearch(organizationId: string) {
  const [results, setResults] = useState<SearchResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(
    async (
      query: string,
      options?: {
        searchType?: "semantic" | "exact" | "pattern"
        filters?: {
          entityType?: string
          repository?: string
          confidenceThreshold?: number
        }
        limit?: number
        offset?: number
      },
    ) => {
      if (!query.trim()) return

      setIsLoading(true)
      setError(null)

      try {
        const searchResults = await searchApi.semantic(organizationId, query, options)
        setResults(searchResults)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed")
      } finally {
        setIsLoading(false)
      }
    },
    [organizationId],
  )

  const clearResults = useCallback(() => {
    setResults(null)
    setError(null)
  }, [])

  return {
    results,
    isLoading,
    error,
    search,
    clearResults,
  }
}
