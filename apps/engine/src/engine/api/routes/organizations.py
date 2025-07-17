from flask import Blueprint, jsonify, request
from engine.api.services.organization_service import list_organizations, get_organization_details, start_organization_analysis

organizations_bp = Blueprint('organizations', __name__)

@organizations_bp.route('/organizations', methods=['GET'])
def get_organizations():
    orgs = list_organizations()
    return jsonify(orgs)

@organizations_bp.route('/organizations/<path:org_id>', methods=['GET'])
def get_organization(org_id):
    org = get_organization_details(org_id)
    if org is None:
        return jsonify({'error': 'Organization not found or invalid'}), 404
    return jsonify(org)

@organizations_bp.route('/organizations/analyze', methods=['POST'])
def analyze_organization():
    data = request.get_json()
    organization_name = data.get('name') if data else None
    if not organization_name:
        return jsonify({'error': 'Organization name is required'}), 400
    result = start_organization_analysis(organization_name)
    return jsonify(result), 202 