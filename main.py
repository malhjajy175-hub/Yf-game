import asyncio
import discord
import subprocess
from discord.ext import commands
from config import TOKEN, PREFIX
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

subprocess.run(["pip", "install", "motor"], check=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    def log_message(self, *args):
        pass

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server.serve_forever()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ البوت شغال الآن: {bot.user}")

async def load_cogs():
    await bot.load_extension("cogs.hisab")
    await bot.load_extension("cogs.jam3")
    await bot.load_extension("cogs.mufrad")
    await bot.load_extension("cogs.as3ar")
    await bot.load_extension("cogs.rabt")
    await bot.load_extension("cogs.aks")
    await bot.load_extension("cogs.fak")
    await bot.load_extension("cogs.s7_5ata")
    await bot.load_extension("cogs.kat")
    await bot.load_extension("cogs.niqat")
    await bot.load_extension("cogs.a3lam")
    await bot.load_extension("cogs.sha3ar")

async def main():
    threading.Thread(target=run_server, daemon=True).start()
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
