#!/usr/bin/env python3
"""
Get Spotify API access token
"""

import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def get_spotify_token():
    """Get Spotify access token using client credentials flow"""
    
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file")
        print("\nTo get these credentials:")
        print("1. Go to https://developer.spotify.com/dashboard")
        print("2. Create a new app")
        print("3. Copy the Client ID and Client Secret")
        print("4. Add them to your .env file")
        return None
    
    # Encode credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Request token
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if access_token:
            print(f"✅ Spotify access token obtained successfully!")
            print(f"Token: {access_token[:20]}...")
            print(f"Expires in: {token_data.get('expires_in', 'unknown')} seconds")
            
            # Save to .env file
            with open('.env', 'a') as f:
                f.write(f"\nSPOTIFY_TOKEN={access_token}\n")
            
            print(f"✅ Token saved to .env file")
            return access_token
        else:
            print("❌ Failed to get access token")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting Spotify token: {e}")
        return None

if __name__ == "__main__":
    get_spotify_token()

