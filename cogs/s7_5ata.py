import asyncio
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
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

def make_image(question):
    img = get_bg()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    font_title = load_font(37)
    font_q = load_font(60)

    GOLD = (255, 215, 0, 255)
    SHADOW = (0, 0, 0, 200)

    title = reshape_ar("صح أم خطأ؟")
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tx = (W - (bbox[2]-bbox[0])) / 2
    ty = H * 0.1
    draw.text((tx+3, ty+3), title, font=font_title, fill=SHADOW)
    draw.text((tx, ty), title, font=font_title, fill=GOLD)

    lines = textwrap.wrap(question, width=22)
    shaped_lines = [reshape_ar(l) for l in lines]
    total_h = sum([draw.textbbox((0,0), l, font=font_q)[3] - draw.textbbox((0,0), l, font=font_q)[1] + 10 for l in shaped_lines])
    y = (H - total_h) / 2
    for line in shaped_lines:
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
    ("القمر كوكب", "خطأ"), ("الشمس تشرق من الشرق", "صح"),
    ("الأرض مسطحة", "خطأ"), ("الماء يغلي عند 100 درجة", "صح"),
    ("الإنسان يعيش في البر", "خطأ"), ("السمك يتنفس الأكسجين", "صح"),
    ("الثلج حار", "خطأ"), ("النخلة شجرة", "صح"),
    ("طوكيو عاصمة الصين", "خطأ"), ("باريس عاصمة فرنسا", "صح"),
    ("الفهد أسرع حيوان في العالم", "صح"), ("النيل أطول نهر في العالم", "صح"),
    ("القرآن الكريم 114 سورة", "صح"), ("الحوت الأزرق أضخم حيوان", "صح"),
    ("الصلوات اليومية 5", "صح"), ("رمضان 31 يوم", "خطأ"),
    ("أركان الإسلام 6", "خطأ"), ("مكة في السعودية", "صح"),
    ("أبوظبي عاصمة الإمارات", "صح"), ("الرياض عاصمة الإمارات", "خطأ"),
    ("الأسبوع 8 أيام", "خطأ"), ("السنة 12 شهر", "صح"),
    ("اليوم 24 ساعة", "صح"), ("الساعة 100 دقيقة", "خطأ"),
    ("الأرض تدور حول الشمس", "صح"), ("المشتري أكبر كوكب", "صح"),
    ("القلب يضخ الدم", "صح"), ("الشمس تدور حول الأرض", "خطأ"),
    ("الدم لون أزرق", "خطأ"), ("الماء H2O", "صح"),
    ("الذهب يصدأ", "خطأ"), ("الحديد يصدأ", "صح"),
    ("الألماس أصلب المواد", "صح"), ("الألوان الأساسية 3", "صح"),
    ("التدخين مفيد للصحة", "خطأ"), ("قوس قزح 7 ألوان", "صح"),
    ("الرياضة تقوي العظام", "صح"), ("الكالسيوم يقوي العظام", "صح"),
    ("من الشمس نحصل على فيتامين D", "صح"), ("البروتين يبني العضلات", "صح"),
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
            file = await asyncio.to_thread(make_image, question)
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
                    user_answer = msg.content.strip()
                    if user_answer == answer:
                        winner = msg.author
                        break
                except asyncio.TimeoutError:
                    break
            if winner:
                await add_solo_points(winner.id)
                await ctx.send(f"✅ فاز بنقطة (+1) {winner.mention}! الإجابة كانت صحيحة")
            else:
                await ctx.send(f"🔴 انتهى الوقت! الإجابة كانت: **{answer}**")
        finally:
            active_games[channel_id] = False

async def setup(bot):
    await bot.add_cog(S7KhataCog(bot))
