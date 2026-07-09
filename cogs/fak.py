import asyncio
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
from points import add_solo_points
from cogs.text_utils import reshape_ar, load_font

active_games: dict[int, bool] = {}
BG_PATH = "bg.png"

_BG_CACHE = None
def get_bg():
    global _BG_CACHE
    if _BG_CACHE is None:
        _BG_CACHE = Image.open(BG_PATH).convert("RGBA")
    return _BG_CACHE.copy()

def make_image(title: str, question: str) -> discord.File:
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    font_title = load_font(37)
    font_question = load_font(60)

    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)

    title = reshape_ar(title)
    question = reshape_ar(question)

    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) / 2
    ty = H * 0.2
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)

    bbox2 = draw.textbbox((0, 0), question, font=font_question)
    qw = bbox2[2] - bbox2[0]
    qx = (W - qw) / 2
    qy = H * 0.5
    draw.text((qx+3, qy+3), question, font=font_question, fill=SHADOW)
    draw.text((qx, qy), question, font=font_question, fill=GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="game.png")

WORDS = [
    "كتاب", "قلم", "بيت", "شجرة", "سيارة", "طائرة", "مدرسة", "مستشفى",
    "جبال", "بحيرة", "صحراء", "غابة", "نجمة", "قمر", "شمس", "سحابة",
    "أسد", "نمر", "فيل", "ذئب", "غزال", "حصان", "جمل", "نسر", "صقر",
    "تفاحة", "موزة", "عنب", "تمر", "ليمون", "فراولة",
    "كتاب", "قلم", "ورقة", "مكتب", "كرسي", "طاولة", "حقيبة", "دفتر",
    "هاتف", "شاشة", "كاميرا", "تلفاز", "ثلاجة", "مكيف",
    "سيارة", "طائرة", "قطار", "دراجة",
    "كرسي", "طاولة", "نافذة", "حقيبة", "ساعة", "نظارة",
    "مطار", "ميناء", "جسر", "شارع", "ملعب", "مسجد",
    "طبيب", "مهندس", "معلم", "شاعر", "لاعب", "بطل",
    "فرح", "حزن", "غضب", "خوف", "أمل", "شجاعة",
]

def scramble(word):
    chars = list(word)
    random.shuffle(chars)
    while ''.join(chars) == word and len(word) > 1:
        random.shuffle(chars)
    return ''.join(chars)

class FakCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="فك")
    async def fak(self, ctx):
        channel_id = ctx.channel.id
        if active_games.get(channel_id):
            await ctx.send("⚠️ هناك لعبة قيد التشغيل!")
            return
        active_games[channel_id] = True
        try:
            answer = random.choice(WORDS)
            scrambled = scramble(answer)
            file = await asyncio.to_thread(make_image, "فك", scrambled)
            await ctx.send(file=file)
            def check(m):
                return m.channel.id == channel_id and not m.author.bot
            end_time = asyncio.get_event_loop().time() + 10
            winner = None
            while True:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    msg = await self.bot.wait_for("message", timeout=remaining, check=check)
                except asyncio.TimeoutError:
                    break
                if msg.content.strip() == answer:
                    winner = msg.author
                    break
            if winner:
                await add_solo_points(winner.id)
                await ctx.send(f"✅ فاز بنقطة (+1) {winner.mention}! إجابة صحيحة")
            else:
                await ctx.send(f"🔴 انتهى الوقت! الكلمة كانت: **{answer}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(FakCog(bot))
