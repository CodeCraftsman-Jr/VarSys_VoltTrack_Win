"""
Environment Configuration Loader for VoltTrack
Securely loads Appwrite configuration from .env file
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

class EnvironmentConfig:
    """Secure environment configuration loader"""
    
    def __init__(self, env_file_path: Optional[str] = None):
        """
        Initialize environment configuration loader
        
        Args:
            env_file_path: Optional path to .env file. If None, looks in project root.
        """
        self.env_file_path = env_file_path or self._find_env_file()
        self.config = {}
        self._load_env_file()
    
    def _find_env_file(self) -> str:
        """Find .env file in project root"""
        # Get the project root (3 levels up from this file)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        env_file = project_root / '.env'
        
        if env_file.exists():
            return str(env_file)
        else:
            raise FileNotFoundError(f"No .env file found at {env_file}")
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.config[key] = value
                        
                        # Also set as environment variable for compatibility
                        os.environ[key] = value
                    else:
                        print(f"Warning: Invalid line format at line {line_num}: {line}")
                        
        except FileNotFoundError:
            raise FileNotFoundError(f"Environment file not found: {self.env_file_path}")
        except Exception as e:
            raise Exception(f"Error loading environment file: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value
        
        Args:
            key: Environment variable key
            default: Default value if key not found
            
        Returns:
            Environment variable value or default
        """
        return self.config.get(key, default)
    
    def get_required(self, key: str) -> str:
        """
        Get required environment variable value
        
        Args:
            key: Environment variable key
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If required key is not found
        """
        value = self.config.get(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' not found in .env file")
        return value
    
    def get_appwrite_config(self) -> Dict[str, str]:
        """
        Get all Appwrite configuration as a dictionary
        
        Returns:
            Dictionary containing all Appwrite configuration
        """
        appwrite_config = {
            'endpoint': self.get_required('APPWRITE_ENDPOINT'),
            'project_id': self.get_required('APPWRITE_PROJECT_ID'),
            'api_key': self.get_required('APPWRITE_API_KEY'),
            'database_id': self.get_required('APPWRITE_DATABASE_ID'),
            'meters_collection_id': self.get_required('APPWRITE_METERS_COLLECTION_ID'),
            'readings_collection_id': self.get_required('APPWRITE_READINGS_COLLECTION_ID'),
        }
        
        return appwrite_config
    
    def validate_config(self) -> bool:
        """
        Validate that all required Appwrite configuration is present
        
        Returns:
            True if all required config is present, False otherwise
        """
        required_keys = [
            'APPWRITE_ENDPOINT',
            'APPWRITE_PROJECT_ID', 
            'APPWRITE_API_KEY',
            'APPWRITE_DATABASE_ID',
            'APPWRITE_METERS_COLLECTION_ID',
            'APPWRITE_READINGS_COLLECTION_ID'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not self.config.get(key):
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Missing required environment variables: {', '.join(missing_keys)}")
            return False
        
        return True
    
    def print_config_status(self):
        """Print configuration status for debugging"""
        print("=== Environment Configuration Status ===")
        print(f"Config file: {self.env_file_path}")
        print(f"Config loaded: {len(self.config)} variables")
        
        appwrite_keys = [
            'APPWRITE_ENDPOINT',
            'APPWRITE_PROJECT_ID',
            'APPWRITE_API_KEY',
            'APPWRITE_DATABASE_ID', 
            'APPWRITE_METERS_COLLECTION_ID',
            'APPWRITE_READINGS_COLLECTION_ID'
        ]
        
        print("\nAppwrite Configuration:")
        for key in appwrite_keys:
            value = self.config.get(key, 'NOT SET')
            # Mask API key for security
            if key == 'APPWRITE_API_KEY' and value != 'NOT SET':
                masked_value = value[:10] + '...' + value[-10:] if len(value) > 20 else '***'
                print(f"  {key}: {masked_value}")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nValidation: {'✅ PASSED' if self.validate_config() else '❌ FAILED'}")


# Global instance for easy access
_env_config = None

def get_env_config() -> EnvironmentConfig:
    """Get global environment configuration instance"""
    global _env_config
    if _env_config is None:
        _env_config = EnvironmentConfig()
    return _env_config

def get_appwrite_config() -> Dict[str, str]:
    """Get Appwrite configuration from environment"""
    return get_env_config().get_appwrite_config()

def validate_environment() -> bool:
    """Validate environment configuration"""
    return get_env_config().validate_config()


if __name__ == "__main__":
    # Test the configuration loader
    try:
        config = EnvironmentConfig()
        config.print_config_status()
        
        print("\n=== Testing Appwrite Config ===")
        appwrite_config = config.get_appwrite_config()
        for key, value in appwrite_config.items():
            if key == 'api_key':
                masked_value = value[:10] + '...' + value[-10:] if len(value) > 20 else '***'
                print(f"{key}: {masked_value}")
            else:
                print(f"{key}: {value}")
                
    except Exception as e:
        print(f"Error: {e}")
