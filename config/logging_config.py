# logging_config.py
import logging.config
import yaml

def setup_logging(default_path='logging_config.yaml', default_level=logging.INFO):
    """Setup logging configuration"""
    try:
        with open(default_path, 'r') as file:
            config = yaml.safe_load(file.read())
        logging.config.dictConfig(config)
    except Exception as e:
        print(f"Error in Logging Configuration: {e}")
        logging.basicConfig(level=default_level)
