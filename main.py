#!/usr/bin/env python3
"""
VoltTrack - Smart Meter Reading Tracker
Main entry point for the desktop application
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import flet as ft
from ui.desktop.main_app import VoltTrackApp

def main(page: ft.Page):
    """Main entry point for Flet application"""
    app = VoltTrackApp()
    app.main(page)

if __name__ == "__main__":
    # Run the desktop application
    ft.app(target=main, name="VoltTrack", assets_dir="assets")
