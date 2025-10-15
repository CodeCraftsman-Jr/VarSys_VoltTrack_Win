"""
Direct Appwrite Service using API Keys
Uses direct database access with API keys for reliable operations
"""

from appwrite.client import Client
from appwrite.services.account import Account
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.id import ID
from appwrite.exception import AppwriteException
from config.env_config import get_appwrite_config
from datetime import datetime, timedelta
import json

class DirectAppwriteService:
    """Direct Appwrite service using API keys for database operations"""
    
    def __init__(self):
        """Initialize with API key configuration"""
        # Load configuration from environment
        try:
            self.config = get_appwrite_config()
        except Exception as e:
            # Fallback to hardcoded values if .env not available
            print(f"Warning: Could not load .env config: {e}")
            self.config = {
                'endpoint': 'https://cloud.appwrite.io/v1',
                'project_id': '68e969ec000646eba8c5',
                'api_key': '',  # Will need to be set
                'database_id': 'volttrack_db',
                'meters_collection_id': 'meters',
                'readings_collection_id': 'readings'
            }
        
        # Client for user authentication (no API key)
        self.auth_client = Client()
        self.auth_client.set_endpoint(self.config['endpoint'])
        self.auth_client.set_project(self.config['project_id'])
        
        # Client for database operations (with API key)
        self.db_client = Client()
        self.db_client.set_endpoint(self.config['endpoint'])
        self.db_client.set_project(self.config['project_id'])
        if self.config.get('api_key'):
            self.db_client.set_key(self.config['api_key'])
        
        # Services
        self.account = Account(self.auth_client)
        self.databases = Databases(self.db_client)
        
        # Session management
        self.current_user = None
        self.session_id = None
    
    def set_api_key(self, api_key: str):
        """Set API key for database operations"""
        self.config['api_key'] = api_key
        self.db_client.set_key(api_key)
        self.databases = Databases(self.db_client)
    
    def set_session(self, session_id):
        """Set user session for authentication"""
        self.session_id = session_id
        self.auth_client.set_session(session_id)
    
    def restore_session(self, session_data):
        """Restore user session from saved data"""
        try:
            if isinstance(session_data, dict) and '$id' in session_data:
                session_id = session_data['$id']
            else:
                session_id = session_data
            
            self.set_session(session_id)
            self.current_user = self.get_current_user()
            return True
        except Exception as e:
            print(f"Session restoration failed: {e}")
            return False
    
    # Authentication methods
    def create_account(self, email, password, name):
        """Create user account"""
        try:
            user = self.account.create(ID.unique(), email, password, name)
            return user
        except AppwriteException as e:
            raise Exception(f"Failed to create account: {e.message}")
        except Exception as e:
            raise Exception(f"Failed to create account: {str(e)}")
    
    def login(self, email, password):
        """Login user and initialize session"""
        try:
            session = self.account.create_email_password_session(email, password)
            self.session_id = session['$id']
            
            # Set the session using the secret
            session_secret = session.get('secret', session['$id'])
            self.auth_client.set_session(session_secret)
            
            # Get user info
            try:
                self.current_user = self.account.get()
            except:
                self.current_user = {'$id': session.get('userId', 'unknown')}
            
            return {
                'session': session,
                'user': self.current_user
            }
        except AppwriteException as e:
            raise Exception(f"Login failed: {e.message}")
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def get_current_user(self):
        """Get current authenticated user"""
        try:
            return self.account.get()
        except Exception as e:
            raise Exception(f"Failed to get user: {str(e)}")
    
    def logout(self):
        """Logout current user"""
        try:
            self.account.delete_session('current')
            self.current_user = None
            self.session_id = None
        except Exception as e:
            print(f"Logout error: {e}")
    
    # Meter operations
    def create_meter(self, home_name, meter_name, meter_type='electricity'):
        """Create a new meter"""
        if not self.current_user:
            raise Exception("User must be logged in")
        
        try:
            # Check for duplicates
            existing = self.databases.list_documents(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                queries=[
                    Query.equal('user_id', self.current_user['$id']),
                    Query.equal('meter_name', meter_name),
                    Query.equal('home_name', home_name)
                ]
            )
            
            if existing.documents:
                raise Exception("A meter with this name already exists for this home")
            
            meter = self.databases.create_document(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                document_id=ID.unique(),
                data={
                    'user_id': self.current_user['$id'],
                    'home_name': home_name,
                    'meter_name': meter_name,
                    'meter_type': meter_type,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            return meter
        except Exception as e:
            raise Exception(f"Failed to create meter: {str(e)}")
    
    def get_user_meters(self):
        """Get all meters for current user"""
        if not self.current_user:
            raise Exception("User must be logged in")
        
        try:
            result = self.databases.list_documents(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                queries=[Query.equal('user_id', self.current_user['$id'])]
            )
            return result.documents
        except Exception as e:
            raise Exception(f"Failed to get meters: {str(e)}")
    
    def update_meter(self, meter_id, **kwargs):
        """Update meter"""
        try:
            # Ensure all values are JSON serializable
            data = {}
            for key, value in kwargs.items():
                if hasattr(value, 'isoformat'):
                    data[key] = value.isoformat()
                elif hasattr(value, 'strftime'):
                    data[key] = value.strftime('%Y-%m-%d')
                else:
                    data[key] = value
            
            meter = self.databases.update_document(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                document_id=meter_id,
                data=data
            )
            return meter
        except Exception as e:
            raise Exception(f"Failed to update meter: {str(e)}")
    
    def delete_meter(self, meter_id):
        """Delete meter"""
        try:
            self.databases.delete_document(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                document_id=meter_id
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to delete meter: {str(e)}")
    
    # Reading operations
    def add_reading(self, meter_id, reading_value, reading_date, reading_time='12:00:00'):
        """Add a new reading"""
        if not self.current_user:
            raise Exception("User must be logged in")
        
        try:
            # Convert date to string if needed
            if isinstance(reading_date, str):
                date_str = reading_date
            else:
                date_str = reading_date.strftime('%Y-%m-%d')
            
            reading = self.databases.create_document(
                database_id=self.config['database_id'],
                collection_id=self.config['readings_collection_id'],
                document_id=ID.unique(),
                data={
                    'user_id': self.current_user['$id'],
                    'meter_id': meter_id,
                    'reading_value': float(reading_value),
                    'reading_date': date_str,
                    'reading_time': reading_time,
                    'consumption_kwh': 0.0,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            return reading
        except Exception as e:
            raise Exception(f"Failed to add reading: {str(e)}")
    
    def get_readings(self, meter_id, start_date=None, end_date=None, limit=100):
        """Get readings for a meter"""
        try:
            queries = [Query.equal('meter_id', meter_id)]
            
            if start_date:
                queries.append(Query.greater_than_equal('reading_date', start_date))
            if end_date:
                queries.append(Query.less_than_equal('reading_date', end_date))
            
            queries.append(Query.limit(limit))
            queries.append(Query.order_desc('reading_date'))
            
            result = self.databases.list_documents(
                database_id=self.config['database_id'],
                collection_id=self.config['readings_collection_id'],
                queries=queries
            )
            return result.documents
        except Exception as e:
            raise Exception(f"Failed to get readings: {str(e)}")
    
    def update_reading(self, reading_id, **kwargs):
        """Update reading"""
        try:
            # Ensure all values are JSON serializable
            data = {}
            for key, value in kwargs.items():
                if hasattr(value, 'isoformat'):
                    data[key] = value.isoformat()
                elif hasattr(value, 'strftime'):
                    data[key] = value.strftime('%Y-%m-%d')
                else:
                    data[key] = value
            
            reading = self.databases.update_document(
                database_id=self.config['database_id'],
                collection_id=self.config['readings_collection_id'],
                document_id=reading_id,
                data=data
            )
            return reading
        except Exception as e:
            raise Exception(f"Failed to update reading: {str(e)}")
    
    def delete_reading(self, reading_id):
        """Delete reading"""
        try:
            self.databases.delete_document(
                database_id=self.config['database_id'],
                collection_id=self.config['readings_collection_id'],
                document_id=reading_id
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to delete reading: {str(e)}")
    
    # Sync operations
    def sync_meter(self, meter_id, home_name, meter_name, meter_type, user_id, created_at=None):
        """Sync a meter with ID preservation"""
        try:
            print(f"DEBUG: Syncing meter - ID: {meter_id}, Name: {meter_name}, User: {user_id}")
            print(f"DEBUG: Database config - DB: {self.config['database_id']}, Collection: {self.config['meters_collection_id']}")
            
            # Check if meter already exists
            existing_meters = self.databases.list_documents(
                database_id=self.config['database_id'],
                collection_id=self.config['meters_collection_id'],
                queries=[
                    Query.equal('user_id', user_id),
                    Query.equal('meter_name', meter_name),
                    Query.equal('home_name', home_name)
                ]
            )
            print(f"DEBUG: Found {len(existing_meters.documents)} existing meters")
            
            if existing_meters.documents:
                print(f"INFO: Meter '{meter_name}' already exists on server")
                return existing_meters.documents[0]
            
            # Create new meter with original ID if possible
            meter_data = {
                'user_id': user_id,
                'home_name': home_name,
                'meter_name': meter_name,
                'meter_type': meter_type,
                'created_at': created_at or datetime.now().isoformat()
            }
            
            try:
                meter = self.databases.create_document(
                    database_id=self.config['database_id'],
                    collection_id=self.config['meters_collection_id'],
                    document_id=meter_id,  # Try to preserve original ID
                    data=meter_data
                )
                print(f"INFO: Successfully synced meter '{meter_name}' with ID {meter['$id']}")
                return meter
            except:
                # If ID conflict, create with new ID
                meter = self.databases.create_document(
                    database_id=self.config['database_id'],
                    collection_id=self.config['meters_collection_id'],
                    document_id=ID.unique(),
                    data=meter_data
                )
                print(f"INFO: Created meter '{meter_name}' with new ID {meter['$id']} (original: {meter_id})")
                return meter
                
        except Exception as e:
            print(f"ERROR: Failed to sync meter {meter_id}: {str(e)}")
            raise Exception(f"Failed to sync meter: {str(e)}")
    
    def sync_reading(self, reading_id, meter_id, reading_value, reading_date, user_id, created_at=None):
        """Sync a reading with ID preservation"""
        try:
            print(f"DEBUG: Syncing reading - ID: {reading_id}, Meter: {meter_id}, Value: {reading_value}, User: {user_id}")
            
            # Convert date format if needed
            if isinstance(reading_date, str):
                date_str = reading_date
            else:
                date_str = reading_date.strftime('%Y-%m-%d')
            
            print(f"DEBUG: Reading date: {date_str}")
            
            # Check if reading already exists (by date and meter)
            existing_readings = self.databases.list_documents(
                database_id=self.config['database_id'],
                collection_id=self.config['readings_collection_id'],
                queries=[
                    Query.equal('user_id', user_id),
                    Query.equal('meter_id', meter_id),
                    Query.equal('reading_date', date_str)
                ]
            )
            
            if existing_readings.documents:
                print(f"INFO: Reading for meter {meter_id} on {date_str} already exists on server")
                return existing_readings.documents[0]
            
            # Create new reading with original ID if possible
            reading_data = {
                'user_id': user_id,
                'meter_id': meter_id,
                'reading_value': float(reading_value),
                'reading_date': date_str,
                'reading_time': '12:00:00',
                'consumption_kwh': 0.0,
                'created_at': created_at or datetime.now().isoformat()
            }
            
            try:
                reading = self.databases.create_document(
                    database_id=self.config['database_id'],
                    collection_id=self.config['readings_collection_id'],
                    document_id=reading_id,  # Try to preserve original ID
                    data=reading_data
                )
                print(f"INFO: Successfully synced reading {reading_value} kWh with ID {reading['$id']}")
                return reading
            except:
                # If ID conflict, create with new ID
                reading = self.databases.create_document(
                    database_id=self.config['database_id'],
                    collection_id=self.config['readings_collection_id'],
                    document_id=ID.unique(),
                    data=reading_data
                )
                print(f"INFO: Created reading {reading_value} kWh with new ID {reading['$id']} (original: {reading_id})")
                return reading
                
        except Exception as e:
            print(f"ERROR: Failed to sync reading {reading_id}: {str(e)}")
            raise Exception(f"Failed to sync reading: {str(e)}")
    
    # Session management
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.session_id is not None and self.current_user is not None
    
    def get_session_info(self):
        """Get session information"""
        return {
            'session_id': self.session_id,
            'user': self.current_user,
            'authenticated': self.is_authenticated()
        }
