"""
src/chart_generator.py  —  Full chart suite
Generates: candlestick, gainers/losers bar, sector heatmap,
           volume bar, RSI indicator, price distribution
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import mplfinance as mpf
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from datetime import datetime

CHART_DIR = "charts"
os.makedirs(CHART_DIR, exist_ok=True)

BULL   = "#00C896"
BEAR   = "#FF4B5C"
BG     = "#0D1117"
TEXT   = "#E6EDF3"
GRID   = "#21262D"
ACCENT = "#58A6FF"
YELLOW = "#FFAA00"

DARK_STYLE = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    marketcolors=mpf.make_marketcolors(
        up=BULL, down=BEAR, edge="inherit",
        wick="inherit", volume={"up": BULL, "down": BEAR},
    ),
    facecolor=BG, edgecolor=BG, figcolor=BG,
    gridcolor=GRID, gridstyle="--", gridaxis="both",
    rc={"font.family": "DejaVu Sans",
        "axes.labelcolor": TEXT, "xtick.color": TEXT,
        "ytick.color": TEXT, "text.color": TEXT},
)

def _save(fig, path):
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    logger.success(f"✅ Chart → {path}")
    return path

def _font(size, bold=False):
    for p in [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(p, size)
        except: pass
    from PIL import ImageFont
    return ImageFont.load_default()


# ── 1. Candlestick + Volume + RSI (3-panel) ──────────────────
def make_candlestick_chart(df: pd.DataFrame, symbol: str) -> str:
    out = os.path.join(CHART_DIR, f"{symbol}_candle.png")
    df  = df.tail(30).copy()

    # Compute RSI
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()

    ap = [
        mpf.make_addplot(df["ma10"], color=ACCENT, width=1.2, label="MA10"),
        mpf.make_addplot(df["ma20"], color=YELLOW, width=1.2, label="MA20"),
        mpf.make_addplot(df["rsi"],  color="#BF5AF2", width=1.2,
                         panel=2, ylabel="RSI", ylim=(0, 100)),
    ]

    fig, axes = mpf.plot(
        df, type="candle", style=DARK_STYLE,
        title=f"\n{symbol}  |  ₹{df['close'].iloc[-1]:,.2f}  |  {datetime.now().strftime('%d %b %Y')}",
        volume=True, addplot=ap,
        figsize=(16, 10), panel_ratios=(4, 1.5, 1.5),
        returnfig=True, tight_layout=True,
    )
    # RSI reference lines
    rsi_ax = axes[4] if len(axes) > 4 else None
    if rsi_ax:
        rsi_ax.axhline(70, color=BEAR,  linestyle="--", alpha=0.6, linewidth=0.8)
        rsi_ax.axhline(30, color=BULL,  linestyle="--", alpha=0.6, linewidth=0.8)
        rsi_ax.axhline(50, color=GRID,  linestyle="--", alpha=0.4, linewidth=0.6)
        rsi_ax.text(0.01, 72, "Overbought", transform=rsi_ax.get_yaxis_transform(),
                    color=BEAR, fontsize=7, alpha=0.8)
        rsi_ax.text(0.01, 24, "Oversold",   transform=rsi_ax.get_yaxis_transform(),
                    color=BULL, fontsize=7, alpha=0.8)

    fig.text(0.98, 0.01, "Not financial advice",
             color=GRID, fontsize=7, ha="right")
    return _save(fig, out)


# ── 2. Gainers / Losers horizontal bar ───────────────────────
def make_gainers_losers_chart(quotes: list) -> str:
    out = os.path.join(CHART_DIR, "gainers_losers.png")
    sq  = sorted(quotes, key=lambda x: x["change_pct"])
    syms    = [q["symbol"].replace("NIFTY 50", "NIFTY") for q in sq]
    changes = [q["change_pct"] for q in sq]
    colors  = [BULL if c >= 0 else BEAR for c in changes]

    fig, ax = plt.subplots(figsize=(14, max(6, len(syms) * 0.75)))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

    bars = ax.barh(syms, changes, color=colors, height=0.55, zorder=3)
    for bar, val in zip(bars, changes):
        xp = bar.get_width()
        ax.text(xp + (0.08 if xp >= 0 else -0.08),
                bar.get_y() + bar.get_height() / 2,
                f"{'+' if val >= 0 else ''}{val:.2f}%",
                va="center", ha="left" if xp >= 0 else "right",
                color=TEXT, fontsize=11, fontweight="bold")

    ax.axvline(0, color=GRID, linewidth=1.5, zorder=4)
    ax.set_xlabel("Change (%)", color=TEXT, fontsize=12)
    ax.set_title(f"Daily Performance  •  {datetime.now().strftime('%d %B %Y')}",
                 color=TEXT, fontsize=15, fontweight="bold", pad=15)
    ax.tick_params(colors=TEXT, labelsize=11)
    ax.spines[:].set_color(GRID)
    ax.grid(axis="x", color=GRID, linestyle="--", alpha=0.4, zorder=0)
    ax.set_xlim(min(changes) - 1.8, max(changes) + 1.8)

    ax.legend(handles=[
        mpatches.Patch(color=BULL, label="Gainers"),
        mpatches.Patch(color=BEAR, label="Losers"),
    ], facecolor=BG, labelcolor=TEXT, fontsize=10)

    fig.tight_layout()
    return _save(fig, out)


# ── 3. Sector Heatmap ────────────────────────────────────────
def make_heatmap(quotes: list) -> str:
    out = os.path.join(CHART_DIR, "heatmap.png")

    # Map symbols to sectors
    SECTOR_MAP = {
        "RELIANCE": "Energy", "ONGC": "Energy", "NTPC": "Energy",
        "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT",
        "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking",
        "AXISBANK": "Banking", "KOTAKBANK": "Banking",
        "MARUTI": "Auto", "TATAMOTORS": "Auto", "BAJAJ-AUTO": "Auto",
        "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
        "NIFTY 50": "Index", "BANKNIFTY": "Index", "SENSEX": "Index",
        "BAJFINANCE": "NBFC", "BAJAJFINSV": "NBFC",
        "LT": "Infra", "ADANIPORTS": "Infra",
    }

    # Group by sector
    sectors = {}
    for q in quotes:
        sec = SECTOR_MAP.get(q["symbol"], "Others")
        sectors.setdefault(sec, []).append(q)

    # Build grid layout
    sector_names = list(sectors.keys())
    n_cols = 3
    n_rows = (len(sector_names) + n_cols - 1) // n_cols

    fig = plt.figure(figsize=(16, max(8, n_rows * 3.5)))
    fig.patch.set_facecolor(BG)
    fig.suptitle(f"Sector Heatmap  •  {datetime.now().strftime('%d %B %Y')}",
                 color=TEXT, fontsize=18, fontweight="bold", y=0.98)

    gs = gridspec.GridSpec(n_rows, n_cols, figure=fig,
                           hspace=0.4, wspace=0.3)

    for i, sec in enumerate(sector_names):
        row, col = divmod(i, n_cols)
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor(BG)
        ax.set_title(sec, color=ACCENT, fontsize=12, fontweight="bold", pad=6)
        ax.tick_params(colors=TEXT, labelsize=8)
        ax.spines[:].set_color(GRID)

        qs  = sectors[sec]
        syms = [q["symbol"][:6] for q in qs]
        vals = [q["change_pct"] for q in qs]

        # Color scale: red→white→green
        norm_vals = [max(-5, min(5, v)) / 5 for v in vals]
        colors = []
        for nv in norm_vals:
            if nv >= 0:
                r = int(13 + (0 - 13) * nv)
                g = int(17 + (200 - 17) * nv)
                b = int(23 + (150 - 23) * nv)
            else:
                r = int(13 + (255 - 13) * (-nv))
                g = int(17 + (75 - 17) * (-nv))
                b = int(23 + (92 - 23) * (-nv))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")

        bars = ax.bar(syms, vals, color=colors, zorder=3, width=0.6)
        ax.axhline(0, color=GRID, linewidth=1, zorder=4)
        ax.set_ylabel("%", color="#8B949E", fontsize=8)

        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.05 if val >= 0 else -0.15),
                    f"{'+' if val >= 0 else ''}{val:.1f}%",
                    ha="center", va="bottom" if val >= 0 else "top",
                    color=TEXT, fontsize=8, fontweight="bold")

        ax.set_ylim(min(vals + [-1]) - 0.8, max(vals + [1]) + 0.8)
        ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.3)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return _save(fig, out)


# ── 4. Volume Analysis chart ──────────────────────────────────
def make_volume_chart(quotes: list) -> str:
    out = os.path.join(CHART_DIR, "volume.png")
    qs  = [q for q in quotes if q.get("volume", 0) > 0]
    if not qs:
        # create placeholder with dummy data
        qs = quotes[:6]
        for q in qs:
            q.setdefault("volume", np.random.randint(1_000_000, 50_000_000))

    qs   = sorted(qs, key=lambda x: x.get("volume", 0), reverse=True)[:10]
    syms = [q["symbol"][:8] for q in qs]
    vols = [q.get("volume", 0) / 1_000_000 for q in qs]  # in millions
    cols = [BULL if q["change_pct"] >= 0 else BEAR for q in qs]

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

    bars = ax.bar(syms, vols, color=cols, zorder=3, width=0.6)
    for bar, vol, q in zip(bars, vols, qs):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{vol:.1f}M\n{'+' if q['change_pct'] >= 0 else ''}{q['change_pct']:.1f}%",
                ha="center", va="bottom", color=TEXT, fontsize=9, fontweight="bold")

    ax.set_ylabel("Volume (Millions)", color=TEXT, fontsize=12)
    ax.set_title(f"Volume Leaders  •  {datetime.now().strftime('%d %B %Y')}",
                 color=TEXT, fontsize=15, fontweight="bold", pad=15)
    ax.tick_params(colors=TEXT, labelsize=11)
    ax.spines[:].set_color(GRID)
    ax.grid(axis="y", color=GRID, linestyle="--", alpha=0.4, zorder=0)

    ax.legend(handles=[
        mpatches.Patch(color=BULL, label="Positive"),
        mpatches.Patch(color=BEAR, label="Negative"),
    ], facecolor=BG, labelcolor=TEXT)

    fig.tight_layout()
    return _save(fig, out)


# ── 5. AI Insight card (Pillow-rendered) ──────────────────────
def make_ai_insight_card(insights: dict) -> str:
    out  = os.path.join(CHART_DIR, "ai_insights.png")
    W, H = 1920, 1080
    img  = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(img)

    # Accent bars
    draw.rectangle([0, 0, W, 10],    fill="#58A6FF")
    draw.rectangle([0, H - 10, W, H], fill="#58A6FF")

    # Header
    draw.text((60, 28), "🤖  AI Market Insights", font=_font(52, True), fill="#E6EDF3")
    draw.text((60, 96), f"Analysis for {insights.get('date', '')}  •  Powered by AI",
              font=_font(28), fill="#8B949E")
    draw.rectangle([60, 138, W - 60, 140], fill="#21262D")

    # Mood banner
    mood    = insights.get("mood", "Neutral")
    mc_map  = {"Bullish": (0,200,150), "Bearish": (255,75,92), "Neutral": (255,170,0)}
    mc      = mc_map.get(mood, (255,170,0))
    draw.rounded_rectangle([60, 154, 380, 216], radius=14, fill=mc)
    draw.text((80, 162), f"Market Mood: {mood}", font=_font(34, True), fill=(13,17,23))

    # Score gauge
    score = insights.get("score", 50)
    gauge_x, gauge_y = 420, 154
    draw.text((gauge_x, gauge_y), "Bullish Score", font=_font(24), fill="#8B949E")
    bar_w = int((score / 100) * 500)
    bar_col = (0,200,150) if score >= 50 else (255,75,92)
    draw.rounded_rectangle([gauge_x, gauge_y+34, gauge_x+500, gauge_y+60],
                            radius=6, fill="#21262D")
    draw.rounded_rectangle([gauge_x, gauge_y+34, gauge_x+bar_w, gauge_y+60],
                            radius=6, fill=bar_col)
    draw.text((gauge_x+510, gauge_y+34), f"{score}/100", font=_font(26, True), fill="#E6EDF3")

    # Three columns: Buy / Sell / Watch
    sections = [
        ("🟢  BUY Candidates",  insights.get("buy",   []), (0,200,150),   80),
        ("🔴  SELL / Avoid",    insights.get("sell",  []), (255,75,92),   700),
        ("🟡  Watch List",      insights.get("watch", []), (255,170,0),  1340),
    ]

    for title, items, col, x in sections:
        draw.text((x, 240), title, font=_font(32, True), fill=col)
        ty = 296
        for item in items[:5]:
            draw.rounded_rectangle([x, ty, x + 520, ty + 86], radius=10,
                                    fill=(20, 28, 40))
            draw.text((x + 16, ty + 8),  item.get("symbol", ""),
                      font=_font(30, True), fill="#E6EDF3")
            draw.text((x + 16, ty + 46), item.get("reason", ""),
                      font=_font(22),     fill="#8B949E")
            price_col = (0,200,150) if item.get("change_pct", 0) >= 0 else (255,75,92)
            sign = "+" if item.get("change_pct", 0) >= 0 else ""
            draw.text((x + 380, ty + 18),
                      f"₹{item.get('ltp', 0):,.0f}\n{sign}{item.get('change_pct',0):.1f}%",
                      font=_font(24, True), fill=price_col)
            ty += 100

    # Key levels section
    draw.rectangle([60, 776, W - 60, 778], fill="#21262D")
    draw.text((60, 790), "📊  Key Levels & Technical Analysis",
              font=_font(34, True), fill="#58A6FF")

    levels = insights.get("levels", [])
    lx = 60
    for lvl in levels[:4]:
        draw.rounded_rectangle([lx, 840, lx + 440, 960], radius=10, fill=(20,28,40))
        draw.text((lx + 16, 850),  lvl.get("label", ""),
                  font=_font(26, True), fill="#8B949E")
        draw.text((lx + 16, 884),  str(lvl.get("value", "")),
                  font=_font(36, True), fill="#E6EDF3")
        draw.text((lx + 16, 928),  lvl.get("note", ""),
                  font=_font(22),     fill="#8B949E")
        lx += 464

    # Summary text
    summary_text = insights.get("summary", "")
    if summary_text:
        draw.text((60, 986), summary_text[:120], font=_font(24), fill="#8B949E")

    draw.text((W - 60, H - 42),
              "Not financial advice  •  AI analysis for educational purposes only",
              font=_font(20), fill=(61,68,77), anchor="rs")

    img.save(out)
    logger.success(f"✅ AI insights card → {out}")
    return out


# ── 6. Summary card (Pillow) ──────────────────────────────────
def make_summary_card(summary: dict) -> str:
    out  = os.path.join(CHART_DIR, "summary_card.png")
    W, H = 1920, 400
    img  = Image.new("RGB", (W, H), (13,17,23))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 8], fill="#58A6FF")
    draw.rectangle([0, H-8, W, H], fill="#58A6FF")

    mood    = summary.get("market_mood", "Sideways")
    mc_map  = {"Bullish": "#00C896", "Bearish": "#FF4B5C", "Sideways": "#FFAA00"}
    mc      = mc_map.get(mood, "#FFAA00")

    draw.text((60, 30), f"Market Summary — {summary['date']}",
              font=_font(52, True), fill="#E6EDF3")
    draw.rounded_rectangle([60,110,280,165], radius=12, fill=mc)
    draw.text((80, 118), mood, font=_font(36, True), fill=(13,17,23))

    if summary.get("nifty"):
        n   = summary["nifty"]
        col = "#00C896" if n["change_pct"] >= 0 else "#FF4B5C"
        draw.text((340, 110), "NIFTY 50",               font=_font(26),      fill="#8B949E")
        draw.text((340, 145), f"₹{n['ltp']:,.2f}",      font=_font(42, True), fill="#E6EDF3")
        sign = "+" if n["change_pct"] >= 0 else ""
        draw.text((560, 158), f"({sign}{n['change_pct']}%)", font=_font(26), fill=col)

    if summary.get("sensex"):
        s   = summary["sensex"]
        col = "#00C896" if s["change_pct"] >= 0 else "#FF4B5C"
        draw.text((780, 110), "SENSEX",                 font=_font(26),       fill="#8B949E")
        draw.text((780, 145), f"₹{s['ltp']:,.2f}",     font=_font(42, True), fill="#E6EDF3")
        sign = "+" if s["change_pct"] >= 0 else ""
        draw.text((1010, 158), f"({sign}{s['change_pct']}%)", font=_font(26), fill=col)

    if summary.get("top_gainer"):
        g = summary["top_gainer"]
        draw.text((1220,100), "🏆 Top Gainer",          font=_font(26),       fill="#8B949E")
        draw.text((1220,135), g["symbol"],               font=_font(42, True), fill="#00C896")
        draw.text((1220,182), f"₹{g['ltp']:,.2f}  (+{g['change_pct']}%)",
                  font=_font(26), fill="#E6EDF3")

    if summary.get("top_loser"):
        lo = summary["top_loser"]
        draw.text((1620,100), "📉 Top Loser",            font=_font(26),       fill="#8B949E")
        draw.text((1620,135), lo["symbol"],               font=_font(42, True), fill="#FF4B5C")
        draw.text((1620,182), f"₹{lo['ltp']:,.2f}  ({lo['change_pct']}%)",
                  font=_font(26), fill="#E6EDF3")

    draw.text((60, H-50), "Not financial advice",
              font=_font(22), fill="#3D444D")
    img.save(out)
    logger.success(f"✅ Summary card → {out}")
    return out


# ── Master function ───────────────────────────────────────────
def generate_all_charts(summary: dict, candle_data: dict, insights: dict = None) -> dict:
    paths = {"candles": {}}
    paths["summary_card"]   = make_summary_card(summary)
    paths["gainers_losers"] = make_gainers_losers_chart(summary["quotes"])
    paths["heatmap"]        = make_heatmap(summary["quotes"])
    paths["volume"]         = make_volume_chart(summary["quotes"])

    if insights:
        paths["ai_insights"] = make_ai_insight_card(insights)

    for sym, df in candle_data.items():
        try:
            paths["candles"][sym] = make_candlestick_chart(df, sym)
        except Exception as e:
            logger.warning(f"⚠️  Candle chart failed for {sym}: {e}")

    return paths
