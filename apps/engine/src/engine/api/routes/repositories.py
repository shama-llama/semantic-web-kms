from flask import Blueprint, jsonify

from engine.api.services.repository_service import list_repositories

repositories_bp = Blueprint("repositories", __name__)


@repositories_bp.route("/repositories", methods=["GET"])
def get_repositories():
    repos = list_repositories()
    return jsonify(repos)
