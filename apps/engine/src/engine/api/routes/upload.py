from flask import Blueprint, jsonify, request
from engine.api.services.upload_service import handle_organization_upload

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload/organization', methods=['POST'])
def upload_organization():
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No files selected'}), 400
    result = handle_organization_upload(files)
    return jsonify(result), 202 