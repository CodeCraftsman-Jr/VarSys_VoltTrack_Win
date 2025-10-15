# VoltTrack API Setup Guide

## ✅ Appwrite Functions Removed

The broken Appwrite functions have been completely removed and replaced with **direct API key access** for reliable database operations.

## 🔑 Setting Up API Keys

### Step 1: Get Your API Key

1. **Go to Appwrite Console**: https://cloud.appwrite.io/console
2. **Select your VoltTrack project** (ID: `68e969ec000646eba8c5`)
3. **Navigate to Settings → API Keys**
4. **Create a new API Key** with name: `VoltTrack Desktop App`

### Step 2: Configure API Key Scopes

**IMPORTANT**: Your API key must have these scopes:

#### Required Scopes:
- ✅ `databases.read` - Read database collections
- ✅ `databases.write` - Write to database collections  
- ✅ `documents.read` - Read documents from collections
- ✅ `documents.write` - Write documents to collections
- ✅ `collections.read` - Read collection metadata
- ✅ `collections.write` - Write collection metadata

#### Optional Scopes (for advanced features):
- `users.read` - Read user information
- `sessions.read` - Read session information

### Step 3: Update .env File

1. **Copy the generated API key**
2. **Open `.env` file** in the project root
3. **Replace `your_api_key_here`** with your actual API key:

```env
# VoltTrack Appwrite Configuration
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=68e969ec000646eba8c5
APPWRITE_API_KEY=your_actual_api_key_here_replace_this
APPWRITE_DATABASE_ID=volttrack_db
APPWRITE_METERS_COLLECTION_ID=meters
APPWRITE_READINGS_COLLECTION_ID=readings
```

## 🚀 What Changed

### ❌ Removed (Broken):
- `functions/` directory - Completely deleted
- `VoltTrackFunctions` class - No longer used
- `SecureAppwriteService` - Replaced with direct access
- Function-based sync operations - Replaced with direct database calls

### ✅ Added (Working):
- `DirectAppwriteService` - Uses API keys for direct database access
- Proper error handling and logging
- ID preservation during sync operations
- Duplicate detection and handling
- Real database operations (not mock responses)

## 🔧 Benefits of Direct API Access

1. **Reliable Operations**: No more "No response from function" errors
2. **Real Database Access**: Actual data upload/download to Appwrite
3. **Better Error Handling**: Clear error messages and debugging
4. **ID Preservation**: Maintains original record IDs during sync
5. **Faster Performance**: No function overhead or timeouts
6. **Easier Debugging**: Direct API calls are easier to troubleshoot

## 🧪 Testing

After setting up your API key:

1. **Start the application**: `python main.py`
2. **Login with your account**
3. **Try syncing data** - Should now work without errors
4. **Check Appwrite Console** - Verify data appears in your database

## 🔒 Security Notes

- **Keep your API key secure** - Don't commit it to version control
- **Use environment variables** - API key is loaded from `.env` file
- **Rotate keys regularly** - Generate new API keys periodically
- **Limit scopes** - Only grant necessary permissions

## 🐛 Troubleshooting

### "Missing scopes" error:
- Check that your API key has all required scopes listed above
- Regenerate the API key if scopes are missing

### "Authentication failed" error:
- Verify your API key is correct in the `.env` file
- Check that the project ID matches your Appwrite project

### "Database not found" error:
- Ensure your database and collections exist in Appwrite Console
- Verify the database/collection IDs in `.env` match your setup
