#!/usr/bin/env python3
"""
API Backend for VoltTrack Web Application
Provides REST API endpoints for the web frontend
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import json
from datetime import datetime

from database.direct_appwrite_service import DirectAppwriteService
from database.local_database import LocalDatabase
from core.session_manager import SessionManager

app = Flask(__name__)
CORS(app)

# Initialize services
appwrite = DirectAppwriteService()
local_db = LocalDatabase()
session_manager = SessionManager()

@app.route('/')
def serve_index():
    """Serve the main web application"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Run async login
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session = loop.run_until_complete(appwrite.login(email, password))
            user = loop.run_until_complete(appwrite.get_current_user())
            
            return jsonify({
                'success': True,
                'user': user,
                'token': session.get('$id', ''),
                'session': session
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/meters', methods=['GET'])
def get_meters():
    """Get user meters"""
    try:
        # Get user from session/token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        # For now, get from local database
        # In production, you'd validate the token and get user_id
        user_id = get_user_id_from_token(auth_header.replace('Bearer ', ''))
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        meters = local_db.get_meters(user_id)
        return jsonify(meters)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/readings', methods=['GET'])
def get_readings():
    """Get user readings"""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = get_user_id_from_token(auth_header.replace('Bearer ', ''))
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get all readings for user's meters
        meters = local_db.get_meters(user_id)
        all_readings = []
        
        for meter in meters:
            readings = local_db.get_readings(meter['id'])
            all_readings.extend(readings)
        
        return jsonify(all_readings)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/meters', methods=['POST'])
def add_meter():
    """Add new meter"""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = get_user_id_from_token(auth_header.replace('Bearer ', ''))
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        meter_data = {
            'id': f"meter_{datetime.now().timestamp()}",
            'user_id': user_id,
            'home_name': data.get('home_name'),
            'meter_name': data.get('meter_name'),
            'meter_type': data.get('meter_type', 'electricity'),
            'created_at': datetime.now().isoformat()
        }
        
        meter_id = local_db.add_meter(meter_data)
        return jsonify({'success': True, 'meter_id': meter_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/readings', methods=['POST'])
def add_reading():
    """Add new reading"""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = get_user_id_from_token(auth_header.replace('Bearer ', ''))
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        reading_data = {
            'id': f"reading_{datetime.now().timestamp()}",
            'user_id': user_id,
            'meter_id': data.get('meter_id'),
            'reading_value': float(data.get('reading_value')),
            'reading_date': data.get('reading_date'),
            'created_at': datetime.now().isoformat()
        }
        
        reading_id = local_db.add_reading(reading_data)
        return jsonify({'success': True, 'reading_id': reading_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync', methods=['POST'])
def sync_data():
    """Sync data with Appwrite"""
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        # Implement sync logic here
        # This would sync local data with Appwrite
        
        return jsonify({'success': True, 'message': 'Sync completed'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_user_id_from_token(token):
    """Extract user ID from token (simplified)"""
    # In production, you'd validate the JWT token properly
    # For now, we'll use a simple approach
    try:
        # Try to get user from current session
        if token.startswith('session_'):
            return token.replace('session_', '')
        return None
    except:
        return None

if __name__ == '__main__':
    print("Starting VoltTrack Web API...")
    print("Web app will be available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
