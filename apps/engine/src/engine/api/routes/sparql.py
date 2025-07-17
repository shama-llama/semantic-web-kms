from flask import Blueprint, jsonify, request
from engine.api.services.sparql_service import execute_sparql

sparql_bp = Blueprint('sparql', __name__)

@sparql_bp.route('/sparql', methods=['POST'])
def sparql_query():
    data = request.get_json()
    query = data.get('query') if data else None
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    try:
        result = execute_sparql(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500 