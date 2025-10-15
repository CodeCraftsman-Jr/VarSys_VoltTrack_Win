import flet as ft
from datetime import datetime, timedelta
import asyncio
import uuid
import sqlite3
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from database.direct_appwrite_service import DirectAppwriteService
from database.local_database import LocalDatabase
from core.session_manager import SessionManager
from core.sync_manager import SyncManager
from core.simple_config import SimpleConfig
from utils.batch_processor import SyncBatchProcessor

class VoltTrackApp:
    def __init__(self):
        self.appwrite = DirectAppwriteService()
        self.local_db = LocalDatabase()
        self.session_manager = SessionManager()
        self.current_user = None
        self.meters = []
        self.selected_meter = None
        self.offline_mode = False
        self.batch_processor = SyncBatchProcessor()
        self.sync_cancelled = False
        self.sync_manager = None  # Will be initialized after authentication
        
    def main(self, page: ft.Page):
        self.page = page
        page.title = "VoltTrack - Meter Reading Tracker"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1200
        page.window_height = 800
        page.window_resizable = True
        
        # Set up window close event handler
        page.window_prevent_close = True
        page.on_window_event = self.on_window_event
        
        # Show secure configuration status
        print("🔐 VoltTrack starting with secure configuration (no .env needed)")
        SimpleConfig.print_status()
        
        # Initialize UI first
        self.init_ui()
        
        # Check for saved session
        saved_user, saved_session = self.session_manager.load_session()
        print(f"DEBUG: Loaded session - User: {saved_user.get('email', 'Unknown') if saved_user else 'None'}, Session: {saved_session}")
        
        if saved_user and saved_session:
            # Try to restore the Appwrite session
            def restore_session():
                try:
                    # Use synchronous session restoration with full session data
                    full_session_data = {
                        'user': saved_user,
                        'session': saved_session
                    }
                    session_restored = self.appwrite.restore_session(full_session_data)
                    if session_restored:
                        self.current_user = saved_user
                        # Initialize sync manager after authentication
                        self.sync_manager = SyncManager(self.local_db, self.appwrite)
                        self.show_main_app()
                        # Check sync status after login
                        self.check_comprehensive_sync_on_startup()
                    else:
                        # Session invalid, clear and show login
                        self.session_manager.clear_session()
                        self.show_login()
                except Exception as ex:
                    print(f"Error restoring session: {ex}")
                    self.session_manager.clear_session()
                    self.show_login()
            
            import threading
            threading.Thread(target=restore_session, daemon=True).start()
        else:
            # Show login screen
            self.show_login()
    
    def init_ui(self):
        """Initialize UI components"""
        self.page.appbar = ft.AppBar(
            title=ft.Text("VoltTrack"),
            center_title=True,
            bgcolor="#1976d2",
            color="white",
            actions=[
                ft.IconButton(
                    icon="upload",
                    tooltip="Sync to Cloud",
                    on_click=lambda e: self.debug_sync_click("upload"),
                    visible=False
                ),
                ft.IconButton(
                    icon="download",
                    tooltip="Sync from Cloud",
                    on_click=lambda e: self.debug_sync_click("download"),
                    visible=False
                ),
                ft.IconButton(
                    icon="logout",
                    tooltip="Logout",
                    on_click=self.logout_clicked,
                    visible=False
                )
            ]
        )
        
        self.main_container = ft.Container(
            content=ft.Column([]),
            padding=20,
            expand=True
        )
        
        self.page.add(self.main_container)
    
    def debug_sync_click(self, sync_type):
        """Debug method to track sync button clicks"""
        print(f"DEBUG: Sync button clicked - Type: {sync_type}")
        print(f"DEBUG: Current user: {self.current_user}")
        print(f"DEBUG: Page dialog: {getattr(self.page, 'dialog', 'No dialog attribute')}")
        
        # Show a simple test dialog first
        try:
            test_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Test Dialog - {sync_type}"),
                content=ft.Text("This is a test dialog to verify dialog functionality works."),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: self.close_dialog())
                ]
            )
            
            self.page.dialog = test_dialog
            test_dialog.open = True
            self.page.update()
            print(f"DEBUG: Test dialog shown")
            
        except Exception as e:
            print(f"DEBUG: Error showing test dialog: {e}")
            import traceback
            traceback.print_exc()
        
        # Also try the original sync
        try:
            self.start_sync(sync_type)
            print(f"DEBUG: start_sync called successfully")
        except Exception as e:
            print(f"DEBUG: Error in start_sync: {e}")
            import traceback
            traceback.print_exc()
    
    def show_login(self):
        """Show login/register form"""
        self.page.appbar.actions[0].visible = False  # Sync to Cloud button
        self.page.appbar.actions[1].visible = False  # Sync from Cloud button
        self.page.appbar.actions[2].visible = False  # Logout button
        
        self.email_field = ft.TextField(
            label="Email",
            width=300,
            autofocus=True
        )
        
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        self.name_field = ft.TextField(
            label="Full Name",
            width=300,
            visible=False
        )
        
        self.login_button = ft.ElevatedButton(
            "Login",
            on_click=self.login_clicked,
            width=300
        )
        
        self.register_button = ft.TextButton(
            "Don't have an account? Register",
            on_click=self.toggle_register
        )
        
        self.remember_me_checkbox = ft.Checkbox(
            label="Remember me for 30 days",
            value=True
        )
        
        self.status_text = ft.Text("", color="red")
        
        login_form = ft.Column([
            ft.Text("Welcome to VoltTrack", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Track your meter readings efficiently", size=16, color="#757575"),
            ft.Container(height=20),
            self.email_field,
            self.password_field,
            self.name_field,
            ft.Container(height=10),
            self.remember_me_checkbox,
            ft.Container(height=10),
            self.login_button,
            self.register_button,
            self.status_text
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        self.main_container.content = ft.Row([
            ft.Container(expand=True),
            login_form,
            ft.Container(expand=True)
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        self.page.update()
    
    def toggle_register(self, e):
        """Toggle between login and register forms"""
        is_register = self.login_button.text == "Login"
        
        if is_register:
            self.name_field.visible = True
            self.login_button.text = "Register"
            self.register_button.text = "Already have an account? Login"
        else:
            self.name_field.visible = False
            self.login_button.text = "Login"
            self.register_button.text = "Don't have an account? Register"
        
        self.page.update()
    
    def login_clicked(self, e):
        """Handle login/register button click"""
        email = self.email_field.value
        password = self.password_field.value
        name = self.name_field.value
        
        if not email or not password:
            self.status_text.value = "Please fill in all fields"
            self.status_text.color = "red"
            self.page.update()
            return
        
        def login_process():
            try:
                if self.login_button.text == "Register":
                    if not name:
                        self.status_text.value = "Please enter your full name"
                        self.status_text.color = "red"
                        self.page.update()
                        return
                    
                    # Create account using synchronous method
                    user = self.appwrite.create_account(email, password, name)
                    self.status_text.value = "Registration successful! Please login."
                    self.status_text.color = "green"
                    self.toggle_register(None)
                else:
                    # Login using synchronous method
                    result = self.appwrite.login(email, password)
                    session = result['session']
                    self.current_user = result['user']
                    
                    # Initialize sync manager after authentication
                    self.sync_manager = SyncManager(self.local_db, self.appwrite)
                    
                    # Save session if remember me is checked
                    if self.remember_me_checkbox.value:
                        self.session_manager.save_session(self.current_user, session)
                        print(f"DEBUG: Session saved successfully")
                    
                    self.show_main_app()
                    # Check sync status after login
                    self.check_comprehensive_sync_on_startup()
            except Exception as ex:
                self.status_text.value = str(ex)
                self.status_text.color = "red"
                self.page.update()
        
        # Run in thread to avoid blocking UI
        import threading
        threading.Thread(target=login_process, daemon=True).start()
    
    def logout_clicked(self, e):
        """Handle logout"""
        def run_logout():
            try:
                # Use synchronous logout method
                self.appwrite.logout()
                self.current_user = None
                
                # Clear saved session
                self.session_manager.clear_session()
                
                self.show_login()
            except Exception as ex:
                for meter in local_meters:
                    readings = self.local_db.get_readings(meter['$id'])
                    total_local_readings += len(readings)
                
                # Get unsynced changes
                unsynced_changes = self.local_db.get_unsynced_changes()
                unsynced_count = len(unsynced_changes)
                
                print(f"DEBUG: Local data - Meters: {local_meter_count}, Readings: {total_local_readings}, Unsynced: {unsynced_count}")
                
                # Check Appwrite data
                try:
                    server_meters = self.appwrite.get_user_meters()
                    server_meter_count = len(server_meters)
                    
                    total_server_readings = 0
                    for meter in server_meters:
                        try:
                            readings = self.appwrite.get_daily_readings(meter['$id'])
                            total_server_readings += len(readings)
                        except:
                            pass  # Skip if error getting readings
                    
                    print(f"DEBUG: Server data - Meters: {server_meter_count}, Readings: {total_server_readings}")
                    
                    # Determine sync status and show appropriate prompt
                    self.show_sync_status_prompt(local_meter_count, total_local_readings, unsynced_count, 
                                                server_meter_count, total_server_readings)
                    
                except Exception as e:
                    print(f"DEBUG: Error checking server data: {e}")
                    # Show offline prompt
                    if local_meter_count > 0 or unsynced_count > 0:
                        self.show_sync_status_prompt(local_meter_count, total_local_readings, unsynced_count, 0, 0)
                
            except Exception as ex:
                print(f"Error checking sync status: {ex}")
        
        # Run in background thread
        import threading
        threading.Thread(target=check_status, daemon=True).start()
    
    def show_sync_status_prompt(self, local_meters, local_readings, unsynced, server_meters, server_readings):
        """Show sync status prompt based on data comparison"""
        try:
            print(f"DEBUG: Showing sync status prompt - Local: {local_meters}m/{local_readings}r, Server: {server_meters}m/{server_readings}r, Unsynced: {unsynced}")
            
            # Determine the appropriate message and actions
            if unsynced > 0:
                # Has unsynced local changes
                title = "Unsynced Changes Detected"
                message = f"You have {unsynced} unsynced changes in your local database."
                if server_meters > 0 or server_readings > 0:
                    message += f"\n\nLocal: {local_meters} meters, {local_readings} readings"
                    message += f"\nCloud: {server_meters} meters, {server_readings} readings"
                    message += f"\n\nWould you like to sync your changes?"
                else:
                    message += f"\n\nWould you like to upload your data to the cloud?"
                
                actions = [
                    ft.TextButton("Later", on_click=lambda e: self.close_dialog()),
                    ft.ElevatedButton("Sync to Cloud", 
                                    icon="upload",
                                    style=ft.ButtonStyle(bgcolor="green", color="white"),
                                    on_click=lambda e: (self.close_dialog(), self.start_sync("upload"))),
                ]
                
            elif local_meters == 0 and local_readings == 0 and (server_meters > 0 or server_readings > 0):
                # No local data but has server data
                title = "Cloud Data Available"
                message = f"Found data in your cloud storage:\n{server_meters} meters, {server_readings} readings"
                message += f"\n\nWould you like to download your data from the cloud?"
                
                actions = [
                    ft.TextButton("Later", on_click=lambda e: self.close_dialog()),
                    ft.ElevatedButton("Sync from Cloud", 
                                    icon="download",
                                    style=ft.ButtonStyle(bgcolor="blue", color="white"),
                                    on_click=lambda e: (self.close_dialog(), self.start_sync("download"))),
                ]
                
            elif local_meters > 0 and server_meters == 0:
                # Has local data but no server data
                title = "Local Data Only"
                message = f"You have local data that hasn't been backed up:\n{local_meters} meters, {local_readings} readings"
                message += f"\n\nWould you like to back up your data to the cloud?"
                
                actions = [
                    ft.TextButton("Later", on_click=lambda e: self.close_dialog()),
                    ft.ElevatedButton("Backup to Cloud", 
                                    icon="upload",
                                    style=ft.ButtonStyle(bgcolor="orange", color="white"),
                                    on_click=lambda e: (self.close_dialog(), self.start_sync("upload"))),
                ]
                
            elif abs(local_meters - server_meters) > 0 or abs(local_readings - server_readings) > 5:
                # Data mismatch between local and server
                title = "Data Sync Mismatch"
                message = f"Your local and cloud data don't match:\n"
                message += f"Local: {local_meters} meters, {local_readings} readings\n"
                message += f"Cloud: {server_meters} meters, {server_readings} readings\n"
                message += f"\nWould you like to sync your data?"
                
                actions = [
                    ft.TextButton("Later", on_click=lambda e: self.close_dialog()),
                    ft.ElevatedButton("Sync to Cloud", 
                                    icon="upload",
                                    style=ft.ButtonStyle(bgcolor="green", color="white"),
                                    on_click=lambda e: (self.close_dialog(), self.start_sync("upload"))),
                    ft.ElevatedButton("Sync from Cloud", 
                                    icon="download",
                                    style=ft.ButtonStyle(bgcolor="blue", color="white"),
                                    on_click=lambda e: (self.close_dialog(), self.start_sync("download"))),
                ]
            else:
                # Data is in sync, no prompt needed
                print(f"DEBUG: Data appears to be in sync, no prompt needed")
                return
            
            # Show the prompt dialog
            sync_prompt = ft.AlertDialog(
                modal=True,
                title=ft.Text(title),
                content=ft.Text(message, size=14),
                actions=actions
            )
            
            # Delay showing the dialog to avoid conflicts with app initialization
            def show_delayed():
                import time
                time.sleep(2)  # Wait 2 seconds
                self.page.dialog = sync_prompt
                sync_prompt.open = True
                self.page.update()
                print(f"DEBUG: Sync status prompt shown")
            
            import threading
            threading.Thread(target=show_delayed, daemon=True).start()
            
        except Exception as e:
            print(f"Error showing sync status prompt: {e}")
    
    def show_main_app(self):
        """Show main application interface"""
        self.page.appbar.actions[0].visible = True  # Sync to Cloud button
        self.page.appbar.actions[1].visible = True  # Sync from Cloud button
        self.page.appbar.actions[2].visible = True  # Logout button
        self.page.update()  # Ensure buttons are visible
        
        # Load user meters
        self.load_meters()
        
        # Create navigation tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Dashboard", icon="dashboard"),
                ft.Tab(text="Add Reading", icon="add"),
                ft.Tab(text="Manage Meters", icon="electrical_services"),
                ft.Tab(text="History & Analytics", icon="analytics"),
            ],
            on_change=self.tab_changed
        )
        
        self.content_container = ft.Container(
            content=ft.Column([]),
            padding=20,
            expand=True
        )
        
        self.main_container.content = ft.Column([
            self.tabs,
            self.content_container
        ], expand=True)
        
        self.show_dashboard()
        self.page.update()
    
    def tab_changed(self, e):
        """Handle tab change"""
        print(f"DEBUG: Tab changed to index {e.control.selected_index}")
        if e.control.selected_index == 0:
            self.show_dashboard()
        elif e.control.selected_index == 1:
            self.show_add_reading()
        elif e.control.selected_index == 2:
            self.show_manage_meters()
        elif e.control.selected_index == 3:
            self.show_history_analytics()
        self.page.update()
    
    def switch_to_tab(self, index):
        """Switch to a specific tab and update the view"""
        self.tabs.selected_index = index
        self.tab_changed(type('obj', (object,), {'control': type('obj', (object,), {'selected_index': index})})())
    
    def load_meters(self):
        """Load user meters from local database (faster)"""
        try:
            if self.current_user:
                # Clean up any duplicate meters first
                removed_count = self.local_db.remove_duplicate_meters(self.current_user['$id'])
                if removed_count > 0:
                    print(f"DEBUG: Removed {removed_count} duplicate meters")
                
                # Load from local database first (fast)
                self.meters = self.local_db.get_meters(self.current_user['$id'])
                print(f"DEBUG: Loaded {len(self.meters)} meters from local database")
                
                # No automatic sync - user must manually sync if needed
                if not self.meters:
                    print("No local meters found. Use 'Sync from Cloud' to download from server.")
        except Exception as ex:
            print(f"Error loading meters: {ex}")
            self.meters = []
    
    def show_dashboard(self):
        """Show dashboard with comprehensive overview and visuals"""
        if not self.meters:
            self.content_container.content = ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Icon("dashboard", size=64, color="#42a5f5"),
                        ft.Text("Welcome to VoltTrack!", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text("Your Smart Meter Reading Tracker", size=16, color="#757575", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Text("Get started by adding your first meter", size=14, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=10),
                        ft.ElevatedButton(
                            "Add Your First Meter",
                            icon="add_circle",
                            style=ft.ButtonStyle(
                                bgcolor="#1976d2",
                                color="white",
                                padding=ft.padding.symmetric(horizontal=30, vertical=15)
                            ),
                            on_click=lambda _: self.switch_to_tab(2)
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                    alignment=ft.alignment.center
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            # Calculate dashboard statistics
            total_meters = len(self.meters)
            total_readings = 0
            total_consumption = 0
            latest_readings = []
            monthly_consumption = 0
            
            # Get current month data
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            for meter in self.meters:
                # Get all readings for this meter
                all_readings = self.local_db.get_readings(meter['$id'])
                total_readings += len(all_readings)
                
                # Calculate total consumption
                meter_consumption = sum(r['consumption_kwh'] for r in all_readings)
                total_consumption += meter_consumption
                
                # Get current month consumption
                month_readings = self.local_db.get_readings(meter['$id'], current_year, current_month)
                monthly_consumption += sum(r['consumption_kwh'] for r in month_readings)
                
                # Get latest reading for each meter
                if all_readings:
                    latest_reading = all_readings[0]  # Already sorted by date desc
                    latest_readings.append({
                        'meter': meter,
                        'reading': latest_reading,
                        'consumption': meter_consumption
                    })
            
            # Create summary cards
            summary_cards = [
                self.create_dashboard_card("Total Meters", str(total_meters), "electrical_services", "blue"),
                self.create_dashboard_card("Total Readings", str(total_readings), "analytics", "green"),
                self.create_dashboard_card("Total Consumption", f"{total_consumption:.1f} units", "bolt", "orange"),
                self.create_dashboard_card("This Month", f"{monthly_consumption:.1f} units", "calendar_month", "purple")
            ]
            
            # Create meter overview cards
            meter_cards = []
            for item in latest_readings[:4]:  # Show max 4 meters
                meter = item['meter']
                reading = item['reading']
                consumption = item['consumption']
                
                # Calculate days since last reading
                last_date = datetime.fromisoformat(reading['reading_date'])
                days_ago = (datetime.now().date() - last_date.date()).days
                
                status_color = "green" if days_ago <= 7 else "orange" if days_ago <= 30 else "red"
                status_text = "Recent" if days_ago <= 7 else f"{days_ago} days ago"
                
                meter_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon("home", size=20, color="#42a5f5"),
                                ft.Text(meter['home_name'][:15] + ('...' if len(meter['home_name']) > 15 else ''), 
                                        weight=ft.FontWeight.BOLD, size=14)
                            ]),
                            ft.Text(meter['meter_name'][:20] + ('...' if len(meter['meter_name']) > 20 else ''), 
                                   size=12, color="#757575"),
                            ft.Divider(height=1),
                            ft.Row([
                                ft.Text("Latest:", size=10, color="#757575"),
                                ft.Text(f"{reading['reading_value']:.0f}", size=12, weight=ft.FontWeight.BOLD)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Text("Total:", size=10, color="#757575"),
                                ft.Text(f"{consumption:.1f} units", size=12, weight=ft.FontWeight.BOLD, color="green")
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Text("Status:", size=10, color="#757575"),
                                ft.Text(status_text, size=10, color=status_color)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ], spacing=5),
                        padding=15,
                        width=250
                    ),
                    elevation=2
                )
                meter_cards.append(meter_card)
            
            # Quick actions
            quick_actions = ft.Row([
                ft.ElevatedButton(
                    "Add Reading",
                    icon="add",
                    style=ft.ButtonStyle(bgcolor="#43a047", color="white"),
                    on_click=lambda _: self.switch_to_tab(1)
                ),
                ft.ElevatedButton(
                    "View Analytics",
                    icon="analytics",
                    style=ft.ButtonStyle(bgcolor="#1976d2", color="white"),
                    on_click=lambda _: self.switch_to_tab(3)
                )
            ], spacing=10)
            
            self.content_container.content = ft.Column([
                # Header
                ft.Row([
                    ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Text(f"Last updated: {datetime.now().strftime('%H:%M')}", size=12, color="#757575")
                ]),
                ft.Container(height=20),
                
                # Summary cards
                ft.Text("Overview", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Row(summary_cards, wrap=True, spacing=15),
                ft.Container(height=30),
                
                # Meter cards
                ft.Text("Your Meters", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Row(meter_cards, wrap=True, spacing=10) if meter_cards else ft.Text("No meter data available", color="#757575"),
                ft.Container(height=20),
                
                # Quick actions
                ft.Text("Quick Actions", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                quick_actions
            ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def create_dashboard_card(self, title, value, icon, color):
        """Create a dashboard summary card"""
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=40, color=color),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(value, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(title, size=12, color="#757575")
                    ], spacing=2)
                ], alignment=ft.MainAxisAlignment.START),
                padding=20,
                width=200
            ),
            elevation=2
        )
    
    def show_add_reading(self):
        """Show add reading form"""
        if not self.meters:
            self.content_container.content = ft.Column([
                ft.Text("No meters available", size=18),
                ft.Text("Please add a meter first in the Manage Meters tab."),
                ft.ElevatedButton("Go to Manage Meters", on_click=lambda _: self.switch_to_tab(2))
            ])
            self.page.update()
            return
        
        self.meter_dropdown = ft.Dropdown(
            label="Select Meter",
            options=[
                ft.dropdown.Option(key=meter['$id'], text=f"{meter['home_name']} - {meter['meter_name']}")
                for meter in self.meters
            ],
            width=300
        )
        
        self.reading_field = ft.TextField(
            label="Meter Reading",
            hint_text="Enter current meter reading",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.date_field = ft.TextField(
            label="Reading Date",
            value=datetime.now().strftime('%Y-%m-%d'),
            width=300
        )
        
        self.time_field = ft.TextField(
            label="Reading Time",
            hint_text="HH:MM:SS (24-hour format)",
            value=datetime.now().strftime('%H:%M:%S'),
            width=300
        )
        
        self.submit_button = ft.ElevatedButton(
            "Add Reading",
            icon="save",
            on_click=self.submit_reading
        )
        
        self.status_text = ft.Text("")
        
        self.content_container.content = ft.Column([
            ft.Text("Add New Meter Reading", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            self.meter_dropdown,
            self.reading_field,
            self.date_field,
            self.time_field,
            ft.Container(height=20),
            self.submit_button,
            self.status_text
        ])
        
        self.page.update()
    
    def submit_reading(self, e):
        """Submit new meter reading"""
        if not self.meter_dropdown.value or not self.reading_field.value:
            self.status_text.value = "Please select a meter and enter a reading"
            self.status_text.color = "red"
            self.page.update()
            return
        
        def run_submit():
            try:
                reading_value = float(self.reading_field.value)
                reading_date = datetime.strptime(self.date_field.value, '%Y-%m-%d').date()
                reading_time = self.time_field.value if self.time_field.value else datetime.now().strftime('%H:%M:%S')
                
                # Validate time format
                try:
                    datetime.strptime(reading_time, '%H:%M:%S')
                except ValueError:
                    self.status_text.value = "Please enter time in HH:MM:SS format (e.g., 14:30:00)"
                    self.status_text.color = "red"
                    self.page.update()
                    return
                
                # Add to local database (fast)
                reading_data = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.current_user['$id'],
                    'meter_id': self.meter_dropdown.value,
                    'reading_value': reading_value,
                    'reading_date': reading_date.isoformat(),
                    'reading_time': reading_time,
                    'created_at': datetime.now().isoformat()
                }
                
                reading_id = self.local_db.add_reading(reading_data)
                print(f"DEBUG: Added reading {reading_id} to local database")
                
                self.status_text.value = "Reading added successfully! (Use 'Sync with Cloud' to upload to Appwrite)"
                self.status_text.color = "green"
                self.reading_field.value = ""
                self.page.update()
                
            except ValueError:
                self.status_text.value = "Please enter a valid number for the reading"
                self.status_text.color = "red"
                self.page.update()
            except Exception as ex:
                self.status_text.value = f"Error adding reading: {ex}"
                self.status_text.color = "red"
                self.page.update()
        
        import threading
        threading.Thread(target=run_submit, daemon=True).start()
    
    def show_manage_meters(self):
        """Show meter management interface"""
        self.home_name_field = ft.TextField(
            label="Home Name",
            hint_text="e.g., Main House, Guest House",
            width=300
        )
        
        self.meter_name_field = ft.TextField(
            label="Meter Name",
            hint_text="e.g., Main Meter, Kitchen Meter",
            width=300
        )
        
        self.meter_type_dropdown = ft.Dropdown(
            label="Meter Type",
            options=[
                ft.dropdown.Option("electricity", "Electricity"),
                ft.dropdown.Option("water", "Water"),
                ft.dropdown.Option("gas", "Gas")
            ],
            value="electricity",
            width=300
        )
        
        self.add_meter_button = ft.ElevatedButton(
            "Add Meter",
            icon="add",
            on_click=self.add_meter
        )
        
        self.meter_status_text = ft.Text("")
        
        # Create meters list
        meters_list = []
        for meter in self.meters:
            meter_tile = ft.ListTile(
                leading=ft.Icon("electrical_services"),
                title=ft.Text(f"{meter['home_name']} - {meter['meter_name']}"),
                subtitle=ft.Text(f"Type: {meter.get('meter_type_fixed', meter.get('meter_type', 'electricity')).title()}"),
            )
            meters_list.append(meter_tile)
        
        self.content_container.content = ft.Column([
            ft.Text("Manage Meters", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            ft.Text("Add New Meter", size=18),
            self.home_name_field,
            self.meter_name_field,
            self.meter_type_dropdown,
            ft.Container(height=10),
            self.add_meter_button,
            self.meter_status_text,
            ft.Container(height=30),
            ft.Text("Your Meters", size=18),
            ft.Column(meters_list) if meters_list else ft.Text("No meters added yet", color="#757575")
        ])
        
        self.page.update()
    
    def add_meter(self, e):
        """Add new meter"""
        home_name = self.home_name_field.value
        meter_name = self.meter_name_field.value
        meter_type = self.meter_type_dropdown.value
        
        if not home_name or not meter_name:
            self.meter_status_text.value = "Please fill in all fields"
            self.meter_status_text.color = "red"
            self.page.update()
            return
        
        def run_add():
            try:
                # Add to local database (fast)
                meter_data = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.current_user['$id'],
                    'home_name': home_name,
                    'meter_name': meter_name,
                    'meter_type': meter_type,
                    'created_at': datetime.now().isoformat()
                }
                
                meter_id = self.local_db.add_meter(meter_data)
                
                self.meter_status_text.value = "Meter added successfully! (Use 'Sync with Cloud' to upload to Appwrite)"
                self.meter_status_text.color = "green"
                
                # Clear form
                self.home_name_field.value = ""
                self.meter_name_field.value = ""
                self.meter_type_dropdown.value = "electricity"
                
                # Reload meters and refresh display
                self.load_meters()
                self.page.update()
                self.show_manage_meters()
                
            except Exception as ex:
                self.meter_status_text.value = f"Error adding meter: {ex}"
                self.meter_status_text.color = "red"
                self.page.update()
        
        import threading
        threading.Thread(target=run_add, daemon=True).start()
    
    def show_history_analytics(self):
        """Show comprehensive history and analytics"""
        if not self.meters:
            self.content_container.content = ft.Column([
                ft.Text("No meters available", size=18),
                ft.Text("Please add a meter first in the Manage Meters tab.")
            ])
            self.page.update()
            return
        
        # Meter selection with text wrapping for long names
        meter_options = []
        for meter in self.meters:
            home_name = meter['home_name']
            meter_name = meter['meter_name']
            
            # Truncate long names for display
            display_home = home_name[:15] + '...' if len(home_name) > 15 else home_name
            display_meter = meter_name[:20] + '...' if len(meter_name) > 20 else meter_name
            
            meter_options.append(ft.dropdown.Option(
                key=meter['$id'], 
                text=f"{display_home} - {display_meter}"
            ))
        
        self.history_meter_dropdown = ft.Dropdown(
            label="Select Meter",
            options=meter_options,
            width=350,
            content_padding=ft.padding.all(10),
            on_change=self.load_history_data
        )
        
        # View type selection
        self.view_type_dropdown = ft.Dropdown(
            label="View Type",
            options=[
                ft.dropdown.Option("readings_table", "All Readings (Editable)"),
                ft.dropdown.Option("daily_consumption", "Daily Consumption"),
                ft.dropdown.Option("daily", "Daily Readings"),
                ft.dropdown.Option("monthly", "Monthly Summary"),
                ft.dropdown.Option("yearly", "Yearly Summary"),
                ft.dropdown.Option("consumption", "Consumption Analysis")
            ],
            value="readings_table",
            width=220,
            on_change=self.load_history_data
        )
        
        # Year selection
        current_year = datetime.now().year
        self.year_dropdown = ft.Dropdown(
            label="Year",
            options=[
                ft.dropdown.Option(str(year), str(year))
                for year in range(2020, current_year + 2)
            ],
            value=str(current_year),
            width=120,
            on_change=self.load_history_data
        )
        
        # Month selection (for daily view)
        self.month_dropdown = ft.Dropdown(
            label="Month",
            options=[
                ft.dropdown.Option(str(i), datetime(2000, i, 1).strftime('%B'))
                for i in range(1, 13)
            ],
            value=str(datetime.now().month),
            width=120,
            visible=False,
            on_change=self.load_history_data
        )
        
        # Data display container
        self.history_data_container = ft.Container(
            content=ft.Text("Select a meter and view type to see history", size=16),
            padding=20,
            border=ft.border.all(1, "#e0e0e0"),
            border_radius=10,
            expand=True
        )
        
        # Statistics container
        self.stats_container = ft.Container(
            content=ft.Row([]),
            padding=10
        )
        
        self.content_container.content = ft.Column([
            ft.Text("History & Analytics", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            ft.Row([
                self.history_meter_dropdown,
                self.view_type_dropdown,
                self.year_dropdown,
                self.month_dropdown
            ]),
            ft.Container(height=20),
            self.stats_container,
            ft.Container(height=10),
            self.history_data_container
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.page.update()
    
    def load_history_data(self, e=None):
        """Load and display history data based on selections (using local database)"""
        if not hasattr(self, 'history_meter_dropdown') or not self.history_meter_dropdown.value:
            return
        
        meter_id = self.history_meter_dropdown.value
        view_type = self.view_type_dropdown.value
        year = int(self.year_dropdown.value)
        
        # Show/hide month dropdown based on view type
        self.month_dropdown.visible = (view_type == "daily")
        self.page.update()
        
        try:
            if view_type == "readings_table":
                # Get all readings for the selected meter and year from local database
                all_readings = self.local_db.get_readings(meter_id, year)
                print(f"DEBUG: Found {len(all_readings)} readings for meter {meter_id}, year {year}")
                if all_readings:
                    print(f"DEBUG: First reading: {all_readings[0]}")
                self.display_readings_table(all_readings, year)
                
            elif view_type == "daily_consumption":
                # Get daily consumption data (first to last reading of each day)
                daily_consumption = self.local_db.get_daily_consumption(meter_id, year)
                self.display_daily_consumption_data(daily_consumption, year)
                
            elif view_type == "daily":
                month = int(self.month_dropdown.value)
                readings = self.local_db.get_readings(meter_id, year, month)
                self.display_daily_data(readings, year, month)
                
            elif view_type == "monthly":
                # Calculate monthly summaries from local data
                summaries = []
                for m in range(1, 13):
                    monthly_readings = self.local_db.get_readings(meter_id, year, m)
                    total_consumption = sum(r['consumption_fixed'] for r in monthly_readings)
                    summaries.append({
                        'month': m,
                        'year': year,
                        'total_consumption': total_consumption,
                        'reading_count': len(monthly_readings)
                    })
                self.display_monthly_data(summaries, year)
                
            elif view_type == "yearly":
                yearly_data = []
                for y in range(2020, year + 1):
                    year_readings = self.local_db.get_readings(meter_id, y)
                    total_consumption = sum(r['consumption_fixed'] for r in year_readings)
                    yearly_data.append({'year': y, 'total_consumption': total_consumption})
                self.display_yearly_data(yearly_data)
                
            elif view_type == "consumption":
                # Get consumption analysis from local data
                consumption_data = []
                for m in range(1, 13):
                    monthly_readings = self.local_db.get_readings(meter_id, year, m)
                    monthly_consumption = sum(r['consumption_fixed'] for r in monthly_readings)
                    consumption_data.append({
                        'month': datetime(year, m, 1).strftime('%B'),
                        'consumption': monthly_consumption,
                        'readings_count': len(monthly_readings)
                    })
                self.display_consumption_analysis(consumption_data, year)
                
        except Exception as ex:
            self.history_data_container.content = ft.Text(f"Error loading data: {ex}", color="red")
            self.page.update()
    
    def display_daily_data(self, readings, year, month):
        """Display daily readings data"""
        if not readings:
            self.history_data_container.content = ft.Text("No readings found for this period")
            self.stats_container.content = ft.Row([])
        else:
            # Create statistics cards
            total_consumption = sum(r['consumption_fixed'] for r in readings)
            avg_consumption = total_consumption / len(readings) if readings else 0
            max_reading = max(r['reading_value'] for r in readings)
            min_reading = min(r['reading_value'] for r in readings)
            
            stats_cards = [
                self.create_stat_card("Total Consumption", f"{total_consumption:.2f} kWh", "blue"),
                self.create_stat_card("Average Daily", f"{avg_consumption:.2f} kWh", "green"),
                self.create_stat_card("Highest Reading", f"{max_reading:.2f}", "orange"),
                self.create_stat_card("Lowest Reading", f"{min_reading:.2f}", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create data table
            data_rows = []
            for reading in sorted(readings, key=lambda x: x['reading_date'], reverse=True):
                date = datetime.fromisoformat(reading['reading_date']).strftime('%Y-%m-%d')
                data_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(date)),
                        ft.DataCell(ft.Text(f"{reading['reading_value']:.2f}")),
                        ft.DataCell(ft.Text(f"{reading['consumption_fixed']:.2f}")),
                    ])
                )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Reading", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Consumption (kWh)", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows[:31]  # Limit to 31 days
            )
            
            month_name = datetime(year, month, 1).strftime('%B %Y')
            self.history_data_container.content = ft.Column([
                ft.Text(f"Daily readings for {month_name}", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
                    border=ft.border.all(1, "#e0e0e0"),
                    border_radius=5,
                    expand=True
                )
            ], expand=True)
        
        self.page.update()
    
    def display_daily_consumption_data(self, daily_consumption, year):
        """Display daily consumption data (first to last reading of each day)"""
        if not daily_consumption:
            self.history_data_container.content = ft.Text("No daily consumption data found for this year")
            self.stats_container.content = ft.Row([])
        else:
            # Filter out days with no consumption
            active_days = [d for d in daily_consumption if d['daily_consumption'] > 0]
            
            # Create statistics
            total_consumption = sum(d['daily_consumption'] for d in active_days)
            avg_consumption = total_consumption / len(active_days) if active_days else 0
            max_day = max(active_days, key=lambda x: x['daily_consumption']) if active_days else None
            total_days = len(daily_consumption)
            active_days_count = len(active_days)
            
            stats_cards = [
                self.create_stat_card("Total Consumption", f"{total_consumption:.2f} kWh", "blue"),
                self.create_stat_card("Average Daily", f"{avg_consumption:.2f} kWh", "green"),
                self.create_stat_card("Peak Day", f"{max_day['daily_consumption']:.2f} kWh" if max_day else "0 kWh", "orange"),
                self.create_stat_card("Active Days", f"{active_days_count}/{total_days}", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create data table
            data_rows = []
            for day_data in daily_consumption:
                date = datetime.fromisoformat(day_data['date']).strftime('%Y-%m-%d')
                
                # Format time range
                time_range = f"{day_data['first_time']} - {day_data['last_time']}" if day_data['reading_count'] > 1 else day_data['first_time']
                
                data_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(date)),
                        ft.DataCell(ft.Text(time_range)),
                        ft.DataCell(ft.Text(f"{day_data['first_reading']:.2f}")),
                        ft.DataCell(ft.Text(f"{day_data['last_reading']:.2f}")),
                        ft.DataCell(ft.Text(f"{day_data['daily_consumption']:.2f}")),
                        ft.DataCell(ft.Text(str(day_data['reading_count']))),
                    ])
                )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Time Range", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("First Reading", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Last Reading", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Daily Consumption", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Readings", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows
            )
            
            self.history_data_container.content = ft.Column([
                ft.Text(f"Daily consumption for {year}", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Shows consumption from first to last reading of each day", size=12, color="#757575"),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
                    border=ft.border.all(1, "#e0e0e0"),
                    border_radius=5,
                    expand=True
                )
            ], expand=True)
        
        self.page.update()
    
    def display_monthly_data(self, summaries, year):
        """Display monthly summary data"""
        active_summaries = [s for s in summaries if s['reading_count'] > 0]
        
        if not active_summaries:
            self.history_data_container.content = ft.Text("No readings found for this year")
            self.stats_container.content = ft.Row([])
        else:
            # Create statistics
            total_yearly = sum(s['total_consumption'] for s in active_summaries)
            avg_monthly = total_yearly / len(active_summaries) if active_summaries else 0
            max_month = max(active_summaries, key=lambda x: x['total_consumption'])
            min_month = min(active_summaries, key=lambda x: x['total_consumption'])
            
            stats_cards = [
                self.create_stat_card("Total Year", f"{total_yearly:.2f} units", "blue"),
                self.create_stat_card("Average Monthly", f"{avg_monthly:.2f} units", "green"),
                self.create_stat_card("Highest Month", f"{datetime(year, max_month['month'], 1).strftime('%B')}: {max_month['total_consumption']:.2f}", "orange"),
                self.create_stat_card("Active Months", f"{len(active_summaries)}/12", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create data table
            data_rows = []
            for summary in active_summaries:
                month_name = datetime(year, summary['month'], 1).strftime('%B')
                data_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(month_name)),
                        ft.DataCell(ft.Text(f"{summary['total_consumption']:.2f}")),
                        ft.DataCell(ft.Text(str(summary['reading_count']))),
                    ])
                )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Month", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Total Consumption", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Readings Count", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows
            )
            
            self.history_data_container.content = ft.Column([
                ft.Text(f"Monthly summary for {year}", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                data_table
            ])
        
        self.page.update()
    
    def display_yearly_data(self, yearly_data):
        """Display yearly comparison data"""
        active_years = [y for y in yearly_data if y['total_consumption'] > 0]
        
        if not active_years:
            self.history_data_container.content = ft.Text("No data found")
            self.stats_container.content = ft.Row([])
        else:
            # Create statistics
            total_all_years = sum(y['total_consumption'] for y in active_years)
            avg_yearly = total_all_years / len(active_years) if active_years else 0
            max_year = max(active_years, key=lambda x: x['total_consumption'])
            min_year = min(active_years, key=lambda x: x['total_consumption'])
            
            stats_cards = [
                self.create_stat_card("Total All Years", f"{total_all_years:.2f} units", "blue"),
                self.create_stat_card("Average Yearly", f"{avg_yearly:.2f} units", "green"),
                self.create_stat_card("Highest Year", f"{max_year['year']}: {max_year['total_consumption']:.2f}", "orange"),
                self.create_stat_card("Lowest Year", f"{min_year['year']}: {min_year['total_consumption']:.2f}", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create data table
            data_rows = []
            for year_data in sorted(active_years, key=lambda x: x['year'], reverse=True):
                data_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(year_data['year']))),
                        ft.DataCell(ft.Text(f"{year_data['total_consumption']:.2f}")),
                    ])
                )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Year", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Total Consumption", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows
            )
            
            self.history_data_container.content = ft.Column([
                ft.Text("Yearly consumption comparison", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                data_table
            ])
        
        self.page.update()
    
    def display_consumption_analysis(self, consumption_data, year):
        """Display consumption analysis"""
        active_months = [m for m in consumption_data if m['consumption'] > 0]
        
        if not active_months:
            self.history_data_container.content = ft.Text("No consumption data found")
            self.stats_container.content = ft.Row([])
        else:
            # Create statistics
            total_consumption = sum(m['consumption'] for m in active_months)
            avg_consumption = total_consumption / len(active_months) if active_months else 0
            max_month = max(active_months, key=lambda x: x['consumption'])
            min_month = min(active_months, key=lambda x: x['consumption'])
            
            stats_cards = [
                self.create_stat_card("Total Consumption", f"{total_consumption:.2f} units", "blue"),
                self.create_stat_card("Average Monthly", f"{avg_consumption:.2f} units", "green"),
                self.create_stat_card("Peak Month", f"{max_month['month']}: {max_month['consumption']:.2f}", "orange"),
                self.create_stat_card("Low Month", f"{min_month['month']}: {min_month['consumption']:.2f}", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create data table with trend analysis
            data_rows = []
            for i, month_data in enumerate(consumption_data):
                if month_data['consumption'] > 0:
                    # Calculate trend (simple comparison with previous month)
                    trend = "→"
                    if i > 0 and consumption_data[i-1]['consumption'] > 0:
                        if month_data['consumption'] > consumption_data[i-1]['consumption']:
                            trend = "↗"
                        elif month_data['consumption'] < consumption_data[i-1]['consumption']:
                            trend = "↘"
                    
                    data_rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(month_data['month'])),
                            ft.DataCell(ft.Text(f"{month_data['consumption']:.2f}")),
                            ft.DataCell(ft.Text(str(month_data['readings_count']))),
                            ft.DataCell(ft.Text(trend)),
                        ])
                    )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Month", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Consumption", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Readings", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Trend", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows
            )
            
            self.history_data_container.content = ft.Column([
                ft.Text(f"Consumption analysis for {year}", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                data_table
            ])
        
        self.page.update()
    
    def display_readings_table(self, readings, year):
        """Display all readings in an editable table format"""
        if not readings:
            self.history_data_container.content = ft.Text("No readings found for this year")
            self.stats_container.content = ft.Row([])
        else:
            # Sort readings by date (newest first)
            sorted_readings = sorted(readings, key=lambda x: x['reading_date'], reverse=True)
            
            # Create statistics
            total_consumption = sum(r['consumption_fixed'] for r in readings)
            avg_consumption = total_consumption / len(readings) if readings else 0
            max_reading = max(r['reading_value'] for r in readings)
            min_reading = min(r['reading_value'] for r in readings)
            
            stats_cards = [
                self.create_stat_card("Total Readings", str(len(readings)), "blue"),
                self.create_stat_card("Total Consumption", f"{total_consumption:.2f} kWh", "green"),
                self.create_stat_card("Average Consumption", f"{avg_consumption:.2f} kWh", "orange"),
                self.create_stat_card("Reading Range", f"{min_reading:.0f} - {max_reading:.0f}", "purple")
            ]
            
            self.stats_container.content = ft.Row(stats_cards, wrap=True, spacing=10)
            
            # Create editable data table
            data_rows = []
            for i, reading in enumerate(sorted_readings):
                date = datetime.fromisoformat(reading['reading_date']).strftime('%Y-%m-%d')
                time = reading.get('reading_time', '12:00:00')
                
                # Store reading data with unique key
                reading_key = f"reading_{i}_{reading['$id']}"
                setattr(self, reading_key, reading)
                
                # Create action buttons for each row with unique handlers
                edit_button = ft.IconButton(
                    "edit",
                    tooltip="Edit Reading",
                    data=reading_key,
                    on_click=self.handle_edit_click
                )
                
                delete_button = ft.IconButton(
                    "delete",
                    tooltip="Delete Reading",
                    data=reading_key,
                    on_click=self.handle_delete_click
                )
                
                data_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(date)),
                        ft.DataCell(ft.Text(time)),
                        ft.DataCell(ft.Text(f"{reading['reading_value']:.2f}")),
                        ft.DataCell(ft.Text(f"{reading['consumption_fixed']:.2f}")),
                        ft.DataCell(ft.Row([edit_button, delete_button], spacing=5)),
                    ])
                )
            
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Time", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Reading Value", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Consumption (kWh)", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
                ],
                rows=data_rows
            )
            
            # Add button to add new reading
            add_reading_button = ft.ElevatedButton(
                "Add New Reading",
                icon="add",
                on_click=lambda _: self.switch_to_tab(1)  # Switch to Add Reading tab
            )
            
            self.history_data_container.content = ft.Column([
                ft.Row([
                    ft.Text(f"All Readings for {year}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    add_reading_button
                ]),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
                    border=ft.border.all(1, "#e0e0e0"),
                    border_radius=5,
                    expand=True
                )
            ], expand=True)
        
        self.page.update()
    
    def handle_edit_click(self, e):
        """Handle edit button click"""
        reading_key = e.control.data
        reading = getattr(self, reading_key, None)
        if reading:
            print(f"DEBUG: Edit button clicked for reading: {reading['$id']}")
            # Use the working dialog approach
            self.show_working_edit_dialog(reading)
        else:
            print(f"DEBUG: Could not find reading data for key: {reading_key}")
    
    
    def show_working_edit_dialog(self, reading):
        """Show a working edit dialog"""
        print(f"DEBUG: *** SHOWING WORKING EDIT DIALOG *** for reading: {reading['$id']}")
        
        try:
            # Create form fields
            print(f"DEBUG: Creating date field...")
            date_field = ft.TextField(
                label="Date",
                value=datetime.fromisoformat(reading['reading_date']).strftime('%Y-%m-%d'),
                width=200
            )
            print(f"DEBUG: Date field created successfully")
        except Exception as e:
            print(f"DEBUG: Error creating date field: {e}")
            date_field = ft.TextField(label="Date", value="2025-10-14", width=200)
        
        time_field = ft.TextField(
            label="Reading Time",
            value=reading.get('reading_time', '12:00:00'),
            width=200,
            hint_text="HH:MM:SS"
        )
        
        reading_field = ft.TextField(
            label="Reading Value",
            value=str(reading['reading_value']),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        def save_changes(e):
            try:
                new_date = datetime.strptime(date_field.value, '%Y-%m-%d').date()
                new_reading = float(reading_field.value)
                new_time = time_field.value if time_field.value else '12:00:00'
                
                # Validate time format
                try:
                    datetime.strptime(new_time, '%H:%M:%S')
                except ValueError:
                    self.show_snackbar("Please enter time in HH:MM:SS format", "red")
                    return
                
                # Update reading in local database
                def update_reading():
                    try:
                        success = self.local_db.update_reading(
                            reading['$id'], new_reading, new_date.isoformat(), new_time
                        )
                        
                        if success:
                            self.show_snackbar("Reading updated successfully!", "green")
                            self.load_history_data()
                        else:
                            self.show_snackbar("Error updating reading", "red")
                            
                    except Exception as ex:
                        self.show_snackbar(f"Error updating reading: {ex}", "red")
                
                import threading
                threading.Thread(target=update_reading, daemon=True).start()
                
                # Close dialog
                if hasattr(self, 'edit_dialog'):
                    self.edit_dialog.open = False
                    self.page.update()
                
            except ValueError:
                self.show_snackbar("Please enter valid values", "red")
        
        def cancel_edit(e):
            if hasattr(self, 'edit_dialog'):
                self.edit_dialog.open = False
                self.page.update()
        
        # Create dialog
        print(f"DEBUG: Creating edit dialog with form fields...")
        self.edit_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Reading - WORKING VERSION"),
            content=ft.Column([
                date_field,
                time_field,
                reading_field,
            ], height=200, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_edit),
                ft.ElevatedButton("Save Changes", on_click=save_changes),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        try:
            # Clear any existing dialog (including sync prompts)
            if self.page.dialog:
                print(f"DEBUG: Found existing dialog, closing it")
                self.page.dialog.open = False
                self.page.dialog = None
                self.page.update()
                import time
                time.sleep(0.2)
            
            # Set and show dialog
            self.page.dialog = self.edit_dialog
            self.edit_dialog.open = True
            self.page.update()
            
            # Also try overlay approach as backup
            if hasattr(self.page, 'overlay'):
                self.page.overlay.append(self.edit_dialog)
                self.page.update()
            
            print(f"DEBUG: Edit dialog should now be visible")
            
        except Exception as e:
            print(f"DEBUG: Error showing edit dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_delete_click(self, e):
        """Handle delete button click"""
        reading_key = e.control.data
        reading = getattr(self, reading_key, None)
        if reading:
            print(f"DEBUG: Delete button clicked for reading: {reading['$id']}")
            self.delete_reading_dialog(reading)
        else:
            print(f"DEBUG: Could not find reading data for key: {reading_key}")
    
    def edit_reading_dialog(self, reading):
        """Show dialog to edit a reading"""
        print(f"DEBUG: Edit reading dialog called for reading: {reading['$id']}")
        print(f"DEBUG: Reading data: {reading}")
        
        try:
            # Create dialog fields
            date_field = ft.TextField(
                label="Date",
                value=datetime.fromisoformat(reading['reading_date']).strftime('%Y-%m-%d'),
                width=200
            )
            print(f"DEBUG: Date field created successfully")
        except Exception as e:
            print(f"DEBUG: Error creating date field: {e}")
            # Fallback date field
            date_field = ft.TextField(
                label="Date",
                value="2025-10-14",
                width=200
            )
        
        reading_field = ft.TextField(
            label="Reading Value",
            value=str(reading['reading_value']),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        time_field = ft.TextField(
            label="Reading Time",
            value=reading.get('reading_time', '12:00:00'),
            width=200,
            hint_text="HH:MM:SS"
        )
        
        def save_changes(e):
            try:
                new_date = datetime.strptime(date_field.value, '%Y-%m-%d').date()
                new_reading = float(reading_field.value)
                new_time = time_field.value if time_field.value else '12:00:00'
                
                # Validate time format
                try:
                    datetime.strptime(new_time, '%H:%M:%S')
                except ValueError:
                    self.show_snackbar("Please enter time in HH:MM:SS format", "red")
                    return
                
                # Update reading in local database
                def update_reading():
                    try:
                        # Update in local database (fast)
                        success = self.local_db.update_reading(
                            reading['$id'], new_reading, new_date.isoformat(), new_time
                        )
                        
                        if success:
                            self.show_snackbar(f"Reading updated successfully! (Use 'Sync with Cloud' to upload to Appwrite)", "green")
                            # Refresh the data
                            self.load_history_data()
                        else:
                            self.show_snackbar(f"Error updating reading", "red")
                            
                    except Exception as ex:
                        self.show_snackbar(f"Error updating reading: {ex}", "red")
                
                import threading
                threading.Thread(target=update_reading, daemon=True).start()
                
                # Close dialog
                edit_dialog.open = False
                self.page.update()
                
            except ValueError:
                self.show_snackbar("Please enter valid values", "red")
        
        def cancel_edit(e):
            edit_dialog.open = False
            self.page.update()
        
        try:
            # Close any existing dialog first
            if hasattr(self.page, 'dialog') and self.page.dialog:
                print(f"DEBUG: Closing existing dialog before opening edit dialog")
                self.page.dialog.open = False
                self.page.dialog = None
                self.page.update()
            
            print(f"DEBUG: Creating edit dialog...")
            edit_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Edit Reading"),
                content=ft.Column([
                    date_field,
                    time_field,
                    reading_field,
                ], height=200, spacing=10),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_edit),
                    ft.ElevatedButton("Save Changes", on_click=save_changes),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            print(f"DEBUG: Edit dialog created successfully")
            
            print(f"DEBUG: Setting page dialog...")
            self.page.dialog = edit_dialog
            edit_dialog.open = True
            print(f"DEBUG: Dialog opened, updating page...")
            self.page.update()
            print(f"DEBUG: Page updated successfully")
            
        except Exception as e:
            print(f"DEBUG: Error creating or showing edit dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def delete_reading_dialog(self, reading):
        """Show confirmation dialog to delete a reading"""
        print(f"DEBUG: Delete reading dialog called for reading: {reading['$id']}")
        def confirm_delete(e):
            # Delete reading from local database
            def delete_reading():
                try:
                    # Delete from local database (fast)
                    success = self.local_db.delete_reading(reading['$id'])
                    
                    if success:
                        self.show_snackbar(f"Reading deleted successfully! (Use 'Sync with Cloud' to upload to Appwrite)", "green")
                        # Refresh the data
                        self.load_history_data()
                    else:
                        self.show_snackbar(f"Error deleting reading", "red")
                        
                except Exception as ex:
                    self.show_snackbar(f"Error deleting reading: {ex}", "red")
            
            import threading
            threading.Thread(target=delete_reading, daemon=True).start()
            
            # Close dialog
            delete_dialog.open = False
            self.page.update()
        
        def cancel_delete(e):
            delete_dialog.open = False
            self.page.update()
        
        # Close any existing dialog first
        if hasattr(self.page, 'dialog') and self.page.dialog:
            print(f"DEBUG: Closing existing dialog before opening delete dialog")
            self.page.dialog.open = False
            self.page.dialog = None
            self.page.update()
        
        reading_date = datetime.fromisoformat(reading['reading_date']).strftime('%Y-%m-%d')
        
        delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Reading"),
            content=ft.Text(f"Are you sure you want to delete the reading from {reading_date}?\n\nReading Value: {reading['reading_value']:.2f}\nConsumption: {reading['consumption_fixed']:.2f} units\n\nThis action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_delete),
                ft.ElevatedButton("Delete", on_click=confirm_delete, bgcolor="#f44336"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        print(f"DEBUG: Setting delete dialog and opening...")
        self.page.dialog = delete_dialog
        delete_dialog.open = True
        self.page.update()
        print(f"DEBUG: Delete dialog should now be visible")
    
    def show_snackbar(self, message, color):
        """Show a snackbar message"""
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color,
            duration=3000
        )
        self.page.snack_bar = snackbar
        snackbar.open = True
        self.page.update()
    
    def sync_with_server(self, e):
        """Bidirectional sync: Upload local changes and download server data"""
        def show_sync_dialog():
            unsynced_changes = self.local_db.get_unsynced_changes()
            
            sync_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Sync with Appwrite Cloud"),
                content=ft.Column([
                    ft.Text("Choose sync direction:", weight=ft.FontWeight.BOLD),
                    ft.Container(height=15),
                    ft.Row([
                        ft.Icon("upload", size=16, color="green"),
                        ft.Text(f"Sync to Cloud: Upload {len(unsynced_changes)} local changes to Appwrite", size=12)
                    ]),
                    ft.Container(height=8),
                    ft.Row([
                        ft.Icon("download", size=16, color="blue"),
                        ft.Text("Sync from Cloud: Download latest data from Appwrite to local", size=12)
                    ]),
                    ft.Container(height=8),
                    ft.Row([
                        ft.Icon("sync", size=16, color="orange"),
                        ft.Text("Full Sync: Both upload local changes and download server data", size=12)
                    ]),
                ], height=140),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                    ft.ElevatedButton(
                        "Sync to Cloud", 
                        icon="upload",
                        style=ft.ButtonStyle(bgcolor="green", color="white"),
                        on_click=lambda e: self.start_sync("upload")
                    ),
                    ft.ElevatedButton(
                        "Sync from Cloud", 
                        icon="download",
                        style=ft.ButtonStyle(bgcolor="blue", color="white"),
                        on_click=lambda e: self.start_sync("download")
                    ),
                    ft.ElevatedButton(
                        "Full Sync", 
                        icon="sync",
                        style=ft.ButtonStyle(bgcolor="orange", color="white"),
                        on_click=lambda e: self.start_sync("full")
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            self.page.dialog = sync_dialog
            sync_dialog.open = True
            self.page.update()
        
        show_sync_dialog()
    
    def show_sync_progress_dialog(self, sync_type):
        """Show sync progress overlay with detailed status"""
        print(f"DEBUG: Creating sync progress overlay for type: {sync_type}")
        
        # Initialize progress tracking variables
        self.sync_progress = 0
        self.sync_total = 0
        self.sync_current_operation = ""
        self.sync_details = []
        
        # Create progress components
        self.progress_bar = ft.ProgressBar(width=400, value=0)
        self.progress_text = ft.Text("Preparing to sync...", size=14, weight=ft.FontWeight.BOLD)
        self.operation_text = ft.Text("", size=12, color="#666666")
        
        # Create details list with proper scrolling
        self.details_column = ft.Column([], scroll=ft.ScrollMode.ALWAYS, expand=True)
        
        # Create sync title
        sync_title = {
            "upload": "Syncing to Cloud",
            "download": "Syncing from Cloud",
            "full": "Full Sync"
        }.get(sync_type, "Syncing")
        
        # Create button references first
        self.cancel_button = ft.TextButton(
            "Cancel Sync",
            icon="cancel",
            on_click=lambda e: self.cancel_sync(),
            style=ft.ButtonStyle(color="red")
        )
        
        self.close_button = ft.TextButton(
            "Close",
            icon="check",
            on_click=lambda e: self.close_sync_overlay(),
            visible=False,
            style=ft.ButtonStyle(color="green")
        )
        
        # Create the overlay content with proper structure and fixed sizing
        card_content = ft.Column([
            # Header with title and close button (fixed height)
            ft.Container(
                content=ft.Row([
                    ft.Icon("sync", size=24, color="#1976d2"),
                    ft.Text(sync_title, size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(
                        icon="close",
                        icon_size=20,
                        on_click=lambda e: self.cancel_sync(),
                        tooltip="Cancel Sync"
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                height=50
            ),
            
            ft.Divider(height=1),
            
            # Progress section (fixed height)
            ft.Container(
                content=ft.Column([
                    self.progress_text,
                    ft.Container(height=5),
                    self.progress_bar,
                    ft.Container(height=5),
                    self.operation_text,
                ]),
                padding=ft.padding.symmetric(vertical=10),
                height=100
            ),
            
            # Details section with proper scrolling (expandable)
            ft.Container(
                content=ft.Column([
                    ft.Text("Sync Details:", weight=ft.FontWeight.BOLD, size=14),
                    ft.Container(height=5),
                    ft.Container(
                        content=self.details_column,
                        border=ft.border.all(1, "#e0e0e0"),
                        border_radius=5,
                        padding=10,
                        bgcolor="#f8f9fa",
                        height=200,  # Fixed height for scrolling
                    )
                ]),
                expand=True
            ),
            
            # Action buttons (fixed height)
            ft.Container(
                content=ft.Row([
                    self.cancel_button,
                    ft.Container(expand=True),
                    self.close_button
                ]),
                padding=ft.padding.only(top=10),
                height=50
            )
        ], spacing=5, expand=True)
        
        # Create the overlay content
        overlay_content = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=card_content,
                    padding=20,
                    width=550,
                    height=400
                ),
                elevation=8
            ),
            bgcolor="rgba(0,0,0,0.5)",  # Semi-transparent background
            alignment=ft.alignment.center,
            expand=True
        )
        
        # Store overlay reference
        self.sync_overlay = overlay_content
        
        # Show the overlay using the page's overlay property
        print(f"DEBUG: Adding sync overlay to page")
        try:
            # Use Flet's built-in overlay system
            self.page.overlay.append(overlay_content)
            self.page.update()
            print(f"DEBUG: Sync overlay should be visible now")
            
            # Start the actual sync process
            print(f"DEBUG: Starting sync process...")
            self.run_sync_with_progress(sync_type)
            
        except Exception as e:
            print(f"DEBUG: Error showing sync overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def run_sync_with_progress(self, sync_type):
        """Run sync with progress updates"""
        self.sync_cancelled = False
        
        def run_sync():
            try:
                print(f"DEBUG: Sync thread started for {sync_type}")
                self.update_sync_progress(0, 0, "Initializing sync...", "Starting sync operation")
                
                # Check if user is authenticated
                if not self.current_user:
                    print(f"DEBUG: No current user, finishing with error")
                    self.finish_sync_progress(False, "Please log in first to sync with cloud")
                    return
                
                # Check if in offline mode
                if getattr(self, 'offline_mode', False):
                    print(f"DEBUG: In offline mode, finishing with error")
                    self.finish_sync_progress(False, "Cannot sync - application is in offline mode")
                    return
                
                print(f"DEBUG: Starting {sync_type} sync")
                if sync_type == "upload":
                    self.upload_to_server_batch()  # Use improved batch method
                elif sync_type == "download":
                    self.download_from_server_with_progress()
                
                print(f"DEBUG: Sync thread completed")
                
            except Exception as ex:
                print(f"DEBUG: Exception in sync thread: {ex}")
                import traceback
                traceback.print_exc()
                self.finish_sync_progress(False, f"Sync error: {ex}")
        
        import threading
        sync_thread = threading.Thread(target=run_sync, daemon=True)
        sync_thread.start()
        print(f"DEBUG: Sync thread started")
    
    def update_sync_progress(self, progress, total, operation, detail=None):
        """Update sync progress dialog"""
        try:
            print(f"DEBUG: Updating sync progress - {progress}/{total} - {operation}")
            
            self.sync_progress = progress
            self.sync_total = total
            self.sync_current_operation = operation
            
            # Update progress bar
            if total > 0:
                progress_value = progress / total
                self.progress_bar.value = progress_value
                self.progress_text.value = f"Progress: {progress}/{total} ({int(progress_value * 100)}%)"
            else:
                self.progress_bar.value = None  # Indeterminate
                self.progress_text.value = "Processing..."
            
            # Update operation text
            self.operation_text.value = operation
            
            # Add detail to list
            if detail:
                timestamp = datetime.now().strftime("%H:%M:%S")
                detail_text = ft.Text(f"[{timestamp}] {detail}", size=11, selectable=True)
                self.details_column.controls.append(detail_text)
                
                # Keep only last 30 details for better history
                if len(self.details_column.controls) > 30:
                    self.details_column.controls.pop(0)
                
                # Auto-scroll to bottom by updating the column
                try:
                    self.details_column.scroll_to(offset=-1, duration=100)
                except:
                    pass  # Ignore scroll errors
            
            self.page.update()
            
        except Exception as e:
            print(f"Error updating sync progress: {e}")
    
    def finish_sync_progress(self, success, message):
        """Finish sync progress overlay"""
        try:
            print(f"DEBUG: Finishing sync progress - Success: {success}, Message: {message}")
            
            if success:
                self.progress_bar.value = 1.0
                self.progress_text.value = "✅ Sync completed successfully!"
                self.progress_text.color = "green"
            else:
                self.progress_text.value = "❌ Sync failed"
                self.progress_text.color = "red"
            
            self.operation_text.value = message
            
            # Add final detail to log
            timestamp = datetime.now().strftime("%H:%M:%S")
            final_detail = ft.Text(f"[{timestamp}] {message}", size=11, color="green" if success else "red")
            self.details_column.controls.append(final_detail)
            
            # Hide cancel button, show close button
            if hasattr(self, 'cancel_button') and hasattr(self, 'close_button'):
                self.cancel_button.visible = False
                self.close_button.visible = True
            
            print(f"DEBUG: About to update page after finishing sync")
            self.page.update()
            print(f"DEBUG: Page updated after finishing sync")
            
            # Auto-close after 3 seconds if successful
            if success:
                def auto_close():
                    import time
                    time.sleep(3)
                    self.close_sync_overlay()
                
                import threading
                threading.Thread(target=auto_close, daemon=True).start()
            
        except Exception as e:
            print(f"Error finishing sync progress: {e}")
            import traceback
            traceback.print_exc()
    
    def cancel_sync(self):
        """Cancel ongoing sync operation"""
        self.sync_cancelled = True
        self.close_sync_overlay()
    
    def close_sync_overlay(self):
        """Close the sync overlay"""
        try:
            print(f"DEBUG: Closing sync overlay")
            if hasattr(self, 'sync_overlay') and self.sync_overlay in self.page.overlay:
                self.page.overlay.remove(self.sync_overlay)
                self.page.update()
                print(f"DEBUG: Sync overlay removed")
                
                # Clean up references
                if hasattr(self, 'sync_overlay'):
                    delattr(self, 'sync_overlay')
            else:
                print(f"DEBUG: No sync overlay to remove")
        except Exception as e:
            print(f"Error closing sync overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def restore_page_content(self):
        """Restore the original page content (legacy method, now just calls close_sync_overlay)"""
        self.close_sync_overlay()
    
    def close_dialog(self):
        """Close the current dialog"""
        print(f"DEBUG: Closing dialog - Current dialog: {self.page.dialog}")
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
            print(f"DEBUG: Dialog closed")
        else:
            print(f"DEBUG: No dialog to close")
    
    def start_sync(self, sync_type):
        """Start the sync process"""
        print(f"DEBUG: start_sync called with type: {sync_type}")
        
        # Only close dialog if it exists AND it's not our sync dialog (when called from other dialogs)
        if hasattr(self.page, 'dialog') and self.page.dialog and not hasattr(self, 'sync_dialog'):
            print(f"DEBUG: Closing existing dialog before showing sync dialog")
            self.close_dialog()
        
        # Show sync progress dialog
        self.show_sync_progress_dialog(sync_type)
    
    def upload_to_server_with_progress(self):
        """Upload local changes to server with progress updates"""
        try:
            self.update_sync_progress(0, 0, "Comparing with server...", "Checking what needs to be synced")
            
            # Use sync manager to properly compare local vs server data
            if not self.sync_manager:
                print("ERROR: Sync manager not initialized")
                self.finish_sync_progress(False, "Sync manager not available")
                return
            
            try:
                # Get proper comparison instead of just checking sync_log
                comparison = self.sync_manager.compare_databases()
                items_to_upload = comparison['local_only'] + comparison['local_newer']
                
                print(f"DEBUG: Comparison found {len(items_to_upload)} items to upload")
                print(f"DEBUG: Local only: {len(comparison['local_only'])}, Local newer: {len(comparison['local_newer'])}")
                
            except Exception as e:
                print(f"DEBUG: Error comparing databases: {e}")
                import traceback
                traceback.print_exc()
                self.finish_sync_progress(False, f"Database comparison error: {e}")
                return
            
            total_changes = len(items_to_upload)
            
            if total_changes == 0:
                print(f"DEBUG: No changes to upload, finishing sync")
                self.finish_sync_progress(True, "No local changes to upload")
                return
            
            self.update_sync_progress(0, total_changes, f"Found {total_changes} changes to upload", 
                                    f"Uploading {total_changes} items to Appwrite")
            
            # Use sync manager to upload the items
            result = self.sync_manager.sync_local_to_server(items_to_upload)
            
            self.update_sync_progress(total_changes, total_changes, f"Upload complete", 
                                    f"✅ Uploaded {result['success']} items, {result['failed']} failed")
            
            if result['failed'] > 0:
                self.finish_sync_progress(False, f"Upload completed with {result['failed']} failures")
            else:
                self.finish_sync_progress(True, f"Successfully uploaded {result['success']} items")
            
            return
            
            # OLD CODE - keeping for reference but not used
            synced_count = 0
            synced_ids = []
            
            for i, change in enumerate([]):
                if self.sync_cancelled:
                    self.finish_sync_progress(False, "Sync cancelled by user")
                    return
                
                try:
                    sync_success = False
                    
                    if change['table_name'] == 'meters':
                        if change['operation'] == 'INSERT':
                            self.update_sync_progress(i, total_changes, f"Uploading meter...", 
                                                    f"Syncing meter {change['record_id']}")
                            
                            # Get meter data from local DB
                            meters = self.local_db.get_meters(self.current_user['$id'])
                            meter = next((m for m in meters if m['$id'] == change['record_id']), None)
                            if meter:
                                # Sync meter to server with original ID
                                result = self.appwrite.sync_meter(
                                    meter_id=meter['$id'],
                                    home_name=meter['home_name'], 
                                    meter_name=meter['meter_name'], 
                                    meter_type=meter.get('meter_type', 'electricity'),
                                    user_id=meter['user_id'],
                                    created_at=meter.get('created_at')
                                )
                                if result:
                                    sync_success = True
                                    self.update_sync_progress(i + 1, total_changes, f"Meter uploaded successfully", 
                                                            f"✅ Meter '{meter['meter_name']}' synced")
                            else:
                                print(f"DEBUG: Meter {change['record_id']} not found in local database")
                    
                    elif change['table_name'] == 'readings':
                        if change['operation'] == 'INSERT':
                            self.update_sync_progress(i, total_changes, f"Uploading reading...", 
                                                    f"Syncing reading {change['record_id']}")
                            
                            # Get reading data from local DB
                            conn = sqlite3.connect(self.local_db.db_path)
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                            row = cursor.fetchone()
                            conn.close()
                            
                            if row:
                                # Sync reading to server with original ID
                                result = self.appwrite.sync_reading(
                                    reading_id=row[0],  # id
                                    meter_id=row[2],  # meter_id
                                    reading_value=row[3],  # reading_value
                                    reading_date=row[6],  # reading_date
                                    user_id=row[1],  # user_id
                                    created_at=row[7],  # created_at
                                    consumption_kwh=row[5]  # consumption_kwh
                                )
                                if result:
                                    sync_success = True
                                    self.update_sync_progress(i + 1, total_changes, f"Reading uploaded successfully", 
                                                            f"✅ Reading {row[3]} kWh synced")
                            else:
                                print(f"DEBUG: Reading {change['record_id']} not found in local database")
                        
                        elif change['operation'] == 'UPDATE':
                            self.update_sync_progress(i, total_changes, f"Updating reading...", 
                                                    f"Updating reading {change['record_id']}")
                            
                            # Update reading on server
                            conn = sqlite3.connect(self.local_db.db_path)
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                            row = cursor.fetchone()
                            conn.close()
                            
                            if row:
                                reading_date = datetime.fromisoformat(row[6]).date()
                                
                                # Try to find the reading on server by meter_id and date instead of ID
                                try:
                                    # First, check if reading exists on server by meter and date
                                    server_readings = self.appwrite.get_readings(
                                        meter_id=row[2],  # meter_id
                                        start_date=reading_date.strftime('%Y-%m-%d'),
                                        end_date=reading_date.strftime('%Y-%m-%d'),
                                        limit=1
                                    )
                                    
                                    if server_readings:
                                        # Update existing server reading
                                        server_reading_id = server_readings[0]['$id']
                                        result = self.appwrite.update_reading(
                                            reading_id=server_reading_id,
                                            reading_value=row[3],  # reading_value
                                            reading_date=reading_date
                                        )
                                        if result:
                                            sync_success = True
                                            print(f"DEBUG: Updated server reading {server_reading_id} (was local {row[0]})")
                                    else:
                                        # Reading doesn't exist on server, create it instead
                                        print(f"DEBUG: Reading {row[0]} not found on server, creating new one")
                                        result = self.appwrite.sync_reading(
                                            reading_id=row[0],  # id
                                            meter_id=row[2],  # meter_id
                                            reading_value=row[3],  # reading_value
                                            reading_date=row[6],  # reading_date
                                            user_id=row[1],  # user_id
                                            created_at=row[7],  # created_at
                                            consumption_kwh=row[5]  # consumption_kwh
                                        )
                                        if result:
                                            sync_success = True
                                    
                                    if sync_success:
                                        self.update_sync_progress(i + 1, total_changes, f"Reading updated successfully", 
                                                                f"✅ Reading updated: {row[3]} kWh")
                                except Exception as update_error:
                                    print(f"DEBUG: Failed to update reading {row[0]}: {update_error}")
                                    # Continue with next item instead of failing completely
                        
                        elif change['operation'] == 'DELETE':
                            self.update_sync_progress(i, total_changes, f"Deleting reading...", 
                                                    f"Deleting reading {change['record_id']}")
                            
                            # For DELETE operations, we need to find the reading on server first
                            # since the local ID might not match the server ID
                            try:
                                # Try direct delete first (in case IDs match)
                                result = self.appwrite.delete_reading(change['record_id'])
                                sync_success = True
                                print(f"DEBUG: Deleted reading {change['record_id']} directly")
                            except Exception as direct_delete_error:
                                print(f"DEBUG: Direct delete failed for {change['record_id']}: {direct_delete_error}")
                                # If direct delete fails, we can't easily find the reading to delete
                                # since we don't have the meter_id and date for deleted records
                                # This is a limitation - we'll just mark it as synced locally
                                sync_success = True  # Mark as success to avoid infinite retry
                            
                            if sync_success:
                                self.update_sync_progress(i + 1, total_changes, f"Reading deleted successfully", 
                                                        f"✅ Reading deleted from server")
                    
                    # Only increment counters if sync was successful
                    if sync_success:
                        synced_ids.append(change['record_id'])
                        synced_count += 1
                        print(f"DEBUG: Successfully synced {change['record_id']}, count now: {synced_count}")
                    else:
                        print(f"DEBUG: Failed to sync {change['record_id']}")
                            
                except Exception as ex:
                    self.update_sync_progress(i + 1, total_changes, f"Error syncing item", 
                                            f"❌ Error syncing {change['record_id']}: {ex}")
                    print(f"Error syncing {change['record_id']}: {ex}")
            
            # Mark as synced
            if synced_ids:
                self.local_db.mark_synced(synced_ids)
            
            self.finish_sync_progress(True, f"Successfully uploaded {synced_count} of {total_changes} changes")
            
        except Exception as ex:
            self.finish_sync_progress(False, f"Upload failed: {ex}")
    
    def upload_to_server_batch(self):
        """Improved batch upload with rate limiting and better error handling"""
        try:
            self.update_sync_progress(0, 0, "Comparing with server...", "Checking what needs to be synced")
            
            # Use sync manager to properly compare local vs server data
            if not self.sync_manager:
                print("ERROR: Sync manager not initialized")
                self.finish_sync_progress(False, "Sync manager not available")
                return
            
            try:
                # Get proper comparison instead of just checking sync_log
                comparison = self.sync_manager.compare_databases()
                items_to_upload = comparison['local_only'] + comparison['local_newer']
                
                print(f"DEBUG: Comparison found {len(items_to_upload)} items to upload")
                print(f"DEBUG: Local only: {len(comparison['local_only'])}, Local newer: {len(comparison['local_newer'])}")
                
            except Exception as e:
                print(f"DEBUG: Error comparing databases: {e}")
                import traceback
                traceback.print_exc()
                self.finish_sync_progress(False, f"Database comparison error: {e}")
                return
            
            total_changes = len(items_to_upload)
            
            if total_changes == 0:
                print(f"DEBUG: No changes to upload, finishing sync")
                self.finish_sync_progress(True, "No local changes to upload")
                return
            
            # Use sync manager to upload the items
            self.update_sync_progress(0, total_changes, f"Uploading {total_changes} items...", "Starting upload process")
            
            result = self.sync_manager.sync_local_to_server(items_to_upload)
            
            self.update_sync_progress(total_changes, total_changes, f"Upload complete", 
                                    f"✅ Uploaded {result['success']} items, {result['failed']} failed")
            
            if result['failed'] > 0:
                self.finish_sync_progress(False, f"Upload completed with {result['failed']} failures")
            else:
                self.finish_sync_progress(True, f"Successfully uploaded {result['success']} items")
            
            return
            
            # OLD CODE BELOW - keeping for reference but not used
            
            # Group changes by type and operation
            meter_inserts = []
            reading_inserts = []
            reading_updates = []
            reading_deletes = []
            
            for change in unsynced_changes:
                if change['table_name'] == 'meters' and change['operation'] == 'INSERT':
                    meters = self.local_db.get_meters(self.current_user['$id'])
                    meter = next((m for m in meters if m['$id'] == change['record_id']), None)
                    if meter:
                        meter_inserts.append(meter)
                
                elif change['table_name'] == 'readings':
                    if change['operation'] == 'INSERT':
                        # Get reading data
                        conn = sqlite3.connect(self.local_db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                        row = cursor.fetchone()
                        conn.close()
                        if row:
                            reading_inserts.append({
                                'id': row[0], 'user_id': row[1], 'meter_id': row[2],
                                'reading_value': row[3], 'consumption_kwh': row[4],
                                'reading_time': row[5], 'reading_date': row[6], 'created_at': row[7]
                            })
                    elif change['operation'] == 'UPDATE':
                        conn = sqlite3.connect(self.local_db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                        row = cursor.fetchone()
                        conn.close()
                        if row:
                            reading_updates.append({
                                'id': row[0], 'reading_value': row[3], 'reading_date': row[6]
                            })
                    elif change['operation'] == 'DELETE':
                        reading_deletes.append(change['record_id'])
            
            # Set up batch processor progress callback
            def progress_callback(current, total, message):
                if not self.sync_cancelled:
                    self.update_sync_progress(current, total, message, f"Processing batch {current}/{total}")
            
            self.batch_processor.set_progress_callback(progress_callback)
            
            synced_count = 0
            synced_ids = []
            
            # Process meter inserts
            if meter_inserts and not self.sync_cancelled:
                self.update_sync_progress(0, total_changes, "Syncing meters...", f"Processing {len(meter_inserts)} meters")
                
                def sync_meter_func(meter):
                    return self.appwrite.sync_meter(
                        meter_id=meter['$id'],
                        home_name=meter['home_name'],
                        meter_name=meter['meter_name'],
                        meter_type=meter.get('meter_type', 'electricity'),
                        user_id=meter['user_id'],
                        created_at=meter.get('created_at')
                    )
                
                result = self.batch_processor.sync_meters(meter_inserts, sync_meter_func)
                synced_count += result['success_count']
                synced_ids.extend([m['$id'] for m in meter_inserts[:result['success_count']]])
                
                if result['failed_items']:
                    print(f"Failed to sync {len(result['failed_items'])} meters")
            
            # Process reading inserts
            if reading_inserts and not self.sync_cancelled:
                self.update_sync_progress(synced_count, total_changes, "Syncing readings...", f"Processing {len(reading_inserts)} readings")
                
                def sync_reading_func(reading):
                    return self.appwrite.sync_reading(
                        reading_id=reading['id'],
                        meter_id=reading['meter_id'],
                        reading_value=reading['reading_value'],
                        reading_date=reading['reading_date'],
                        user_id=reading['user_id'],
                        created_at=reading.get('created_at'),
                        consumption_kwh=reading.get('consumption_kwh', 0.0)
                    )
                
                result = self.batch_processor.sync_readings(reading_inserts, sync_reading_func)
                synced_count += result['success_count']
                synced_ids.extend([r['id'] for r in reading_inserts[:result['success_count']]])
            
            # Process reading updates (smaller batches)
            if reading_updates and not self.sync_cancelled:
                self.update_sync_progress(synced_count, total_changes, "Updating readings...", f"Processing {len(reading_updates)} updates")
                
                for reading in reading_updates:
                    if self.sync_cancelled:
                        break
                    try:
                        # Convert date to string format for JSON serialization
                        if isinstance(reading['reading_date'], str):
                            reading_date_str = reading['reading_date'][:10]  # Take only YYYY-MM-DD part
                        else:
                            reading_date_str = reading['reading_date'].strftime('%Y-%m-%d')
                        
                        self.appwrite.update_reading(
                            reading_id=reading['id'],
                            reading_value=reading['reading_value'],
                            reading_date=reading_date_str
                        )
                        synced_ids.append(reading['id'])
                        synced_count += 1
                        time.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        print(f"Failed to update reading {reading['id']}: {e}")
            
            # Process reading deletes (smaller batches)
            if reading_deletes and not self.sync_cancelled:
                self.update_sync_progress(synced_count, total_changes, "Deleting readings...", f"Processing {len(reading_deletes)} deletions")
                
                for reading_id in reading_deletes:
                    if self.sync_cancelled:
                        break
                    try:
                        self.appwrite.delete_reading(reading_id)
                        synced_ids.append(reading_id)
                        synced_count += 1
                        time.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        print(f"Failed to delete reading {reading_id}: {e}")
            
            # Mark as synced
            if synced_ids:
                self.local_db.mark_synced(synced_ids)
            
            if self.sync_cancelled:
                self.finish_sync_progress(False, "Sync cancelled by user")
            else:
                self.finish_sync_progress(True, f"Successfully uploaded {synced_count} of {total_changes} changes")
            
        except Exception as ex:
            self.finish_sync_progress(False, f"Upload failed: {ex}")
    
    def download_from_server_with_progress(self):
        """Download data from server to local SQLite with progress updates"""
        try:
            self.update_sync_progress(0, 0, "Connecting to server...", "Fetching data from Appwrite")
            
            downloaded_count = 0
            
            # Download meters from server
            self.update_sync_progress(0, 0, "Downloading meters...", "Getting meters from server")
            server_meters = self.appwrite.get_user_meters()
            
            total_items = len(server_meters)
            
            for i, meter in enumerate(server_meters):
                if self.sync_cancelled:
                    self.finish_sync_progress(False, "Sync cancelled by user")
                    return
                
                self.update_sync_progress(i, total_items, f"Processing meter...", 
                                        f"Checking meter: {meter['meter_name']}")
                
                # Check if meter exists locally
                local_meters = self.local_db.get_meters(self.current_user['$id'])
                existing_meter = next((m for m in local_meters if m['$id'] == meter['$id']), None)
                
                if not existing_meter:
                    # Add new meter to local database
                    meter_data = {
                        'id': meter['$id'],
                        'user_id': meter['user_id'],
                        'home_name': meter['home_name'],
                        'meter_name': meter['meter_name'],
                        'meter_type': meter.get('meter_type', meter.get('meter_type_fixed', 'electricity')),
                        'created_at': meter['created_at']
                    }
                    self.local_db.add_meter(meter_data)
                    downloaded_count += 1
                    
                    self.update_sync_progress(i + 1, total_items, f"Meter downloaded", 
                                            f"✅ Downloaded meter: {meter['meter_name']}")
                else:
                    self.update_sync_progress(i + 1, total_items, f"Meter already exists", 
                                            f"⏭️ Skipped existing meter: {meter['meter_name']}")
            
            # Download readings from server
            readings_downloaded = 0
            for i, meter in enumerate(server_meters):
                if self.sync_cancelled:
                    self.finish_sync_progress(False, "Sync cancelled by user")
                    return
                
                try:
                    self.update_sync_progress(i, len(server_meters), f"Downloading readings...", 
                                            f"Getting readings for meter: {meter['meter_name']}")
                    
                    server_readings = self.appwrite.get_daily_readings(meter['$id'])
                    local_readings = self.local_db.get_readings(meter['$id'])
                    local_reading_ids = {r['$id'] for r in local_readings}
                    
                    for reading in server_readings:
                        if reading['$id'] not in local_reading_ids:
                            # Add new reading to local database
                            reading_data = {
                                'id': reading['$id'],
                                'user_id': reading['user_id'],
                                'meter_id': reading['meter_id'],
                                'reading_value': reading['reading_value'],
                                'reading_date': reading['reading_date'],
                                'created_at': reading['created_at']
                            }
                            self.local_db.add_reading(reading_data)
                            readings_downloaded += 1
                            downloaded_count += 1
                    
                    if server_readings:
                        self.update_sync_progress(i + 1, len(server_meters), f"Readings downloaded", 
                                                f"✅ Downloaded {len(server_readings)} readings for {meter['meter_name']}")
                    
                except Exception as ex:
                    self.update_sync_progress(i + 1, len(server_meters), f"Error downloading readings", 
                                            f"❌ Error downloading readings for {meter['meter_name']}: {ex}")
                    print(f"Error downloading readings for meter {meter['$id']}: {ex}")
            
            if downloaded_count > 0:
                self.finish_sync_progress(True, f"Successfully downloaded {downloaded_count} items from server")
                # Refresh the current view
                self.load_meters()
                if hasattr(self, 'tabs') and self.tabs.selected_index == 0:
                    self.show_dashboard()
            else:
                self.finish_sync_progress(True, "No new data to download from server")
                
        except Exception as ex:
            self.finish_sync_progress(False, f"Download failed: {ex}")
    
    def upload_to_server(self, loop):
        """Upload local changes to server"""
        unsynced_changes = self.local_db.get_unsynced_changes()
        synced_count = 0
        synced_ids = []
        
        for change in unsynced_changes:
            try:
                if change['table_name'] == 'meters':
                    if change['operation'] == 'INSERT':
                        # Get meter data from local DB
                        meters = self.local_db.get_meters(self.current_user['$id'])
                        meter = next((m for m in meters if m['$id'] == change['record_id']), None)
                        if meter:
                            # Sync meter to server with original ID
                            self.appwrite.sync_meter(
                                meter_id=meter['$id'],
                                home_name=meter['home_name'], 
                                meter_name=meter['meter_name'], 
                                meter_type=meter.get('meter_type', 'electricity'),
                                user_id=meter['user_id'],
                                created_at=meter.get('created_at')
                            )
                            synced_ids.append(change['record_id'])
                            synced_count += 1
                
                elif change['table_name'] == 'readings':
                    if change['operation'] == 'INSERT':
                        # Get reading data from local DB
                        conn = sqlite3.connect(self.local_db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row:
                            # Sync reading to server with original ID
                            self.appwrite.sync_reading(
                                reading_id=row[0],  # id
                                meter_id=row[2],  # meter_id
                                reading_value=row[3],  # reading_value
                                reading_date=row[6],  # reading_date
                                user_id=row[1],  # user_id
                                created_at=row[7]  # created_at
                            )
                            synced_ids.append(change['record_id'])
                            synced_count += 1
                    
                    elif change['operation'] == 'UPDATE':
                        # Update reading on server
                        conn = sqlite3.connect(self.local_db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row:
                            reading_date = datetime.fromisoformat(row[6]).date()
                            self.appwrite.update_reading(
                                reading_id=row[0],  # id
                                reading_value=row[3],  # reading_value
                                reading_date=reading_date
                            )
                            synced_ids.append(change['record_id'])
                            synced_count += 1
                    
                    elif change['operation'] == 'DELETE':
                        # Delete reading on server
                        self.appwrite.delete_reading(change['record_id'])
                        synced_ids.append(change['record_id'])
                        synced_count += 1
                        
            except Exception as ex:
                print(f"Error syncing {change['record_id']}: {ex}")
        
        # Mark as synced
        if synced_ids:
            self.local_db.mark_synced(synced_ids)
        
        return synced_count
    
    def download_from_server(self):
        """Download data from server to local SQLite"""
        downloaded_count = 0
        
        try:
            # Download meters from server
            server_meters = self.appwrite.get_user_meters()
            
            for meter in server_meters:
                # Check if meter exists locally
                local_meters = self.local_db.get_meters(self.current_user['$id'])
                existing_meter = next((m for m in local_meters if m['$id'] == meter['$id']), None)
                
                if not existing_meter:
                    # Add new meter to local database
                    meter_data = {
                        'id': meter['$id'],
                        'user_id': meter['user_id'],
                        'home_name': meter['home_name'],
                        'meter_name': meter['meter_name'],
                        'meter_type': meter.get('meter_type', meter.get('meter_type_fixed', 'electricity')),
                        'created_at': meter['created_at']
                    }
                    self.local_db.add_meter(meter_data)
                    downloaded_count += 1
            
            # Download readings from server
            for meter in server_meters:
                try:
                    server_readings = self.appwrite.get_daily_readings(meter['$id'])
                    local_readings = self.local_db.get_readings(meter['$id'])
                    local_reading_ids = {r['$id'] for r in local_readings}
                    
                    for reading in server_readings:
                        if reading['$id'] not in local_reading_ids:
                            # Add new reading to local database
                            reading_data = {
                                'id': reading['$id'],
                                'user_id': reading['user_id'],
                                'meter_id': reading['meter_id'],
                                'reading_value': reading['reading_value'],
                                'reading_date': reading['reading_date'],
                                'created_at': reading['created_at']
                            }
                            self.local_db.add_reading(reading_data)
                            downloaded_count += 1
                except Exception as ex:
                    print(f"Error downloading readings for meter {meter['$id']}: {ex}")
            
        except Exception as ex:
            print(f"Error downloading from server: {ex}")
            raise ex
        
        return downloaded_count
    
    def create_stat_card(self, title, value, color):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color="#757575", text_align=ft.TextAlign.CENTER),
                ft.Text(value, size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=180,
            height=80,
            bgcolor=color + "20",  # Add transparency
            border=ft.border.all(1, color),
            border_radius=10,
            padding=10
        )

    def check_comprehensive_sync_on_startup(self):
        """Comprehensive sync check when app starts - compares local vs server data"""
        # Store reference to self for use in nested function
        app_instance = self
        
        def check_sync():
            try:
                print("🔍 Starting comprehensive sync check...")
                
                if not app_instance.sync_manager:
                    print("ERROR: Sync manager not initialized")
                    return
                
                # Compare databases
                comparison = app_instance.sync_manager.compare_databases()
                
                # Debug: Print detailed comparison results
                print(f"DEBUG: Comparison results:")
                print(f"  Local only: {len(comparison['local_only'])} items")
                print(f"  Server only: {len(comparison['server_only'])} items") 
                print(f"  Local newer: {len(comparison['local_newer'])} items")
                print(f"  Server newer: {len(comparison['server_newer'])} items")
                print(f"  In sync: {len(comparison['in_sync'])} items")
                print(f"  Conflicts: {len(comparison['conflicts'])} items")
                
                # Generate summary
                summary = app_instance.sync_manager.get_sync_summary(comparison)
                print(f"📊 Sync Summary:\n{summary}")
                
                # Check if server is completely empty but local has data
                local_has_data = comparison['local_only'] or comparison['local_newer'] or comparison['in_sync']
                server_is_empty = not (comparison['server_only'] or comparison['server_newer'] or comparison['in_sync'])
                
                print(f"DEBUG: Local has data: {local_has_data}, Server is empty: {server_is_empty}")
                
                if server_is_empty and local_has_data:
                    # Server is empty but local has data - show upload prompt
                    app_instance.show_empty_server_upload_overlay(comparison)
                elif comparison['local_only'] or comparison['server_only'] or comparison['local_newer'] or comparison['server_newer'] or comparison['conflicts']:
                    # Normal sync needed
                    app_instance.show_comprehensive_sync_dialog(comparison, summary)
                else:
                    print("✅ All data is in sync - no action needed")
                    
            except Exception as ex:
                print(f"ERROR: Failed comprehensive sync check: {ex}")
                # Fallback to simple sync check
                app_instance.check_sync_status_on_startup()
        
        # Run in background thread
        import threading
        threading.Thread(target=check_sync, daemon=True).start()
    
    def check_sync_status_on_startup(self):
        """Simple fallback sync status check"""
        try:
            print("DEBUG: Running simple sync status check (fallback)")
            
            # Get basic sync status
            if not self.session_manager.is_session_valid():
                print("DEBUG: No valid session, skipping sync check")
                return
            
            # Get local data counts
            user_id = self.session_manager.get_session()['user']['$id']
            local_meters = self.local_db.get_meters(user_id)
            
            local_reading_count = 0
            for meter in local_meters:
                readings = self.local_db.get_readings(meter['$id'])
                local_reading_count += len(readings)
            
            # Get unsynced changes
            unsynced_changes = self.local_db.get_unsynced_changes()
            
            # Also check if server is empty (simple check)
            try:
                server_meters = self.appwrite.get_user_meters()
                server_meter_count = len(server_meters)
                print(f"DEBUG: Simple sync check - Local: {len(local_meters)} meters, {local_reading_count} readings, {len(unsynced_changes)} unsynced, Server: {server_meter_count} meters")
            except:
                server_meter_count = 0
                print(f"DEBUG: Simple sync check - Local: {len(local_meters)} meters, {local_reading_count} readings, {len(unsynced_changes)} unsynced, Server: unknown")
            
            # Show prompt if there are unsynced changes OR if we have local data but empty server
            has_local_data = len(local_meters) > 0 or local_reading_count > 0
            server_is_empty = server_meter_count == 0
            
            if len(unsynced_changes) > 0 or (has_local_data and server_is_empty):
                self.show_sync_status_prompt(
                    local_meters=len(local_meters),
                    local_readings=local_reading_count, 
                    unsynced=max(len(unsynced_changes), len(local_meters) if server_is_empty else 0),
                    server_meters=server_meter_count,
                    server_readings=0  # Unknown in fallback mode
                )
            else:
                print("DEBUG: No sync needed - data is in sync")
                
        except Exception as e:
            print(f"ERROR: Simple sync status check failed: {e}")
    
    def show_comprehensive_sync_dialog(self, comparison, summary):
        """Show comprehensive sync dialog with options"""
        def close_dialog(e):
            sync_dialog.open = False
            self.page.update()
        
        def sync_all(e):
            """Perform comprehensive sync"""
            close_dialog(e)
            self.perform_comprehensive_sync(comparison)
        
        def sync_later(e):
            """Skip sync for now"""
            close_dialog(e)
            print("ℹ️ Sync skipped by user")
        
        # Create dialog content
        content = [
            ft.Text("🔄 Sync Required", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(summary, size=14),
            ft.Divider(),
        ]
        
        # Add specific sync options
        if comparison['local_only']:
            content.append(ft.Text(f"📤 Upload {len(comparison['local_only'])} items to server", color="blue"))
        
        if comparison['server_only']:
            content.append(ft.Text(f"📥 Download {len(comparison['server_only'])} items from server", color="green"))
        
        if comparison['conflicts']:
            content.append(ft.Text(f"⚠️ {len(comparison['conflicts'])} conflicts (local data will be preferred)", color="orange"))
        
        sync_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Database Sync Required"),
            content=ft.Column(content, height=300, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Sync Now", on_click=sync_all),
                ft.TextButton("Skip", on_click=sync_later),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = sync_dialog
        sync_dialog.open = True
        self.page.update()
    
    def show_empty_server_upload_overlay(self, comparison):
        """Show overlay prompt when server is empty but local has data"""
        def close_overlay(e):
            self.page.overlay.clear()
            self.page.update()
        
        def upload_all_data(e):
            """Upload all local data to empty server"""
            close_overlay(e)
            self.upload_all_local_data_to_server(comparison)
        
        def skip_upload(e):
            """Skip uploading data"""
            close_overlay(e)
            print("ℹ️ Upload to empty server skipped by user")
        
        # Count local data
        total_items = len(comparison['local_only'])
        meters_count = len([item for item in comparison['local_only'] if item['type'] == 'meter'])
        readings_count = len([item for item in comparison['local_only'] if item['type'] == 'reading'])
        
        # Create overlay content
        overlay_content = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Icon(ft.Icons.CLOUD_UPLOAD, size=40, color=ft.Colors.BLUE),
                        ft.Text("📤 Upload Local Data", size=24, weight=ft.FontWeight.BOLD),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    
                    ft.Divider(height=20),
                    
                    # Message
                    ft.Text(
                        "Your cloud database is empty, but you have data stored locally.",
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.OUTLINE
                    ),
                    
                    ft.Container(height=10),
                    
                    # Data summary
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📊 Local Data Summary:", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.Icon(ft.Icons.ELECTRIC_METER, size=20, color=ft.Colors.GREEN),
                                ft.Text(f"{meters_count} Meters", size=14),
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.ANALYTICS, size=20, color=ft.Colors.ORANGE),
                                ft.Text(f"{readings_count} Readings", size=14),
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.UPLOAD, size=20, color=ft.Colors.BLUE),
                                ft.Text(f"{total_items} Total Items to Upload", size=14, weight=ft.FontWeight.BOLD),
                            ]),
                        ], spacing=8),
                        padding=ft.padding.all(16),
                        bgcolor=ft.Colors.SURFACE_TINT,
                        border_radius=8,
                    ),
                    
                    ft.Container(height=20),
                    
                    ft.Text(
                        "Would you like to upload your local data to the cloud?",
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.BOLD
                    ),
                    
                    ft.Container(height=20),
                    
                    # Action buttons
                    ft.Row([
                        ft.ElevatedButton(
                            "📤 Upload All Data",
                            on_click=upload_all_data,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE,
                                color=ft.Colors.WHITE,
                                padding=ft.padding.symmetric(horizontal=20, vertical=12)
                            ),
                            width=200
                        ),
                        ft.OutlinedButton(
                            "Skip for Now",
                            on_click=skip_upload,
                            style=ft.ButtonStyle(
                                padding=ft.padding.symmetric(horizontal=20, vertical=12)
                            ),
                            width=150
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
                ),
                width=500,
                padding=ft.padding.all(30),
                bgcolor=ft.Colors.SURFACE,
                border_radius=16,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.3, ft.Colors.SHADOW),
                    offset=ft.Offset(0, 4),
                )
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            expand=True
        )
        
        # Add overlay to page
        self.page.overlay.append(overlay_content)
        self.page.update()
    
    def upload_all_local_data_to_server(self, comparison):
        """Upload all local data to empty server with progress overlay"""
        def upload_process():
            try:
                print("🔄 Starting bulk upload to empty server...")
                
                # Show progress overlay
                self.show_upload_progress_overlay()
                
                # Upload all local data
                if comparison['local_only']:
                    result = self.sync_manager.sync_local_to_server(comparison['local_only'])
                    print(f"✅ Bulk upload complete: {result['success']} success, {result['failed']} failed")
                    
                    # Mark all as synced
                    unsynced_changes = self.local_db.get_unsynced_changes()
                    if unsynced_changes:
                        sync_ids = [change['record_id'] for change in unsynced_changes]
                        self.local_db.mark_synced(sync_ids)
                
                print("🎉 All local data uploaded to server successfully!")
                
                # Close progress overlay and refresh UI
                self.page.overlay.clear()
                self.load_meters()
                self.page.update()
                
            except Exception as ex:
                print(f"❌ Bulk upload failed: {ex}")
                self.page.overlay.clear()
                self.page.update()
        
        # Run upload in background thread
        import threading
        threading.Thread(target=upload_process, daemon=True).start()
    
    def show_upload_progress_overlay(self):
        """Show upload progress overlay"""
        progress_overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CLOUD_UPLOAD, size=60, color=ft.Colors.BLUE),
                    ft.Text("Uploading Data to Cloud...", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=20),
                    ft.ProgressRing(width=50, height=50, stroke_width=4),
                    ft.Container(height=10),
                    ft.Text("Please wait while we sync your data", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
                ),
                width=300,
                padding=ft.padding.all(40),
                bgcolor=ft.Colors.SURFACE,
                border_radius=16,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.3, ft.Colors.SHADOW),
                    offset=ft.Offset(0, 4),
                )
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            expand=True
        )
        
        self.page.overlay.clear()
        self.page.overlay.append(progress_overlay)
        self.page.update()
    
    def perform_comprehensive_sync(self, comparison):
        """Perform comprehensive bidirectional sync"""
        def sync_process():
            try:
                print("🔄 Starting comprehensive sync...")
                
                # Sync local-only items to server
                if comparison['local_only']:
                    print(f"📤 Uploading {len(comparison['local_only'])} items to server...")
                    result = self.sync_manager.sync_local_to_server(comparison['local_only'])
                    print(f"✅ Upload complete: {result['success']} success, {result['failed']} failed")
                
                # Sync server-only items to local
                if comparison['server_only']:
                    print(f"📥 Downloading {len(comparison['server_only'])} items from server...")
                    result = self.sync_manager.sync_server_to_local(comparison['server_only'])
                    print(f"✅ Download complete: {result['success']} success, {result['failed']} failed")
                
                # Handle newer items (prefer local for conflicts)
                if comparison['local_newer']:
                    print(f"⬆️ Updating {len(comparison['local_newer'])} newer local items on server...")
                    result = self.sync_manager.sync_local_to_server(comparison['local_newer'])
                    print(f"✅ Local updates complete: {result['success']} success, {result['failed']} failed")
                
                if comparison['server_newer']:
                    print(f"⬇️ Updating {len(comparison['server_newer'])} newer server items locally...")
                    result = self.sync_manager.sync_server_to_local(comparison['server_newer'])
                    print(f"✅ Server updates complete: {result['success']} success, {result['failed']} failed")
                
                # Handle conflicts (prefer local data)
                if comparison['conflicts']:
                    print(f"⚠️ Resolving {len(comparison['conflicts'])} conflicts (preferring local data)...")
                    result = self.sync_manager.sync_local_to_server(comparison['conflicts'])
                    print(f"✅ Conflict resolution complete: {result['success']} success, {result['failed']} failed")
                
                # Mark all local changes as synced
                unsynced_changes = self.local_db.get_unsynced_changes()
                if unsynced_changes:
                    sync_ids = [change['record_id'] for change in unsynced_changes]
                    self.local_db.mark_synced(sync_ids)
                
                print("🎉 Comprehensive sync completed successfully!")
                
                # Refresh the UI
                self.load_meters()
                
            except Exception as ex:
                print(f"❌ Comprehensive sync failed: {ex}")
        
        # Run sync in background thread
        import threading
        threading.Thread(target=sync_process, daemon=True).start()
    
    def show_app_closing_sync_prompt(self):
        """Show sync prompt when app is closing"""
        if not self.current_user or not self.sync_manager:
            return
        
        # Check if there are unsynced changes
        unsynced_changes = self.local_db.get_unsynced_changes()
        if not unsynced_changes:
            return  # No unsynced changes, no need to prompt
        
        def close_dialog(e):
            sync_dialog.open = False
            self.page.update()
        
        def sync_and_close(e):
            """Sync data and then close app"""
            close_dialog(e)
            self.sync_before_closing()
        
        def close_without_sync(e):
            """Close app without syncing"""
            close_dialog(e)
            print("ℹ️ App closed without syncing")
            self.page.window_close()
        
        sync_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Unsaved Changes"),
            content=ft.Column([
                ft.Text(f"You have {len(unsynced_changes)} unsaved changes that haven't been synced to the cloud."),
                ft.Text("Would you like to sync your data before closing?"),
            ]),
            actions=[
                ft.TextButton("Sync & Close", on_click=sync_and_close),
                ft.TextButton("Close Without Sync", on_click=close_without_sync),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = sync_dialog
        sync_dialog.open = True
        self.page.update()
    
    def sync_before_closing(self):
        """Sync data before closing the app"""
        def sync_process():
            try:
                print("🔄 Syncing data before closing...")
                
                # Get unsynced changes
                unsynced_changes = self.local_db.get_unsynced_changes()
                
                # Group changes by type
                local_only = []
                for change in unsynced_changes:
                    if change['table_name'] == 'meters':
                        meters = self.local_db.get_meters(self.current_user['$id'])
                        meter = next((m for m in meters if m['$id'] == change['record_id']), None)
                        if meter:
                            local_only.append({'type': 'meter', 'data': meter})
                    elif change['table_name'] == 'readings':
                        conn = sqlite3.connect(self.local_db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM readings WHERE id = ?', (change['record_id'],))
                        row = cursor.fetchone()
                        conn.close()
                        if row:
                            reading_data = {
                                '$id': row[0],
                                'user_id': row[1],
                                'meter_id': row[2],
                                'reading_value': row[3],
                                'consumption_kwh': row[5],
                                'reading_date': row[6],
                                'created_at': row[8]
                            }
                            local_only.append({'type': 'reading', 'data': reading_data})
                
                # Sync to server
                if local_only:
                    result = self.sync_manager.sync_local_to_server(local_only)
                    print(f"✅ Sync complete: {result['success']} success, {result['failed']} failed")
                    
                    # Mark as synced
                    sync_ids = [change['record_id'] for change in unsynced_changes]
                    self.local_db.mark_synced(sync_ids)
                
                print("🎉 Data synced successfully before closing!")
                
                # Close the app
                self.page.window_close()
                
            except Exception as ex:
                print(f"❌ Sync before closing failed: {ex}")
                # Close anyway
                self.page.window_close()
        
        # Run sync in background thread
        import threading
        threading.Thread(target=sync_process, daemon=True).start()
    
    def on_window_event(self, e):
        """Handle window events, especially close event"""
        if e.data == "close":
            # Show sync prompt before closing
            self.show_app_closing_sync_prompt()

def main(page: ft.Page):
    app = VoltTrackApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)
