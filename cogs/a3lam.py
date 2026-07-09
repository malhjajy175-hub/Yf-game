import asyncio
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
from points import add_solo_points

active_games: dict[int, bool] = {}
BG_PATH = "bg.png"

_BG_CACHE = None
def get_bg():
    global _BG_CACHE
    if _BG_CACHE is None:
        _BG_CACHE = Image.open(BG_PATH).convert("RGBA")
    return _BG_CACHE.copy()

COUNTRIES = [
    ("السعودية", "sa"), ("مصر", "eg"), ("الإمارات", "ae"), ("الكويت", "kw"),
    ("قطر", "qa"), ("البحرين", "bh"), ("عُمان", "om"), ("اليمن", "ye"),
    ("العراق", "iq"), ("سوريا", "sy"), ("لبنان", "lb"), ("الأردن", "jo"),
    ("فلسطين", "ps"), ("ليبيا", "ly"), ("تونس", "tn"), ("الجزائر", "dz"),
    ("المغرب", "ma"), ("السودان", "sd"), ("فرنسا", "fr"), ("ألمانيا", "de"),
    ("إيطاليا", "it"), ("إسبانيا", "es"), ("البرتغال", "pt"), ("هولندا", "nl"),
    ("السويد", "se"), ("النرويج", "no"), ("الدنمارك", "dk"), ("تركيا", "tr"),
    ("روسيا", "ru"), ("إنجلترا", "gb"), ("الولايات المتحدة", "us"), ("كندا", "ca"),
    ("البرازيل", "br"), ("الأرجنتين", "ar"), ("الصين", "cn"), ("اليابان", "jp"),
    ("كوريا الجنوبية", "kr"), ("الهند", "in"), ("باكستان", "pk"), ("إيران", "ir"),
    ("إندونيسيا", "id"), ("ماليزيا", "my"), ("أستراليا", "au"), ("جنوب أفريقيا", "za"),
    ("نيجيريا", "ng"), ("كينيا", "ke"), ("إثيوبيا", "et"), ("غانا", "gh"),
]

async def make_image(flag_code: str) -> discord.File:
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font_title = ImageFont.load_default()

    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)

    title = "علم"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) / 2
    ty = H * 0.05
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)

    flag_url = f"https://flagcdn.com/w320/{flag_code}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(flag_url) as resp:
            flag_data = await resp.read()

    flag_img = Image.open(io.BytesIO(flag_data)).convert("RGBA")
    flag_w = int(W * 0.55)
    flag_h = int(flag_w * flag_img.height / flag_img.width)
    flag_img = flag_img.resize((flag_w, flag_h))
    fx = (W - flag_w) // 2
    fy = (H - flag_h) // 2 + 20
    img.paste(flag_img, (fx, fy), flag_img)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="flag.png")

class A3lamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="اعلام")
    async def a3lam(self, ctx):
        channel_id = ctx.channel.id
        if active_games.get(channel_id):
            await ctx.send("⚠️ هناك لعبة قيد التشغيل!")
            return
        active_games[channel_id] = True
        try:
            country_name, flag_code = random.choice(COUNTRIES)
            file = await make_image(flag_code)
            await ctx.send(file=file)

            def check(m):
                return m.channel.id == channel_id and not m.author.bot and m.content.strip() == country_name

            end_time = asyncio.get_event_loop().time() + 10
            winner = None
            while True:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    msg = await self.bot.wait_for("message", timeout=remaining, check=check)
                    winner = msg.author
                    break
                except asyncio.TimeoutError:
                    break

            if winner:
                await add_solo_points(winner.id)
                await ctx.send(f"✅ إجابة صحيحة! {winner.mention} فاز بنقطة (+1)")
            else:
                await ctx.send(f"🔴 انتهى الوقت! الدولة كانت: **{country_name}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(A3lamCog(bot))
    
