# --- EMERGENCY COMPATIBILITY PATCHES ---
import sys
import types
# Creates a fake empty audioop module to prevent discord.py crashes
if 'audioop' not in sys.modules:
    fake_audioop = types.ModuleType('audioop')
    sys.modules['audioop'] = fake_audioop
# =======================================

import os
import discord
from discord.ext import tasks
import urllib.request
import json
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# ================= CONFIGURATION =================
TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", 0))

# Fixed BattleMetrics ID for Official Server #1414 PvP
BATTLEMETRICS_ID = "24536640" 
# =================================================

# --- TINY WEB SERVER TO TRICK RENDER FOR FREE TIER ---
class HealthCheckServer(BaseHTTPRequestHandler):
    def send_alive_response(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
    def do_GET(self):
        self.send_alive_response()
        self.wfile.write(b"Bot is alive!")
    def do_HEAD(self):
        self.send_alive_response()

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckServer)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# =====================================================

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

class ServerStatus:
    def __init__(self):
        self.is_online = False

status_tracker = ServerStatus()

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    check_server.start()

@tasks.loop(seconds=30) # Checked every 30 seconds to respect API rate limits
async def check_server():
    channel = client.get_channel(CHANNEL_ID)
    if not channel or not TOKEN:
        return

    url = f"https://api.battlemetrics.com/servers/{BATTLEMETRICS_ID}"
    loop = asyncio.get_event_loop()
    
    try:
        def fetch_data():
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode())
                
        data = await loop.run_in_executor(None, fetch_data)
        
        attributes = data["data"]["attributes"]
        status = attributes["status"] # "online" or "offline"
        server_name = attributes["name"]
        players = attributes["players"]
        max_players = attributes["maxPlayers"]
            
        if status == "online":
            if not status_tracker.is_online:
                status_tracker.is_online = True
                
                embed = discord.Embed(
                    title="⚔️ CONAN SERVER IS ONLINE! ⚔️",
                    description=f"**Server:** {server_name}\n**Players:** {players}/{max_players}\n\n*Slots are open, let's get back in!*",
                    color=discord.Color.green()
                )
                await channel.send(content="@everyone SLOTS ARE OPEN!", embed=embed)
        else:
            if status_tracker.is_online:
                status_tracker.is_online = False
                
                embed = discord.Embed(
                    title="🚨 SERVER CRASHED / OFFLINE 🚨",
                    description=f"**Server:** {server_name}\n\nThe official server is no longer reporting online status.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
            
    except Exception as e:
        print(f"API Fetch Error: {e}")

client.run(TOKEN)
