import asyncio
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
from points import add_solo_points

active_games: dict[int, bool] = {}
BG_PATH = "bg.png"

_BG_CACHE = None
def get_bg():
    global _BG_CACHE
    if _BG_CACHE is None:
        _BG_CACHE = Image.open(BG_PATH).convert("RGBA")
    return _BG_CACHE.copy()

def make_image(question):
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_q = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    except:
        font_title = ImageFont.load_default()
        font_q = font_title
    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)
    title = "ربط"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tx = (W - (bbox[2]-bbox[0])) / 2
    ty = H * 0.1
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)
    lines = textwrap.wrap(question, width=20)
    total_h = sum([draw.textbbox((0,0), l, font=font_q)[3] - draw.textbbox((0,0), l, font=font_q)[1] + 10 for l in lines])
    y = (H - total_h) / 2
    for line in lines:
        bbox2 = draw.textbbox((0, 0), line, font=font_q)
        lw = bbox2[2] - bbox2[0]
        lh = bbox2[3] - bbox2[1]
        x = (W - lw) / 2
        draw.text((x+3, y+3), line, font=font_q, fill=SHADOW)
        draw.text((x, y), line, font=font_q, fill=GOLD)
        y += lh + 10
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="game.png")

QUESTIONS = [
    ("عاصمة فرنسا", "باريس"), ("عاصمة اليابان", "طوكيو"), ("عاصمة مصر", "القاهرة"),
    ("عاصمة السعودية", "الرياض"), ("عاصمة الإمارات", "أبوظبي"), ("عاصمة الكويت", "الكويت"),
    ("عاصمة قطر", "الدوحة"), ("عاصمة البحرين", "المنامة"), ("عاصمة عُمان", "مسقط"),
    ("عاصمة العراق", "بغداد"), ("عاصمة سوريا", "دمشق"), ("عاصمة لبنان", "بيروت"),
    ("عاصمة الأردن", "عمّان"), ("عاصمة ليبيا", "طرابلس"), ("عاصمة تونس", "تونس"),
    ("عاصمة المغرب", "الرباط"), ("عاصمة الجزائر", "الجزائر"), ("عاصمة السودان", "الخرطوم"),
    ("عاصمة الهند", "نيودلهي"), ("عاصمة الصين", "بكين"), ("عاصمة روسيا", "موسكو"),
    ("عاصمة ألمانيا", "برلين"), ("عاصمة إيطاليا", "روما"), ("عاصمة إسبانيا", "مدريد"),
    ("أطول نهر في العالم", "النيل"), ("أعلى جبل في العالم", "إيفرست"),
    ("أكبر محيط في العالم", "المحيط الهادئ"), ("أكبر دولة في العالم", "روسيا"),
    ("أسرع حيوان في العالم", "الفهد"), ("أضخم حيوان في العالم", "الحوت الأزرق"),
    ("أطول حيوان في العالم", "الزرافة"), ("لون السماء", "أزرق"),
    ("لون الذهب", "أصفر"), ("لون الدم", "أحمر"),
    ("كوكب الحلقات", "زحل"), ("أقرب كوكب للشمس", "عطارد"),
    ("عدد أيام السنة", "365"), ("عدد أشهر السنة", "12"),
    ("عدد أيام الأسبوع", "7"), ("عدد ساعات اليوم", "24"),
    ("عاصمة إنجلترا", "لندن"), ("عاصمة أمريكا", "واشنطن"),
    ("مخترع الهاتف", "غراهام بيل"), ("عدد أركان الإسلام", "5"),
    ("عدد الصلوات اليومية", "5"), ("عدد سور القرآن الكريم", "114"),
]

class RabtCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ربط")
    async def rabt(self, ctx):
        channel_id = ctx.channel.id
        if active_games.get(channel_id):
            await ctx.send("⚠️ هناك لعبة قيد التشغيل!")
            return
        active_games[channel_id] = True
        try:
            question, answer = random.choice(QUESTIONS)
            file = make_image(question)
            await ctx.send(file=file)
            def check(m):
                return m.channel.id == channel_id and not m.author.bot and m.content.strip() == answer
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
                await ctx.send(f"🔴 انتهى الوقت! الإجابة كانت: **{answer}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(RabtCog(bot))
