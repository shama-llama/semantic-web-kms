from flask import Blueprint, jsonify, request

from engine.api.services.graph_service import get_graph_data

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/graph", methods=["GET"])
def graph():
    max_nodes = int(request.args.get("maxNodes", 100))
    data = get_graph_data(max_nodes)
    return jsonify(data)
