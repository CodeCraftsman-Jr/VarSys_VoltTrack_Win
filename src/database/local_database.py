import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class LocalDatabase:
    def __init__(self, db_path="volttrack_local.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize local SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create meters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meters (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                home_name TEXT NOT NULL,
                meter_name TEXT NOT NULL,
                meter_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        # Create readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                meter_id TEXT NOT NULL,
                reading_value REAL NOT NULL,
                previous_reading REAL DEFAULT 0,
                consumption_kwh REAL NOT NULL,
                reading_date TEXT NOT NULL,
                reading_time TEXT DEFAULT '12:00:00',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        # Add reading_time column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE readings ADD COLUMN reading_time TEXT DEFAULT "12:00:00"')
        except:
            pass  # Column already exists
        
        # Create sync log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_meter(self, meter_data: Dict) -> str:
        """Add meter to local database (with duplicate prevention)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if meter already exists by ID
        cursor.execute('SELECT id FROM meters WHERE id = ?', (meter_data['id'],))
        existing = cursor.fetchone()
        
        if existing:
            print(f"DEBUG: Meter {meter_data['id']} already exists, skipping")
            conn.close()
            return meter_data['id']
        
        cursor.execute('''
            INSERT INTO meters (id, user_id, home_name, meter_name, meter_type, created_at, synced)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (
            meter_data['id'],
            meter_data['user_id'],
            meter_data['home_name'],
            meter_data['meter_name'],
            meter_data['meter_type'],
            meter_data['created_at']
        ))
        
        # Log for sync
        cursor.execute('''
            INSERT INTO sync_log (operation, table_name, record_id, timestamp)
            VALUES ('INSERT', 'meters', ?, ?)
        ''', (meter_data['id'], datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return meter_data['id']
    
    def add_reading(self, reading_data: Dict) -> str:
        """Add reading to local database with kWh calculation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get previous reading for kWh calculation
        cursor.execute('''
            SELECT reading_value FROM readings 
            WHERE meter_id = ? AND reading_date < ? 
            ORDER BY reading_date DESC LIMIT 1
        ''', (reading_data['meter_id'], reading_data['reading_date']))
        
        previous_result = cursor.fetchone()
        current_reading = reading_data['reading_value']
        
        if previous_result:
            # Not the first reading - calculate consumption normally
            previous_reading = previous_result[0]
            consumption_kwh = max(0, current_reading - previous_reading)
        else:
            # First reading - previous reading equals current reading (consumption = 0)
            previous_reading = current_reading
            consumption_kwh = 0
        
        cursor.execute('''
            INSERT INTO readings (id, user_id, meter_id, reading_value, previous_reading, 
                                consumption_kwh, reading_date, reading_time, created_at, synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (
            reading_data['id'],
            reading_data['user_id'],
            reading_data['meter_id'],
            current_reading,
            previous_reading,
            consumption_kwh,
            reading_data['reading_date'],
            reading_data.get('reading_time', '12:00:00'),
            reading_data['created_at']
        ))
        
        # Log for sync
        cursor.execute('''
            INSERT INTO sync_log (operation, table_name, record_id, timestamp)
            VALUES ('INSERT', 'readings', ?, ?)
        ''', (reading_data['id'], datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return reading_data['id']
    
    def get_meters(self, user_id: str) -> List[Dict]:
        """Get all active meters for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, home_name, meter_name, meter_type, created_at
            FROM meters WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
        ''', (user_id,))
        
        meters = []
        for row in cursor.fetchall():
            meters.append({
                '$id': row[0],
                'user_id': row[1],
                'home_name': row[2],
                'meter_name': row[3],
                'meter_type_fixed': row[4],  # Keep for backward compatibility
                'meter_type': row[4],        # Also map to meter_type
                'created_at': row[5]
            })
        
        conn.close()
        return meters
    
    def get_readings(self, meter_id: str, year: int = None, month: int = None) -> List[Dict]:
        """Get readings for a meter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, user_id, meter_id, reading_value, previous_reading, consumption_kwh, reading_date, reading_time, created_at
            FROM readings WHERE meter_id = ?
        '''
        params = [meter_id]
        
        if year:
            query += " AND strftime('%Y', reading_date) = ?"
            params.append(str(year))
        
        if month:
            query += " AND strftime('%m', reading_date) = ?"
            params.append(f"{month:02d}")
        
        query += " ORDER BY reading_date DESC, reading_time DESC"
        
        cursor.execute(query, params)
        
        readings = []
        for row in cursor.fetchall():
            readings.append({
                '$id': row[0],
                'user_id': row[1],    # Include user_id from the query
                'meter_id': row[2],   # Include meter_id from the query
                'reading_value': row[3],
                'previous_reading': row[4],
                'consumption_fixed': row[5],  # This is kWh consumption
                'consumption_kwh': row[5],    # Also map to consumption_kwh for consistency
                'reading_date': row[6],
                'reading_time': row[7] if len(row) > 8 else '12:00:00',  # Default time if not available
                'created_at': row[8] if len(row) > 8 else row[7]
            })
        
        conn.close()
        return readings
    
    def get_daily_consumption(self, meter_id: str, year: int = None, month: int = None) -> List[Dict]:
        """Get daily consumption (difference between first and last reading of each day)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT reading_date, 
                   MIN(reading_time) as first_time, MAX(reading_time) as last_time,
                   MIN(reading_value) as first_reading, MAX(reading_value) as last_reading,
                   COUNT(*) as reading_count
            FROM readings WHERE meter_id = ?
        '''
        params = [meter_id]
        
        if year:
            query += " AND strftime('%Y', reading_date) = ?"
            params.append(str(year))
        
        if month:
            query += " AND strftime('%m', reading_date) = ?"
            params.append(f"{month:02d}")
        
        query += " GROUP BY reading_date ORDER BY reading_date DESC"
        
        cursor.execute(query, params)
        
        daily_consumption = []
        for row in cursor.fetchall():
            date = row[0]
            first_time = row[1]
            last_time = row[2]
            first_reading = row[3]
            last_reading = row[4]
            reading_count = row[5]
            
            # Calculate daily consumption (last - first reading of the day)
            consumption = max(0, last_reading - first_reading) if reading_count > 1 else 0
            
            daily_consumption.append({
                'date': date,
                'first_time': first_time,
                'last_time': last_time,
                'first_reading': first_reading,
                'last_reading': last_reading,
                'daily_consumption': consumption,
                'reading_count': reading_count
            })
        
        conn.close()
        return daily_consumption
    
    def update_reading(self, reading_id: str, reading_value: float, reading_date: str, reading_time: str = None) -> bool:
        """Update a reading and recalculate kWh"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get meter_id for this reading
        cursor.execute('SELECT meter_id FROM readings WHERE id = ?', (reading_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        meter_id = result[0]
        
        # Get previous reading
        cursor.execute('''
            SELECT reading_value FROM readings 
            WHERE meter_id = ? AND reading_date < ? AND id != ?
            ORDER BY reading_date DESC LIMIT 1
        ''', (meter_id, reading_date, reading_id))
        
        previous_result = cursor.fetchone()
        
        if previous_result:
            # Not the first reading - calculate consumption normally
            previous_reading = previous_result[0]
            consumption_kwh = max(0, reading_value - previous_reading)
        else:
            # First reading - previous reading equals current reading (consumption = 0)
            previous_reading = reading_value
            consumption_kwh = 0
        
        # Update reading with optional time
        if reading_time:
            cursor.execute('''
                UPDATE readings 
                SET reading_value = ?, previous_reading = ?, consumption_kwh = ?, 
                    reading_date = ?, reading_time = ?, updated_at = ?, synced = 0
                WHERE id = ?
            ''', (reading_value, previous_reading, consumption_kwh, reading_date, 
                  reading_time, datetime.now().isoformat(), reading_id))
        else:
            cursor.execute('''
                UPDATE readings 
                SET reading_value = ?, previous_reading = ?, consumption_kwh = ?, 
                    reading_date = ?, updated_at = ?, synced = 0
                WHERE id = ?
            ''', (reading_value, previous_reading, consumption_kwh, reading_date, 
                  datetime.now().isoformat(), reading_id))
        
        # Log for sync
        cursor.execute('''
            INSERT INTO sync_log (operation, table_name, record_id, timestamp)
            VALUES ('UPDATE', 'readings', ?, ?)
        ''', (reading_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    
    def delete_reading(self, reading_id: str) -> bool:
        """Delete a reading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if reading exists
        cursor.execute('SELECT COUNT(*) FROM readings WHERE id = ?', (reading_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return False
        
        cursor.execute('DELETE FROM readings WHERE id = ?', (reading_id,))
        
        # Log for sync
        cursor.execute('''
            INSERT INTO sync_log (operation, table_name, record_id, timestamp)
            VALUES ('DELETE', 'readings', ?, ?)
        ''', (reading_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    
    def remove_duplicate_meters(self, user_id: str) -> int:
        """Remove duplicate meters, keeping the oldest one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find duplicates by home_name and meter_name
        cursor.execute('''
            SELECT home_name, meter_name, COUNT(*) as count
            FROM meters 
            WHERE user_id = ?
            GROUP BY home_name, meter_name 
            HAVING COUNT(*) > 1
        ''', (user_id,))
        
        duplicates = cursor.fetchall()
        removed_count = 0
        
        for home_name, meter_name, count in duplicates:
            # Get all meters with this name, ordered by creation date (oldest first)
            cursor.execute('''
                SELECT id, created_at FROM meters 
                WHERE user_id = ? AND home_name = ? AND meter_name = ?
                ORDER BY created_at ASC
            ''', (user_id, home_name, meter_name))
            
            meters = cursor.fetchall()
            
            # Keep the first (oldest) one, remove the rest
            for meter_id, created_at in meters[1:]:
                cursor.execute('DELETE FROM meters WHERE id = ?', (meter_id,))
                cursor.execute('DELETE FROM readings WHERE meter_id = ?', (meter_id,))
                cursor.execute('DELETE FROM sync_log WHERE record_id = ?', (meter_id,))
                removed_count += 1
                print(f"DEBUG: Removed duplicate meter {meter_id} ({home_name} - {meter_name})")
        
        conn.commit()
        conn.close()
        return removed_count
    
    def get_unsynced_changes(self) -> List[Dict]:
        """Get all unsynced changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT operation, table_name, record_id, timestamp
            FROM sync_log WHERE synced = 0
            ORDER BY timestamp ASC
        ''')
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'operation': row[0],
                'table_name': row[1],
                'record_id': row[2],
                'timestamp': row[3]
            })
        
        conn.close()
        return changes
    
    def mark_synced(self, record_ids: List[str]):
        """Mark records as synced"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record_id in record_ids:
            cursor.execute('''
                UPDATE sync_log SET synced = 1 
                WHERE record_id = ?
            ''', (record_id,))
        
        conn.commit()
        conn.close()
