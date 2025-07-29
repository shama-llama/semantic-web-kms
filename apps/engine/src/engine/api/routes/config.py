from flask import Blueprint, current_app, jsonify

from engine.api.services.config_service import get_config

config_bp = Blueprint("config", __name__)


@config_bp.route("/config", methods=["GET"])
def config():
    data = get_config(current_app)
    return jsonify(data)
