from flask import Blueprint, jsonify

from engine.api.services.entity_service import get_entity_details

entities_bp = Blueprint("entities", __name__)


@entities_bp.route("/entities/<path:entity_id>", methods=["GET"])
def entity_details(entity_id):
    entity = get_entity_details(entity_id)
    if entity is None:
        return jsonify({"error": "Entity not found"}), 404
    return jsonify(entity)
