"use client"
import dynamic from "next/dynamic"

const SemanticSearch = dynamic(
  () => import("./semantic-search").then(mod => mod.SemanticSearch),
  { ssr: false }
)

export default function SemanticSearchClient() {
  return <SemanticSearch />
} 