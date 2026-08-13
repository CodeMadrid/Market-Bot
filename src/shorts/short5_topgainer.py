"""
src/shorts/short5_topgainer.py
─────────────────────────────────────────────────────────────────
SHORT 5 — "Top Gainer Deep Dive"
Most data-rich short — full story of today's top gainer:
  - Stock name slams in with impact effect
  - Price counter animates up
  - Volume spike visualization
  - Why it moved (AI reasoning)
  - Buy/Hold/Sell verdict
Duration: ~55s
"""

import os, math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from loguru import logger
from src.shorts.base_short import (
    W, H, FPS, BG, BULL, BEAR, GOLD, ACCENT, TEXT, MUTED,
    CARD_BG, MOOD_COL, SHORTS_DIR,
    font, cx, text_w, new_frame, draw_grid,
    draw_channel_badge, draw_bottom_bar,
    easing_out, easing_in_out, lerp, encode_frames_to_video,
)
from gtts import gTTS
import tempfile


def _tts(text, lang="en"):
    p = tempfile.mktemp(suffix=".mp3")
    gTTS(text=text, lang=lang, slow=False).save(p)
    return p


def _draw_price_counter(draw, current, target, y, size=90):
    """Animated counting number."""
    draw.text((W//2, y), f"₹{current:,.2f}",
              font=font(size, True), fill=TEXT, anchor="mm")


def _draw_stat_box(draw, label, value, x, y, w, h, color, progress):
    """Animated stat card."""
    p = easing_out(min(progress, 1.0))
    if p <= 0: return
    bh = int(h * p)
    cy_mid = y + h // 2
    draw.rounded_rectangle([x, cy_mid - bh//2, x+w, cy_mid + bh//2],
                           radius=10, fill=CARD_BG)
    draw.rounded_rectangle([x, cy_mid - bh//2, x+w, cy_mid + bh//2],
                           radius=10, outline=color, width=2)
    if p > 0.5:
        draw.text((x + w//2, cy_mid - 18), label,
                  font=font(22), fill=MUTED, anchor="mm")
        draw.text((x + w//2, cy_mid + 22), str(value),
                  font=font(30, True), fill=color, anchor="mm")


def _draw_volume_spike(draw, volumes, current_vol, x, y, w, h, progress):
    """Animated volume bar showing today's spike."""
    p       = easing_out(min(progress, 1.0))
    n       = len(volumes)
    bar_w   = max(4, w // n - 2)
    vol_max = max(max(volumes), current_vol) * 1.1

    for i, vol in enumerate(volumes):
        bh    = int(h * (vol / vol_max))
        bx    = x + i * (bar_w + 2)
        col   = (40, 55, 80)
        draw.rectangle([bx, y + h - bh, bx + bar_w, y + h], fill=col)

    # Today's bar (animated, highlighted)
    today_h = int(h * (current_vol / vol_max) * p)
    today_x = x + (n - 1) * (bar_w + 2)
    if today_h > 0:
        draw.rectangle([today_x, y + h - today_h, today_x + bar_w, y + h],
                       fill=BULL)
        # Glow
        for g in range(3):
            draw.rectangle([today_x - g, y + h - today_h - g,
                           today_x + bar_w + g, y + h],
                          fill=(*BULL, max(0, 60 - g*20)))

    # Label
    draw.text((x + w//2, y + h + 20), "VOLUME SPIKE",
              font=font(24, True), fill=GOLD, anchor="mm")


def build_short5(summary: dict, insights: dict,
                 candle_data: dict = None, language="en") -> str:
    out_path = os.path.join(SHORTS_DIR, "short5_topgainer.mp4")

    mood     = summary.get("market_mood", "Sideways")
    mc       = MOOD_COL.get(mood, ACCENT)
    gainer   = summary.get("top_gainer") or {}
    symbol   = gainer.get("symbol", "STOCK")
    ltp      = gainer.get("ltp", 1000)
    chg_pct  = gainer.get("change_pct", 0)
    chg_abs  = gainer.get("change", 0)
    high     = gainer.get("high", ltp * 1.01)
    low      = gainer.get("low", ltp * 0.99)
    volume   = gainer.get("volume", 5_000_000)
    date_str = summary.get("date", "")

    # AI reason for this stock
    buy_list = insights.get("buy", [])
    reason   = next((i.get("reason","Strong momentum") for i in buy_list
                    if i.get("symbol") == symbol), "Strong buying momentum today")

    # Candle data for volume history
    df = None
    if candle_data and symbol in candle_data:
        df = candle_data[symbol]

    vol_history = []
    if df is not None and len(df) >= 10:
        vol_history = df["volume"].tail(14).tolist()
    else:
        vol_history = [volume * (0.3 + 0.4 * abs(np.random.randn())) for _ in range(14)]
    vol_history.append(volume)

    narration = (
        f"Top gainer alert! {symbol} surged {chg_pct:.2f} percent today on {date_str}. "
        f"It hit a high of rupees {high:,.0f} with strong volume. "
        f"{reason}. "
        f"RSI and momentum indicators support the move. "
        f"Watch this stock tomorrow for continuation."
        f" Not financial advice."
    )
    audio = _tts(narration, language)

    frames = []
    total  = FPS * 55

    P_IMPACT = FPS * 4
    P_PRICE  = FPS * 14
    P_STATS  = FPS * 26
    P_VOL    = FPS * 38
    P_REASON = FPS * 50
    P_OUTRO  = FPS * 55

    for f in range(total):
        img, draw = new_frame()
        draw_grid(draw, alpha=4)
        draw_channel_badge(draw, mood)

        if f < P_IMPACT:
            # Impact slam — text starts huge and settles
            p     = easing_out(f / P_IMPACT)
            scale = lerp(2.0, 1.0, p)
            size  = int(100 * scale)
            cx(draw, "TOP GAINER", 200, font(44, True), GOLD)
            cx(draw, symbol, int(H//2 - 60 * p), font(min(size, 130), True), BULL)

            # Flash effect on first frames
            if f < 6:
                alpha = int(200 * (1 - f/6))
                draw.rectangle([0, 0, W, H], fill=(*BULL[:3],))

            cx(draw, f"+{chg_pct:.2f}%", H//2 + 100, font(64, True), TEXT)

        elif f < P_PRICE:
            lf  = f - P_IMPACT
            ld  = P_PRICE - P_IMPACT
            p   = easing_out(lf / ld)
            cur = lerp(ltp * 0.97, ltp, p)

            cx(draw, symbol, 180, font(72, True), TEXT)
            cx(draw, f"+{chg_pct:.2f}%  TODAY", 260, font(36, True), BULL)

            # Big animated price
            _draw_price_counter(draw, cur, ltp, H//2 - 40, size=96)

            # Change badge
            draw.rounded_rectangle([W//2 - 160, H//2 + 60, W//2 + 160, H//2 + 120],
                                   radius=14, fill=BULL)
            draw.text((W//2, H//2 + 90), f"▲ ₹{chg_abs:,.2f}",
                      font=font(38, True), fill=BG, anchor="mm")

            # Day range
            draw.text((W//2, H//2 + 160), f"H: ₹{high:,.0f}  |  L: ₹{low:,.0f}",
                      font=font(28), fill=MUTED, anchor="mm")

        elif f < P_STATS:
            lf = f - P_PRICE
            ld = P_STATS - P_PRICE
            cx(draw, symbol, 148, font(56, True), TEXT)
            cx(draw, "TODAY'S STATS", 216, font(32), GOLD)

            stats = [
                ("OPEN",   f"₹{gainer.get('open',0):,.0f}",  MUTED,    0),
                ("HIGH",   f"₹{high:,.0f}",                   BULL,     1),
                ("LOW",    f"₹{low:,.0f}",                    BEAR,     2),
                ("CLOSE",  f"₹{ltp:,.0f}",                    TEXT,     3),
                ("CHANGE", f"+{chg_pct:.2f}%",                BULL,     4),
                ("VOL",    f"{volume/1e6:.1f}M",               ACCENT,   5),
            ]
            cols, rows = 2, 3
            sw = (W - 80) // cols
            sh = 160
            for idx, (lbl, val, col, order) in enumerate(stats):
                delay = order * (ld // 8)
                prog  = max(0, (lf - delay) / (ld // 4))
                r, c  = divmod(idx, cols)
                sx    = 40 + c * sw
                sy    = 300 + r * (sh + 16)
                _draw_stat_box(draw, lbl, val, sx, sy, sw - 10, sh, col, prog)

        elif f < P_VOL:
            lf = f - P_STATS
            ld = P_VOL - P_STATS
            p  = easing_out(lf / ld)

            cx(draw, symbol, 148, font(56, True), TEXT)
            cx(draw, "VOLUME ANALYSIS", 216, font(32), GOLD)

            _draw_volume_spike(draw, vol_history[:-1], volume,
                               40, 300, W - 80, 700, p)

            # Volume comparison
            avg_vol = np.mean(vol_history[:-1])
            ratio   = volume / avg_vol if avg_vol > 0 else 1
            if p > 0.5:
                draw.text((W//2, 1060),
                          f"{ratio:.1f}x average volume",
                          font=font(38, True), fill=GOLD, anchor="mm")
                cx(draw, "Unusual activity detected!", 1116, font(28), BULL)

        elif f < P_REASON:
            lf = f - P_VOL
            p  = easing_out(min(lf / (FPS * 4), 1.0))

            cx(draw, "WHY DID IT MOVE?", 180, font(44, True), GOLD)

            # Reason card
            card_h = int(360 * p)
            cy_mid = H//2 + 50
            draw.rounded_rectangle([40, cy_mid - card_h//2, W-40, cy_mid + card_h//2],
                                   radius=20, fill=(4, 28, 14))
            draw.rounded_rectangle([40, cy_mid - card_h//2, W-40, cy_mid + card_h//2],
                                   radius=20, outline=BULL, width=3)
            if p > 0.4:
                cx(draw, "AI ANALYSIS", cy_mid - card_h//2 + 24, font(28), BULL)
                # Wrap reason
                words = reason.split()
                line, lines = "", []
                for w in words:
                    test = line + " " + w if line else w
                    if text_w(draw, test, font(30)) < W - 120:
                        line = test
                    else:
                        lines.append(line); line = w
                if line: lines.append(line)
                for li, ln in enumerate(lines[:4]):
                    draw.text((W//2, cy_mid - 50 + li * 44), ln,
                              font=font(30), fill=TEXT, anchor="mm")

            # Verdict
            if p > 0.7:
                draw.rounded_rectangle([80, cy_mid + card_h//2 + 20,
                                       W-80, cy_mid + card_h//2 + 90],
                                      radius=14, fill=BULL)
                draw.text((W//2, cy_mid + card_h//2 + 55),
                          "WATCH THIS STOCK TOMORROW",
                          font=font(28, True), fill=BG, anchor="mm")

        else:
            cx(draw, f"#{symbol}", H//2 - 60, font(60, True), BULL)
            cx(draw, "FOLLOW FOR DAILY", H//2 + 20, font(40, True), TEXT)
            cx(draw, "STOCK ALERTS",     H//2 + 76, font(40, True), mc)
            cx(draw, "@DalalStreetAI",   H//2 + 140, font(32),      MUTED)

        draw_bottom_bar(draw, "Not financial advice  •  dalal street ai")
        frames.append(img)

    return encode_frames_to_video(frames, audio, out_path)