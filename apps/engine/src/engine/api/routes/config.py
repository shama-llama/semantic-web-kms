from flask import Blueprint, jsonify, current_app
from engine.api.services.config_service import get_config

config_bp = Blueprint('config', __name__)

@config_bp.route('/config', methods=['GET'])
def config():
    data = get_config(current_app)
    return jsonify(data) 