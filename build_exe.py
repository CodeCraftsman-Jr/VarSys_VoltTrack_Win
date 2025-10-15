#!/usr/bin/env python3
"""
VoltTrack Executable Builder
Builds the VoltTrack application into a standalone executable
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"🧹 Removing {spec_file}...")
        spec_file.unlink()

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        ('flet', 'flet'),
        ('pyinstaller', 'PyInstaller'),
        ('appwrite', 'appwrite')
    ]
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name} is installed")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} is missing")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages)
    
    return len(missing_packages) == 0

def create_build_script():
    """Create PyInstaller build script"""
    build_script = """
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
"""
    
    with open('build_script.py', 'w') as f:
        f.write(build_script.strip())
    
    print("📝 Created build_script.py")

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable...")
    
    # Check if icon exists, if not create a simple one or skip
    icon_path = "assets/icon.ico"
    if not os.path.exists(icon_path):
        print(f"⚠️  Icon file {icon_path} not found, building without icon")
        icon_arg = []
    else:
        icon_arg = [f'--icon={icon_path}']
    
    # PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'main.py',
        '--name=VoltTrack',
        '--onefile',
        '--windowed',
        '--add-data=assets;assets' if os.path.exists('assets') else '',
        '--add-data=src;src',
        '--hidden-import=flet',
        '--hidden-import=appwrite',
        '--hidden-import=sqlite3',
        '--hidden-import=asyncio',
        '--hidden-import=threading',
        '--hidden-import=json',
        '--hidden-import=requests',
        '--hidden-import=time',
        '--hidden-import=random',
        '--collect-all=flet',
        '--noconfirm',
        '--clean',
        '--log-level=INFO',
    ] + icon_arg
    
    # Remove empty strings
    cmd = [arg for arg in cmd if arg]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False

def post_build_tasks():
    """Perform post-build tasks"""
    exe_path = Path('dist/VoltTrack.exe')
    
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
        print(f"📦 Executable created: {exe_path}")
        print(f"📏 File size: {file_size:.1f} MB")
        
        # Copy important files to dist folder
        files_to_copy = [
            'README.md',
            'requirements.txt',
        ]
        
        for file_name in files_to_copy:
            if os.path.exists(file_name):
                shutil.copy2(file_name, 'dist/')
                print(f"📋 Copied {file_name} to dist/")
        
        print(f"\n🎉 Build complete! Your executable is ready:")
        print(f"   📁 Location: {exe_path.absolute()}")
        print(f"   🚀 You can now distribute this single file!")
        
        return True
    else:
        print("❌ Executable not found in dist/ folder")
        return False

def main():
    """Main build process"""
    print("🏗️  VoltTrack Executable Builder")
    print("=" * 40)
    
    # Step 1: Clean previous builds
    clean_build_dirs()
    
    # Step 2: Check dependencies
    if not check_dependencies():
        print("❌ Please install missing dependencies first")
        return False
    
    # Step 3: Create build script
    create_build_script()
    
    # Step 4: Build executable
    if not build_executable():
        return False
    
    # Step 5: Post-build tasks
    if not post_build_tasks():
        return False
    
    print("\n✅ All done! Your VoltTrack executable is ready to use.")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
