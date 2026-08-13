"""
src/shorts/short3_tomorrow.py
─────────────────────────────────────────────────────────────────
SHORT 3 — "Tomorrow's Prediction"
Premium AI outlook short:
  - Support/resistance levels animate in with horizontal lines
  - Buy/Sell/Watch cards flip in sequence
  - AI score meter fills up
  - Tomorrow outlook text types in
Duration: ~55s
"""

import os, math
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


def _draw_level_line(draw, label, value, y, progress, color=ACCENT):
    """Animated horizontal level line that draws from left."""
    p  = easing_out(min(progress, 1.0))
    lw = int(W * p)
    if lw > 0:
        draw.line([(0, y), (lw, y)], fill=(*color[:3],), width=2)
    if p > 0.3:
        draw.text((20, y - 26), label, font=font(24, True), fill=color)
        draw.text((20, y + 6),  str(value), font=font(28, True), fill=TEXT)


def _draw_ai_meter(draw, score, progress):
    """Circular AI confidence meter."""
    p   = easing_out(min(progress, 1.0))
    cx_m, cy_m = W // 2, 680
    r   = 160
    col = BULL if score >= 50 else BEAR

    # Background arc
    draw.ellipse([cx_m-r, cy_m-r, cx_m+r, cy_m+r], outline=(25,35,55), width=16)

    # Fallback: simple pie wedge
    angle = int(270 * (score / 100) * p)
    if angle > 0:
        draw.arc([cx_m-r, cy_m-r, cx_m+r, cy_m+r],
                 start=-90, end=-90+angle, fill=col, width=16)

    # Score text
    displayed = int(score * p)
    draw.text((cx_m, cy_m - 20), f"{displayed}",
              font=font(90, True), fill=TEXT, anchor="mm")
    draw.text((cx_m, cy_m + 46), "AI SCORE", font=font(26), fill=MUTED, anchor="mm")
    draw.text((cx_m, cy_m + 80), "/100",      font=font(22), fill=MUTED, anchor="mm")


def _draw_rec_card(draw, item, x, y, w, h, progress, card_type="buy"):
    """Buy/Sell/Watch recommendation card."""
    p = easing_out(min(progress, 1.0))
    if p <= 0: return

    colors = {"buy": BULL, "sell": BEAR, "watch": GOLD}
    bgs    = {"buy": (4,28,14), "sell": (28,4,10), "watch": (28,24,4)}
    mc     = colors.get(card_type, ACCENT)
    bg_c   = bgs.get(card_type, CARD_BG)

    # Slide in from right
    ox  = int(lerp(W, x, p))
    x2  = ox + w
    draw.rounded_rectangle([ox, y, x2, y+h], radius=12, fill=bg_c)
    draw.rounded_rectangle([ox, y, x2, y+h], radius=12, outline=mc, width=2)

    if p > 0.5:
        label = card_type.upper()
        draw.text((ox + 14, y + 10), label,
                  font=font(20, True), fill=mc)
        draw.text((ox + 14, y + 38), item.get("symbol",""),
                  font=font(36, True), fill=TEXT)
        reason = item.get("reason","")[:28]
        draw.text((ox + 14, y + 82), reason,
                  font=font(20), fill=MUTED)
        pct  = item.get("change_pct", 0)
        sign = "+" if pct >= 0 else ""
        pct_col = mc
        draw.text((x2 - 14, y + 50), f"{sign}{pct:.1f}%",
                  font=font(30, True), fill=pct_col, anchor="ra")


def build_short3(summary: dict, insights: dict, language="en") -> str:
    out_path = os.path.join(SHORTS_DIR, "short3_tomorrow.mp4")

    mood     = summary.get("market_mood", "Sideways")
    mc       = MOOD_COL.get(mood, ACCENT)
    score    = insights.get("score", 50)
    outlook  = insights.get("tomorrow_outlook", "Markets expected to open stable.")
    levels   = insights.get("levels", [])
    buy_list = insights.get("buy",   [])[:3]
    sell_list= insights.get("sell",  [])[:2]
    watch    = insights.get("watch", [])[:2]
    date_str = summary.get("date", "")
    nifty    = summary.get("nifty") or {}

    narration = (
        f"Tomorrow's AI prediction for {date_str}. "
        f"AI bullish score is {score} out of 100. "
        + outlook +
        f" Top picks: {', '.join(i['symbol'] for i in buy_list)}. "
        f"Not financial advice — always do your own research."
    )
    audio = _tts(narration, language)

    frames = []
    total  = FPS * 55

    P_INTRO  = FPS * 5
    P_METER  = FPS * 16
    P_LEVELS = FPS * 28
    P_RECS   = FPS * 44
    P_OUTRO  = FPS * 55

    for f in range(total):
        img, draw = new_frame()
        draw_grid(draw, alpha=5)
        draw_channel_badge(draw, mood)

        if f < P_INTRO:
            p = easing_out(f / P_INTRO)
            y = int(lerp(H//2 + 80, H//2 - 60, p))
            cx(draw, "TOMORROW'S", y - 60, font(60, True), MUTED)
            cx(draw, "PREDICTION", y + 20,  font(80, True), mc)
            cx(draw, f"AI Analysis • {date_str}", y + 112, font(28), MUTED)

        elif f < P_METER:
            lf = f - P_INTRO
            ld = P_METER - P_INTRO
            p  = easing_out(lf / ld)

            cx(draw, "AI CONFIDENCE", 140, font(42, True), GOLD)

            # Simple arc meter using draw.arc
            cx_m, cy_m = W//2, 700
            r = 200
            draw.ellipse([cx_m-r, cy_m-r, cx_m+r, cy_m+r],
                         outline=(25,35,55), width=20)
            angle = int(270 * (score/100) * p)
            col   = BULL if score >= 50 else BEAR
            if angle > 0:
                draw.arc([cx_m-r, cy_m-r, cx_m+r, cy_m+r],
                         start=135, end=135+angle, fill=col, width=20)
            disp = int(score * p)
            draw.text((cx_m, cy_m - 20), f"{disp}",
                      font=font(120, True), fill=TEXT, anchor="mm")
            draw.text((cx_m, cy_m + 60), "/ 100", font=font(36), fill=MUTED, anchor="mm")
            draw.text((cx_m, cy_m + 110), "BULLISH SCORE", font=font(28), fill=mc, anchor="mm")

            # Mood label
            draw.rounded_rectangle([W//2-120, 1020, W//2+120, 1080],
                                   radius=12, fill=mc)
            draw.text((W//2, 1050), mood.upper(), font=font(36, True),
                      fill=BG, anchor="mm")

        elif f < P_LEVELS:
            lf = f - P_METER
            ld = P_LEVELS - P_METER

            cx(draw, "KEY LEVELS", 148, font(44, True), ACCENT)

            # Nifty current
            draw.text((54, 210), "NIFTY NOW",
                      font=font(26), fill=MUTED)
            draw.text((54, 248), f"{nifty.get('ltp',0):,.0f}",
                      font=font(60, True), fill=TEXT)

            # Level lines
            ly_start = 380
            for i, lvl in enumerate(levels[:4]):
                delay = i * (ld // 5)
                prog  = max(0, (lf - delay) / (ld // 3))
                col   = BULL if "Support" in lvl.get("label","") else BEAR
                col   = GOLD if "Bank" in lvl.get("label","") else col
                ly    = ly_start + i * 180
                _draw_level_line(draw, lvl.get("label",""), lvl.get("value",""), ly, prog, col)
                if prog > 0.5:
                    draw.text((W - 20, ly - 20), lvl.get("note",""),
                              font=font(20), fill=MUTED, anchor="ra")

        elif f < P_RECS:
            lf = f - P_LEVELS
            ld = P_RECS - P_LEVELS

            cx(draw, "AI RECOMMENDATIONS", 148, font(38, True), GOLD)

            # Buy cards
            cx(draw, "BUY 🟢", 216, font(30, True), BULL)
            for i, item in enumerate(buy_list):
                delay = i * (ld // 6)
                prog  = max(0, (lf - delay) / (ld // 3))
                _draw_rec_card(draw, item, 40, 260 + i * 130, W - 80, 118, prog, "buy")

            # Sell cards
            cy_sell = 260 + len(buy_list) * 130 + 20
            cx(draw, "AVOID 🔴", cy_sell, font(30, True), BEAR)
            for i, item in enumerate(sell_list):
                delay = (len(buy_list) + i) * (ld // 6)
                prog  = max(0, (lf - delay) / (ld // 3))
                _draw_rec_card(draw, item, 40, cy_sell + 48 + i*130, W-80, 118, prog, "sell")

        else:
            lf = f - P_RECS
            p  = easing_in_out(lf / (P_OUTRO - P_RECS))
            cx(draw, "FOLLOW FOR DAILY", H//2 - 60, font(44, True), TEXT)
            cx(draw, "AI PREDICTIONS",   H//2 + 10,  font(44, True), mc)
            cx(draw, "@DalalStreetAI",   H//2 + 90,  font(32),       MUTED)

        draw_bottom_bar(draw, "Not financial advice  •  AI analysis  •  dalal street ai")
        frames.append(img)

    return encode_frames_to_video(frames, audio, out_path)