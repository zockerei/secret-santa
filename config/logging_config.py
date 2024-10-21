import logging.config
import yaml

def setup_logging(default_path='logging_config.yaml', default_level=logging.INFO):
    """Setup logging configuration"""
    try:
        with open(default_path, 'r') as file:
            config = yaml.safe_load(file.read())
        logging.config.dictConfig(config)
    except FileNotFoundError:
        print(f"Logging configuration file not found: {default_path}")
        logging.basicConfig(level=default_level)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        logging.basicConfig(level=default_level)
    except Exception as e:
        print(f"Unexpected error in Logging Configuration: {e}")
        logging.basicConfig(level=default_level)
