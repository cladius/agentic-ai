# Google Cloud Text-to-Speech Setup Guide

1. Create a Google Cloud Project
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Click “Create Project” → give it a name → click “Create”.

2. Enable the Text-to-Speech API
   - Navigate to “APIs & Services” → “Library”.
   - Search for “Text-to-Speech API” → Click “Enable”.

3. Create a Service Account
   - Go to “IAM & Admin” → “Service Accounts”.
   - Click “Create Service Account”.
   - Give it a name → click “Create and Continue”.

4. Assign Roles to the Service Account
   - Assign role: “Project” > “Editor” (or a stricter role if preferred).
   - Click “Continue” → “Done”.

5. Generate and Download Credentials
   - Click your new service account → “Keys” tab.
   - Add Key → Create New Key → choose JSON.
   - Download and rename it to `gcp-tts.json` and place it in your project root.

This file authenticates the Google TTS client used in podcast generation.

---
