import os

# Adjust the app_dir to point to the root of the project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A SECRET KEY'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEVELOPMENT_DATABASE_URI') or  \
        'sqlite:///' + os.path.join(project_root, 'instance', 'secret_santa_dev.db')
    
class TestingConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TESTING_DATABASE_URI') or \
        'sqlite:///' + os.path.join(project_root, 'instance', 'secret_santa_test.db')

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URI') or  \
        'sqlite:///' + os.path.join(project_root, 'instance', 'secret_santa.db')
