from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query


def get_graph_data(max_nodes=100):
    """
    Get graph data for visualization: nodes, edges, clusters.

    Args:
        max_nodes (int): Maximum number of nodes.

    Returns:
        dict: Graph data with nodes, edges, clusters.
    """
    # Nodes
    nodes_query = load_query("graph/graph_nodes.rq").format(max_nodes=max_nodes)
    nodes_result = db_connector.execute_sparql_query(nodes_query)
    bindings = nodes_result.get("results", {}).get("bindings", [])
    nodes = []
    node_ids = set()
    for binding in bindings:
        if "entityType" not in binding:
            continue
        entity_id = binding["entity"]["value"]
        name = binding.get("name", {}).get("value", "Unknown")
        entity_type = binding["entityType"]["value"].split("#")[-1]
        repo = binding.get("repo", {}).get("value", "")
        language = binding.get("language", {}).get("value", "")
        if entity_id not in node_ids:
            node_ids.add(entity_id)
            node_type = "concept"
            size = 10
            color = "#3b82f6"
            if entity_type.lower() in ["repository"]:
                node_type = "repository"
                size = 20
                color = "#10b981"
            elif entity_type.lower() in ["file", "sourcefile"]:
                node_type = "file"
                size = 12
                color = "#f59e0b"
            elif entity_type.lower() in ["function", "functiondefinition"]:
                node_type = "function"
                size = 8
                color = "#8b5cf6"
            elif entity_type.lower() in ["class", "classdefinition"]:
                node_type = "class"
                size = 10
                color = "#ef4444"
            nodes.append({
                "id": entity_id,
                "name": name,
                "type": node_type,
                "size": size,
                "color": color,
                "repository": repo.split("/")[-1] if repo else "",
                "language": language,
            })
    # Edges
    edges_query = load_query("graph/graph_edges.rq")
    edges_result = db_connector.execute_sparql_query(edges_query)
    edges_bindings = edges_result.get("results", {}).get("bindings", [])
    edges = []
    for binding in edges_bindings:
        if "relationship" not in binding:
            continue
        source = binding["source"]["value"]
        target = binding["target"]["value"]
        relationship = binding["relationship"]["value"].split("#")[-1]
        if source in node_ids and target in node_ids:
            edge_type = "depends_on"
            weight = 0.5
            if relationship in ["invokes", "callsFunction"]:
                edge_type = "calls"
                weight = 0.8
            elif relationship in ["extendsType"]:
                edge_type = "extends"
                weight = 0.9
            elif relationship in ["implementsInterface"]:
                edge_type = "implements"
                weight = 0.9
            elif relationship in ["hasFile", "belongsToRepository"]:
                edge_type = "contains"
                weight = 1.0
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": weight,
            })
    # Clusters
    repo_clusters = {}
    for node in nodes:
        if node["repository"]:
            if node["repository"] not in repo_clusters:
                repo_clusters[node["repository"]] = {
                    "id": f"cluster-{node['repository']}",
                    "name": f"{node['repository']} Repository",
                    "nodes": [],
                    "color": node["color"],
                }
            repo_clusters[node["repository"]]["nodes"].append(node["id"])
    clusters = list(repo_clusters.values())
    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
    }
