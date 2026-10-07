import discord
from discord.ext import commands
import json
import asyncio

# Màu sắc giao diện chuẩn (Dark Minimalist)
EMBED_COLOR = discord.Color.from_rgb(43, 45, 49) # 0x2b2d31

# Link GIF hiển thị trên khung Embed (Thay link GIF của bạn vào đây)
GIF_URL = "https://cdn.discordapp.com/attachments/1553393170241425458/1555504362007044178/welcome_shop_NO_VER_DIE.gif?backend=b2&ex=6ac0c3d3&is=6abf7253&hm=e234554accacb62020dd42d71578f52f2f229812c3de0bdfb18edce51893cc9c&"

# Hàm đọc dữ liệu từ file json
def load_data():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# Hàm ghi dữ liệu vào file json
def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Hàm định dạng giá tiền
def format_price(price):
    if isinstance(price, int):
        return f"{price:,} VNĐ"
    price_str = str(price).strip()
    if price_str.isdigit():
        return f"{int(price_str):,} VNĐ"
    return price_str if "đ" in price_str.lower() or "vnd" in price_str.lower() else f"{price_str} VNĐ"

# Nút Đóng Ticket
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Đóng Ticket", style=discord.ButtonStyle.secondary, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Kênh sẽ tự động xóa sau 5 giây...", ephemeral=False)
        
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete()
        except Exception as e:
            print(f"Lỗi khi xóa channel ticket: {e}")

# Menu Thả Xuống (Dropdown Select Menu)
class ProductSelect(discord.ui.Select):
    def __init__(self, products):
        options = []
        for pid, info in products.items():
            mode_label = "Tự động" if info.get("type", "auto") == "auto" else "Ticket"
            count = len(info.get("items", []))
            stock_info = f"Còn {count}" if info.get("type", "auto") == "auto" else "Liên hệ"
            
            price_display = format_price(info.get("price", 0))
            label_text = f"{info['name']} — {price_display}"[:100]

            options.append(
                discord.SelectOption(
                    label=label_text,
                    value=pid,
                    description=f"Loại: {mode_label} | Kho: {stock_info}"
                )
            )

        if not options:
            options.append(discord.SelectOption(label="Hiện chưa có sản phẩm nào", value="none"))

        super().__init__(
            placeholder="Chọn sản phẩm bạn cần mua...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="shop_product_select"
        )

    async def callback(self, interaction: discord.Interaction):
        product_id = self.values[0]
        if product_id == "none":
            await interaction.response.send_message("Chưa có sản phẩm nào để chọn.", ephemeral=True)
            return

        await handle_product_action(interaction, product_id)

# Giao diện chính chứa Menu + Nút Kiểm Tra Kho
class DynamicShopView(discord.ui.View):
    def __init__(self, products):
        super().__init__(timeout=None)
        self.add_item(ProductSelect(products))

        check_btn = discord.ui.Button(
            label="Kiểm Tra Kho Hàng",
            style=discord.ButtonStyle.secondary,
            custom_id="check_stock_all",
            row=1
        )
        check_btn.callback = self.check_stock_callback
        self.add_item(check_btn)

    async def check_stock_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        stock = data.get("stock", {})
        
        if not stock:
            await interaction.followup.send("Cửa hàng hiện chưa có sản phẩm.", ephemeral=True)
            return

        lines = ["**TÌNH TRẠNG KHO HÀNG**\n"]
        for pid, info in stock.items():
            p_type = info.get("type", "auto")
            if p_type == "auto":
                count = len(info.get("items", []))
                status = f"Còn `{count}` SP" if count > 0 else "Hết hàng"
                lines.append(f"• **{info['name']}** (`{pid}`): {status}")
            else:
                lines.append(f"• **{info['name']}** (`{pid}`): Liên hệ / Ticket")

        await interaction.followup.send("\n".join(lines), ephemeral=True)

# Xử lý mua hàng
async def handle_product_action(interaction: discord.Interaction, product_id: str):
    await interaction.response.defer(ephemeral=True)

    data = load_data()
    product_info = data.get("stock", {}).get(product_id, {})
    if not product_info:
        await interaction.followup.send("Sản phẩm không tồn tại hoặc đã bị xóa.", ephemeral=True)
        return

    p_type = product_info.get("type", "auto")
    name = product_info.get("name", "Sản phẩm")
    price = product_info.get("price", 0)
    price_fmt = format_price(price)
    user = interaction.user
    guild = interaction.guild

    # 1. TRƯỜNG HỢP: TẠO TICKET
    if p_type == "ticket":
        category = discord.utils.get(guild.categories, name="TICKETS MUA HÀNG")
        if not category:
            category = await guild.create_category("TICKETS MUA HÀNG")

        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in ["-", "_"])
        channel_name = f"ticket-{clean_username}-{product_id}".lower()
        
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.followup.send(f"Bạn đã có một ticket đang mở: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket mua hàng | {user.name} | SP: {name}"
        )

        embed_ticket = discord.Embed(
            title=f"Ticket Mua Hàng: {name}",
            description=f"Xin chào {user.mention},\nBạn đã tạo ticket để trao đổi cho sản phẩm **{name}**.\n\n"
                        f"• **Mã sản phẩm**: `{product_id}`\n"
                        f"• **Giá bán**: `{price_fmt}`\n\n"
                        f"Quản trị viên sẽ phản hồi và hỗ trợ bạn trong thời gian sớm nhất.",
            color=EMBED_COLOR
        )
        embed_ticket.set_footer(text="Bấm 'Đóng Ticket' bên dưới khi đã hoàn tất giao dịch.")

        await ticket_channel.send(content=f"{user.mention} | Admin sẽ hỗ trợ bạn ngay.", embed=embed_ticket, view=CloseTicketView())
        await interaction.followup.send(f"Đã tạo kênh hỗ trợ giao dịch: {ticket_channel.mention}", ephemeral=True)

    # 2. TRƯỜNG HỢP: BÁN TỰ ĐỘNG (XUẤT VIETQR)
    else:
        items = product_info.get("items", [])
        if not items:
            await interaction.followup.send("Sản phẩm này hiện đang hết hàng. Vui lòng quay lại sau.", ephemeral=True)
            return

        memo = f"SHOP{user.id}"
        bank_id = "MB"          
        account_no = "0345100625" 
        account_name = "LE GIA KHANH" 

        clean_amount = "".join(filter(str.isdigit, str(price)))
        qr_amount = clean_amount if clean_amount else "0"

        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={qr_amount}&addInfo={memo}&accountName={account_name}"

        embed = discord.Embed(
            title=f"Thanh Toán Đơn Hàng: {name}",
            description="Vui lòng chuyển khoản theo thông tin bên dưới hoặc quét mã QR.",
            color=EMBED_COLOR
        )
        embed.add_field(name="Số tiền", value=f"`{price_fmt}`", inline=True)
        embed.add_field(name="Nội dung chuyển khoản", value=f"`{memo}`", inline=True)
        embed.add_field(name="Thông tin tài khoản", value=f"• Ngân hàng: **{bank_id}**\n• Số TK: `{account_no}`\n• Tên TK: **{account_name}**", inline=False)
        embed.set_image(url=qr_url)
        embed.set_footer(text="Sau khi hoàn tất thanh toán, Admin sẽ gửi hàng qua DM cho bạn.")

        await interaction.followup.send(embed=embed, ephemeral=True)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. Lệnh Thêm Sản Phẩm
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addsp(self, ctx, product_id: str, price: str, p_type: str, *, name: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        p_type = p_type.lower()
        if p_type not in ["auto", "ticket"]:
            await ctx.author.send("Loại sản phẩm phải là `auto` (Tự động) hoặc `ticket` (Thủ công)!")
            return

        data = load_data()
        if "stock" not in data:
            data["stock"] = {}

        data["stock"][product_id] = {
            "name": name,
            "price": price,
            "type": p_type,
            "items": data["stock"].get(product_id, {}).get("items", [])
        }
        save_data(data)

        type_text = "Tự động" if p_type == "auto" else "Ticket"
        price_fmt = format_price(price)

        try:
            await ctx.author.send(
                f"Đã thêm/cập nhật sản phẩm thành công:\n"
                f"• Mã SP: `{product_id}`\n"
                f"• Tên SP: **{name}**\n"
                f"• Giá bán: `{price_fmt}`\n"
                f"• Loại: **{type_text}**"
            )
        except discord.Forbidden:
            pass

    # 2. Lệnh Sửa Giá
    @commands.command(name="setgia", aliases=["suagia", "editgia"])
    @commands.has_permissions(administrator=True)
    async def setgia(self, ctx, product_id: str, *, new_price: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        product_id = product_id.lower()
        data = load_data()
        stock = data.get("stock", {})

        if product_id not in stock:
            await ctx.author.send(f"Không tìm thấy sản phẩm có mã `{product_id}`.")
            return

        old_price_fmt = format_price(stock[product_id]["price"])
        stock[product_id]["price"] = new_price
        save_data(data)

        new_price_fmt = format_price(new_price)

        try:
            await ctx.author.send(
                f"Cập nhật giá thành công cho **{stock[product_id]['name']}** (`{product_id}`):\n"
                f"~~{old_price_fmt}~~ ➔ **{new_price_fmt}**"
            )
        except discord.Forbidden:
            pass

    # 3. Lệnh Xóa Sản Phẩm
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def delsp(self, ctx, product_id: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        data = load_data()
        stock = data.get("stock", {})

        if product_id not in stock:
            await ctx.author.send(f"Không tìm thấy sản phẩm có mã `{product_id}`.")
            return

        removed_product = stock.pop(product_id)
        save_data(data)

        try:
            await ctx.author.send(f"Đã xóa sản phẩm **{removed_product.get('name', 'N/A')}** (`{product_id}`).")
        except discord.Forbidden:
            pass

    # 4. Lệnh Nhập Kho
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addstock(self, ctx, product_id: str, *, keys: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        data = load_data()
        stock = data.get("stock", {})

        if product_id not in stock:
            await ctx.author.send(f"Mã sản phẩm `{product_id}` không tồn tại.")
            return

        key_list = [k.strip() for k in keys.splitlines() if k.strip()]
        if not key_list:
            key_list = [k.strip() for k in keys.split() if k.strip()]

        stock[product_id]["items"].extend(key_list)
        save_data(data)

        total_count = len(stock[product_id]["items"])

        try:
            await ctx.author.send(
                f"Đã thêm `{len(key_list)}` sản phẩm vào kho `{product_id}`.\n"
                f"Tổng tồn kho hiện tại: `{total_count}`"
            )
        except discord.Forbidden:
            pass

    # 5. Lệnh Hiển Thị Shop (Đã cập nhật Tiêu đề, Căn chỉnh & Banner GIF)
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def shop(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        data = load_data()
        stock = data.get("stock", {})

        if not stock:
            await ctx.send("Cửa hàng hiện chưa có sản phẩm nào.", delete_after=10)
            return

        embed = discord.Embed(
            title="❖ CHÀO MỪNG ĐẾN VỚI SHOP NO VER DIE! ❖",
            description=(
                "```fix\n"
                "VUI LÒNG CHỌN DỊCH VỤ BẠN MUỐN MUA Ở BÊN DƯỚI\n"
                "```\n"
                "──────────────────────────────────"
            ),
            color=EMBED_COLOR
        )

        for pid, info in stock.items():
            p_type = info.get("type", "auto")
            price_fmt = format_price(info.get("price", 0))

            if p_type == "auto":
                count = len(info.get("items", []))
                status = f"Còn `{count}` SP" if count > 0 else "Hết hàng"
            else:
                status = "Hỗ trợ qua Ticket"

            embed.add_field(
                name=f"✦ {info['name']} (`{pid}`)",
                value=f"• **Giá**: `{price_fmt}`\n• **Trạng thái**: {status}",
                inline=False
            )

        if GIF_URL:
            embed.set_image(url=GIF_URL)

        embed.set_footer(text="Hệ thống hỗ trợ tự động 24/7 • NO VER DIE!")
        await ctx.send(embed=embed, view=DynamicShopView(stock))

    # 6. Lệnh Trả Hàng
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def trahang(self, ctx, member: discord.Member, product_id: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        data = load_data()
        stock = data.get("stock", {}).get(product_id, {})
        items = stock.get("items", [])

        if not items:
            await ctx.send(f"Kho sản phẩm `{product_id}` hiện đang trống.", delete_after=5)
            return

        item_delivered = items.pop(0)
        save_data(data)

        try:
            embed_dm = discord.Embed(
                title="Giao Hàng Thành Công",
                description=f"Cảm ơn bạn đã mua **{stock['name']}**.",
                color=EMBED_COLOR
            )
            embed_dm.add_field(name="Thông tin sản phẩm / Key", value=f"```\n{item_delivered}\n```", inline=False)
            embed_dm.set_footer(text="Cảm ơn bạn đã tin tưởng dịch vụ.")
            await member.send(embed=embed_dm)
            await ctx.send(f"Đã trả hàng cho {member.mention}.", delete_after=5)
        except discord.Forbidden:
            await ctx.send(f"{member.mention} chặn DM! Nội dung: `{item_delivered}`", delete_after=15)

async def setup(bot):
    await bot.add_cog(Shop(bot))
    bot.add_view(CloseTicketView())
    data = load_data()
    stock = data.get("stock", {})
    bot.add_view(DynamicShopView(stock))