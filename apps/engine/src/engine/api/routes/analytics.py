from flask import Blueprint, jsonify

from engine.api.services.analytics_service import get_analytics

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics", methods=["GET"])
def analytics():
    data = get_analytics()
    return jsonify(data)
