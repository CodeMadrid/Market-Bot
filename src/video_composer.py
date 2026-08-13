"""
src/video_composer.py
──────────────────────────────────────────────────────────────────────────────
Premium animated Market Video Composer

Designed to work with the existing Market Video Bot pipeline:

    main.py
        ↓
    chart_generator.py
        ↓
    tts_narrator.py
        ↓
    THIS FILE
        ↓
    market_video_YYYYMMDD.mp4

Features
--------
• Dynamic frame-by-frame motion
• Animated market cards
• Nifty / BankNifty hero
• Number counters
• Moving ticker
• Animated chart reveal
• Chart zoom / camera movement
• Gainers / losers ranking animation
• Sector visualization
• Volume visualization
• Candlestick chart presentation
• AI insights reveal
• Mood-based background
• Particles / glow / grid
• Kinetic typography
• Audio synchronized sections
• FFmpeg streaming renderer
• No external video framework required
"""

import os
import math
import shutil
import subprocess
import tempfile
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from loguru import logger


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 1920, 1080
FPS = 24

BG_RGB = (5, 8, 13)
SURFACE = (10, 15, 23)
SURFACE_2 = (14, 21, 31)
SURFACE_3 = (19, 28, 40)

TEXT = (236, 242, 248)
WHITE = (255, 255, 255)
MUTED = (133, 146, 162)
DIM = (76, 88, 104)

ACCENT = (88, 166, 255)
ACCENT_2 = (77, 145, 255)

BULL = (0, 210, 145)
BEAR = (255, 72, 94)
GOLD = (255, 190, 65)

MOOD_COL = {
    "Bullish": BULL,
    "Bearish": BEAR,
    "Sideways": GOLD,
}

GRID = (24, 34, 47)

# Brand
BRAND = "DALAL STREET AI"
BRAND_HANDLE = "@DalalStreetAI"

# Rendering quality
VIDEO_PRESET = "medium"
VIDEO_CRF = "19"


# ══════════════════════════════════════════════════════════════════════════════
# FONT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

_FONT_CACHE = {}


def _font(size, bold=False):
    key = (size, bold)

    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    paths = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for path in paths:
        try:
            f = ImageFont.truetype(path, size)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            continue

    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ══════════════════════════════════════════════════════════════════════════════
# MATH / ANIMATION
# ══════════════════════════════════════════════════════════════════════════════

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    t = clamp(t)
    return 1 - pow(1 - t, 3)


def ease_in(t):
    t = clamp(t)
    return t * t * t


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_back(t):
    """
    Smooth overshoot.
    """
    t = clamp(t)
    c1 = 1.70158
    c3 = c1 + 1

    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def spring(t):
    """
    Small spring-like overshoot.
    """
    t = clamp(t)
    return 1 - math.exp(-7 * t) * math.cos(10 * t)


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def smoothstep(a, b, x):
    if a == b:
        return 1.0

    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def pulse(t, frequency=1.0):
    return 0.5 + 0.5 * math.sin(t * math.pi * 2 * frequency)


def stagger(index, count, total):
    if count <= 1:
        return 0

    return (index / max(1, count - 1)) * total


# ══════════════════════════════════════════════════════════════════════════════
# BASIC DRAW HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _canvas():
    img = Image.new("RGB", (W, H), BG_RGB)
    return img


def _text_size(draw, text, font):
    bb = draw.textbbox((0, 0), str(text), font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _center_text(draw, text, y, font, color=TEXT):
    tw, th = _text_size(draw, text, font)
    draw.text(
        ((W - tw) / 2, y),
        text,
        font=font,
        fill=color,
    )


def _rounded(draw, box, radius=16, fill=None, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def _hex(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgba(color, alpha):
    return (
        int(color[0]),
        int(color[1]),
        int(color[2]),
        int(clamp(alpha / 255.0) * 255),
    )


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND / ATMOSPHERE
# ══════════════════════════════════════════════════════════════════════════════

def _gradient_background(mood="Bullish", frame=0):
    """
    Creates a subtle radial financial-terminal background.
    """

    mc = MOOD_COL.get(mood, ACCENT)

    img = Image.new("RGB", (W, H), BG_RGB)
    px = img.load()

    glow_x = int(W * 0.72 + math.sin(frame * 0.008) * 120)
    glow_y = int(H * 0.28)

    radius = 800

    for y in range(0, H, 8):
        for x in range(0, W, 8):
            dx = x - glow_x
            dy = y - glow_y
            d = math.sqrt(dx * dx + dy * dy)

            strength = max(0.0, 1.0 - d / radius)
            strength *= 0.10

            r = int(BG_RGB[0] + mc[0] * strength)
            g = int(BG_RGB[1] + mc[1] * strength)
            b = int(BG_RGB[2] + mc[2] * strength)

            for yy in range(y, min(y + 8, H)):
                for xx in range(x, min(x + 8, W)):
                    px[xx, yy] = (r, g, b)

    return img


def _draw_grid(draw, frame=0, opacity=1.0):
    """
    Moving subtle grid.
    """

    step = 80
    offset_x = int((frame * 0.25) % step)
    offset_y = int((frame * 0.12) % step)

    col = tuple(
        int(c * opacity)
        for c in GRID
    )

    for x in range(-step, W + step, step):
        xx = x + offset_x
        draw.line(
            [(xx, 0), (xx, H)],
            fill=col,
            width=1,
        )

    for y in range(-step, H + step, step):
        yy = y + offset_y
        draw.line(
            [(0, yy), (W, yy)],
            fill=col,
            width=1,
        )


def _draw_vignette(img):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Top
    for i in range(160):
        alpha = int(100 * (1 - i / 160))
        d.rectangle(
            [0, i, W, i + 1],
            fill=(0, 0, 0, alpha),
        )

    # Bottom
    for i in range(180):
        alpha = int(120 * (1 - i / 180))
        y = H - i
        d.rectangle(
            [0, y, W, y + 1],
            fill=(0, 0, 0, alpha),
        )

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _glow_circle(img, center, radius, color, strength=100):
    """
    Soft radial glow.
    """

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))

    cx, cy = center

    d = ImageDraw.Draw(layer)

    for r in range(radius, 4, -12):
        ratio = 1 - (r / radius)
        alpha = int(strength * ratio * ratio)

        d.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, alpha),
        )

    layer = layer.filter(ImageFilter.GaussianBlur(18))

    return Image.alpha_composite(
        img.convert("RGBA"),
        layer,
    ).convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# BRAND / HEADER
# ══════════════════════════════════════════════════════════════════════════════

def _draw_brand(draw, frame=0):
    draw.text(
        (55, 34),
        BRAND,
        font=_font(25, True),
        fill=TEXT,
    )

    draw.text(
        (55, 67),
        "MARKET INTELLIGENCE",
        font=_font(14, True),
        fill=MUTED,
    )

    # Status indicator
    x = W - 220
    y = 50

    glow = int(3 + pulse(frame / FPS, 0.6) * 3)

    draw.ellipse(
        [x, y - glow, x + 12, y + 12 + glow],
        fill=BULL,
    )

    draw.text(
        (x + 23, y - 5),
        "MARKET CLOSE",
        font=_font(18, True),
        fill=MUTED,
    )


def _draw_footer(draw):
    draw.text(
        (55, H - 38),
        "DALAL STREET AI  •  NOT FINANCIAL ADVICE",
        font=_font(15, True),
        fill=(70, 82, 98),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PARTICLES
# ══════════════════════════════════════════════════════════════════════════════

def _draw_particles(draw, cx, cy, frame, color, count=28, radius=250):
    """
    Controlled particle burst.
    """

    random.seed(700 + frame // 3)

    for i in range(count):
        angle = random.random() * math.pi * 2
        speed = random.uniform(0.3, 1.0)

        r = min(
            radius,
            30 + frame * 9 * speed,
        )

        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r

        if not (0 <= x < W and 0 <= y < H):
            continue

        size = random.choice([2, 2, 3, 4])

        alpha = max(
            0,
            int(220 - frame * 5),
        )

        draw.ellipse(
            [
                x - size,
                y - size,
                x + size,
                y + size,
            ],
            fill=(
                color[0],
                color[1],
                color[2],
            ),
        )


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATED TEXT
# ══════════════════════════════════════════════════════════════════════════════

def _draw_reveal_text(
    draw,
    text,
    center_y,
    progress,
    font,
    color=TEXT,
    direction="up",
):
    p = ease_out(progress)

    tw, th = _text_size(draw, text, font)

    if direction == "up":
        y = center_y + lerp(50, 0, p)
    elif direction == "down":
        y = center_y + lerp(-50, 0, p)
    else:
        y = center_y

    alpha = int(255 * p)

    # Shadow
    if alpha > 0:
        draw.text(
            (
                (W - tw) / 2 + 3,
                y + 5,
            ),
            text,
            font=font,
            fill=(0, 0, 0),
        )

        draw.text(
            (
                (W - tw) / 2,
                y,
            ),
            text,
            font=font,
            fill=color,
        )


# ══════════════════════════════════════════════════════════════════════════════
# NUMBER COUNTER
# ══════════════════════════════════════════════════════════════════════════════

def _counter_value(start, end, progress):
    p = ease_out(progress)
    return start + (end - start) * p


def _draw_counter(
    draw,
    value,
    x,
    y,
    font,
    color=TEXT,
    prefix="",
    suffix="",
):
    txt = f"{prefix}{value:,.2f}{suffix}"

    tw, th = _text_size(draw, txt, font)

    draw.text(
        (x - tw / 2, y),
        txt,
        font=font,
        fill=color,
    )


# ══════════════════════════════════════════════════════════════════════════════
# STOCK CARD
# ══════════════════════════════════════════════════════════════════════════════

def _draw_stock_card(
    img,
    q,
    x,
    y,
    w,
    h,
    progress,
    rank,
    positive=True,
):
    if not q:
        return

    p = ease_back(progress)

    mc = BULL if positive else BEAR

    # Clamp overshoot
    scale = clamp(p, 0.0, 1.08)

    current_h = int(h * scale)

    if current_h < 10:
        return

    cy = y + h // 2

    y1 = int(cy - current_h / 2)
    y2 = int(cy + current_h / 2)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Glow
    d.rounded_rectangle(
        [x - 5, y1 - 5, x + w + 5, y2 + 5],
        radius=22,
        fill=(*mc, 15),
    )

    # Main card
    d.rounded_rectangle(
        [x, y1, x + w, y2],
        radius=18,
        fill=(11, 18, 27, 245),
        outline=(*mc, 180),
        width=2,
    )

    # Accent stripe
    d.rounded_rectangle(
        [x, y1, x + 7, y2],
        radius=4,
        fill=(*mc, 230),
    )

    if progress > 0.55:

        text_p = ease_out(
            (progress - 0.55) / 0.45
        )

        alpha = int(255 * text_p)

        symbol = str(
            q.get("symbol", "")
        )[:12]

        pct = float(
            q.get("change_pct", 0)
        )

        price = float(
            q.get("ltp", 0)
        )

        sign = "+" if pct >= 0 else ""

        d.text(
            (x + 30, y1 + 24),
            f"#{rank:02d}",
            font=_font(18, True),
            fill=(*MUTED, alpha),
        )

        d.text(
            (x + 30, y1 + 55),
            symbol,
            font=_font(34, True),
            fill=(*TEXT, alpha),
        )

        d.text(
            (x + 30, y1 + 105),
            f"₹{price:,.2f}",
            font=_font(22),
            fill=(*MUTED, alpha),
        )

        pct_text = f"{sign}{pct:.2f}%"

        tw, th = _text_size(
            d,
            pct_text,
            _font(29, True),
        )

        d.text(
            (
                x + w - tw - 25,
                y1 + 58,
            ),
            pct_text,
            font=_font(29, True),
            fill=(*mc, alpha),
        )

        # Mini change bar
        bar_w = max(
            20,
            min(
                w - 60,
                int(abs(pct) * 22),
            ),
        )

        d.rounded_rectangle(
            [
                x + 30,
                y2 - 35,
                x + 30 + bar_w,
                y2 - 27,
            ],
            radius=4,
            fill=(*mc, alpha),
        )

    img.paste(
        layer,
        (0, 0),
        layer,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TICKER
# ══════════════════════════════════════════════════════════════════════════════

def _draw_ticker(draw, summary, frame):
    quotes = []

    for q in summary.get("quotes", []):
        symbol = q.get("symbol", "")
        if symbol in ("NIFTY 50", "BANKNIFTY"):
            continue

        pct = float(q.get("change_pct", 0))
        sign = "+" if pct >= 0 else ""

        quotes.append(
            f"{symbol}  {sign}{pct:.2f}%"
        )

    if not quotes:
        return

    text = "   •   ".join(quotes)

    font = _font(18, True)

    tw, th = _text_size(
        draw,
        text,
        font,
    )

    speed = 1.2
    offset = int((frame * speed) % (tw + W))

    draw.rectangle(
        [0, H - 72, W, H],
        fill=(7, 11, 17),
    )

    draw.line(
        [(0, H - 72), (W, H - 72)],
        fill=(35, 48, 64),
        width=1,
    )

    x = W - offset

    draw.text(
        (x, H - 51),
        text,
        font=font,
        fill=MUTED,
    )

    # Repeat text for seamless movement
    draw.text(
        (x + tw + 180, H - 51),
        text,
        font=font,
        fill=MUTED,
    )


# ══════════════════════════════════════════════════════════════════════════════
# INTRO
# ══════════════════════════════════════════════════════════════════════════════

def _scene_intro(summary, frame, duration):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    mc = MOOD_COL.get(
        mood,
        GOLD,
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.7,
    )

    p = clamp(
        frame / max(1, int(FPS * 1.8))
    )

    # Large atmospheric glow
    img = _glow_circle(
        img,
        (W // 2, 430),
        420,
        mc,
        80,
    )

    draw = ImageDraw.Draw(img)

    _draw_brand(draw, frame)

    _draw_reveal_text(
        draw,
        "DAILY MARKET",
        320,
        p,
        _font(42, True),
        MUTED,
    )

    _draw_reveal_text(
        draw,
        "INTELLIGENCE",
        385,
        max(0, p - 0.08) / 0.92,
        _font(90, True),
        TEXT,
    )

    date = summary.get(
        "date",
        datetime.now().strftime("%d %B %Y"),
    )

    _draw_reveal_text(
        draw,
        date.upper(),
        510,
        max(0, p - 0.18) / 0.82,
        _font(27, True),
        mc,
    )

    # Animated status
    if p > 0.45:
        q = ease_out(
            (p - 0.45) / 0.55
        )

        box_w = int(
            lerp(0, 420, q)
        )

        bx = (W - box_w) // 2

        if box_w > 20:
            _rounded(
                draw,
                [bx, 610, bx + box_w, 670],
                16,
                fill=(12, 20, 29),
                outline=mc,
                width=1,
            )

            txt = f"MARKET MOOD  •  {mood.upper()}"

            _center_text(
                draw,
                txt,
                626,
                _font(19, True),
                mc,
            )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def _draw_index_hero(
    draw,
    q,
    x,
    y,
    w,
    h,
    progress,
    label,
):
    if not q:
        return

    p = ease_out(progress)

    pct = float(
        q.get("change_pct", 0)
    )

    ltp = float(
        q.get("ltp", 0)
    )

    mc = BULL if pct >= 0 else BEAR

    # Card
    _rounded(
        draw,
        [x, y, x + w, y + h],
        22,
        fill=(10, 16, 24),
        outline=(35, 48, 64),
        width=2,
    )

    draw.text(
        (x + 28, y + 24),
        label.upper(),
        font=_font(18, True),
        fill=MUTED,
    )

    draw.text(
        (x + 28, y + 60),
        q.get("symbol", label),
        font=_font(32, True),
        fill=TEXT,
    )

    animated_ltp = lerp(
        0,
        ltp,
        p,
    )

    draw.text(
        (x + 28, y + 105),
        f"{animated_ltp:,.2f}",
        font=_font(40, True),
        fill=TEXT,
    )

    sign = "+" if pct >= 0 else "-"

    animated_pct = abs(
        lerp(
            0,
            pct,
            p,
        )
    )

    draw.text(
        (x + 30, y + 160),
        f"{sign}{animated_pct:.2f}%",
        font=_font(25, True),
        fill=mc,
    )

    # High/low line
    low = float(q.get("low", ltp))
    high = float(q.get("high", ltp))

    if high > low:
        ratio = clamp(
            (ltp - low) / (high - low)
        )
    else:
        ratio = 0.5

    bar_y = y + h - 35

    draw.line(
        [(x + 30, bar_y),
         (x + w - 30, bar_y)],
        fill=(35, 48, 64),
        width=4,
    )

    px = int(
        lerp(
            x + 30,
            x + w - 30,
            ratio,
        )
    )

    draw.ellipse(
        [px - 6, bar_y - 6,
         px + 6, bar_y + 6],
        fill=mc,
    )


def _scene_summary(summary, frame, duration):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    mc = MOOD_COL.get(
        mood,
        GOLD,
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.45,
    )

    _draw_brand(
        draw,
        frame,
    )

    # Section title
    p = ease_out(
        clamp(frame / int(FPS * 1.2))
    )

    draw.text(
        (55, 145),
        "MARKET SNAPSHOT",
        font=_font(52, True),
        fill=TEXT,
    )

    draw.text(
        (58, 205),
        summary.get("date", ""),
        font=_font(21, True),
        fill=MUTED,
    )

    # Mood badge
    _rounded(
        draw,
        [W - 400, 150, W - 60, 215],
        18,
        fill=(12, 20, 29),
        outline=mc,
        width=2,
    )

    draw.text(
        (W - 370, 170),
        f"MOOD  {mood.upper()}",
        font=_font(20, True),
        fill=mc,
    )

    # Hero indices
    nifty = summary.get("nifty")
    bank = summary.get("banknifty")
    sensex = summary.get("sensex")

    _draw_index_hero(
        draw,
        nifty,
        60,
        285,
        400,
        235,
        p,
        "NIFTY 50",
    )

    _draw_index_hero(
        draw,
        bank,
        485,
        285,
        400,
        235,
        max(0, p - 0.12) / 0.88,
        "BANK NIFTY",
    )

    if sensex:
        _draw_index_hero(
            draw,
            sensex,
            910,
            285,
            400,
            235,
            max(0, p - 0.24) / 0.76,
            "SENSEX",
        )

    # Top gainer / loser
    gain = summary.get("top_gainer")
    loss = summary.get("top_loser")

    if gain:
        _draw_stock_card(
            img,
            gain,
            60,
            590,
            610,
            190,
            max(0, p - 0.20) / 0.80,
            1,
            True,
        )

    if loss:
        _draw_stock_card(
            img,
            loss,
            700,
            590,
            610,
            190,
            max(0, p - 0.35) / 0.65,
            1,
            False,
        )

    # AI score
    score = summary.get(
        "ai_score",
        None,
    )

    if score is not None:
        draw.text(
            (1360, 320),
            "AI MARKET SCORE",
            font=_font(20, True),
            fill=MUTED,
        )

        score_v = int(
            lerp(
                0,
                float(score),
                p,
            )
        )

        draw.text(
            (1360, 355),
            str(score_v),
            font=_font(90, True),
            fill=mc,
        )

        draw.text(
            (1365, 455),
            "/ 100",
            font=_font(24),
            fill=MUTED,
        )

    _draw_ticker(
        draw,
        summary,
        frame,
    )

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# CHART ANIMATION
# ══════════════════════════════════════════════════════════════════════════════

def _load_chart(path):
    if not path or not os.path.exists(path):
        return None

    try:
        return Image.open(path).convert("RGB")
    except Exception as e:
        logger.error(
            f"Chart load error {path}: {e}"
        )
        return None


def _animated_chart(
    base_img,
    chart,
    progress,
    x=60,
    y=170,
    w=W - 120,
    h=760,
    zoom=1.0,
):
    """
    Displays a chart with:
    • reveal
    • zoom
    • subtle horizontal camera movement
    """

    if chart is None:
        return base_img

    p = ease_out(progress)

    target_ratio = chart.width / chart.height
    box_ratio = w / h

    if target_ratio > box_ratio:
        nw = int(w * zoom)
        nh = int(nw / target_ratio)
    else:
        nh = int(h * zoom)
        nw = int(nh * target_ratio)

    nw = max(10, nw)
    nh = max(10, nh)

    chart2 = chart.resize(
        (nw, nh),
        Image.Resampling.LANCZOS,
    )

    # Camera movement
    movement = int(
        math.sin(progress * math.pi) * 20
    )

    px = x + (w - nw) // 2 + movement
    py = y + (h - nh) // 2

    # Reveal mask
    reveal_w = int(
        nw * p
    )

    if reveal_w <= 0:
        return base_img

    reveal_w = min(
        reveal_w,
        nw,
    )

    cropped = chart2.crop(
        (0, 0, reveal_w, nh)
    )

    base_img.paste(
        cropped,
        (px, py),
    )

    return base_img


def _scene_chart(
    summary,
    chart_path,
    frame,
    duration,
    title,
    subtitle="",
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.35,
    )

    _draw_brand(
        draw,
        frame,
    )

    # Title
    title_p = ease_out(
        clamp(frame / int(FPS * 0.8))
    )

    draw.text(
        (60, 130),
        title,
        font=_font(44, True),
        fill=TEXT,
    )

    if subtitle:
        draw.text(
            (62, 182),
            subtitle,
            font=_font(19, True),
            fill=MUTED,
        )

    chart = _load_chart(
        chart_path
    )

    chart_p = clamp(
        frame / int(FPS * 1.7)
    )

    img = _animated_chart(
        img,
        chart,
        chart_p,
        x=55,
        y=235,
        w=W - 110,
        h=680,
        zoom=1.035,
    )

    draw = ImageDraw.Draw(img)

    # Top accent line
    draw.line(
        [(60, 220), (W - 60, 220)],
        fill=(36, 52, 70),
        width=1,
    )

    # Progress marker
    p = clamp(
        frame / max(1, int(duration * FPS))
    )

    draw.line(
        [
            (60, 950),
            (60 + int((W - 120) * p), 950),
        ],
        fill=ACCENT,
        width=3,
    )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# GAINERS / LOSERS
# ══════════════════════════════════════════════════════════════════════════════

def _scene_movers(summary, frame, duration):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.32,
    )

    _draw_brand(
        draw,
        frame,
    )

    draw.text(
        (60, 120),
        "TODAY'S BIG MOVERS",
        font=_font(52, True),
        fill=TEXT,
    )

    draw.text(
        (62, 185),
        "Stocks creating the strongest moves",
        font=_font(20),
        fill=MUTED,
    )

    gainers = summary.get(
        "top_gainers",
        [],
    )[:3]

    losers = summary.get(
        "top_losers",
        [],
    )[:3]

    card_w = 560
    card_h = 155

    start_y = 270
    gap = 22

    for i, q in enumerate(gainers):
        delay = i * 0.16

        p = clamp(
            frame / FPS / 1.1 - delay
        )

        _draw_stock_card(
            img,
            q,
            70,
            start_y + i * (card_h + gap),
            card_w,
            card_h,
            p,
            i + 1,
            True,
        )

    for i, q in enumerate(losers):
        delay = i * 0.16

        p = clamp(
            frame / FPS / 1.1 - delay
        )

        _draw_stock_card(
            img,
            q,
            1290,
            start_y + i * (card_h + gap),
            card_w,
            card_h,
            p,
            i + 1,
            False,
        )

    # Center divider
    draw.line(
        [(960, 265), (960, 870)],
        fill=(40, 52, 68),
        width=1,
    )

    draw.text(
        (70, 235),
        "GAINERS",
        font=_font(18, True),
        fill=BULL,
    )

    draw.text(
        (1290, 235),
        "LOSERS",
        font=_font(18, True),
        fill=BEAR,
    )

    _draw_ticker(
        draw,
        summary,
        frame,
    )

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# SECTOR HEATMAP ENHANCEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _scene_heatmap(
    summary,
    chart_path,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.3,
    )

    _draw_brand(
        draw,
        frame,
    )

    draw.text(
        (60, 120),
        "SECTOR PULSE",
        font=_font(52, True),
        fill=TEXT,
    )

    draw.text(
        (62, 184),
        "Where the market momentum is flowing",
        font=_font(20),
        fill=MUTED,
    )

    # Chart
    chart = _load_chart(
        chart_path
    )

    p = clamp(
        frame / int(FPS * 1.6)
    )

    img = _animated_chart(
        img,
        chart,
        p,
        x=60,
        y=235,
        w=1100,
        h=660,
        zoom=1.02,
    )

    draw = ImageDraw.Draw(img)

    # Dynamic sector side panel
    sectors = summary.get(
        "sectors",
        {},
    )

    sx = 1220
    sy = 270

    draw.text(
        (sx, sy),
        "SECTOR RANKING",
        font=_font(20, True),
        fill=ACCENT,
    )

    sy += 55

    sector_rows = []

    for name, stocks in sectors.items():

        values = [
            float(q.get("change_pct", 0))
            for q in stocks
        ]

        avg = (
            sum(values) / len(values)
            if values
            else 0
        )

        sector_rows.append(
            (name, avg)
        )

    sector_rows.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    for i, (name, value) in enumerate(
        sector_rows[:6]
    ):
        row_p = clamp(
            (frame / FPS - 0.5 - i * 0.12) / 0.8
        )

        row_p = ease_out(row_p)

        mc = (
            BULL
            if value >= 0
            else BEAR
        )

        draw.text(
            (sx, sy + i * 82),
            f"{i + 1:02d}",
            font=_font(18, True),
            fill=DIM,
        )

        draw.text(
            (sx + 55, sy + i * 82),
            name.upper(),
            font=_font(21, True),
            fill=TEXT,
        )

        bar_x = sx + 55
        bar_y = sy + 36 + i * 82

        max_bar = 420

        normalized = clamp(
            abs(value) / 5.0
        )

        bw = int(
            max_bar *
            normalized *
            row_p
        )

        draw.rounded_rectangle(
            [
                bar_x,
                bar_y,
                bar_x + max_bar,
                bar_y + 8,
            ],
            radius=4,
            fill=(28, 39, 53),
        )

        if bw > 0:
            draw.rounded_rectangle(
                [
                    bar_x,
                    bar_y,
                    bar_x + bw,
                    bar_y + 8,
                ],
                radius=4,
                fill=mc,
            )

        sign = "+" if value >= 0 else ""

        draw.text(
            (
                bar_x + max_bar + 20,
                sy + i * 82 + 7,
            ),
            f"{sign}{value:.2f}%",
            font=_font(18, True),
            fill=mc,
        )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# VOLUME
# ══════════════════════════════════════════════════════════════════════════════

def _scene_volume(
    summary,
    chart_path,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.3,
    )

    _draw_brand(
        draw,
        frame,
    )

    draw.text(
        (60, 120),
        "VOLUME ACTIVITY",
        font=_font(52, True),
        fill=TEXT,
    )

    draw.text(
        (62, 185),
        "Where the strongest participation is visible",
        font=_font(20),
        fill=MUTED,
    )

    chart = _load_chart(
        chart_path
    )

    p = clamp(
        frame / int(FPS * 1.6)
    )

    img = _animated_chart(
        img,
        chart,
        p,
        x=60,
        y=240,
        w=1800,
        h=650,
        zoom=1.03,
    )

    draw = ImageDraw.Draw(img)

    # Activity pulse
    pulse_x = int(
        1200 +
        math.sin(frame * 0.05) * 500
    )

    draw.line(
        [
            (pulse_x, 245),
            (pulse_x, 890),
        ],
        fill=(*ACCENT, 90),
        width=2,
    )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# CANDLESTICK SCENE
# ══════════════════════════════════════════════════════════════════════════════

def _scene_candle(
    summary,
    chart_path,
    symbol,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.32,
    )

    _draw_brand(
        draw,
        frame,
    )

    draw.text(
        (60, 110),
        symbol,
        font=_font(56, True),
        fill=TEXT,
    )

    draw.text(
        (62, 175),
        "30 DAY PRICE ACTION",
        font=_font(20, True),
        fill=ACCENT,
    )

    chart = _load_chart(
        chart_path
    )

    # Camera movement across chart
    p = clamp(
        frame / int(FPS * 1.5)
    )

    img = _animated_chart(
        img,
        chart,
        p,
        x=60,
        y=225,
        w=1800,
        h=700,
        zoom=1.04,
    )

    draw = ImageDraw.Draw(img)

    # Scan line
    scan_x = int(
        70 + 1740 *
        smoothstep(
            0,
            1,
            (frame % int(FPS * 4)) /
            int(FPS * 4),
        )
    )

    draw.line(
        [
            (scan_x, 230),
            (scan_x, 910),
        ],
        fill=(*ACCENT, 70),
        width=1,
    )

    # Bottom label
    _rounded(
        draw,
        [60, 940, 620, 995],
        14,
        fill=(10, 16, 24),
        outline=(40, 54, 72),
        width=1,
    )

    draw.text(
        (82, 956),
        "CANDLESTICK  •  VOLUME  •  RSI",
        font=_font(16, True),
        fill=MUTED,
    )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════

def _scene_ai(
    summary,
    chart_path,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    mc = MOOD_COL.get(
        mood,
        GOLD,
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.25,
    )

    _draw_brand(
        draw,
        frame,
    )

    # AI header
    p = clamp(
        frame / int(FPS * 1.3)
    )

    draw.text(
        (60, 115),
        "AI MARKET INTELLIGENCE",
        font=_font(48, True),
        fill=TEXT,
    )

    draw.text(
        (62, 176),
        "Signal extraction from today's market data",
        font=_font(20),
        fill=MUTED,
    )

    # Animated AI ring
    cx = 310
    cy = 500

    radius = 190

    for i in range(4):
        rr = radius - i * 28

        alpha = int(
            100 /
            (i + 1)
        )

        draw.arc(
            [
                cx - rr,
                cy - rr,
                cx + rr,
                cy + rr,
            ],
            start=frame * 2 + i * 40,
            end=frame * 2 + 280 + i * 40,
            fill=mc,
            width=3,
        )

    draw.text(
        (cx - 68, cy - 35),
        "AI",
        font=_font(58, True),
        fill=mc,
    )

    draw.text(
        (cx - 96, cy + 38),
        mood.upper(),
        font=_font(18, True),
        fill=MUTED,
    )

    # Card
    chart = _load_chart(
        chart_path
    )

    if chart:
        p_chart = clamp(
            (frame / FPS - 0.5) / 1.2
        )

        img = _animated_chart(
            img,
            chart,
            p_chart,
            x=600,
            y=270,
            w=1220,
            h=600,
            zoom=1.02,
        )

    draw = ImageDraw.Draw(img)

    # Mood badge
    _rounded(
        draw,
        [600, 890, 1000, 955],
        18,
        fill=(10, 17, 26),
        outline=mc,
        width=2,
    )

    draw.text(
        (630, 910),
        f"VERDICT  •  {mood.upper()}",
        font=_font(19, True),
        fill=mc,
    )

    # Animated particles after reveal
    if frame > int(FPS * 1.2):
        _draw_particles(
            draw,
            310,
            500,
            frame - int(FPS * 1.2),
            mc,
            count=18,
            radius=180,
        )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# OUTLOOK
# ══════════════════════════════════════════════════════════════════════════════

def _scene_outlook(
    summary,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    mc = MOOD_COL.get(
        mood,
        GOLD,
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.4,
    )

    _draw_brand(
        draw,
        frame,
    )

    # Large radial glow
    img = _glow_circle(
        img,
        (W // 2, 480),
        400,
        mc,
        90,
    )

    draw = ImageDraw.Draw(img)

    p = clamp(
        frame / int(FPS * 2)
    )

    _draw_reveal_text(
        draw,
        "MARKET VERDICT",
        260,
        p,
        _font(30, True),
        MUTED,
    )

    _draw_reveal_text(
        draw,
        mood.upper(),
        345,
        max(0, p - 0.12) / 0.88,
        _font(105, True),
        mc,
    )

    # Particle burst
    if frame > int(FPS * 1.0):
        _draw_particles(
            draw,
            W // 2,
            470,
            frame - int(FPS * 1.0),
            mc,
            count=45,
            radius=420,
        )

    # Nifty stat
    nifty = summary.get(
        "nifty"
    )

    if nifty:
        pct = float(
            nifty.get(
                "change_pct",
                0,
            )
        )

        sign = "+" if pct >= 0 else ""

        _rounded(
            draw,
            [W // 2 - 260, 585,
             W // 2 + 260, 665],
            20,
            fill=(9, 15, 23),
            outline=mc,
            width=2,
        )

        txt = (
            f"NIFTY 50   "
            f"{sign}{pct:.2f}%"
        )

        _center_text(
            draw,
            txt,
            610,
            _font(27, True),
            TEXT,
        )

    draw.text(
        (W // 2 - 230, 730),
        "Use data. Manage risk. Stay disciplined.",
        font=_font(20, True),
        fill=MUTED,
    )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# OUTRO
# ══════════════════════════════════════════════════════════════════════════════

def _scene_outro(
    summary,
    frame,
    duration,
):
    mood = summary.get(
        "market_mood",
        "Sideways",
    )

    mc = MOOD_COL.get(
        mood,
        GOLD,
    )

    img = _gradient_background(
        mood,
        frame,
    )

    draw = ImageDraw.Draw(img)

    _draw_grid(
        draw,
        frame,
        0.35,
    )

    p = clamp(
        frame / int(FPS * 1.5)
    )

    # Logo block
    _draw_reveal_text(
        draw,
        "DALAL STREET AI",
        365,
        p,
        _font(70, True),
        TEXT,
    )

    _draw_reveal_text(
        draw,
        "MARKETS. EXPLAINED DAILY.",
        470,
        max(0, p - 0.12) / 0.88,
        _font(29, True),
        mc,
    )

    if p > 0.5:
        q = ease_out(
            (p - 0.5) / 0.5
        )

        box_w = int(
            430 * q
        )

        if box_w > 10:
            _rounded(
                draw,
                [
                    (W - box_w) // 2,
                    580,
                    (W + box_w) // 2,
                    645,
                ],
                18,
                fill=(10, 16, 24),
                outline=(48, 64, 84),
                width=1,
            )

            _center_text(
                draw,
                BRAND_HANDLE,
                600,
                _font(22, True),
                TEXT,
            )

    _draw_footer(draw)

    return _draw_vignette(img)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO
# ══════════════════════════════════════════════════════════════════════════════

def _dur(path, fallback=5.0):
    if not path or not os.path.exists(path):
        return fallback

    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        value = float(
            r.stdout.strip()
        )

        # Small breathing room at the end of speech
        return max(
            0.5,
            value + 0.25,
        )

    except Exception:
        return fallback


def _absp(path):
    return os.path.abspath(
        path
    ).replace("\\", "/")


def _concat_audio(paths, out):
    paths = [
        p for p in paths
        if p and os.path.exists(p)
    ]

    if not paths:
        return None

    if len(paths) == 1:
        shutil.copy(
            paths[0],
            out,
        )
        return out

    lst = out + ".list.txt"

    with open(
        lst,
        "w",
        encoding="utf-8",
    ) as f:

        for p in paths:
            safe = _absp(p).replace(
                "'",
                "'\\''",
            )

            f.write(
                f"file '{safe}'\n"
            )

    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            out,
        ],
        "concat audio",
    )

    try:
        os.remove(lst)
    except Exception:
        pass

    return out


# ══════════════════════════════════════════════════════════════════════════════
# FFMPEG
# ══════════════════════════════════════════════════════════════════════════════

def _run(cmd, label):
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if r.returncode != 0:
        logger.error(
            f"{label} failed:\n"
            f"{r.stderr[-4000:]}"
        )

        raise RuntimeError(
            f"{label} failed"
        )

    return r


def _render_frames(
    render_func,
    duration,
    out_video,
):
    """
    Stream raw RGB frames directly into FFmpeg.

    This avoids creating thousands of PNG files.
    """

    total_frames = max(
        1,
        int(math.ceil(duration * FPS))
    )

    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            VIDEO_PRESET,
            "-crf",
            VIDEO_CRF,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            out_video,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:

        for frame_no in range(total_frames):

            img = render_func(
                frame_no,
                duration,
            )

            if img.mode != "RGB":
                img = img.convert("RGB")

            ffmpeg.stdin.write(
                img.tobytes()
            )

        ffmpeg.stdin.close()

        stderr = ffmpeg.stderr.read().decode(
            "utf-8",
            errors="ignore",
        )

        rc = ffmpeg.wait()

        if rc != 0:
            logger.error(
                stderr[-4000:]
            )

            raise RuntimeError(
                "FFmpeg frame rendering failed"
            )

    except Exception:

        try:
            ffmpeg.stdin.close()
        except Exception:
            pass

        ffmpeg.kill()
        ffmpeg.wait()

        raise


def _mux_audio(
    video_path,
    audio_path,
    output_path,
):
    if not audio_path:
        shutil.copy(
            video_path,
            output_path,
        )
        return

    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            _absp(video_path),
            "-i",
            _absp(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            output_path,
        ],
        "mux audio",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SEGMENT DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

def _audio_list(audio, *keys):
    result = []

    for key in keys:
        path = audio.get(key)

        if path and os.path.exists(path):
            result.append(path)

    return result


def _build_segments(
    chart_paths,
    audio,
    summary,
    language,
):
    """
    Creates dynamic scene definitions.

    Each entry:

        {
            name,
            duration,
            audio,
            renderer
        }
    """

    do_hi = language in (
        "hindi",
        "both",
    )

    segs = []

    # ─────────────────────────────────────────────────────────
    # INTRO
    # ─────────────────────────────────────────────────────────

    intro_audio = _audio_list(
        audio,
        "intro_en",
    )

    segs.append(
        {
            "name": "intro",
            "duration": _dur(
                audio.get("intro_en"),
                4.5,
            ),
            "audio": intro_audio,
            "renderer": lambda f, d:
                _scene_intro(
                    summary,
                    f,
                    d,
                ),
        }
    )

    # ─────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────

    summary_audio = _audio_list(
        audio,
        "summary_en",
    )

    segs.append(
        {
            "name": "summary_en",
            "duration": _dur(
                audio.get("summary_en"),
                10.0,
            ),
            "audio": summary_audio,
            "renderer": lambda f, d:
                _scene_summary(
                    summary,
                    f,
                    d,
                ),
        }
    )

    if do_hi and audio.get("summary_hi"):
        segs.append(
            {
                "name": "summary_hi",
                "duration": _dur(
                    audio.get("summary_hi"),
                    10.0,
                ),
                "audio": _audio_list(
                    audio,
                    "summary_hi",
                ),
                "renderer": lambda f, d:
                    _scene_summary(
                        summary,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # GAINERS / LOSERS
    # ─────────────────────────────────────────────────────────

    segs.append(
        {
            "name": "movers",
            "duration": max(
                _dur(
                    audio.get(
                        "gainers_en"
                    ),
                    7.0,
                ),
                7.0,
            ),
            "audio": _audio_list(
                audio,
                "gainers_en",
            ),
            "renderer": lambda f, d:
                _scene_movers(
                    summary,
                    f,
                    d,
                ),
        }
    )

    if do_hi and audio.get("gainers_hi"):
        segs.append(
            {
                "name": "movers_hi",
                "duration": max(
                    _dur(
                        audio.get(
                            "gainers_hi"
                        ),
                        7.0,
                    ),
                    7.0,
                ),
                "audio": _audio_list(
                    audio,
                    "gainers_hi",
                ),
                "renderer": lambda f, d:
                    _scene_movers(
                        summary,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # HEATMAP
    # ─────────────────────────────────────────────────────────

    heatmap = chart_paths.get(
        "heatmap",
        "",
    )

    segs.append(
        {
            "name": "heatmap",
            "duration": max(
                _dur(
                    audio.get(
                        "heatmap_en"
                    ),
                    8.0,
                ),
                8.0,
            ),
            "audio": _audio_list(
                audio,
                "heatmap_en",
            ),
            "renderer": lambda f, d:
                _scene_heatmap(
                    summary,
                    heatmap,
                    f,
                    d,
                ),
        }
    )

    if do_hi and audio.get("heatmap_hi"):
        segs.append(
            {
                "name": "heatmap_hi",
                "duration": max(
                    _dur(
                        audio.get(
                            "heatmap_hi"
                        ),
                        8.0,
                    ),
                    8.0,
                ),
                "audio": _audio_list(
                    audio,
                    "heatmap_hi",
                ),
                "renderer": lambda f, d:
                    _scene_heatmap(
                        summary,
                        heatmap,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # VOLUME
    # ─────────────────────────────────────────────────────────

    volume = chart_paths.get(
        "volume",
        "",
    )

    segs.append(
        {
            "name": "volume",
            "duration": max(
                _dur(
                    audio.get(
                        "volume_en"
                    ),
                    7.0,
                ),
                7.0,
            ),
            "audio": _audio_list(
                audio,
                "volume_en",
            ),
            "renderer": lambda f, d:
                _scene_volume(
                    summary,
                    volume,
                    f,
                    d,
                ),
        }
    )

    # ─────────────────────────────────────────────────────────
    # CANDLESTICKS
    # ─────────────────────────────────────────────────────────

    candles = chart_paths.get(
        "candles",
        {},
    )

    for sym, cpath in candles.items():

        if not cpath or not os.path.exists(cpath):
            continue

        segs.append(
            {
                "name": f"candle_{sym}",
                "duration": 6.0,
                "audio": [],
                "renderer": lambda f, d,
                s=sym,
                p=cpath:
                    _scene_candle(
                        summary,
                        p,
                        s,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # AI INSIGHTS
    # ─────────────────────────────────────────────────────────

    ai_card = chart_paths.get(
        "ai_insights",
        "",
    )

    segs.append(
        {
            "name": "ai",
            "duration": max(
                _dur(
                    audio.get("ai_en"),
                    14.0,
                ),
                10.0,
            ),
            "audio": _audio_list(
                audio,
                "ai_en",
            ),
            "renderer": lambda f, d:
                _scene_ai(
                    summary,
                    ai_card,
                    f,
                    d,
                ),
        }
    )

    if do_hi and audio.get("ai_hi"):
        segs.append(
            {
                "name": "ai_hi",
                "duration": max(
                    _dur(
                        audio.get("ai_hi"),
                        14.0,
                    ),
                    10.0,
                ),
                "audio": _audio_list(
                    audio,
                    "ai_hi",
                ),
                "renderer": lambda f, d:
                    _scene_ai(
                        summary,
                        ai_card,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # OUTLOOK
    # ─────────────────────────────────────────────────────────

    if audio.get("outlook_en"):
        segs.append(
            {
                "name": "outlook",
                "duration": max(
                    _dur(
                        audio.get(
                            "outlook_en"
                        ),
                        8.0,
                    ),
                    8.0,
                ),
                "audio": _audio_list(
                    audio,
                    "outlook_en",
                ),
                "renderer": lambda f, d:
                    _scene_outlook(
                        summary,
                        f,
                        d,
                    ),
            }
        )

    # ─────────────────────────────────────────────────────────
    # OUTRO
    # ─────────────────────────────────────────────────────────

    segs.append(
        {
            "name": "outro",
            "duration": max(
                _dur(
                    audio.get("outro_en"),
                    5.0,
                ),
                4.0,
            ),
            "audio": _audio_list(
                audio,
                "outro_en",
            ),
            "renderer": lambda f, d:
                _scene_outro(
                    summary,
                    f,
                    d,
                ),
        }
    )

    return segs


# ══════════════════════════════════════════════════════════════════════════════
# MAIN COMPOSER
# ══════════════════════════════════════════════════════════════════════════════

def compose_video(
    chart_paths,
    audio_paths,
    summary,
    language="both",
):
    """
    Main public API used by main.py.

    Existing call remains valid:

        video_path = compose_video(
            chart_paths,
            audio_paths,
            summary,
            language=language,
        )
    """

    date_str = datetime.now().strftime(
        "%Y%m%d"
    )

    out_path = os.path.join(
        OUTPUT_DIR,
        f"market_video_{date_str}.mp4",
    )

    tmp = tempfile.mkdtemp(
        prefix="mktbot_premium_"
    )

    try:

        logger.info(
            "🎬 Building premium animated market video..."
        )

        segments = _build_segments(
            chart_paths,
            audio_paths,
            summary,
            language,
        )

        logger.info(
            f"   {len(segments)} animated scenes"
        )

        rendered_segments = []

        for idx, seg in enumerate(
            segments
        ):

            name = seg["name"]
            duration = seg["duration"]
            renderer = seg["renderer"]
            aud_paths = seg["audio"]

            logger.info(
                f"   Scene {idx + 1}/{len(segments)} "
                f"{name} — {duration:.1f}s"
            )

            seg_dir = os.path.join(
                tmp,
                f"seg_{idx:03d}",
            )

            os.makedirs(
                seg_dir,
                exist_ok=True,
            )

            raw_video = os.path.join(
                seg_dir,
                "video.mp4",
            )

            # Render animation
            _render_frames(
                renderer,
                duration,
                raw_video,
            )

            # Audio
            final_seg = raw_video

            if aud_paths:

                seg_audio = os.path.join(
                    seg_dir,
                    "audio.mp3",
                )

                _concat_audio(
                    aud_paths,
                    seg_audio,
                )

                muxed = os.path.join(
                    seg_dir,
                    "final.mp4",
                )

                _mux_audio(
                    raw_video,
                    seg_audio,
                    muxed,
                )

                final_seg = muxed

            rendered_segments.append(
                final_seg
            )

        # ─────────────────────────────────────────────────────
        # CONCAT
        # ─────────────────────────────────────────────────────

        logger.info(
            "🎞️ Concatenating animated scenes..."
        )

        concat_list = os.path.join(
            tmp,
            "concat.txt",
        )

        with open(
            concat_list,
            "w",
            encoding="utf-8",
        ) as f:

            for video in rendered_segments:

                path = _absp(video)

                # Escape single quotes
                path = path.replace(
                    "'",
                    "'\\''",
                )

                f.write(
                    f"file '{path}'\n"
                )

        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                out_path,
            ],
            "final video concat",
        )

        # ─────────────────────────────────────────────────────
        # Final file size
        # ─────────────────────────────────────────────────────

        mb = (
            os.path.getsize(out_path)
            / (1024 * 1024)
        )

        logger.success(
            f"✅ Premium market video ready → "
            f"{out_path} ({mb:.1f} MB)"
        )

        return out_path

    finally:

        shutil.rmtree(
            tmp,
            ignore_errors=True,
        )