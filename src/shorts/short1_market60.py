"""
src/shorts/short1_market60.py
─────────────────────────────────────────────────────────────────
SHORT 1 — "Market in 60 Seconds"
Premium animated short:
  - Nifty meter animates up/down with glow
  - Top 3 gainers flip in as cards (green)
  - Top 3 losers flip in as cards (red)
  - Market mood verdict with particle burst
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
import tempfile, os as _os


def _tts(text, lang="en"):
    p = tempfile.mktemp(suffix=".mp3")
    gTTS(text=text, lang=lang, slow=False).save(p)
    return p


def _draw_nifty_meter(draw, ltp, change_pct, progress):
    """Animated Nifty display with glowing value."""
    mc  = BULL if change_pct >= 0 else BEAR
    val = int(ltp * progress)

    # Label
    draw.text((W//2, 180), "NIFTY 50", font=font(36), fill=MUTED, anchor="mm")

    # Glowing value
    for offset, alpha in [(8, 20), (4, 40), (0, 255)]:
        col = (*mc[:3],) if offset == 0 else mc
        draw.text((W//2 + offset, 300 + offset),
                  f"{val:,}", font=font(110, True), fill=col, anchor="mm")

    # Change badge
    sign   = "▲" if change_pct >= 0 else "▼"
    ch_txt = f"{sign} {abs(change_pct):.2f}%"
    bw     = text_w(draw, ch_txt, font(44, True)) + 40
    bx     = (W - bw) // 2
    draw.rounded_rectangle([bx, 360, bx + bw, 416], radius=14, fill=mc)
    draw.text((W//2, 388), ch_txt, font=font(44, True), fill=BG, anchor="mm")

    # Horizontal progress bar
    draw.rounded_rectangle([80, 440, W - 80, 460], radius=6, fill=(25, 35, 55))
    bar = int((W - 160) * min(progress, 1.0))
    if bar > 0:
        draw.rounded_rectangle([80, 440, 80 + bar, 460], radius=6, fill=mc)


def _draw_stock_card(draw, q, x, y, w, h, flip_progress, is_gainer=True):
    """
    Animated flip-in card for a stock.
    flip_progress: 0→1, card scales in from center
    """
    if flip_progress <= 0:
        return

    mc   = BULL if is_gainer else BEAR
    bg_c = (4, 28, 14) if is_gainer else (28, 4, 10)
    p    = easing_out(min(flip_progress, 1.0))

    # Scale effect
    card_h = int(h * p)
    if card_h < 4:
        return
    cy_mid = y + h // 2
    y1     = cy_mid - card_h // 2
    y2     = cy_mid + card_h // 2

    draw.rounded_rectangle([x, y1, x + w, y2], radius=12, fill=bg_c)
    draw.rounded_rectangle([x, y1, x + w, y2], radius=12, outline=mc, width=2)

    if p > 0.5:
        text_alpha = int(255 * ((p - 0.5) / 0.5))
        sym   = q.get("symbol", "")[:8]
        pct   = q.get("change_pct", 0)
        price = q.get("ltp", 0)
        sign  = "+" if pct >= 0 else ""

        mid_y = (y1 + y2) // 2

        # Symbol
        draw.text((x + w//2, mid_y - 30), sym,
                  font=font(34, True), fill=TEXT, anchor="mm")
        # Price
        draw.text((x + w//2, mid_y + 14), f"₹{price:,.0f}",
                  font=font(24), fill=MUTED, anchor="mm")
        # Change
        draw.text((x + w//2, mid_y + 52), f"{sign}{pct:.2f}%",
                  font=font(30, True), fill=mc, anchor="mm")


def _draw_particles(draw, cx_p, cy_p, count, frame, color):
    """Burst particles from center."""
    for i in range(count):
        angle = (2 * math.pi * i / count) + frame * 0.1
        r     = 60 + frame * 8
        alpha = max(0, 255 - frame * 12)
        px    = int(cx_p + r * math.cos(angle))
        py    = int(cy_p + r * math.sin(angle))
        size  = max(2, 8 - frame // 5)
        if 0 < px < W and 0 < py < H:
            draw.ellipse([px-size, py-size, px+size, py+size], fill=color)


def build_short1(summary: dict, insights: dict, language="en") -> str:
    out_path = os.path.join(SHORTS_DIR, "short1_market60.mp4")

    mood      = summary.get("market_mood", "Sideways")
    mc        = MOOD_COL.get(mood, ACCENT)
    nifty     = summary.get("nifty") or {}
    ltp       = nifty.get("ltp", 24000)
    chg_pct   = nifty.get("change_pct", 0)
    date_str  = summary.get("date", "")
    gainers   = summary.get("top_gainers", [])[:3]
    losers    = summary.get("top_losers",  [])[:3]

    # TTS
    mood_hi = {"Bullish":"Bullish","Bearish":"Bearish","Sideways":"Sideways"}.get(mood, mood)
    sign_txt = "gained" if chg_pct >= 0 else "fell"
    narration = (
        f"Market update for {date_str}. "
        f"Nifty {sign_txt} {abs(chg_pct):.2f} percent, closing at {ltp:,.0f}. "
        f"Market mood is {mood}. "
        f"Top gainers today: {', '.join(q['symbol'] for q in gainers[:3])}. "
        f"Biggest losers: {', '.join(q['symbol'] for q in losers[:3])}. "
        f"Stay informed, stay invested!"
    )
    audio = _tts(narration, language)

    frames = []
    total  = FPS * 55  # 55 seconds

    # Phase timing
    P_INTRO  = FPS * 6
    P_NIFTY  = FPS * 14   # nifty animates in
    P_GAIN   = FPS * 26   # gainers flip in
    P_LOSE   = FPS * 38   # losers flip in
    P_VERDICT= FPS * 50   # mood verdict
    P_OUTRO  = FPS * 55

    for f in range(total):
        img, draw = new_frame()
        draw_grid(draw, alpha=6)

        # ── Channel badge ──────────────────────────────────────
        draw_channel_badge(draw, mood)

        # ── Phase: Intro ──────────────────────────────────────
        if f < P_INTRO:
            p = easing_out(f / P_INTRO)
            y = int(lerp(H//2 + 100, H//2 - 80, p))
            cx(draw, "MARKET IN", y - 70, font(52), MUTED)
            cx(draw, "60 SECONDS", y,      font(96, True), TEXT)
            cx(draw, date_str,    y + 90,  font(36), mc)

        # ── Phase: Nifty ──────────────────────────────────────
        elif f < P_NIFTY:
            lf = f - P_INTRO
            ld = P_NIFTY - P_INTRO
            p  = easing_out(lf / ld)

            # Glow behind nifty
            glow_col = (*BULL[:3], 40) if chg_pct >= 0 else (*BEAR[:3], 40)
            for r in [200, 150, 100]:
                a = 20 if r == 200 else 35 if r == 150 else 50
                draw.ellipse([W//2 - r, 240 - r, W//2 + r, 240 + r],
                             fill=(*mc[:3], a))

            _draw_nifty_meter(draw, ltp, chg_pct, p)
            cx(draw, "TODAY'S INDEX", 500, font(30), MUTED)

        # ── Phase: Gainers ────────────────────────────────────
        elif f < P_GAIN:
            lf = f - P_NIFTY
            ld = P_GAIN - P_NIFTY
            _draw_nifty_meter(draw, ltp, chg_pct, 1.0)

            cx(draw, "TOP GAINERS 🟢", 520, font(38, True), BULL)
            card_w = (W - 80) // 3 - 10
            for i, q in enumerate(gainers):
                delay = i * (ld // 4)
                fp    = max(0, (lf - delay) / (ld // 2))
                cx_c  = 40 + i * (card_w + 10)
                _draw_stock_card(draw, q, cx_c, 580, card_w, 200, fp, True)

        # ── Phase: Losers ─────────────────────────────────────
        elif f < P_LOSE:
            lf = f - P_GAIN
            ld = P_LOSE - P_GAIN
            _draw_nifty_meter(draw, ltp, chg_pct, 1.0)

            cx(draw, "TOP GAINERS 🟢", 520, font(38, True), BULL)
            card_w = (W - 80) // 3 - 10
            for i, q in enumerate(gainers):
                cx_c = 40 + i * (card_w + 10)
                _draw_stock_card(draw, q, cx_c, 580, card_w, 200, 1.0, True)

            cx(draw, "TOP LOSERS 🔴", 820, font(38, True), BEAR)
            for i, q in enumerate(losers):
                delay = i * (ld // 4)
                fp    = max(0, (lf - delay) / (ld // 2))
                cx_c  = 40 + i * (card_w + 10)
                _draw_stock_card(draw, q, cx_c, 880, card_w, 200, fp, False)

        # ── Phase: Verdict ────────────────────────────────────
        elif f < P_VERDICT:
            lf  = f - P_LOSE
            p   = easing_out(min(lf / (FPS * 4), 1.0))
            pf  = lf - FPS * 4

            # All cards settled
            card_w = (W - 80) // 3 - 10
            cx(draw, "TOP GAINERS 🟢", 520, font(34, True), BULL)
            for i, q in enumerate(gainers):
                _draw_stock_card(draw, q, 40 + i*(card_w+10), 580, card_w, 180, 1.0, True)
            cx(draw, "TOP LOSERS 🔴", 800, font(34, True), BEAR)
            for i, q in enumerate(losers):
                _draw_stock_card(draw, q, 40 + i*(card_w+10), 860, card_w, 180, 1.0, False)

            # Verdict
            verdict_y = int(lerp(H, 1200, p))
            mood_emoji = {"Bullish":"🟢","Bearish":"🔴","Sideways":"🟡"}.get(mood,"📊")
            draw.rounded_rectangle([60, verdict_y - 10, W - 60, verdict_y + 110],
                                   radius=20, fill=mc)
            cx(draw, f"MARKET IS {mood.upper()}", verdict_y + 8,  font(48, True), BG)
            cx(draw, f"{mood_emoji} {date_str}",  verdict_y + 62, font(30),        BG)

            # Particles
            if pf > 0:
                _draw_particles(draw, W//2, verdict_y + 50, 12, int(pf), mc)

        # ── Outro ─────────────────────────────────────────────
        else:
            lf = f - P_VERDICT
            p  = easing_in_out(lf / (P_OUTRO - P_VERDICT))
            cx(draw, "FOLLOW FOR DAILY", H//2 - 60, font(44, True), TEXT)
            cx(draw, "MARKET UPDATES",   H//2,       font(44, True), mc)
            cx(draw, "@DalalStreetAI",   H//2 + 70,  font(34),       MUTED)

        draw_bottom_bar(draw)
        frames.append(img)

    return encode_frames_to_video(frames, audio, out_path)