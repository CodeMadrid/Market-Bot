"""
src/thumbnail_generator.py  —  Dalal Street AI branded thumbnail
1280x720 YouTube thumbnail with:
  - "DALAL STREET AI" channel name at top
  - Date as main visual
  - Nifty level + mood
  - Top gainer (green) + top loser (red)
"""

import os
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from datetime import datetime

THUMB_DIR = "charts"
os.makedirs(THUMB_DIR, exist_ok=True)

W, H = 1280, 720


def _font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf"  if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()


def _cx(draw, text, y, font, color):
    bb = draw.textbbox((0, 0), text, font=font)
    x  = (W - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=font, fill=color)


def _text_w(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def generate_thumbnail(summary: dict, insights: dict) -> str:
    out = os.path.join(THUMB_DIR, "thumbnail.png")

    mood     = summary.get("market_mood", "Sideways")
    date_str = summary.get("date", datetime.now().strftime("%d %B %Y"))
    nifty    = summary.get("nifty") or {}
    gainer   = summary.get("top_gainer") or {}
    loser    = summary.get("top_loser")  or {}
    score    = insights.get("score", 50)

    # Parse date into parts for big display
    try:
        dt       = datetime.strptime(date_str, "%d %B %Y")
        day_num  = dt.strftime("%d")       # "05"
        month    = dt.strftime("%B").upper()  # "AUGUST"
        year     = dt.strftime("%Y")       # "2026"
        weekday  = dt.strftime("%A").upper()  # "WEDNESDAY"
    except:
        day_num = ""; month = date_str; year = ""; weekday = ""

    mood_colors = {
        "Bullish":  (0, 210, 120),
        "Bearish":  (220, 50, 70),
        "Sideways": (255, 165, 0),
    }
    mc = mood_colors.get(mood, (255, 165, 0))

    # ── Base background — deep dark ───────────────────────────
    img  = Image.new("RGB", (W, H), (6, 10, 18))
    draw = ImageDraw.Draw(img)

    # Subtle diagonal lines texture
    for i in range(-H, W, 40):
        draw.line([(i, 0), (i + H, H)], fill=(255, 255, 255, 6), width=1)

    # ══════════════════════════════════════════════════════════
    #  TOP BAR — Channel name "DALAL STREET AI"
    # ══════════════════════════════════════════════════════════
    # Full-width top bar with channel color
    draw.rectangle([0, 0, W, 90], fill=(14, 20, 36))
    draw.rectangle([0, 86, W, 90], fill=mc)   # bottom accent line

    # Channel logo circle
    draw.ellipse([18, 10, 72, 70], fill=mc)
    draw.text((45, 40), "D", font=_font(38, bold=True),
              fill=(6, 10, 18), anchor="mm")

    # Channel name
    draw.text((86, 14), "DALAL STREET AI",
              font=_font(42, bold=True), fill=(255, 255, 255))
    draw.text((88, 56), "Daily Market Analysis  •  NSE/BSE",
              font=_font(22), fill=(140, 150, 170))

    # LIVE badge on right
    draw.rounded_rectangle([1120, 22, 1258, 62], radius=8, fill=(200, 0, 0))
    draw.text((1190, 42), "DAILY", font=_font(26, bold=True),
              fill=(255, 255, 255), anchor="mm")

    # ══════════════════════════════════════════════════════════
    #  DATE — Big visual center-left
    # ══════════════════════════════════════════════════════════

    # Date background card
    draw.rounded_rectangle([28, 108, 520, 480], radius=20, fill=(12, 18, 32))
    draw.rounded_rectangle([28, 108, 520, 480], radius=20,
                            outline=mc, width=3)

    # Weekday (small, top of card)
    draw.text((274, 132), weekday, font=_font(28),
              fill=mc, anchor="mm")

    # Day number (HUGE)
    draw.text((274, 258), day_num, font=_font(210, bold=True),
              fill=(255, 255, 255), anchor="mm")

    # Month
    draw.text((274, 362), month, font=_font(52, bold=True),
              fill=(230, 237, 243), anchor="mm")

    # Year
    draw.text((274, 422), year, font=_font(34),
              fill=(100, 115, 135), anchor="mm")

    # Thin line under day
    draw.rectangle([60, 316, 488, 318], fill=(30, 42, 60))

    # ══════════════════════════════════════════════════════════
    #  RIGHT SIDE — Market data
    # ══════════════════════════════════════════════════════════
    RX = 548   # right section start x

    # ── Nifty block ───────────────────────────────────────────
    nifty_col  = (0, 210, 120) if nifty.get("change_pct", 0) >= 0 else (220, 50, 70)
    sign_arrow = "▲" if nifty.get("change_pct", 0) >= 0 else "▼"

    draw.text((RX, 108), "NIFTY 50", font=_font(28), fill=(100, 115, 135))
    draw.text((RX, 140), f"{nifty.get('ltp', 0):,.0f}",
              font=_font(86, bold=True), fill=(255, 255, 255))
    draw.text((RX, 234),
              f"{sign_arrow}  {abs(nifty.get('change_pct', 0)):.2f}%  "
              f"({'+' if nifty.get('change_pct',0)>=0 else ''}{nifty.get('change',0):,.0f})",
              font=_font(34, bold=True), fill=nifty_col)

    # Mood pill
    mood_text = f"  {mood.upper()}  "
    mw = _text_w(draw, mood_text, _font(28, bold=True)) + 20
    draw.rounded_rectangle([RX, 282, RX + mw, 326], radius=10, fill=mc)
    draw.text((RX + 10, 304), mood.upper(),
              font=_font(28, bold=True), fill=(6, 10, 18), anchor="lm")

    # ── Divider ───────────────────────────────────────────────
    draw.rectangle([RX, 344, 1252, 346], fill=(25, 35, 55))

    # ── Top Gainer ────────────────────────────────────────────
    draw.rounded_rectangle([RX, 358, 1252, 468], radius=14, fill=(4, 28, 18))
    draw.rounded_rectangle([RX, 358, 1252, 468], radius=14,
                            outline=(0, 180, 100), width=2)

    draw.text((RX + 18, 374), "BEST PERFORMER TODAY",
              font=_font(22), fill=(0, 180, 100))
    draw.text((RX + 18, 402), gainer.get("symbol", "—"),
              font=_font(52, bold=True), fill=(255, 255, 255))
    draw.text((RX + 18, 454), f"₹{gainer.get('ltp', 0):,.2f}",
              font=_font(26), fill=(160, 170, 185), anchor="lm")

    gpct = gainer.get("change_pct", 0)
    gtxt = f"+{gpct:.2f}%"
    gw   = _text_w(draw, gtxt, _font(44, bold=True))
    draw.text((1252 - 18 - gw, 416), gtxt,
              font=_font(44, bold=True), fill=(0, 220, 120))

    # ── Top Loser ─────────────────────────────────────────────
    draw.rounded_rectangle([RX, 480, 1252, 590], radius=14, fill=(28, 4, 8))
    draw.rounded_rectangle([RX, 480, 1252, 590], radius=14,
                            outline=(180, 40, 60), width=2)

    draw.text((RX + 18, 496), "BIGGEST DECLINER TODAY",
              font=_font(22), fill=(180, 40, 60))
    draw.text((RX + 18, 524), loser.get("symbol", "—"),
              font=_font(52, bold=True), fill=(255, 255, 255))
    draw.text((RX + 18, 576), f"₹{loser.get('ltp', 0):,.2f}",
              font=_font(26), fill=(160, 170, 185), anchor="lm")

    lpct = loser.get("change_pct", 0)
    ltxt = f"{lpct:.2f}%"
    lw   = _text_w(draw, ltxt, _font(44, bold=True))
    draw.text((1252 - 18 - lw, 538), ltxt,
              font=_font(44, bold=True), fill=(220, 60, 80))

    # ══════════════════════════════════════════════════════════
    #  BOTTOM BAR
    # ══════════════════════════════════════════════════════════
    draw.rectangle([0, 610, W, 720], fill=(10, 16, 28))
    draw.rectangle([0, 610, W, 614], fill=mc)

    # AI score bar
    draw.text((40, 630), "AI BULLISH SCORE",
              font=_font(22, bold=True), fill=(100, 115, 135))
    draw.rounded_rectangle([40, 656, 700, 686], radius=6, fill=(22, 30, 48))
    bar_w = max(6, int((score / 100) * 660))
    bar_c = (0, 200, 110) if score >= 50 else (200, 50, 70)
    draw.rounded_rectangle([40, 656, 40 + bar_w, 686], radius=6, fill=bar_c)
    draw.text((714, 671), f"{score}/100",
              font=_font(28, bold=True), fill=(230, 237, 243), anchor="lm")

    # Hashtags / disclaimer right side
    draw.text((1252, 635), "#StockMarket  #Nifty  #NSE",
              font=_font(20), fill=(70, 85, 105), anchor="ra")
    draw.text((1252, 662), "Not financial advice",
              font=_font(20), fill=(55, 68, 88), anchor="ra")
    draw.text((1252, 688), "dalal street ai",
              font=_font(22, bold=True), fill=(mc[0]//2, mc[1]//2+30, mc[2]//2),
              anchor="ra")

    img.save(out, "PNG", quality=95)
    logger.success(f"✅ Thumbnail saved → {out}")
    return out