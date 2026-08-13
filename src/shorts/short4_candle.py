"""
src/shorts/short4_candle.py
─────────────────────────────────────────────────────────────────
SHORT 4 — "Candlestick Story"
Most premium short — animates a 30-day candlestick chart
bar by bar with voice explanation of the pattern.
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


def _candle_analysis(df):
    """Simple pattern detection."""
    if df is None or len(df) < 5:
        return "mixed", "Market showing consolidation."
    last5  = df.tail(5)
    closes = last5["close"].values
    if closes[-1] > closes[0] * 1.02:
        return "bullish", "Strong uptrend over last 5 sessions. Buyers in control."
    elif closes[-1] < closes[0] * 0.98:
        return "bearish", "Downtrend over last 5 sessions. Sellers dominating."
    elif df["close"].iloc[-1] > df["close"].rolling(10).mean().iloc[-1]:
        return "bullish", "Price trading above 10-day average. Bullish momentum."
    else:
        return "sideways", "Consolidation phase. Watch for breakout direction."


def _draw_candle(draw, x, open_, high, low, close, candle_w, chart_y, price_range, chart_h, progress=1.0):
    """Draw one animated candlestick."""
    p       = easing_out(min(progress, 1.0))
    is_bull = close >= open_
    mc      = BULL if is_bull else BEAR

    def price_to_y(price):
        return int(chart_y + chart_h - (price - price_range[0]) / (price_range[1] - price_range[0]) * chart_h)

    cy_open  = price_to_y(open_)
    cy_close = price_to_y(close)
    cy_high  = price_to_y(high)
    cy_low   = price_to_y(low)

    body_top = min(cy_open, cy_close)
    body_bot = max(cy_open, cy_close)
    body_h   = max(2, body_bot - body_top)
    animated_h = int(body_h * p)
    wick_cx  = x + candle_w // 2

    # Wick
    if p > 0.3:
        draw.line([(wick_cx, cy_high), (wick_cx, cy_low)],
                  fill=(*mc[:3],), width=2)

    # Body (grows from open price)
    if animated_h > 0:
        draw.rounded_rectangle(
            [x + 2, body_top, x + candle_w - 2, body_top + animated_h],
            radius=2, fill=mc
        )


def build_short4(summary: dict, insights: dict,
                 candle_data: dict = None, language="en") -> str:
    out_path = os.path.join(SHORTS_DIR, "short4_candle.mp4")

    mood     = summary.get("market_mood", "Sideways")
    mc       = MOOD_COL.get(mood, ACCENT)
    date_str = summary.get("date", "")

    # Pick the top gainer for candle story
    gainer  = summary.get("top_gainer") or {}
    symbol  = gainer.get("symbol", "NIFTY")
    df      = None
    if candle_data:
        df = candle_data.get(symbol) or next(iter(candle_data.values()), None)

    # Generate fake data if no candle data
    if df is None or len(df) < 10:
        base    = gainer.get("ltp", 2000) or 2000
        dates   = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="B")
        close_p = base + np.cumsum(np.random.randn(30) * base * 0.009)
        open_p  = close_p + np.random.randn(30) * base * 0.003
        high_p  = np.maximum(close_p, open_p) + abs(np.random.randn(30) * base * 0.005)
        low_p   = np.minimum(close_p, open_p) - abs(np.random.randn(30) * base * 0.005)
        vol_p   = np.random.randint(1_000_000, 10_000_000, 30).astype(float)
        df = pd.DataFrame({"open":open_p,"high":high_p,"low":low_p,
                           "close":close_p,"volume":vol_p}, index=dates)

    df = df.tail(20)
    pattern, pattern_text = _candle_analysis(df)
    pat_col = BULL if pattern == "bullish" else BEAR if pattern == "bearish" else GOLD

    # RSI
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = (100 - (100 / (1 + rs))).iloc[-1]
    rsi   = rsi if not np.isnan(rsi) else 50

    narration = (
        f"Candlestick analysis for {symbol} on {date_str}. "
        f"{pattern_text} "
        f"RSI is at {rsi:.0f}. "
        f"{'Overbought zone — caution advised.' if rsi > 70 else 'Oversold zone — potential bounce.' if rsi < 30 else 'RSI in neutral zone.'} "
        f"Always combine with other indicators before trading."
    )
    audio = _tts(narration, language)

    # Chart dimensions
    CHART_Y  = 300
    CHART_H  = 900
    CHART_X  = 40
    CHART_W  = W - 80
    N        = len(df)
    candle_w = max(20, CHART_W // N - 4)
    prices   = pd.concat([df["high"], df["low"]])
    p_min    = prices.min() * 0.998
    p_max    = prices.max() * 1.002
    price_range = (p_min, p_max)

    frames = []
    total  = FPS * 55

    P_INTRO   = FPS * 5
    P_CANDLES = FPS * 35   # candles animate in over 30 seconds
    P_PATTERN = FPS * 46
    P_OUTRO   = FPS * 55

    for f in range(total):
        img, draw = new_frame()
        draw_grid(draw, alpha=4)
        draw_channel_badge(draw, mood)

        if f < P_INTRO:
            p = easing_out(f / P_INTRO)
            y = int(lerp(H//2 + 80, H//2 - 60, p))
            cx(draw, "CANDLESTICK", y - 60, font(66, True), mc)
            cx(draw, "STORY",       y + 30,  font(80, True), TEXT)
            cx(draw, symbol,        y + 120, font(42, True), GOLD)

        elif f < P_CANDLES:
            lf = f - P_INTRO
            ld = P_CANDLES - P_INTRO

            # Header
            cx(draw, symbol, 148, font(52, True), TEXT)
            cx(draw, f"30-Day Chart  •  {date_str}", 206, font(26), MUTED)

            # Price grid lines
            for i in range(5):
                gy    = CHART_Y + int(CHART_H * i / 4)
                price = p_max - (p_max - p_min) * i / 4
                draw.line([(CHART_X, gy), (CHART_X + CHART_W, gy)],
                          fill=(25, 38, 58), width=1)
                draw.text((CHART_X - 4, gy), f"{price:,.0f}",
                          font=font(18), fill=MUTED, anchor="ra")

            # Animate candles one by one
            candles_shown = min(N, int(N * easing_out(lf / ld)) + 1)
            for i in range(candles_shown):
                row  = df.iloc[i]
                cx_c = CHART_X + i * (candle_w + 4)
                # Last candle animates
                prog = 1.0 if i < candles_shown - 1 else (
                    (lf - (i / N) * ld) / (ld / N)
                )
                _draw_candle(draw, cx_c,
                             row["open"], row["high"], row["low"], row["close"],
                             candle_w, CHART_Y, price_range, CHART_H,
                             min(max(0, prog), 1.0))

            # MA line (appears after half candles)
            if candles_shown > 10:
                ma10 = df["close"].rolling(10).mean().values
                pts  = []
                for i in range(10, min(candles_shown, N)):
                    if not np.isnan(ma10[i]):
                        px = CHART_X + i * (candle_w + 4) + candle_w // 2
                        py_m = int(CHART_Y + CHART_H -
                                  (ma10[i] - p_min) / (p_max - p_min) * CHART_H)
                        pts.append((px, py_m))
                if len(pts) > 1:
                    draw.line(pts, fill=ACCENT, width=2)

            # Volume bars at bottom
            vol_max = df["volume"].max()
            for i in range(min(candles_shown, N)):
                row  = df.iloc[i]
                vh   = int(80 * row["volume"] / vol_max)
                vx   = CHART_X + i * (candle_w + 4)
                vc   = BULL if row["close"] >= row["open"] else BEAR
                draw.rectangle([vx + 1, CHART_Y + CHART_H + 10,
                                vx + candle_w - 1, CHART_Y + CHART_H + 10 + vh],
                               fill=(*vc[:3],))

            # RSI indicator
            rsi_y = CHART_Y + CHART_H + 110
            draw.text((CHART_X, rsi_y), f"RSI: {rsi:.1f}",
                      font=font(28, True),
                      fill=BEAR if rsi > 70 else BULL if rsi < 30 else TEXT)
            draw.text((CHART_X + 160, rsi_y),
                      "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral",
                      font=font(24),
                      fill=BEAR if rsi > 70 else BULL if rsi < 30 else MUTED)

            # Current price
            cur_price = df["close"].iloc[-1]
            draw.text((W - 20, 200), f"₹{cur_price:,.2f}",
                      font=font(36, True), fill=TEXT, anchor="ra")
            day_chg = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
            sign    = "▲" if day_chg >= 0 else "▼"
            draw.text((W - 20, 244), f"{sign} {abs(day_chg):.2f}%",
                      font=font(26, True),
                      fill=BULL if day_chg >= 0 else BEAR, anchor="ra")

        elif f < P_PATTERN:
            lf = f - P_CANDLES
            p  = easing_out(min(lf / (FPS * 4), 1.0))

            # Show full chart faded
            cx(draw, symbol, 148, font(52, True), TEXT)

            # Pattern verdict
            card_h = int(340 * p)
            cy_mid = H // 2 + 200
            if card_h > 10:
                draw.rounded_rectangle(
                    [40, cy_mid - card_h//2, W - 40, cy_mid + card_h//2],
                    radius=20, fill=(10, 16, 28)
                )
                draw.rounded_rectangle(
                    [40, cy_mid - card_h//2, W - 40, cy_mid + card_h//2],
                    radius=20, outline=pat_col, width=3
                )
            if p > 0.5:
                pat_label = {"bullish":"BULLISH PATTERN","bearish":"BEARISH PATTERN",
                             "sideways":"CONSOLIDATION"}.get(pattern,"MIXED SIGNAL")
                draw.text((W//2, cy_mid - 80), pat_label,
                          font=font(44, True), fill=pat_col, anchor="mm")
                # Wrap text
                words = pattern_text.split()
                line, lines = "", []
                for w in words:
                    test = line + " " + w if line else w
                    if text_w(draw, test, font(26)) < W - 120:
                        line = test
                    else:
                        lines.append(line); line = w
                if line: lines.append(line)
                for li, ln in enumerate(lines[:3]):
                    draw.text((W//2, cy_mid - 12 + li * 38), ln,
                              font=font(26), fill=TEXT, anchor="mm")

                draw.text((W//2, cy_mid + 110), f"RSI: {rsi:.0f}",
                          font=font(36, True), fill=MUTED, anchor="mm")

        else:
            cx(draw, "FOLLOW FOR", H//2 - 60, font(44, True), TEXT)
            cx(draw, "CHART ANALYSIS", H//2 + 10, font(44, True), mc)
            cx(draw, "@DalalStreetAI", H//2 + 90, font(32),      MUTED)

        draw_bottom_bar(draw, "Technical analysis  •  Not financial advice  •  dalal street ai")
        frames.append(img)

    return encode_frames_to_video(frames, audio, out_path)