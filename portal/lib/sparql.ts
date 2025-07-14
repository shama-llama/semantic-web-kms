export interface SPARQLQuery {
  query: string
  variables?: Record<string, unknown>
  format?: "json" | "xml" | "turtle" | "n3"
}

export interface SPARQLResult {
  head: {
    vars: string[]
  }
  results: {
    bindings: Array<Record<string, { type: string; value: string; datatype?: string }>>
  }
}

export interface KnowledgeGraphNode {
  id: string
  uri: string
  label: string
  type: string
  properties: Record<string, unknown>
  x?: number
  y?: number
  z?: number
  size: number
  color: string
  cluster?: string
  centrality: number
  inDegree: number
  outDegree: number
}

export interface KnowledgeGraphEdge {
  id: string
  source: string
  target: string
  label: string
  type: string
  weight: number
  properties: Record<string, unknown>
}

export interface GraphData {
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  statistics: {
    totalNodes: number
    totalEdges: number
    clusters: number
    density: number
  }
}

class SPARQLClient {
  private baseUrl: string
  private endpoint: string

  constructor(baseUrl: string, endpoint = "/sparql") {
    this.baseUrl = baseUrl
    this.endpoint = endpoint
  }

  async query(sparqlQuery: SPARQLQuery): Promise<SPARQLResult> {
    const url = `${this.baseUrl}${this.endpoint}`

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/sparql-query",
        Accept: "application/sparql-results+json",
      },
      body: sparqlQuery.query,
    })

    if (!response.ok) {
      throw new Error(`SPARQL query failed: ${response.statusText}`)
    }

    return await response.json()
  }

  async construct(sparqlQuery: SPARQLQuery): Promise<unknown> {
    const url = `${this.baseUrl}${this.endpoint}`

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/sparql-query",
        Accept: "application/rdf+json",
      },
      body: sparqlQuery.query,
    })

    if (!response.ok) {
      throw new Error(`SPARQL construct failed: ${response.statusText}`)
    }

    return await response.json()
  }

  // Predefined SPARQL queries for common operations
  static queries = {
    getAllNodes: `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX code: <http://example.org/code#>
      
      SELECT ?node ?label ?type ?cluster ?centrality WHERE {
        ?node rdf:type ?type .
        ?node rdfs:label ?label .
        OPTIONAL { ?node code:cluster ?cluster }
        OPTIONAL { ?node code:centrality ?centrality }
      }
      LIMIT 10000
    `,

    getAllEdges: `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX code: <http://example.org/code#>
      
      SELECT ?source ?target ?relation ?weight WHERE {
        ?source ?relation ?target .
        FILTER(?relation != rdf:type && ?relation != rdfs:label)
        OPTIONAL { ?relation code:weight ?weight }
      }
      LIMIT 50000
    `,

    getNodeDetails: (nodeUri: string) => `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX code: <http://example.org/code#>
      
      SELECT ?property ?value WHERE {
        <${nodeUri}> ?property ?value .
      }
    `,

    searchNodes: (searchTerm: string) => `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX code: <http://example.org/code#>
      
      SELECT ?node ?label ?type ?score WHERE {
        ?node rdfs:label ?label .
        ?node rdf:type ?type .
        FILTER(CONTAINS(LCASE(?label), LCASE("${searchTerm}")))
        OPTIONAL { ?node code:semanticScore ?score }
      }
      ORDER BY DESC(?score)
      LIMIT 100
    `,

    getClusterNodes: (clusterId: string) => `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX code: <http://example.org/code#>
      
      SELECT ?node ?label ?type WHERE {
        ?node code:cluster "${clusterId}" .
        ?node rdfs:label ?label .
        ?node rdf:type ?type .
      }
    `,

    getNodeNeighbors: (nodeUri: string) => `
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      
      SELECT ?neighbor ?relation ?label WHERE {
        {
          <${nodeUri}> ?relation ?neighbor .
          ?neighbor rdfs:label ?label .
          FILTER(?relation != rdf:type)
        }
        UNION
        {
          ?neighbor ?relation <${nodeUri}> .
          ?neighbor rdfs:label ?label .
          FILTER(?relation != rdf:type)
        }
      }
      LIMIT 50
    `,
  }
}

export { SPARQLClient }
