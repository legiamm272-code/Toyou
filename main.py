import discord
from discord.ext import commands
import os
import json
import asyncio
from flask import Flask
from threading import Thread

# Web Server ngầm hỗ trợ treo 24/7 trên Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot đang hoạt động 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

keep_alive()

# Cấu hình Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Tạo Bot với Prefix linh hoạt (m., M., ., ?)
bot = commands.Bot(command_prefix=["m.", "M.", ".", "?"], intents=intents, help_command=None)

# Tự động nạp toàn bộ Cogs trong thư mục ./cogs
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"📦 Đã tải Cog: cogs.{filename[:-3]}")
            except Exception as e:
                print(f"❌ Lỗi khi tải cogs.{filename[:-3]}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user.name} ({bot.user.id}) đã sẵn sàng hoạt động!")
    await bot.change_presence(activity=discord.Game(name="m.shop | .gg/noverdie"))

async def main():
    async with bot:
        await load_extensions()
        # Token Bot Discord
        token = os.environ.get("DISCORD_TOKEN", "MTU1NTExNjMzNTIzNzk2MzgwMA.Gv6uOQ.ax-ujwd9Y6Zu-xMyEJQXs2qOGMwRL9hfypyem8")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())