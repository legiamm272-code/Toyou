import discord
from discord.ext import commands
import json

class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_data(self):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": {}, "autoresponders": {}}

    def save_data(self, data):
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # Lệnh thêm trigger phản hồi: m.ar create <từ_khóa> | <nội_dung_trả_lời>
    @commands.command(name="ar")
    @commands.has_permissions(administrator=True)
    async def create_ar(self, ctx, *, args: str):
        if "|" not in args:
            await ctx.send("❌ Cú pháp sai! Sử dụng: `m.ar từ_khóa | nội dung trả lời`")
            return
        
        trigger, response = [x.strip() for x in args.split("|", 1)]
        data = self.load_data()
        data["autoresponders"][trigger.lower()] = response
        self.save_data(data)
        
        await ctx.send(f"✅ Đã tạo auto-responder cho từ khóa: `{trigger}`")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        data = self.load_data()
        msg_content = message.content.lower().strip()

        if msg_content in data.get("autoresponders", {}):
            await message.channel.send(data["autoresponders"][msg_content])

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))