#!/bin/bash
# Load environment variables from .env file

# Read the .env file and export variables
while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ -n "$line" && ! "$line" =~ ^# ]]; then
        # Remove quotes and export the variable
        export "$line"
    fi
done < .env

echo "Environment variables loaded successfully!"
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}..."
echo "ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY:0:10}..." 