#!/usr/bin/env python3

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class SessionManager:
    def __init__(self):
        self.session_file = Path.home() / '.volttrack_session.json'
    
    def save_session(self, user_data, session_data=None, remember_me=True):
        """Save user session to local file"""
        try:
            if not remember_me:
                print("DEBUG: Remember me is False, clearing session")
                self.clear_session()
                return
            
            save_data = {
                'user': user_data,
                'session': session_data,  # Store Appwrite session data
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            print(f"DEBUG: Saving session to: {self.session_file}")
            print(f"DEBUG: Session expires at: {save_data['expires_at']}")
            
            with open(self.session_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            # Set file permissions (readable only by user)
            os.chmod(self.session_file, 0o600)
            print(f"DEBUG: Session file saved successfully")
            
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def load_session(self):
        """Load user session from local file"""
        try:
            if not self.session_file.exists():
                print(f"DEBUG: Session file does not exist: {self.session_file}")
                return None, None
            
            print(f"DEBUG: Loading session from: {self.session_file}")
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session has expired
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            now = datetime.now()
            
            print(f"DEBUG: Session expires at: {expires_at}")
            print(f"DEBUG: Current time: {now}")
            
            if now > expires_at:
                print(f"DEBUG: Session has expired, clearing")
                self.clear_session()
                return None, None
            
            print(f"DEBUG: Session is valid, returning user and session data")
            return session_data.get('user'), session_data.get('session')
            
        except Exception as e:
            print(f"Error loading session: {e}")
            self.clear_session()
            return None, None
    
    def clear_session(self):
        """Clear saved session"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
        except Exception as e:
            print(f"Error clearing session: {e}")
    
    def is_session_valid(self):
        """Check if current session is valid"""
        user, session = self.load_session()
        return user is not None
    
    def get_session(self):
        """Get current session data"""
        user, session = self.load_session()
        if user:
            return {
                'user': user,
                'session': session,
                'session_id': session.get('$id') if session else None
            }
        return None
