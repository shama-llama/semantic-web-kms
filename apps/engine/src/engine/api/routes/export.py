from flask import Blueprint, current_app, make_response
from engine.api.services.export_service import export_data

export_bp = Blueprint('export', __name__)

@export_bp.route('/export/<export_format>', methods=['GET'])
def export_route(export_format):
    result = export_data(export_format, current_app)
    if isinstance(result, tuple):
        if len(result) == 3:
            data, status, headers = result
            resp = make_response(data, status)
            resp.headers.extend(headers)
            return resp
        elif len(result) == 2:
            data, status = result
            return make_response(data, status)
    return make_response(result) 