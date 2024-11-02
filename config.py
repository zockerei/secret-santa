import os
import logging.config
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).resolve().parent / 'instance' / '.env', override=True)

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Log file path
LOG_FOLDER_PATH = BASE_DIR / 'logs'
LOG_FOLDER_PATH.mkdir(parents=True, exist_ok=True)


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = os.environ.get('PORT')
    HOST = os.environ.get('HOST')


class DevelopmentConfig(BaseConfig):
    DEBUG = 1
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'secret_santa_dev.db')


class TestingConfig(BaseConfig):
    DEBUG = 1
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'secret_santa_test.db')


class ProductionConfig(BaseConfig):
    DEBUG = 0
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'secret_santa.db')


def setup_logging(default_path='config/logging_config.yaml'):
    """Setup logging configuration"""
    try:
        with open(default_path, 'r') as file:
            config = yaml.safe_load(file.read())

        # Update log file paths
        config['handlers']['rotating_file']['filename'] = str(LOG_FOLDER_PATH / 'app.log')
        config['handlers']['error_file']['filename'] = str(LOG_FOLDER_PATH / 'error.log')
        logging.config.dictConfig(config)
    except FileNotFoundError:
        print(f"Logging configuration file not found: {default_path}")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
    except Exception as e:
        print(f"Unexpected error in Logging Configuration: {e}")
