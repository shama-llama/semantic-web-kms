import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    AGRAPH_SERVER_URL = os.environ.get('AGRAPH_SERVER_URL')
    AGRAPH_REPO = os.environ.get('AGRAPH_REPO')
    AGRAPH_USERNAME = os.environ.get('AGRAPH_USERNAME')
    AGRAPH_PASSWORD = os.environ.get('AGRAPH_PASSWORD')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
} 