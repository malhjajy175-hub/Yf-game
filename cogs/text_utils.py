import os
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import ImageFont

# مسار الخط العربي - موجود في جذر المشروع (بجانب main.py و bg.png)
FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "Amiri-Bold.ttf")

_FALLBACKS = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
]


def reshape_ar(text: str) -> str:
    """يربط حروف النص العربي بشكل صحيح ويرتب اتجاهه قبل رسمه بـ PIL."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """يحمل خطاً يدعم العربية. يجرب الخط الأساسي ثم بدائل ثم يرجع للافتراضي كحل أخير."""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        for fb in _FALLBACKS:
            if os.path.exists(fb):
                return ImageFont.truetype(fb, size)
        return ImageFont.load_default()
