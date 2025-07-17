from flask import Blueprint, jsonify
from engine.api.services.input_dir_service import get_input_directory

input_dir_bp = Blueprint('input_dir', __name__)

@input_dir_bp.route('/input-directory', methods=['GET'])
def input_directory():
    data = get_input_directory()
    return jsonify(data) 