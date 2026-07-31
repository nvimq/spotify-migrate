#!/usr/bin/env python3
"""
Spotify Transfer - With Detailed Token Debugging
"""

import requests
import json
import os
import base64
from urllib.parse import urlencode, parse_qs, urlparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from pathlib import Path

def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, val = line.partition('=')
                    os.environ.setdefault(key.strip(), val.strip())

load_env()

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
TOKENS_FILE = str(Path(__file__).parent / "spotify_tokens.json")

if not CLIENT_ID or not CLIENT_SECRET:
    print(" Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")
    print("   Create a .env file or export the variables")
    exit(1)

auth_code_received = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code_received
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if 'code' in params:
            auth_code_received = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<h2>Success! You can close this window.</h2>")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h2>Error: No code received</h2>")
    
    def log_message(self, format, *args):
        pass

def start_callback_server():
    """Start server in background"""
    try:
        server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    except:
        return None

def get_auth_code(account_num):
    """Get authorization code"""
    global auth_code_received
    auth_code_received = None
    
    print(f"\n{'='*60}")
    print(f"STEP {account_num}: AUTHORIZE ACCOUNT {account_num}")
    print(f"{'='*60}\n")
    
    if account_num == 2:
        print("  CRITICAL: Use INCOGNITO/PRIVATE window!")
        print("Close the first browser window BEFORE opening private window!\n")
    
    input("Press ENTER when ready...")
    
    # Start server
    server = start_callback_server()
    if not server:
        print(" Could not start local server")
        return None
    
    # Generate auth URL
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode({
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': 'http://127.0.0.1:8888/callback',
        'scope': 'user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private',
        'show_dialog': 'true'
    })
    
    print("\nOpening browser...")
    try:
        webbrowser.open(auth_url)
    except:
        print(f"Could not open browser. URL: {auth_url}")
    
    print("Waiting for authorization (120 seconds)...\n")
    
    # Wait for callback
    start = time.time()
    while time.time() - start < 120:
        if auth_code_received:
            print(f" Got authorization code!")
            print(f"   Code: {auth_code_received[:20]}...\n")
            try:
                server.shutdown()
            except:
                pass
            return auth_code_received
        time.sleep(0.2)
    
    print(" Timeout - authorization not received")
    try:
        server.shutdown()
    except:
        pass
    return None

def get_token(auth_code, account_num):
    """Exchange code for token with detailed debugging"""
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    
    print(f"   Exchanging code for token...")
    
    try:
        r = requests.post(
            'https://accounts.spotify.com/api/token',
            headers={'Authorization': f'Basic {auth}'},
            data={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://127.0.0.1:8888/callback'
            },
            timeout=10
        )
        
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            token = r.json()['access_token']
            print(f"    Got token!")
            return token
        else:
            print(f"    ERROR: {r.status_code}")
            print(f"   Response: {r.text}")
            return None
            
    except Exception as e:
        print(f"    Exception: {e}")
        return None

def get_user_id(token, account_num):
    """Get Spotify user ID"""
    print(f"   Getting user info...")
    try:
        r = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': f'Bearer {token}'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            user_id = data.get('id')
            email = data.get('email')
            print(f"    User ID: {user_id}")
            print(f"    Email: {email}")
            return user_id
        else:
            print(f"    Error: {r.status_code}")
            print(f"   Response: {r.text}")
    except Exception as e:
        print(f"    Exception: {e}")
    return None

def get_liked_songs(token):
    """Get all liked songs"""
    print(" Loading liked songs...")
    tracks = []
    offset = 0
    while True:
        r = requests.get(
            f'https://api.spotify.com/v1/me/tracks?limit=50&offset={offset}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get('items', [])
        if not items:
            break
        tracks.extend([i['track']['id'] for i in items if i['track']['id']])
        print(f"   {len(tracks)} loaded...")
        if not data.get('next'):
            break
        offset += 50
    return tracks

def add_liked_songs(token, track_ids):
    """Add liked songs"""
    if not track_ids:
        print("No tracks to add")
        return 0
    
    print(f" Adding {len(track_ids)} likes...")
    added = 0
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i:i+50]
        r = requests.put(
            'https://api.spotify.com/v1/me/tracks',
            headers={'Authorization': f'Bearer {token}'},
            json={'ids': batch},
            timeout=10
        )
        if r.status_code == 200:
            added += len(batch)
            print(f"   {added}/{len(track_ids)}")
    return added

def get_playlists(token):
    """Get all playlists"""
    print(" Loading playlists...")
    playlists = []
    offset = 0
    while True:
        r = requests.get(
            f'https://api.spotify.com/v1/me/playlists?limit=50&offset={offset}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get('items', [])
        if not items:
            break
        for item in items:
            playlists.append({
                'id': item['id'],
                'name': item['name'],
                'desc': item.get('description', '')
            })
        print(f"   {len(playlists)} loaded...")
        if not data.get('next'):
            break
        offset += 50
    return playlists

def get_playlist_tracks(token, playlist_id):
    """Get tracks from a playlist"""
    tracks = []
    offset = 0
    while True:
        r = requests.get(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50&offset={offset}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get('items', [])
        if not items:
            break
        tracks.extend([i['track']['id'] for i in items if i['track']['id']])
        if not data.get('next'):
            break
        offset += 50
    return tracks

def create_playlist(token, user_id, name, desc):
    """Create a playlist"""
    try:
        r = requests.post(
            f'https://api.spotify.com/v1/users/{user_id}/playlists',
            headers={'Authorization': f'Bearer {token}'},
            json={'name': name, 'description': desc, 'public': False},
            timeout=10
        )
        if r.status_code == 201:
            return r.json()['id']
    except:
        pass
    return None

def add_to_playlist(token, playlist_id, track_ids):
    """Add tracks to playlist"""
    if not track_ids:
        return 0
    added = 0
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i+100]
        uris = [f'spotify:track:{t}' for t in batch]
        r = requests.post(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
            headers={'Authorization': f'Bearer {token}'},
            json={'uris': uris},
            timeout=10
        )
        if r.status_code in [200, 201]:
            added += len(batch)
    return added

def main():
    print("\n" + "="*60)
    print("SPOTIFY TRANSFER TOOL - DEBUG MODE")
    print("="*60)
    
    # Get authorization codes
    code1 = get_auth_code(1)
    if not code1:
        print(" Account 1 authorization failed")
        return
    
    code2 = get_auth_code(2)
    if not code2:
        print(" Account 2 authorization failed")
        return
    
    # Get tokens with debugging
    print("\n Getting tokens...\n")
    
    print(" Account 1:")
    token1 = get_token(code1, 1)
    if not token1:
        print(" Failed to get token for Account 1")
        return
    
    print("\n Account 2:")
    token2 = get_token(code2, 2)
    if not token2:
        print(" Failed to get token for Account 2")
        return
    
    # Get user IDs
    print("\n Verifying Account 1:")
    user1 = get_user_id(token1, 1)
    if not user1:
        print(" Could not get Account 1 info")
        return
    
    print("\n Verifying Account 2:")
    user2 = get_user_id(token2, 2)
    if not user2:
        print(" Could not get Account 2 info")
        return
    
    if user1 == user2:
        print("\n" + "="*60)
        print(" ERROR: BOTH ACCOUNTS ARE THE SAME!")
        print("="*60)
        print("\nYou logged into the same account twice.")
        print("Solution:")
        print("  1. Close browser completely")
        print("  2. Open PRIVATE/INCOGNITO window")
        print("  3. Try again")
        return
    
    # Transfer likes
    print("\n" + "="*60)
    print("TRANSFER LIKES")
    print("="*60)
    liked = get_liked_songs(token1)
    if liked:
        added = add_liked_songs(token2, liked)
        print(f" Transferred {added}/{len(liked)} likes\n")
    else:
        print("No likes found\n")
    
    # Transfer playlists
    print("="*60)
    print("TRANSFER PLAYLISTS")
    print("="*60)
    playlists = get_playlists(token1)
    
    if playlists:
        print(f"\nTransferring {len(playlists)} playlists...\n")
        for idx, pl in enumerate(playlists, 1):
            print(f"[{idx}/{len(playlists)}] {pl['name']}")
            tracks = get_playlist_tracks(token1, pl['id'])
            if tracks:
                new_id = create_playlist(token2, user2, pl['name'], pl['desc'])
                if new_id:
                    added = add_to_playlist(token2, new_id, tracks)
                    print(f"   {added}/{len(tracks)} tracks")
                else:
                    print("   Failed to create")
            else:
                print("  (empty)")
    else:
        print("No playlists found")
    
    print("\n" + "="*60)
    print(" DONE!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

