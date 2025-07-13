"use client"
import dynamic from "next/dynamic"

const KnowledgeGraph = dynamic(
  () => import("./knowledge-graph").then(mod => mod.KnowledgeGraph),
  { ssr: false }
)

export default function KnowledgeGraphClient() {
  return <KnowledgeGraph />
} 