import discord
from discord.ext import commands
import asyncio

# Nút đóng Ticket
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Đóng Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        try:
            await interaction.response.edit_message(view=self)
        except Exception:
            pass

        await interaction.followup.send("⌛ Ticket sẽ tự động xóa sau 5 giây...", ephemeral=False)
        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete()
        except Exception as e:
            print(f"Lỗi khi xóa kênh ticket: {e}")

# Nút bấm tạo Ticket nhận Danh mục từ Embed
class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Tạo Ticket Hỗ Trợ", style=discord.ButtonStyle.primary, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        if not guild:
            await interaction.followup.send("❌ Lệnh này chỉ hoạt động trong Server!", ephemeral=True)
            return

        # ⚡ Tự động kiểm tra & tạo 2 Role quản trị nếu chưa có
        admin_role = discord.utils.get(guild.roles, name="Admin Ticket")
        support_role = discord.utils.get(guild.roles, name="Hỗ Trợ Ticket")

        if not admin_role:
            try:
                admin_role = await guild.create_role(
                    name="Admin Ticket",
                    color=discord.Color.red(),
                    mentionable=True,
                    reason="Tự động tạo Role Admin Ticket"
                )
            except discord.Forbidden:
                admin_role = None

        if not support_role:
            try:
                support_role = await guild.create_role(
                    name="Hỗ Trợ Ticket",
                    color=discord.Color.blue(),
                    mentionable=True,
                    reason="Tự động tạo Role Hỗ Trợ Ticket"
                )
            except discord.Forbidden:
                support_role = None

        # ⚡ Lấy tên Danh mục từ Footer của Embed tin nhắn
        category_name = "🎫-TICKETS HỖ TRỢ"
        if interaction.message and interaction.message.embeds:
            footer_text = interaction.message.embeds[0].footer.text
            if footer_text and "Category: " in footer_text:
                category_name = footer_text.split("Category: ")[1].strip()

        # Tìm hoặc tạo Danh mục theo yêu cầu
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            try:
                category = await guild.create_category(category_name)
            except discord.Forbidden:
                await interaction.followup.send("❌ Bot thiếu quyền `Manage Channels` để tạo danh mục Ticket!", ephemeral=True)
                return

        # Chuẩn hóa tên kênh ticket
        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in ["-", "_"])
        if not clean_username:
            clean_username = f"user-{user.id}"
        channel_name = f"ticket-{clean_username}"

        # Kiểm tra xem người dùng đã mở ticket trong danh mục này chưa
        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
        if existing_channel:
            await interaction.followup.send(f"⚠️ Bạn đã có một ticket đang mở tại {existing_channel.mention}!", ephemeral=True)
            return

        # ⚡ Phân quyền riêng tư (User + Bot + Admin Ticket + Hỗ Trợ Ticket)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket hỗ trợ của {user.name} ({user.id})"
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot thiếu quyền tạo kênh Discord trong server!", ephemeral=True)
            return

        # ⚡ Tạo danh sách Tag tên người tạo + Role hỗ trợ
        pings = [user.mention]
        if admin_role:
            pings.append(admin_role.mention)
        if support_role:
            pings.append(support_role.mention)
        ping_content = " | ".join(pings)

        embed = discord.Embed(
            title=f"🎫 TICKET HỖ TRỢ CỦA {user.display_name.upper()}",
            description="Chào bạn! Vui lòng mô tả chi tiết vấn đề hoặc thắc mắc của bạn bên dưới. Ban quản trị sẽ hỗ trợ bạn sớm nhất có thể.",
            color=discord.Color.brand_green()
        )
        embed.set_footer(text="Bấm vào nút bên dưới khi bạn muốn đóng ticket này.")

        await ticket_channel.send(content=f"{ping_content} - Ban Quản Trị hãy vào hỗ trợ khách hàng!", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ Đã tạo ticket thành công tại {ticket_channel.mention}", ephemeral=True)

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Cú pháp: m.ticket [Tên Danh Mục]
    # Ví dụ: m.ticket 💎-NẠP TIỀN & THANH TOÁN
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx, *, category_name: str = "🎫-TICKETS HỖ TRỢ"):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        # ⚡ Tự động tạo 2 Role ngay khi chạy lệnh cài đặt ticket
        guild = ctx.guild
        if guild:
            admin_role = discord.utils.get(guild.roles, name="Admin Ticket")
            if not admin_role:
                try:
                    await guild.create_role(name="Admin Ticket", color=discord.Color.red(), mentionable=True)
                except Exception:
                    pass

            support_role = discord.utils.get(guild.roles, name="Hỗ Trợ Ticket")
            if not support_role:
                try:
                    await guild.create_role(name="Hỗ Trợ Ticket", color=discord.Color.blue(), mentionable=True)
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎫 TRUNG TÂM HỖ TRỢ / TICKET SYSTEM",
            description=f"Nếu bạn cần trợ giúp về **{category_name}**, hãy bấm vào nút **📩 Tạo Ticket Hỗ Trợ** bên dưới!",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Category: {category_name}")

        await ctx.send(embed=embed, view=TicketLaunchView())

async def setup(bot):
    await bot.add_cog(Ticket(bot))
    bot.add_view(TicketLaunchView())
    bot.add_view(CloseTicketView())