# VoltTrack Build Guide

This guide explains how to build VoltTrack for different platforms.

## Prerequisites

### General Requirements
- Python 3.8 or higher
- Git
- Internet connection for dependencies

### Platform-Specific Requirements

#### Windows Application
- Windows 10 or higher
- PyInstaller (installed automatically)
- Optional: NSIS for installer creation

#### Web Application  
- Modern web browser
- Netlify account (for deployment)

#### Android Application
- Android SDK
- Flutter SDK
- Flet CLI

## Project Structure

```
VoltTrack/
├── src/                     # Source code
│   ├── core/               # Core application logic
│   ├── database/           # Database layer
│   ├── ui/                 # User interfaces
│   │   ├── desktop/        # Desktop UI (Flet)
│   │   └── web/           # Web UI (HTML/CSS/JS)
│   └── utils/             # Utility functions
├── build/                  # Build outputs
├── scripts/               # Build scripts
├── tests/                 # Test files
└── docs/                  # Documentation
```

## Building Applications

### 1. Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/volttrack.git
cd volttrack

# Install Python dependencies
pip install -r requirements.txt

# Test desktop application
python main.py
```

### 2. Build Web Application

```bash
# Build web application
python scripts/build_web.py

# Serve locally for testing
python -m http.server 8000 --directory build/web
```

**Netlify Deployment:**
1. Connect GitHub repository to Netlify
2. Set build command: `python scripts/build_web.py`
3. Set publish directory: `build/web`
4. Deploy!

### 3. Build Windows Application

```bash
# Build Windows executable
python scripts/build_windows.py
```

This creates:
- `build/windows/VoltTrack.exe` - Standalone executable
- `VoltTrack.nsi` - NSIS installer script

**Create Installer:**
1. Install NSIS from https://nsis.sourceforge.io/
2. Right-click `VoltTrack.nsi` and select "Compile NSIS Script"
3. Installer will be created as `build/windows/VoltTrack-Setup.exe`

### 4. Build Android Application

```bash
# Setup Android build
python scripts/build_android.py

# Build APK (requires Android SDK setup)
flet build apk --project . --output build/android
```

**Android Setup Requirements:**
1. Install Android Studio
2. Install Flutter SDK
3. Install Flet CLI: `pip install flet`
4. Configure environment variables

## Build Scripts

### Available Scripts

```bash
# Development
npm run dev                 # Run desktop app
npm run serve:web          # Serve web app locally

# Building
npm run build:web          # Build web application
npm run build:windows      # Build Windows executable
npm run build:android      # Setup Android build
npm run build:all          # Build all platforms

# Maintenance
npm run clean              # Clean build artifacts
npm run test               # Run tests
npm run lint               # Code linting
```

### Manual Build Commands

```bash
# Web Application
python scripts/build_web.py

# Windows Application  
python scripts/build_windows.py

# Android Application
python scripts/build_android.py

# Cleanup
python scripts/cleanup.py
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Appwrite Configuration
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=your_project_id
APPWRITE_API_KEY=your_api_key
APPWRITE_DATABASE_ID=your_database_id
APPWRITE_METERS_COLLECTION_ID=your_meters_collection_id
APPWRITE_READINGS_COLLECTION_ID=your_readings_collection_id

# Application Settings
APP_NAME=VoltTrack
APP_VERSION=1.0.0
DEBUG=False
```

### Build Configuration

Modify build settings in respective build scripts:
- `scripts/build_web.py` - Web app configuration
- `scripts/build_windows.py` - Windows app configuration  
- `scripts/build_android.py` - Android app configuration

## Deployment

### Web Application (Netlify)

1. **Automatic Deployment:**
   - Connect GitHub repository to Netlify
   - Netlify will automatically build and deploy on git push

2. **Manual Deployment:**
   ```bash
   # Build locally
   python scripts/build_web.py
   
   # Deploy to Netlify
   netlify deploy --prod --dir build/web
   ```

### Windows Application

1. **Direct Distribution:**
   - Share `build/windows/VoltTrack.exe` directly
   - Users can run without installation

2. **Installer Distribution:**
   - Create installer using NSIS
   - Distribute `VoltTrack-Setup.exe`

### Android Application

1. **APK Distribution:**
   - Share APK file directly
   - Users need to enable "Unknown Sources"

2. **Play Store Distribution:**
   - Sign APK with release key
   - Upload to Google Play Console

## Troubleshooting

### Common Issues

**Build Failures:**
- Ensure all dependencies are installed
- Check Python version compatibility
- Verify environment variables

**Import Errors:**
- Check file paths in organized structure
- Verify `__init__.py` files exist
- Update import statements if needed

**Platform-Specific Issues:**

*Windows:*
- Run as administrator if needed
- Check antivirus software interference

*Android:*
- Verify Android SDK installation
- Check Flutter doctor output
- Ensure proper environment variables

### Getting Help

1. Check existing issues on GitHub
2. Create new issue with:
   - Platform and version
   - Error messages
   - Steps to reproduce
3. Join community discussions

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes and test
4. Submit pull request

See `CONTRIBUTING.md` for detailed guidelines.

## License

This project is licensed under the MIT License - see `LICENSE` file for details.
