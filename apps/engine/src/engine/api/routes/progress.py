from flask import Blueprint, jsonify
from engine.api.services.progress_service import get_progress, get_progress_stages, get_progress_stage

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/progress/<job_id>', methods=['GET'])
def progress(job_id):
    status = get_progress(job_id)
    if status is None:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(status)

@progress_bp.route('/progress/<job_id>/stages', methods=['GET'])
def progress_stages(job_id):
    stages = get_progress_stages(job_id)
    if stages is None:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(stages)

@progress_bp.route('/progress/<job_id>/stages/<stage_key>', methods=['GET'])
def progress_stage(job_id, stage_key):
    stage = get_progress_stage(job_id, stage_key)
    if stage is None:
        return jsonify({'error': 'Stage not found'}), 404
    return jsonify(stage) 