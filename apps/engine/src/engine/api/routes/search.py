from flask import Blueprint, jsonify, request

from engine.api.services.search_service import search_entities

search_bp = Blueprint("search", __name__)


@search_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "")
    entity_type = request.args.get("type")
    repository = request.args.get("repository")
    limit = int(request.args.get("limit", 50))
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    entities = search_entities(query, entity_type, repository, limit)
    return jsonify({
        "entities": entities,
        "totalCount": len(entities),
        "semanticInsights": {
            "relatedConcepts": [query, "code", "development"],
            "suggestedQueries": [
                f"{query} patterns",
                f"{query} implementation",
                f"{query} examples",
            ],
            "confidence": 0.8,
        },
    })
