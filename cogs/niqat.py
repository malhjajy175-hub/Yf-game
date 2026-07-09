import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
from points import get_points, transfer_points

PROFILE_BG = "profile.png"

# كاش للصور الشخصية لتسريع الأمر
_avatar_cache: dict[int, bytes] = {}

class NiqatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="فلوس")
    async def floos(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        pts = await get_points(member.id)
        solo = pts["solo"]
        group = pts["group"]
        total = solo + group

        # استخدم الكاش إذا الصورة محفوظة
        if member.id in _avatar_cache:
            avatar_data = _avatar_cache[member.id]
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(member.display_avatar.url)) as resp:
                    avatar_data = await resp.read()
            _avatar_cache[member.id] = avatar_data

        img = Image.open(PROFILE_BG).convert("RGBA")
        draw = ImageDraw.Draw(img)
        W, H = img.size

        GOLD = (255, 215, 0, 255)
        SHADOW = (0, 0, 0, 200)

        # --- الصورة الشخصية (افاتار) داخل الدائرة الذهبية الكبيرة ---
        # الدائرة الذهبية: مركزها ~50.08% عرض، ~21.6% ارتفاع، وقطرها ~32.54% من العرض
        avatar_size = int(W * 0.3254)
        avatar_cx = int(W * 0.5008)
        avatar_cy = int(H * 0.2160)

        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        avatar_img = avatar_img.resize((avatar_size, avatar_size))
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
        avatar_circle = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        avatar_circle.paste(avatar_img, mask=mask)

        ax = avatar_cx - avatar_size // 2
        ay = avatar_cy - avatar_size // 2
        img.paste(avatar_circle, (ax, ay), avatar_circle)

        # --- الأرقام داخل دوائر البادجات الثلاث ---
        # كل دائرة بادج مركزها ~14.58% عرض، وقطرها ~14.66% من العرض
        badge_cx = int(W * 0.1458)
        badge_diam = W * 0.1466

        y1 = int(H * 0.5583)
        y2 = int(H * 0.7186)
        y3 = int(H * 0.8807)

        font_size = int(badge_diam * 0.55)
        try:
            font_num = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font_num = ImageFont.load_default()

        for val, cy in [(solo, y1), (group, y2), (total, y3)]:
            num_str = str(val)
            bbox = draw.textbbox((0, 0), num_str, font=font_num)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            # نحسب نقطة الرسم بحيث يكون منتصف النص فعليًا على مركز الدائرة
            x = badge_cx - text_w // 2 - bbox[0]
            y = cy - text_h // 2 - bbox[1]
            draw.text((x+2, y+2), num_str, font=font_num, fill=SHADOW)
            draw.text((x, y), num_str, font=font_num, fill=GOLD)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename="floos.png"))

    @commands.command(name="تحويل")
    async def tahweel(self, ctx, member: discord.Member = None, amount: int = None):
        if member is None:
            await ctx.send("❌ لازم تذكر شخص! مثال: `!تحويل @شخص 10`")
            return
        if amount is None:
            await ctx.send("❌ لازم تذكر عدد النقاط! مثال: `!تحويل @شخص 10`")
            return
        if amount <= 0:
            await ctx.send("❌ الرقم لازم يكون أكبر من 0!")
            return
        if member.id == ctx.author.id:
            await ctx.send("❌ ما تقدر تحول لنفسك!")
            return
        if member.bot:
            await ctx.send("😂 البوت ما يحتاج منك شفقة يا فقير!")
            return
        success = await transfer_points(ctx.author.id, member.id, amount)
        if success:
            await ctx.send(f"✅ تم تحويل **{amount}** نقطة من {ctx.author.mention} إلى {member.mention}!")
        else:
            pts = await get_points(ctx.author.id)
            total = pts["solo"] + pts["group"]
            await ctx.send(f"❌ ما عندك نقاط كافية! عندك **{total}** نقطة فقط.")

async def setup(bot):
    await bot.add_cog(NiqatCog(bot))

    
