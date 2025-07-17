from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
from .db import db_connector

# Extensions (not yet configured)
cors = CORS()
cache = Cache()

def create_app(config_object=None):
    """Application factory for the modular API."""
    app = Flask(__name__)
    if config_object:
        app.config.from_object(config_object)
    # Initialize extensions
    cors.init_app(app)
    cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})
    db_connector.init_app(app)
    # Blueprints will be registered here in the next steps
    from .routes import health_bp, dashboard_bp, organizations_bp, repositories_bp, analytics_bp, progress_bp, search_bp, entities_bp, graph_bp, relationships_bp, complexity_bp, config_bp, sparql_bp, export_bp, input_dir_bp, upload_bp
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(organizations_bp, url_prefix='/api')
    app.register_blueprint(repositories_bp, url_prefix='/api')
    app.register_blueprint(analytics_bp, url_prefix='/api')
    app.register_blueprint(progress_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(entities_bp, url_prefix='/api')
    app.register_blueprint(graph_bp, url_prefix='/api')
    app.register_blueprint(relationships_bp, url_prefix='/api')
    app.register_blueprint(complexity_bp, url_prefix='/api')
    app.register_blueprint(config_bp, url_prefix='/api')
    app.register_blueprint(sparql_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    app.register_blueprint(input_dir_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    return app
