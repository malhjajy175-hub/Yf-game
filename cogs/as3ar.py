import asyncio
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
from points import add_solo_points

active_games: dict[int, bool] = {}
BG_PATH = "bg.png"

_BG_CACHE = None
def get_bg():
    global _BG_CACHE
    if _BG_CACHE is None:
        _BG_CACHE = Image.open(BG_PATH).convert("RGBA")
    return _BG_CACHE.copy()

def make_image(title, question):
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_question = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
    except:
        font_title = ImageFont.load_default()
        font_question = font_title
    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tx = (W - (bbox[2]-bbox[0])) / 2
    ty = H * 0.2
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)
    bbox2 = draw.textbbox((0, 0), question, font=font_question)
    qx = (W - (bbox2[2]-bbox2[0])) / 2
    qy = H * 0.5
    draw.text((qx+3, qy+3), question, font=font_question, fill=SHADOW)
    draw.text((qx, qy), question, font=font_question, fill=GOLD)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="game.png")

WORDS = [
    "نجم", "قمر", "شمس", "بحر", "جبل", "نهر", "ريح", "برق", "رعد", "ثلج",
    "أسد", "نمر", "فيل", "ذئب", "غزال", "حصان", "جمل", "نسر", "صقر",
    "تفاح", "موز", "عنب", "تمر", "ليمون", "فراولة",
    "كتاب", "قلم", "ورقة", "مكتب", "كرسي", "طاولة", "حقيبة", "دفتر",
    "هاتف", "شاشة", "كاميرا", "تلفاز", "ثلاجة", "مكيف",
    "سيارة", "طائرة", "قطار", "دراجة",
    "مسجد", "مدرسة", "مستشفى", "مطعم", "فندق", "ملعب",
    "فرح", "حزن", "غضب", "خوف", "أمل", "شجاعة",
]

class As3arCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="أسرع")
    async def as3ar(self, ctx):
        channel_id = ctx.channel.id
        if active_games.get(channel_id):
            await ctx.send("⚠️ هناك لعبة قيد التشغيل!")
            return
        active_games[channel_id] = True
        try:
            word = random.choice(WORDS)
            file = make_image("أسرع", word)
            await ctx.send(file=file)
            def check(m):
                return m.channel.id == channel_id and not m.author.bot and m.content.strip() == word
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
                await ctx.send(f"🔴 انتهى الوقت! الكلمة كانت: **{word}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(As3arCog(bot))
