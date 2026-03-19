"""Configuration management for CivitAI Downloader, including loading, saving, and prompting for user input."""

import os
import json
import logging
import logging.handlers
from pathlib import Path

DEFAULT_CONFIG = {
    'api_key': '15e227dd841ce90ecfe28e0eb152abf6',
    'download_dir': os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI'),
    'request_delay': 0.5,
    'max_retries': 3,
    'log_level': 'INFO',
    'log_dir': os.path.join(os.path.expanduser('~'), '.civitai_downloader', 'logs'),
}

class Configuration:
    """Class to manage configuration settings for the CivitAI Downloader."""
    def __init__(self):
        self._data = DEFAULT_CONFIG.copy()

    def get(self, key, default=None):
        """Get a configuration value with an optional default."""
        return self._data.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self._data[key] = value

    def update(self, new_data):
        """Update the configuration with a dictionary of new values."""
        self._data.update(new_data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def __str__(self):
        return str(self._data)

    def to_dict(self):
        """Return the configuration data as a dictionary."""
        return self._data.copy()

config = Configuration()
def prompt_for_config():
    """Prompt the user for necessary configuration settings if they are missing or invalid."""
    print("\n=== CivitAI Downloader Configuration ===")
    api_key = input("Please enter your CivitAI API key: ").strip()

    while not api_key:
        print("Error: API key cannot be empty. It's required for accessing CivitAI.")
        api_key = input("Please enter your CivitAI API key: ").strip()

    default_dir = os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI')
    print(f"\nDefault download directory: {default_dir}")
    custom_dir = input("Press Enter to accept or type a custom path: ").strip()
    download_dir = custom_dir if custom_dir else default_dir

    return {
        'api_key': api_key,
        'download_dir': download_dir
    }

def save_config(config_data, config_file):
    """Save the configuration data to a JSON file."""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        print(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def init_config(config_path=None):
    """Initialize configuration by loading from file or prompting user input if necessary."""
    if config_path:
        config_file = Path(config_path)
    else:
        config_dir = Path(os.path.expanduser('~'), '.civitai_downloader')
        config_file = config_dir / 'config.json'
        config_dir.mkdir(parents=True, exist_ok=True)

    print(f"Looking for config file at: {config_file}")

    need_user_input = False
    if config_file.exists():
        try:
            print("Found existing config file, loading...")
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                print(f"Loaded config contents: {loaded_config}")
                if loaded_config:
                    config.update(loaded_config)
                    print(f"Updated config: {config}")

            if not config.get('api_key'):
                print("API key missing in configuration file.")
                need_user_input = True

        except Exception as e:
            print(f"Error loading configuration: {e}")
            need_user_input = True
    else:
        print("No configuration file found. Setting up initial configuration...")
        need_user_input = True

    if need_user_input:
        user_inputs = prompt_for_config()
        config.update(user_inputs)
        save_config(config.to_dict(), config_file)

    os.makedirs(config['download_dir'], exist_ok=True)
    os.makedirs(config['log_dir'], exist_ok=True)

    return config

def setup_logging():
    """Set up logging to both console and rotating file handler based on configuration settings."""
    log_dir = Path(config['log_dir'])
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console = logging.StreamHandler()
    log_level = getattr(logging, config['log_level'])
    console.setLevel(log_level)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(console_format)
    logger.addHandler(console)

    log_file = log_dir / 'civitai_downloader.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    logging.debug("Logging level set to %s", config['log_level'])
    return logger

def create_direct_config():
    """Directly create a configuration file by prompting the user for input."""
    config_dir = Path(os.path.expanduser('~'), '.civitai_downloader')
    config_file = config_dir / 'config.json'
    config_dir.mkdir(parents=True, exist_ok=True)

    api_key = input("Please enter your CivitAI API key: ").strip()
    while not api_key:
        print("Error: API key cannot be empty. It's required for accessing CivitAI.")
        api_key = input("Please enter your CivitAI API key: ").strip()

    simple_config = {
        'api_key': api_key,
        'download_dir': os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI')
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(simple_config, f, indent=4)
        print(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(simple_config, f, indent=4)
        print(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

    # Create a basic configuration
    simple_config = {
        'api_key': api_key,
        'download_dir': os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI')
    }

    # Save the configuration
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(simple_config, f, indent=4)
        print(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False
