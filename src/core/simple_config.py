"""
Simple Configuration for VoltTrack
No environment files needed - uses secure Appwrite Functions
"""

class SimpleConfig:
    """Simple configuration without environment dependencies"""
    
    # Public configuration (not sensitive)
    APPWRITE_ENDPOINT = "https://cloud.appwrite.io/v1"
    APPWRITE_PROJECT_ID = "68e969ec000646eba8c5"  # Your project ID
    
    # Function IDs (public)
    VOLTTRACK_METERS_FUNCTION_ID = "volttrack-meters"
    VOLTTRACK_READINGS_FUNCTION_ID = "volttrack-readings"
    
    # App configuration
    APP_NAME = "VoltTrack"
    APP_VERSION = "2.0.0"
    
    @classmethod
    def get_appwrite_config(cls):
        """Get Appwrite configuration"""
        return {
            'endpoint': cls.APPWRITE_ENDPOINT,
            'project_id': cls.APPWRITE_PROJECT_ID
        }
    
    @classmethod
    def validate(cls):
        """Validate configuration - always returns True since no env vars needed"""
        return True
    
    @classmethod
    def print_status(cls):
        """Print configuration status"""
        print("=== VoltTrack Secure Configuration ===")
        print(f"App: {cls.APP_NAME} v{cls.APP_VERSION}")
        print(f"Endpoint: {cls.APPWRITE_ENDPOINT}")
        print(f"Project ID: {cls.APPWRITE_PROJECT_ID}")
        print(f"Security: ✅ Using Appwrite Functions (No local API keys)")
        print(f"Meters Function: {cls.VOLTTRACK_METERS_FUNCTION_ID}")
        print(f"Readings Function: {cls.VOLTTRACK_READINGS_FUNCTION_ID}")
        print("✅ Configuration: SECURE")

# Alias for backward compatibility
Config = SimpleConfig
