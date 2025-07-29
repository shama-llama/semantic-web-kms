# This package will contain all API blueprints (routes)

# Example import (to be filled in as blueprints are created):
# from .dashboard import dashboard_bp
# from .organizations import organizations_bp
from .analytics import analytics_bp as analytics_bp
from .complexity import complexity_bp as complexity_bp
from .config import config_bp as config_bp
from .dashboard import dashboard_bp as dashboard_bp
from .entities import entities_bp as entities_bp
from .export import export_bp as export_bp
from .graph import graph_bp as graph_bp
from .health import health_bp as health_bp
from .input_dir import input_dir_bp as input_dir_bp
from .organizations import organizations_bp as organizations_bp
from .progress import progress_bp as progress_bp
from .relationships import relationships_bp as relationships_bp
from .repositories import repositories_bp as repositories_bp
from .search import search_bp as search_bp
from .sparql import sparql_bp as sparql_bp
from .upload import upload_bp as upload_bp

# Other blueprints will be imported and exposed here as they are created
