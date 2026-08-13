"""
src/shorts/short2_sector.py
─────────────────────────────────────────────────────────────────
SHORT 2 — "Sector Spotlight"
Premium animated short showing one sector per day:
  - Animated heatmap cells appear one by one
  - Each stock bar grows from 0
  - Sector leader highlighted with glow
  - Rotates: Mon=Banking, Tue=IT, Wed=Auto, Thu=Pharma, Fri=Energy
Duration: ~55s
"""

import os, math
from datetime import datetime
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

SECTOR_SCHEDULE = {
    0: "Banking",   # Monday
    1: "IT",
    2: "Auto",
    3: "Pharma",
    4: "Energy",
    5: "FMCG",
    6: "Metals",
}

SECTOR_EMOJI = {
    "Banking":"🏦","IT":"💻","Auto":"🚗","Pharma":"💊",
    "Energy":"⚡","FMCG":"🛒","Metals":"⚙️",
}


def _tts(text, lang="en"):
    p = tempfile.mktemp(suffix=".mp3")
    gTTS(text=text, lang=lang, slow=False).save(p)
    return p


def _sector_color(change_pct):
    """Color based on % change — red→yellow→green."""
    if change_pct >= 2:    return (0, 230, 120)
    elif change_pct >= 0:  return (0, int(180 + change_pct*25), int(80 + change_pct*20))
    elif change_pct >= -2: return (int(180 + abs(change_pct)*25), 60, 60)
    else:                  return (230, 40, 60)


def _draw_animated_bar(draw, q, x, y, bar_max_h, progress, bar_w=100):
    """Animated growing bar for one stock."""
    pct    = q.get("change_pct", 0)
    mc     = _sector_color(pct)
    bh     = int(abs(pct) * 30 * easing_out(progress))
    bh     = max(4, min(bh, bar_max_h))

    # Bar
    by2 = y
    by1 = y - bh
    draw.rounded_rectangle([x, by1, x + bar_w, by2], radius=6, fill=mc)

    # Glow at top of bar
    for g in range(min(bh, 20), 0, -5):
        draw.rounded_rectangle([x, by1, x + bar_w, by1 + g],
                               radius=6, fill=(*mc[:3],))

    # Labels
    sym = q.get("symbol", "")[:6]
    sign = "+" if pct >= 0 else ""
    draw.text((x + bar_w//2, by2 + 16), sym,
              font=font(22, True), fill=TEXT, anchor="mm")
    draw.text((x + bar_w//2, by2 + 42), f"{sign}{pct:.1f}%",
              font=font(20, True), fill=mc, anchor="mm")


def _draw_heatmap_cell(draw, q, x, y, w, h, progress):
    """Animated heatmap tile."""
    p  = easing_out(min(progress, 1.0))
    if p <= 0: return
    pct = q.get("change_pct", 0)
    mc  = _sector_color(pct)

    # Scale from center
    cx_c = x + w // 2
    cy_c = y + h // 2
    cw   = int(w * p)
    ch   = int(h * p)
    x1   = cx_c - cw // 2
    y1   = cy_c - ch // 2
    x2   = cx_c + cw // 2
    y2   = cy_c + ch // 2

    draw.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=mc)

    if p > 0.6:
        sym  = q.get("symbol", "")[:6]
        ppct = q.get("change_pct", 0)
        sign = "+" if ppct >= 0 else ""
        text_col = BG if ppct >= -1 else TEXT
        draw.text((cx_c, cy_c - 14), sym,
                  font=font(26, True), fill=text_col, anchor="mm")
        draw.text((cx_c, cy_c + 20), f"{sign}{ppct:.1f}%",
                  font=font(22, True), fill=text_col, anchor="mm")


def build_short2(summary: dict, insights: dict, language="en") -> str:
    out_path = os.path.join(SHORTS_DIR, "short2_sector.mp4")

    # Pick sector for today
    weekday = datetime.now().weekday()
    sector  = SECTOR_SCHEDULE.get(weekday, "Banking")
    emoji   = SECTOR_EMOJI.get(sector, "📊")
    mc      = MOOD_COL.get(summary.get("market_mood","Sideways"), ACCENT)

    # Get sector stocks
    sector_stocks = summary.get("sectors", {}).get(sector, [])
    if not sector_stocks:
        # Fallback — pick from quotes
        sector_stocks = summary.get("quotes", [])[:6]

    # Sort by change_pct
    sector_stocks = sorted(sector_stocks, key=lambda x: x.get("change_pct",0), reverse=True)
    leader = sector_stocks[0] if sector_stocks else {}

    date_str = summary.get("date", "")

    # TTS
    leader_sym = leader.get("symbol","")
    leader_pct = leader.get("change_pct",0)
    narration = (
        f"Sector spotlight for {date_str}. Today we look at the {sector} sector. "
        f"{leader_sym} led the sector with {'+' if leader_pct>=0 else ''}{leader_pct:.2f} percent. "
        + (f"The sector was overall {'positive' if sum(q.get('change_pct',0) for q in sector_stocks)>0 else 'negative'} today. " )
        + f"Watch tomorrow's {sector} sector for continuation of this trend."
    )
    audio = _tts(narration, language)

    frames  = []
    total   = FPS * 55

    P_INTRO  = FPS * 5
    P_BARS   = FPS * 20
    P_HEAT   = FPS * 38
    P_LEADER = FPS * 50
    P_OUTRO  = FPS * 55

    for f in range(total):
        img, draw = new_frame()
        draw_grid(draw, alpha=5)
        draw_channel_badge(draw, summary.get("market_mood","Sideways"))

        if f < P_INTRO:
            p = easing_out(f / P_INTRO)
            y = int(lerp(H//2 + 80, H//2 - 60, p))
            cx(draw, "SECTOR SPOTLIGHT", y - 60, font(52, True), mc)
            cx(draw, f"{emoji}  {sector.upper()}",  y + 10,  font(80, True), TEXT)
            cx(draw, date_str,                       y + 100, font(32),       MUTED)

        elif f < P_BARS:
            lf = f - P_INTRO
            ld = P_BARS - P_INTRO

            cx(draw, f"{emoji} {sector.upper()} SECTOR", 140, font(46, True), mc)
            cx(draw, "Performance Today", 196, font(28), MUTED)

            # Animated bars
            n      = min(len(sector_stocks), 6)
            bar_w  = 100
            gap    = (W - 80 - n * bar_w) // (n + 1)
            bar_y  = 1300
            max_h  = 600

            for i, q in enumerate(sector_stocks[:n]):
                delay = i * (ld // (n + 2))
                prog  = max(0, (lf - delay) / (ld // 2))
                bx    = 40 + gap + i * (bar_w + gap)
                _draw_animated_bar(draw, q, bx, bar_y, max_h, prog, bar_w)

            # Zero line
            draw.rectangle([40, 1300, W - 40, 1302], fill=(40, 55, 80))

        elif f < P_HEAT:
            lf = f - P_BARS
            ld = P_HEAT - P_BARS

            cx(draw, f"{emoji} {sector.upper()} HEATMAP", 140, font(44, True), mc)

            # Heatmap grid
            n      = min(len(sector_stocks), 6)
            cols   = 3
            rows   = math.ceil(n / cols)
            cell_w = (W - 80) // cols
            cell_h = min(280, (H - 400) // rows)
            start_y= 220

            for i, q in enumerate(sector_stocks[:n]):
                row = i // cols
                col = i % cols
                cx_c = 40 + col * cell_w
                cy_c = start_y + row * (cell_h + 16)
                delay = i * (ld // (n + 2))
                prog  = max(0, (lf - delay) / (ld // 3))
                _draw_heatmap_cell(draw, q, cx_c, cy_c, cell_w - 10, cell_h, prog)

        elif f < P_LEADER:
            lf = f - P_HEAT
            p  = easing_out(min(lf / (FPS * 4), 1.0))

            cx(draw, "SECTOR LEADER", 180, font(44, True), GOLD)

            # Big leader card
            lc = easing_out(min(lf / (FPS * 3), 1.0))
            card_h = int(500 * lc)
            cy_mid = H // 2 + 100
            draw.rounded_rectangle(
                [60, cy_mid - card_h//2, W - 60, cy_mid + card_h//2],
                radius=24,
                fill=(4, 28, 14) if leader.get("change_pct",0)>=0 else (28,4,10)
            )
            draw.rounded_rectangle(
                [60, cy_mid - card_h//2, W - 60, cy_mid + card_h//2],
                radius=24, outline=BULL if leader.get("change_pct",0)>=0 else BEAR, width=3
            )

            if lc > 0.5:
                lmc  = BULL if leader.get("change_pct",0)>=0 else BEAR
                sign = "+" if leader.get("change_pct",0)>=0 else ""
                draw.text((W//2, cy_mid - 80), leader.get("symbol",""),
                          font=font(100, True), fill=TEXT, anchor="mm")
                draw.text((W//2, cy_mid + 20), f"₹{leader.get('ltp',0):,.2f}",
                          font=font(44), fill=MUTED, anchor="mm")
                draw.text((W//2, cy_mid + 86), f"{sign}{leader.get('change_pct',0):.2f}%",
                          font=font(64, True), fill=lmc, anchor="mm")

        else:
            lf = f - P_LEADER
            p  = easing_in_out(lf / (P_OUTRO - P_LEADER))
            cx(draw, f"WATCH {sector.upper()}", H//2 - 60, font(52, True), mc)
            cx(draw, "TOMORROW",                H//2 + 10,  font(52, True), TEXT)
            cx(draw, "@DalalStreetAI",           H//2 + 90,  font(32),       MUTED)

        draw_bottom_bar(draw)
        frames.append(img)

    return encode_frames_to_video(frames, audio, out_path)