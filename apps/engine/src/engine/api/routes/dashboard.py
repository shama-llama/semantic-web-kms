from flask import Blueprint, jsonify
from engine.api.services.dashboard_service import get_dashboard_statistics

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    stats = get_dashboard_statistics()
    return jsonify(stats) 