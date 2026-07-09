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

def make_image(title: str, question: str) -> discord.File:
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_question = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    except:
        font_title = ImageFont.load_default()
        font_question = font_title
    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)
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

QUESTIONS = [
    ("كتاب", "كتب"), ("قلم", "أقلام"), ("بيت", "بيوت"), ("ولد", "أولاد"),
    ("بنت", "بنات"), ("شجرة", "أشجار"), ("سيارة", "سيارات"), ("طالب", "طلاب"),
    ("مدرسة", "مدارس"), ("باب", "أبواب"), ("نافذة", "نوافذ"), ("كرسي", "كراسي"),
    ("طاولة", "طاولات"), ("حقيبة", "حقائب"), ("صورة", "صور"), ("لون", "ألوان"),
    ("صوت", "أصوات"), ("يد", "أيدي"), ("عين", "عيون"), ("قلب", "قلوب"),
    ("وجه", "وجوه"), ("رأس", "رؤوس"), ("فم", "أفواه"), ("أنف", "أنوف"),
    ("صديق", "أصدقاء"), ("أخ", "إخوة"), ("أب", "آباء"), ("أم", "أمهات"),
    ("ملك", "ملوك"), ("طبيب", "أطباء"), ("معلم", "معلمون"), ("مهندس", "مهندسون"),
    ("أسد", "أسود"), ("نمر", "نمور"), ("فيل", "أفيال"), ("حصان", "خيول"),
    ("تفاحة", "تفاح"), ("موزة", "موز"), ("عنبة", "عنب"), ("نجم", "نجوم"),
    ("قمر", "أقمار"), ("كوكب", "كواكب"), ("سحابة", "سحب"), ("جبل", "جبال"),
    ("نهر", "أنهار"), ("بحر", "بحار"), ("جزيرة", "جزر"), ("دولة", "دول"),
    ("مدينة", "مدن"), ("شارع", "شوارع"),
]

class Jam3Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="جمع")
    async def jam3(self, ctx):
        channel_id = ctx.channel.id
        if active_games.get(channel_id):
            await ctx.send("⚠️ هناك لعبة قيد التشغيل!")
            return
        active_games[channel_id] = True
        try:
            word, answer = random.choice(QUESTIONS)
            file = make_image("جمع", word)
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
                await ctx.send(f"✅ إجابة صحيحة! {winner.mention} فاز بنقطة (+1)")
            else:
                await ctx.send(f"🔴 انتهى الوقت! الإجابة كانت: **{answer}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(Jam3Cog(bot))
