import discord
from discord.ext import commands
import json
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_data(self):
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_balance(self, user_id):
        data = self.get_data()
        return data["users"].get(str(user_id), {}).get("balance", 0)

    def add_balance(self, user_id, amount):
        data = self.get_data()
        user_str = str(user_id)
        if user_str not in data["users"]:
            data["users"][user_str] = {"balance": 0}
        data["users"][user_str]["balance"] += amount
        self.save_data(data)

    # Lệnh xem số dư: m.bal
    @commands.command(aliases=["balance", "money"])
    async def bal(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        balance = self.get_balance(target.id)
        
        embed = discord.Embed(
            title=f"🌸 Ví tiền của {target.display_name}",
            description=f"Số dư hiện tại: **{balance:,} 🪙**",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    # Lệnh nhận tiền hàng ngày: m.daily
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user) # Cooldown 24 giờ
    async def daily(self, ctx):
        reward = random.randint(100, 500)
        self.add_balance(ctx.author.id, reward)
        
        embed = discord.Embed(
            description=f"🎉 Bạn đã nhận được **{reward} 🪙** quà điểm danh hàng ngày!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @daily.error
    async def daily_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            hours = int(error.retry_after // 3600)
            minutes = int((error.retry_after % 3600) // 60)
            await ctx.send(f"⏳ Bạn đã nhận quà hôm nay rồi. Vui lòng quay lại sau `{hours}h {minutes}m`!")

async def setup(bot):
    await bot.add_cog(Economy(bot))