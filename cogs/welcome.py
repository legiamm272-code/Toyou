import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Chọn channel gửi tin nhắn chào mừng (thay ID channel của bạn vào đây)
        channel = member.guild.system_channel
        if channel:
            embed = discord.Embed(
                title=f"🌸 WELCOME TO {member.guild.name.upper()}! 🌸",
                description=f"Chào mừng {member.mention} đã đến với server!\n• Hãy đọc nội quy và nhận role trải nghiệm nhé.",
                color=discord.Color.from_rgb(255, 192, 203)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Thành viên thứ #{len(member.guild.members)}")
            
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))