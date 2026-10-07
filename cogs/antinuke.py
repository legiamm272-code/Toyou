import discord
from discord.ext import commands
import time
import json
import os
from collections import defaultdict

def load_whitelist():
    if os.path.exists("whitelist.json"):
        try:
            with open("whitelist.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert list back to set
                return defaultdict(set, {int(k): set(v) for k, v in data.items()})
        except Exception:
            return defaultdict(set)
    return defaultdict(set)

def save_whitelist(whitelist_data):
    # Convert set to list for JSON serialization
    serializable = {str(k): list(v) for k, v in whitelist_data.items()}
    with open("whitelist.json", "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=4)

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cấu hình ngưỡng phát hiện phá hoại
        self.MAX_ACTIONS = 3   # Tối đa 3 hành động
        self.TIME_WINDOW = 10  # Trong vòng 10 giây

        # Lưu lịch sử thao tác: guild_id -> user_id -> action_type -> [timestamps]
        self.action_logs = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # Danh sách ngoại lệ (Whitelist)
        self.whitelist = load_whitelist()

    # -------------------------------------------------------------
    # HÀM KIỂM TRA VÀ XỬ LÝ KẺ PHÁ HOẠI
    # -------------------------------------------------------------
    async def check_nuke_limit(self, guild: discord.Guild, user: discord.User, action_type: str):
        if not guild or not user:
            return False

        # Bỏ qua nếu là Bot, Chủ Server hoặc người dùng trong Whitelist
        if user.id == self.bot.user.id or user.id == guild.owner_id:
            return False

        if user.id in self.whitelist[guild.id]:
            return False

        now = time.time()
        timestamps = self.action_logs[guild.id][user.id][action_type]
        
        # Lọc các mốc thời gian trong khoảng TIME_WINDOW (10s)
        timestamps = [t for t in timestamps if now - t <= self.TIME_WINDOW]
        timestamps.append(now)
        self.action_logs[guild.id][user.id][action_type] = timestamps

        # Nếu vượt quá ngưỡng cho phép -> BẮT ĐẦU XỬ LÝ (PUNISH)
        if len(timestamps) >= self.MAX_ACTIONS:
            await self.punish_nuker(guild, user, f"Lỗi Nuke Server: {action_type} quá {self.MAX_ACTIONS} lần/{self.TIME_WINDOW}s")
            return True
        return False

    async def punish_nuker(self, guild: discord.Guild, user: discord.User, reason: str):
        # 1. Cấm (BAN) kẻ phá hoại
        try:
            await guild.ban(user, reason=f"[ANTI-NUKE] {reason}")
            print(f"🚨 [ANTI-NUKE] Đã BAN kẻ phá hoại {user} ({user.id}) trên server {guild.name}.")
        except Exception as e:
            print(f"❌ Không thể BAN kẻ phá hoại {user.id}: {e}")
            # Nếu không BAN được thì gỡ hết Role quản trị của họ
            try:
                member = guild.get_member(user.id)
                if member:
                    dangerous_roles = [r for r in member.roles if r.permissions.administrator or r.permissions.manage_guild or r.permissions.manage_channels or r.permissions.manage_roles]
                    await member.remove_roles(*dangerous_roles, reason=f"[ANTI-NUKE] {reason}")
            except Exception as ex:
                print(f"❌ Lỗi gỡ Role kẻ phá hoại: {ex}")

        # 2. Báo động trực tiếp qua DM cho Chủ Server (Guild Owner)
        try:
            owner = guild.owner
            if owner:
                embed = discord.Embed(
                    title="🚨 BÁO ĐỘNG ANTI-NUKE SERVER!",
                    description=(
                        f"Hệ thống vừa tự động **BAN** kẻ phá hoại khỏi Server **{guild.name}**!\n\n"
                        f"👤 **Kẻ phá hoại:** {user.mention} (`{user.name}` - ID: `{user.id}`)\n"
                        f"📌 **Lý do:** {reason}"
                    ),
                    color=discord.Color.red()
                )
                if user.display_avatar:
                    embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text="Anti-Nuke Protection System")
                await owner.send(embed=embed)
        except Exception as e:
            print(f"Lỗi gửi tin nhắn cho Owner: {e}")

    # -------------------------------------------------------------
    # THEO DÕI SỰ KIỆN AUDIT LOGS (LISTENERS)
    # -------------------------------------------------------------
    
    # 1. Giám sát xóa Kênh (Channel Delete)
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    executor = entry.user
                    await self.check_nuke_limit(guild, executor, "Xóa Kênh (Channel Delete)")
                    break
        except Exception as e:
            print(f"Lỗi Anti-Nuke Channel Delete: {e}")

    # 2. Giám sát xóa Role (Role Delete)
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id:
                    executor = entry.user
                    await self.check_nuke_limit(guild, executor, "Xóa Role (Role Delete)")
                    break
        except Exception as e:
            print(f"Lỗi Anti-Nuke Role Delete: {e}")

    # 3. Giám sát Ban thành viên hàng loạt (Mass Ban)
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    executor = entry.user
                    await self.check_nuke_limit(guild, executor, "Ban Thành Viên (Mass Ban)")
                    break
        except Exception as e:
            print(f"Lỗi Anti-Nuke Mass Ban: {e}")

    # 4. Giám sát thêm Bot lạ vào Server (Anti-Bot Add)
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            return

        guild = member.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    executor = entry.user
                    
                    # Nếu người thêm Bot KHÔNG PHẢI Owner và KHÔNG TRONG Whitelist
                    if executor.id != guild.owner_id and executor.id not in self.whitelist[guild.id]:
                        # Ban Bot mới chui vào
                        await member.ban(reason="[ANTI-NUKE] Bot lạ được thêm bởi người không có quyền Whitelist!")
                        # Ban luôn kẻ đã mời Bot
                        await self.punish_nuker(guild, executor, f"Tự ý mời Bot lạ ({member.name}) vào Server")
                    break
        except Exception as e:
            print(f"Lỗi Anti-Bot Add: {e}")

    # -------------------------------------------------------------
    # LỆNH QUẢN LÝ WHITELIST (CHỈ OWNER MỚI ĐƯỢC DÙNG)
    # -------------------------------------------------------------
    @commands.command(name="whitelist", aliases=["wl"])
    async def whitelist_cmd(self, ctx, member: discord.Member = None):
        """Thêm hoặc xóa người dùng khỏi danh sách tin tưởng Anti-Nuke (Chỉ Owner): m.whitelist @User"""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ **Chỉ Chủ Server (Owner)** mới có quyền quản lý Whitelist Anti-Nuke!")
            return

        # Nếu không tag ai -> Hiển thị danh sách Whitelist
        if not member:
            wl_set = self.whitelist[ctx.guild.id]
            if not wl_set:
                await ctx.send("📋 Danh sách Whitelist Anti-Nuke hiện đang **trống**.")
                return

            users_str = "\n".join([f"- <@{uid}> (`{uid}`)" for uid in wl_set])
            embed = discord.Embed(
                title="📋 DANH SÁCH WHITELIST ANTI-NUKE",
                description=users_str,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        # Bật/Tắt Whitelist cho member được tag
        if member.id in self.whitelist[ctx.guild.id]:
            self.whitelist[ctx.guild.id].remove(member.id)
            save_whitelist(self.whitelist)
            await ctx.send(f"➖ Đã **XÓA** {member.mention} khỏi danh sách Whitelist Anti-Nuke!")
        else:
            self.whitelist[ctx.guild.id].add(member.id)
            save_whitelist(self.whitelist)
            await ctx.send(f"➕ Đã **THÊM** {member.mention} vào danh sách Whitelist Anti-Nuke (Miễn trừ kiểm tra)!")

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))