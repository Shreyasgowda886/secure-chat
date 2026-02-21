# OAuth Setup Guide for Secure Chat

## Google OAuth Setup

### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Go to "APIs & Services" → "OAuth 2.0 Credentials"
4. Click "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Web application"
6. Add Authorized redirect URIs:
   - `http://localhost:5000/login/google/authorized` (for development)
   - `https://yourdomain.com/login/google/authorized` (for production)

### Step 2: Get Credentials
- Copy the **Client ID** and **Client Secret**
- Add them to your environment variables

## GitHub OAuth Setup

### Step 1: Create OAuth App on GitHub
1. Go to GitHub Settings → [Developer settings](https://github.com/settings/developers)
2. Click "OAuth Apps" → "New OAuth App"
3. Fill in the form:
   - **Application name": Secure Chat
   - **Homepage URL**: `http://localhost:5000` (or your domain)
   - **Authorization callback URL**: `http://localhost:5000/login/github/authorized`

### Step 2: Get Credentials
- Copy the **Client ID** and **Client Secret**
- Add them to your environment variables

## Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Flask
SECRET_KEY=your-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Load environment variables:
```bash
# Windows (PowerShell)
$env:GOOGLE_CLIENT_ID = "your-client-id"
$env:GOOGLE_CLIENT_SECRET = "your-secret"
$env:GITHUB_CLIENT_ID = "your-client-id"
$env:GITHUB_CLIENT_SECRET = "your-secret"

# Linux/Mac
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-secret"
export GITHUB_CLIENT_ID="your-client-id"
export GITHUB_CLIENT_SECRET="your-secret"
```

3. Run the app:
```bash
python app.py
```

## How It Works

1. When users click "Login with Google" or "Login with GitHub", they're redirected to the OAuth provider
2. After authentication, they're redirected back with an access token
3. The app creates a user account automatically (if not already created)
4. User is logged in and can start chatting

## Notes

- OAuth users don't need to set a password (random one is generated)
- Email from OAuth provider is used as the username base
- RSA keys are automatically generated for each user for end-to-end encryption
- All messages remain encrypted end-to-end regardless of login method

## Troubleshooting

**"Invalid client" error**: Check that your Client ID and Secret are correct and match the redirect URL

**"Redirect URI mismatch"**: Ensure the callback URL in your OAuth app settings matches exactly with your app's URL

**Module not found errors**: Run `pip install -r requirements.txt` to install all dependencies
