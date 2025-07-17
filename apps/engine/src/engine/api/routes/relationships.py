from flask import Blueprint, jsonify
from engine.api.services.relationship_service import get_relationships

relationships_bp = Blueprint('relationships', __name__)

@relationships_bp.route('/relationships', methods=['GET'])
def relationships():
    data = get_relationships()
    return jsonify(data) 