import os

def get_config(app):
    """
    Get configuration settings for the API.
    Args:
        app: Flask app instance.
    Returns:
        dict: Configuration details.
    """
    return {
        'backend': {
            'version': '1.0.0',
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'debug': app.debug,
        },
        'database': {
            'type': 'AllegroGraph',
            'url': app.config.get('AGRAPH_SERVER_URL'),
            'repository': app.config.get('AGRAPH_REPO'),
            'connected': bool(app.config.get('AGRAPH_SERVER_URL') and app.config.get('AGRAPH_REPO')),
        },
        'features': {
            'sparql_endpoint': True,
            'progress_tracking': True,
            'file_upload': True,
            'analytics': True,
            'export': True,
        },
        'paths': {
            'input_directory': os.environ.get('DEFAULT_INPUT_DIR', '~/downloads/repos/Thinkster/'),
            'output_directory': 'output',
            'logs_directory': 'logs',
        },
    } 