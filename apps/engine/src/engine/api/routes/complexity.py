from flask import Blueprint, jsonify

from engine.api.services.complexity_service import get_code_complexity

complexity_bp = Blueprint("complexity", __name__)


@complexity_bp.route("/metrics/code-complexity", methods=["GET"])
def code_complexity():
    data = get_code_complexity()
    return jsonify(data)
