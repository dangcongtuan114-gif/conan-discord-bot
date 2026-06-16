# --- EMERGENCY COMPATIBILITY PATCHES ---
import sys
import types
import collections

# 1. Fixes the missing 'Mapping' feature required by python-valve
if not hasattr(collections, 'Mapping'):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

# 2. Creates a fake empty audioop module to prevent discord.py crashes
if 'audioop' not in sys.modules:
    fake_audioop = types.ModuleType('audioop')
    sys.modules['audioop'] = fake_audioop
# =======================================

import os
import discord
from discord.ext import tasks
import valve.source.a2s
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# ================= CONFIGURATION =================
TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", 0))
SERVER_IP = "83.223.199.40"
QUERY_PORT = 28900
# =================================================

# --- TINY WEB SERVER TO TRICK RENDER FOR FREE TIER ---
class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckServer)
    server.serve_forever()

# Start the web server in a separate background thread
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

@tasks.loop(seconds=5)
async def check_server():
    channel = client.get_channel(CHANNEL_ID)
    if not channel or not TOKEN:
        return

    loop = asyncio.get_event_loop()
    try:
        with valve.source.a2s.ServerQuerier((SERVER_IP, QUERY_PORT), timeout=2.0) as querier:
            info = await loop.run_in_executor(None, querier.info)
            server_name = info["server_name"]
            players = info["player_count"]
            max_players = info["max_players"]
            
        if not status_tracker.is_online:
            status_tracker.is_online = True
            
            embed = discord.Embed(
                title="⚔️ CONAN SERVER IS ONLINE! ⚔️",
                description=f"**Server:** {server_name}\n**Players:** {players}/{max_players}\n\n*Slots are open, let's get back in!*",
                color=discord.Color.green()
            )
            await channel.send(content="@everyone SLOTS ARE OPEN!", embed=embed)
            
    except Exception:
        if status_tracker.is_online:
            status_tracker.is_online = False
            
            embed = discord.Embed(
                title="🚨 SERVER CRASHED / OFFLINE 🚨",
                description="The server is no longer responding to Steam queries. Watchdog loop is scanning for reboots...",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

client.run(TOKEN)
