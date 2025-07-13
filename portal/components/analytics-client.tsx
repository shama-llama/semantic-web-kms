"use client"
import dynamic from "next/dynamic"

const Analytics = dynamic(
  () => import("./analytics").then(mod => mod.Analytics),
  { ssr: false }
)

export default function AnalyticsClient() {
  return <Analytics />
} 