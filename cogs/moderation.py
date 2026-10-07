import discord
from discord.ext import commands
import datetime
import json
import os

# Hàm đọc dữ liệu file config/data.json
def load_config():
    try:
        if os.path.exists("data.json"):
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

# Hàm ghi dữ liệu file config/data.json
def save_config(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =============================================================
    # 1. HỆ THỐNG CHÀO MỪNG (SET WELCOME, MSG, GIF & PREVIEW)
    # =============================================================
    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def set_welcome(self, ctx, channel: discord.TextChannel = None):
        """Cài đặt kênh gửi tin nhắn chào mừng: m.setwelcome #kênh"""
        channel = channel or ctx.channel
        data = load_config()
        
        if "welcome_channel" not in data:
            data["welcome_channel"] = {}
            
        data["welcome_channel"][str(ctx.guild.id)] = channel.id
        save_config(data)

        await ctx.send(f"✅ Đã đặt kênh chào mừng thành công tại {channel.mention}!")

    @commands.command(name="setwelcomemsg", aliases=["setmsg", "welcomemsg"])
    @commands.has_permissions(administrator=True)
    async def set_welcome_msg(self, ctx, *, message: str):
        """Cài đặt nội dung tin nhắn chào mừng: m.setwelcomemsg <nội dung>"""
        data = load_config()
        
        if "welcome_message" not in data:
            data["welcome_message"] = {}
            
        data["welcome_message"][str(ctx.guild.id)] = message
        save_config(data)

        await ctx.send("✅ Đã cập nhật nội dung chào mừng! Dùng lệnh `m.testwelcome` để xem trước giao diện.")

    @commands.command(name="setwelcomegif", aliases=["setgif", "welcomegif"])
    @commands.has_permissions(administrator=True)
    async def set_welcome_gif(self, ctx, url: str):
        """Cài đặt link ảnh GIF chào mừng: m.setwelcomegif <link_gif>"""
        data = load_config()
        if "welcome_gif" not in data:
            data["welcome_gif"] = {}
            
        if url.startswith("http://") or url.startswith("https://"):
            data["welcome_gif"][str(ctx.guild.id)] = url
            save_config(data)
            await ctx.send("✅ Đã cập nhật ảnh GIF chào mừng! Dùng lệnh `m.testwelcome` để xem trước giao diện.")
        else:
            await ctx.send("❌ Link ảnh GIF không hợp lệ! Link phải bắt đầu bằng `http://` hoặc `https://`.")

    @commands.command(name="testwelcome", aliases=["previewwelcome"])
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Xem trước tin nhắn chào mừng hoàn chỉnh"""
        data = load_config()
        
        default_msg = (
            "### CHÀO MỪNG {user} Đến với **{server}**!\n\n"
            "**Đến Với {server} Được Yêu Thương!**\n\n"
            "Hoà Đồng Hợp Tác Với **{server}**!\n"
            "Các Thành Viên Đều Là Gia Đình!\n"
            "Ở Đâu Vứt Bỏ Bạn **{server}** Chào Đón!\n"
            "Sống Tốt Ngẩng Cao Đầu\n\n"
            "---**{server} KHÔNG BỎ RƠI AI!**---"
        )
        raw_msg = data.get("welcome_message", {}).get(str(ctx.guild.id), default_msg)

        try:
            formatted_msg = raw_msg.format(
                user=ctx.author.mention,
                name=ctx.author.display_name,
                server=ctx.guild.name,
                count=ctx.guild.member_count
            )
        except Exception:
            formatted_msg = raw_msg

        # Embed chuẩn style tối giản như Discord gốc
        embed = discord.Embed(
            description=formatted_msg,
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        gif_url = data.get("welcome_gif", {}).get(str(ctx.guild.id))
        if gif_url:
            embed.set_image(url=gif_url)

        embed.set_footer(text="Join server!")

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Tự động gửi tin nhắn khi có thành viên mới gia nhập Server"""
        data = load_config()
        channel_id = data.get("welcome_channel", {}).get(str(member.guild.id))
        
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel:
                default_msg = (
                    "### CHÀO MỪNG {user} Đến với **{server}**!\n\n"
                    "**Đến Với {server} Được Yêu Thương!**\n\n"
                    "Hoà Đồng Hợp Tác Với **{server}**!\n"
                    "Các Thành Viên Đều Là Gia Đình!\n"
                    "Ở Đâu Vứt Bỏ Bạn **{server}** Chào Đón!\n"
                    "Sống Tốt Ngẩng Cao Đầu\n\n"
                    "---**{server} KHÔNG BỎ RƠI AI!**---"
                )
                raw_msg = data.get("welcome_message", {}).get(str(member.guild.id), default_msg)

                try:
                    formatted_msg = raw_msg.format(
                        user=member.mention,
                        name=member.display_name,
                        server=member.guild.name,
                        count=member.guild.member_count
                    )
                except Exception:
                    formatted_msg = raw_msg

                embed = discord.Embed(
                    description=formatted_msg,
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )

                gif_url = data.get("welcome_gif", {}).get(str(member.guild.id))
                if gif_url:
                    embed.set_image(url=gif_url)

                embed.set_footer(text="Join server!")

                await channel.send(embed=embed)

    # =============================================================
    # 2. QUẢN LÝ VAI TRÒ (ADD / REMOVE ROLE)
    # =============================================================
    @commands.command(name="addrole")
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        """Thêm Role cho thành viên: m.addrole @User @Role"""
        try:
            if role in member.roles:
                await ctx.send(f"⚠️ {member.mention} đã có role **{role.name}** từ trước!")
                return
            await member.add_roles(role)
            await ctx.send(f"✅ Đã thêm role **{role.name}** cho {member.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Không thể thêm role: `{e}`")

    @commands.command(name="removerole")
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        """Xóa Role của thành viên: m.removerole @User @Role"""
        try:
            if role not in member.roles:
                await ctx.send(f"⚠️ {member.mention} không có role **{role.name}**!")
                return
            await member.remove_roles(role)
            await ctx.send(f"✅ Đã xóa role **{role.name}** khỏi {member.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Không thể xóa role: `{e}`")

    # =============================================================
    # 3. QUẢN TRỊ THÀNH VIÊN (KICK / BAN / UNBAN)
    # =============================================================
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Đuổi thành viên khỏi server: m.kick @User [Lý do]"""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ Bạn không thể Kick người có vị trí Role cao hơn hoặc bằng bạn!")
            return
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 Đã kick **{member.display_name}** ra khỏi Server. Lý do: `{reason}`")
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi kick: `{e}`")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Cấm vĩnh viễn thành viên: m.ban @User [Lý do]"""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ Bạn không thể Ban người có vị trí Role cao hơn hoặc bằng bạn!")
            return
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 Đã ban vĩnh viễn **{member.display_name}**. Lý do: `{reason}`")
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi ban: `{e}`")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        """Bỏ ban thành viên bằng ID: m.unban <ID_User>"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"🔓 Đã bỏ Ban cho **{user.name}** (`{user_id}`)!")
        except discord.NotFound:
            await ctx.send("❌ Không tìm thấy User này trong danh sách bị Ban!")
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi unban: `{e}`")

    # =============================================================
    # 4. CHẶN CHAT (MUTE / UNMUTE)
    # =============================================================
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Không có lý do"):
        """Chặn chat thành viên (Timeout): m.mute @User [Số phút] [Lý do]"""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ Bạn không thể Mute người có vị trí Role cao hơn hoặc bằng bạn!")
            return
        try:
            duration = datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await ctx.send(f"🔇 Đã cấm chat **{member.display_name}** trong `{minutes}` phút. Lý do: `{reason}`")
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi mute: `{e}`")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Gỡ cấm chat thành viên: m.unmute @User"""
        try:
            await member.timeout(None)
            await ctx.send(f"🔊 Đã gỡ cấm chat cho **{member.display_name}**!")
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi unmute: `{e}`")

    # =============================================================
    # 5. QUẢN LÝ KÊNH & XÓA TIN NHẮN (LOCK / UNLOCK / CLEAR)
    # =============================================================
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Khóa kênh hiện tại: m.lock"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.send("🔒 **Kênh này đã bị khóa.** Thành viên không thể gửi tin nhắn nữa!")
        except Exception as e:
            await ctx.send(f"❌ Không thể khóa kênh: `{e}`")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Mở khóa kênh hiện tại: m.unlock"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = True
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.send("🔓 **Kênh đã được mở khóa.** Chúc mọi người chat vui vẻ!")
        except Exception as e:
            await ctx.send(f"❌ Không thể mở khóa kênh: `{e}`")

    @commands.command(name="clear", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        """Xóa số lượng tin nhắn trong kênh: m.clear <số_lượng>"""
        if amount <= 0:
            await ctx.send("❌ Số lượng tin nhắn xóa phải lớn hơn 0!")
            return
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await ctx.send(f"🧹 Đã xóa **{len(deleted)-1}** tin nhắn!", delete_after=3)
        except Exception as e:
            await ctx.send(f"❌ Không thể xóa tin nhắn: `{e}`")

async def setup(bot):
    await bot.add_cog(Moderation(bot))