# VoltTrack PyInstaller Build Script
# Generated automatically - do not edit manually

import PyInstaller.__main__
import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# PyInstaller arguments
args = [
    'main.py',                          # Entry point
    '--name=VoltTrack',                 # Executable name
    '--onefile',                        # Single executable file
    '--windowed',                       # No console window (GUI app)
    '--icon=assets/icon.ico',           # Application icon (if exists)
    '--add-data=assets;assets',         # Include assets folder
    '--add-data=src;src',               # Include source code
    '--hidden-import=flet',             # Ensure Flet is included
    '--hidden-import=appwrite',         # Ensure Appwrite is included
    '--hidden-import=sqlite3',          # Ensure SQLite is included
    '--hidden-import=asyncio',          # Ensure asyncio is included
    '--hidden-import=threading',        # Ensure threading is included
    '--hidden-import=json',             # Ensure JSON is included
    '--hidden-import=requests',         # Ensure requests is included
    '--hidden-import=time',             # Ensure time is included
    '--hidden-import=random',           # Ensure random is included
    '--collect-all=flet',               # Collect all Flet dependencies
    '--noconfirm',                      # Overwrite output directory
    '--clean',                          # Clean PyInstaller cache
    '--log-level=INFO',                 # Verbose logging
]

# Add console option for debugging (comment out for release)
# args.append('--console')

# Run PyInstaller
PyInstaller.__main__.run(args)