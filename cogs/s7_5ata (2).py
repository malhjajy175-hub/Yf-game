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
        font_q = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 65)
    except:
        font_title = ImageFont.load_default()
        font_q = font_title
    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)
    title = "صح أم خطأ؟"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tx = (W - (bbox[2]-bbox[0])) / 2
    ty = H * 0.1
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)
    lines = textwrap.wrap(question, width=22)
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
    ("الشمس تشرق من الشرق", "صح"), ("القمر كوكب", "خطأ"),
    ("الماء يغلي عند 100 درجة", "صح"), ("الأرض مسطحة", "خطأ"),
    ("الإنسان يتنفس الأكسجين", "صح"), ("السمك يعيش في البر", "خطأ"),
    ("النخلة شجرة", "صح"), ("الثلج حار", "خطأ"),
    ("باريس عاصمة فرنسا", "صح"), ("طوكيو عاصمة الصين", "خطأ"),
    ("النيل أطول نهر في العالم", "صح"), ("الفهد أسرع حيوان في العالم", "صح"),
    ("الحوت الأزرق أضخم حيوان", "صح"), ("القرآن الكريم 114 سورة", "صح"),
    ("رمضان 31 يوم", "خطأ"), ("الصلوات اليومية 5", "صح"),
    ("أركان الإسلام 6", "خطأ"), ("مكة في السعودية", "صح"),
    ("الرياض عاصمة الإمارات", "خطأ"), ("أبوظبي عاصمة الإمارات", "صح"),
    ("السنة 12 شهر", "صح"), ("الأسبوع 8 أيام", "خطأ"),
    ("اليوم 24 ساعة", "صح"), ("الساعة 100 دقيقة", "خطأ"),
    ("المشتري أكبر كوكب", "صح"), ("الأرض تدور حول الشمس", "صح"),
    ("الشمس تدور حول الأرض", "خطأ"), ("القلب يضخ الدم", "صح"),
    ("الدم لون أزرق", "خطأ"), ("الماء H2O", "صح"),
    ("الذهب يصدأ", "خطأ"), ("الحديد يصدأ", "صح"),
    ("الألماس أصلب المواد", "صح"), ("الألوان الأساسية 3", "صح"),
    ("قوس قزح 7 ألوان", "صح"), ("التدخين مفيد للصحة", "خطأ"),
    ("الرياضة تقوي الجسم", "صح"), ("الكالسيوم يقوي العظام", "صح"),
    ("فيتامين D من الشمس", "صح"), ("البروتين يبني العضلات", "صح"),
]

class S7KhataCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="صواب")
    async def s7_5ata(self, ctx):
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
                return m.channel.id == channel_id and not m.author.bot and m.content.strip() in ["صح", "خطأ", "خطا"]
            end_time = asyncio.get_event_loop().time() + 10
            winner = None
            while True:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    msg = await self.bot.wait_for("message", timeout=remaining, check=check)
                    user_answer = msg.content.strip()
                    if user_answer == answer or (user_answer == "خطا" and answer == "خطأ"):
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
    await bot.add_cog(S7KhataCog(bot))
