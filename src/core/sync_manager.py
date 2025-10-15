#!/usr/bin/env python3
"""
Comprehensive Sync Manager for VoltTrack
Handles bidirectional sync between local database and Appwrite cloud database
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import sqlite3

class SyncManager:
    """Manages comprehensive sync operations between local and cloud databases"""
    
    def __init__(self, local_db, appwrite_service):
        self.local_db = local_db
        self.appwrite = appwrite_service
        self.sync_results = {
            'local_to_server': {'success': 0, 'failed': 0, 'items': []},
            'server_to_local': {'success': 0, 'failed': 0, 'items': []},
            'conflicts': []
        }
    
    def compare_databases(self) -> Dict:
        """Compare local and server databases to determine sync strategy"""
        comparison = {
            'local_newer': [],
            'server_newer': [],
            'local_only': [],
            'server_only': [],
            'conflicts': [],
            'in_sync': []
        }
        
        try:
            # Get all local data
            local_meters = self.local_db.get_meters(self.appwrite.current_user['$id'])
            local_readings = []
            for meter in local_meters:
                readings = self.local_db.get_readings(meter['$id'])
                local_readings.extend(readings)
            
            print(f"DEBUG: Found {len(local_meters)} local meters and {len(local_readings)} local readings")
            
            # Get all server data
            server_meters = self._get_server_meters_safe()
            server_readings = []
            for meter in server_meters:
                readings = self._get_server_readings_safe(meter['$id'])
                print(f"DEBUG: Server meter {meter.get('meter_name', 'Unknown')} has {len(readings)} readings")
                server_readings.extend(readings)
            
            print(f"DEBUG: Found {len(server_meters)} server meters and {len(server_readings)} server readings")
            
            # Compare meters
            self._compare_meters(local_meters, server_meters, comparison)
            
            # Compare readings
            self._compare_readings(local_readings, server_readings, comparison)
            
            return comparison
            
        except Exception as e:
            print(f"ERROR: Failed to compare databases: {e}")
            return comparison
    
    def _get_server_meters_safe(self) -> List[Dict]:
        """Safely get server meters with error handling"""
        try:
            # Use the appwrite service method that filters by user
            meters = self.appwrite.get_user_meters()
            print(f"DEBUG: Got {len(meters)} meters from server for user {self.appwrite.current_user['$id'] if self.appwrite.current_user else 'None'}")
            return meters
        except Exception as e:
            print(f"ERROR: Failed to get server meters: {e}")
            return []
    
    def _get_server_readings_safe(self, meter_id: str) -> List[Dict]:
        """Safely get server readings with error handling"""
        try:
            readings = self.appwrite.get_readings(meter_id, limit=1000)
            return readings if readings else []
        except Exception as e:
            print(f"ERROR: Failed to get server readings for meter {meter_id}: {e}")
            return []
    
    def _compare_meters(self, local_meters: List[Dict], server_meters: List[Dict], comparison: Dict):
        """Compare meters between local and server"""
        server_meter_ids = {m['$id'] for m in server_meters}
        local_meter_ids = {m['$id'] for m in local_meters}
        
        # Create lookup dictionaries
        server_meters_dict = {m['$id']: m for m in server_meters}
        local_meters_dict = {m['$id']: m for m in local_meters}
        
        # Find meters only in local
        for meter_id in local_meter_ids - server_meter_ids:
            comparison['local_only'].append({
                'type': 'meter',
                'id': meter_id,
                'data': local_meters_dict[meter_id]
            })
        
        # Find meters only on server
        for meter_id in server_meter_ids - local_meter_ids:
            comparison['server_only'].append({
                'type': 'meter',
                'id': meter_id,
                'data': server_meters_dict[meter_id]
            })
        
        # Compare common meters
        for meter_id in local_meter_ids & server_meter_ids:
            local_meter = local_meters_dict[meter_id]
            server_meter = server_meters_dict[meter_id]
            
            local_updated = self._parse_datetime(local_meter.get('updated_at') or local_meter.get('created_at'))
            server_updated = self._parse_datetime(server_meter.get('$updatedAt') or server_meter.get('$createdAt'))
            
            if local_updated and server_updated:
                if local_updated > server_updated:
                    comparison['local_newer'].append({
                        'type': 'meter',
                        'id': meter_id,
                        'local_data': local_meter,
                        'server_data': server_meter
                    })
                elif server_updated > local_updated:
                    comparison['server_newer'].append({
                        'type': 'meter',
                        'id': meter_id,
                        'local_data': local_meter,
                        'server_data': server_meter
                    })
                else:
                    comparison['in_sync'].append({
                        'type': 'meter',
                        'id': meter_id
                    })
    
    def _compare_readings(self, local_readings: List[Dict], server_readings: List[Dict], comparison: Dict):
        """Compare readings between local and server"""
        # Create lookup by meter_id and date for efficient comparison
        server_readings_dict = {}
        for reading in server_readings:
            key = f"{reading['meter_id']}_{reading['reading_date'][:10]}"  # Use date only
            server_readings_dict[key] = reading
        
        local_readings_dict = {}
        for reading in local_readings:
            # Skip readings without required fields
            if 'meter_id' not in reading or 'reading_date' not in reading:
                continue
            date_str = reading['reading_date'][:10] if isinstance(reading['reading_date'], str) else reading['reading_date'].strftime('%Y-%m-%d')
            key = f"{reading['meter_id']}_{date_str}"
            local_readings_dict[key] = reading
        
        local_keys = set(local_readings_dict.keys())
        server_keys = set(server_readings_dict.keys())
        
        # Find readings only in local
        for key in local_keys - server_keys:
            comparison['local_only'].append({
                'type': 'reading',
                'key': key,
                'data': local_readings_dict[key]
            })
        
        # Find readings only on server
        for key in server_keys - local_keys:
            comparison['server_only'].append({
                'type': 'reading',
                'key': key,
                'data': server_readings_dict[key]
            })
        
        # Compare common readings
        for key in local_keys & server_keys:
            local_reading = local_readings_dict[key]
            server_reading = server_readings_dict[key]
            
            # Compare reading values
            local_value = float(local_reading['reading_value'])
            server_value = float(server_reading['reading_value'])
            
            if abs(local_value - server_value) > 0.01:  # Allow small floating point differences
                comparison['conflicts'].append({
                    'type': 'reading',
                    'key': key,
                    'local_data': local_reading,
                    'server_data': server_reading,
                    'conflict_reason': f'Value mismatch: local={local_value}, server={server_value}'
                })
            else:
                comparison['in_sync'].append({
                    'type': 'reading',
                    'key': key
                })
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string with multiple format support"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f+00:00',
            '%Y-%m-%dT%H:%M:%S+00:00',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def sync_local_to_server(self, items: List[Dict]) -> Dict:
        """Sync local items to server"""
        results = {'success': 0, 'failed': 0, 'items': []}
        
        print(f"DEBUG: sync_local_to_server called with {len(items)} items")
        
        for i, item in enumerate(items):
            try:
                print(f"DEBUG: Processing item {i+1}/{len(items)}: {item['type']}")
                
                if item['type'] == 'meter':
                    print(f"DEBUG: Syncing meter: {item['data']['meter_name']}")
                    self._sync_meter_to_server(item['data'])
                    results['success'] += 1
                    results['items'].append(f"Meter: {item['data']['meter_name']}")
                    
                elif item['type'] == 'reading':
                    print(f"DEBUG: Syncing reading: {item['data']['reading_value']} kWh on {item['data']['reading_date']}")
                    self._sync_reading_to_server(item['data'])
                    results['success'] += 1
                    results['items'].append(f"Reading: {item['data']['reading_value']} kWh")
                    
            except Exception as e:
                results['failed'] += 1
                print(f"ERROR: Failed to sync {item['type']} to server: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"DEBUG: sync_local_to_server completed: {results['success']} success, {results['failed']} failed")
        return results
    
    def sync_server_to_local(self, items: List[Dict]) -> Dict:
        """Sync server items to local"""
        results = {'success': 0, 'failed': 0, 'items': []}
        
        for item in items:
            try:
                if item['type'] == 'meter':
                    self._sync_meter_to_local(item['data'])
                    results['success'] += 1
                    results['items'].append(f"Meter: {item['data']['meter_name']}")
                    
                elif item['type'] == 'reading':
                    self._sync_reading_to_local(item['data'])
                    results['success'] += 1
                    results['items'].append(f"Reading: {item['data']['reading_value']} kWh")
                    
            except Exception as e:
                results['failed'] += 1
                print(f"ERROR: Failed to sync {item['type']} to local: {e}")
        
        return results
    
    def _sync_meter_to_server(self, meter_data: Dict):
        """Sync a meter to server"""
        self.appwrite.sync_meter(
            meter_id=meter_data['$id'],
            home_name=meter_data['home_name'],
            meter_name=meter_data['meter_name'],
            meter_type=meter_data.get('meter_type', 'electricity'),
            user_id=meter_data['user_id'],
            created_at=meter_data.get('created_at')
        )
    
    def _sync_reading_to_server(self, reading_data: Dict):
        """Sync a reading to server"""
        # Get user_id from current user if not in reading_data
        user_id = reading_data.get('user_id') or self.appwrite.current_user['$id']
        
        self.appwrite.sync_reading(
            reading_id=reading_data['$id'],
            meter_id=reading_data['meter_id'],
            reading_value=reading_data['reading_value'],
            reading_date=reading_data['reading_date'],
            user_id=user_id,
            created_at=reading_data.get('created_at'),
            consumption_kwh=reading_data.get('consumption_kwh', 0.0)
        )
    
    def _sync_meter_to_local(self, meter_data: Dict):
        """Sync a meter to local database"""
        # Check if meter exists locally
        existing_meters = self.local_db.get_meters(meter_data['user_id'])
        existing_meter = next((m for m in existing_meters if m['$id'] == meter_data['$id']), None)
        
        if existing_meter:
            # Update existing meter
            self.local_db.update_meter(
                meter_id=meter_data['$id'],
                home_name=meter_data['home_name'],
                meter_name=meter_data['meter_name'],
                meter_type=meter_data.get('meter_type_fixed', 'electricity')
            )
        else:
            # Create new meter
            self.local_db.add_meter({
                'id': meter_data['$id'],
                'user_id': meter_data['user_id'],
                'home_name': meter_data['home_name'],
                'meter_name': meter_data['meter_name'],
                'meter_type': meter_data.get('meter_type_fixed', 'electricity'),
                'created_at': meter_data.get('created_at', datetime.now().isoformat()),
                'is_active': meter_data.get('is_active_fixed', True)
            })
    
    def _sync_reading_to_local(self, reading_data: Dict):
        """Sync a reading to local database"""
        # Check if reading exists locally
        date_str = reading_data['reading_date'][:10]
        
        conn = sqlite3.connect(self.local_db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM readings 
            WHERE meter_id = ? AND reading_date LIKE ?
        ''', (reading_data['meter_id'], f"{date_str}%"))
        
        exists = cursor.fetchone()[0] > 0
        conn.close()
        
        if not exists:
            # Add new reading
            self.local_db.add_reading({
                'id': reading_data['$id'],
                'user_id': reading_data['user_id'],
                'meter_id': reading_data['meter_id'],
                'reading_value': reading_data['reading_value'],
                'reading_date': reading_data['reading_date'],
                'reading_time': '12:00:00',
                'created_at': reading_data.get('created_at', datetime.now().isoformat())
            })
    
    def get_sync_summary(self, comparison: Dict) -> str:
        """Generate a human-readable sync summary"""
        summary = []
        
        if comparison['local_only']:
            summary.append(f"📤 {len(comparison['local_only'])} items to upload to server")
        
        if comparison['server_only']:
            summary.append(f"📥 {len(comparison['server_only'])} items to download from server")
        
        if comparison['local_newer']:
            summary.append(f"⬆️ {len(comparison['local_newer'])} items newer locally")
        
        if comparison['server_newer']:
            summary.append(f"⬇️ {len(comparison['server_newer'])} items newer on server")
        
        if comparison['conflicts']:
            summary.append(f"⚠️ {len(comparison['conflicts'])} conflicts need resolution")
        
        if comparison['in_sync']:
            summary.append(f"✅ {len(comparison['in_sync'])} items in sync")
        
        return "\n".join(summary) if summary else "✅ All data is in sync"
