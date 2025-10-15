import os
from dotenv import load_dotenv
from config.env_config import get_env_config

# Load environment variables
load_dotenv()

class Config:
    """Enhanced configuration class with secure environment loading"""
    
    def __init__(self):
        # Initialize environment config
        self._env_config = get_env_config()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment"""
        try:
            appwrite_config = self._env_config.get_appwrite_config()
            
            # Set class attributes from environment config
            Config.APPWRITE_ENDPOINT = appwrite_config['endpoint']
            Config.APPWRITE_PROJECT_ID = appwrite_config['project_id']
            Config.APPWRITE_API_KEY = appwrite_config['api_key']
            Config.APPWRITE_DATABASE_ID = appwrite_config['database_id']
            Config.APPWRITE_METERS_COLLECTION_ID = appwrite_config['meters_collection_id']
            Config.APPWRITE_READINGS_COLLECTION_ID = appwrite_config['readings_collection_id']
            
        except Exception as e:
            print(f"Warning: Could not load from env_config, falling back to dotenv: {e}")
            # Fallback to original dotenv method
            Config.APPWRITE_ENDPOINT = os.getenv('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1')
            Config.APPWRITE_PROJECT_ID = os.getenv('APPWRITE_PROJECT_ID')
            Config.APPWRITE_API_KEY = os.getenv('APPWRITE_API_KEY')
            Config.APPWRITE_DATABASE_ID = os.getenv('APPWRITE_DATABASE_ID')
            Config.APPWRITE_METERS_COLLECTION_ID = os.getenv('APPWRITE_METERS_COLLECTION_ID')
            Config.APPWRITE_READINGS_COLLECTION_ID = os.getenv('APPWRITE_READINGS_COLLECTION_ID')
    
    # Class-level attributes (for backward compatibility)
    APPWRITE_ENDPOINT = os.getenv('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1')
    APPWRITE_PROJECT_ID = os.getenv('APPWRITE_PROJECT_ID')
    APPWRITE_API_KEY = os.getenv('APPWRITE_API_KEY')
    APPWRITE_DATABASE_ID = os.getenv('APPWRITE_DATABASE_ID')
    APPWRITE_METERS_COLLECTION_ID = os.getenv('APPWRITE_METERS_COLLECTION_ID')
    APPWRITE_READINGS_COLLECTION_ID = os.getenv('APPWRITE_READINGS_COLLECTION_ID')
    
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            'APPWRITE_PROJECT_ID',
            'APPWRITE_API_KEY',
            'APPWRITE_DATABASE_ID',
            'APPWRITE_METERS_COLLECTION_ID',
            'APPWRITE_READINGS_COLLECTION_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def initialize(cls):
        """Initialize configuration by loading from environment"""
        try:
            config_instance = cls()
            print("✅ Configuration loaded successfully from .env file")
            return True
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return False
    
    @classmethod
    def print_status(cls):
        """Print configuration status for debugging"""
        print("=== Appwrite Configuration Status ===")
        print(f"Endpoint: {cls.APPWRITE_ENDPOINT}")
        print(f"Project ID: {cls.APPWRITE_PROJECT_ID}")
        print(f"API Key: {'***' + cls.APPWRITE_API_KEY[-10:] if cls.APPWRITE_API_KEY else 'NOT SET'}")
        print(f"Database ID: {cls.APPWRITE_DATABASE_ID}")
        print(f"Meters Collection: {cls.APPWRITE_METERS_COLLECTION_ID}")
        print(f"Readings Collection: {cls.APPWRITE_READINGS_COLLECTION_ID}")
        
        try:
            cls.validate()
            print("✅ Configuration validation: PASSED")
        except Exception as e:
            print(f"❌ Configuration validation: FAILED - {e}")


# Initialize configuration on import
Config.initialize()
