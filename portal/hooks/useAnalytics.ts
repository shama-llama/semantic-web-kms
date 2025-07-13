"use client"

import { useState, useCallback } from "react"
import { analyticsApi } from "@/lib/api"
import type { AnalyticsData, Repository } from "@/lib/api"

export function useAnalytics(organizationId: string) {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadAnalytics = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await analyticsApi.getData(organizationId)
      setAnalyticsData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics")
    } finally {
      setIsLoading(false)
    }
  }, [organizationId])

  const loadRepositories = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const repos = await analyticsApi.getData(organizationId)
      setRepositories([]) // Repositories are now part of the main analytics data
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repositories")
    } finally {
      setIsLoading(false)
    }
  }, [organizationId])

  const loadQualityTrends = useCallback(
    async (timeRange: "7d" | "30d" | "90d" = "30d") => {
      try {
        const data = await analyticsApi.getData(organizationId)
        return data.trends
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load trends")
        return null
      }
    },
    [organizationId],
  )

  return {
    analyticsData,
    repositories,
    isLoading,
    error,
    loadAnalytics,
    loadRepositories,
    loadQualityTrends,
  }
}
