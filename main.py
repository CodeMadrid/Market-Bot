"""
main.py  —  Market Video Bot — Full Pipeline
"""

import os, argparse, schedule, time
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
os.makedirs("logs", exist_ok=True)
logger.add(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log",
           rotation="1 day", retention="7 days", level="DEBUG")

console = Console()


# ── Mock data ─────────────────────────────────────────────────
def _mock_summary():
    quotes = [
        {"symbol":"RELIANCE", "ltp":2945.0, "change_pct":2.34,  "change":67.0,  "open":2878.0,"high":2960.0,"low":2870.0,"close":2878.0,"volume":12000000},
        {"symbol":"TCS",      "ltp":3812.0, "change_pct":0.87,  "change":32.9,  "open":3779.0,"high":3830.0,"low":3770.0,"close":3779.0,"volume":4500000},
        {"symbol":"INFY",     "ltp":1476.0, "change_pct":1.15,  "change":16.8,  "open":1459.0,"high":1485.0,"low":1455.0,"close":1459.0,"volume":7800000},
        {"symbol":"HDFCBANK", "ltp":1623.5, "change_pct":0.42,  "change":6.75,  "open":1616.0,"high":1630.0,"low":1610.0,"close":1616.0,"volume":9200000},
        {"symbol":"SBIN",     "ltp":812.0,  "change_pct":-0.63, "change":-5.15, "open":817.0, "high":820.0, "low":808.0, "close":817.0, "volume":15000000},
        {"symbol":"WIPRO",    "ltp":462.5,  "change_pct":-1.82, "change":-8.6,  "open":471.1, "high":473.0, "low":460.0, "close":471.1, "volume":8000000},
        {"symbol":"MARUTI",   "ltp":12450.0,"change_pct":1.65,  "change":202.0, "open":12248.0,"high":12500.0,"low":12200.0,"close":12248.0,"volume":320000},
        {"symbol":"SUNPHARMA","ltp":1680.0, "change_pct":-0.95, "change":-16.1, "open":1696.0,"high":1700.0,"low":1672.0,"close":1696.0,"volume":2100000},
        {"symbol":"NIFTY 50", "ltp":24350.5,"change_pct":1.04,  "change":250.5, "open":24100.0,"high":24400.0,"low":24050.0,"close":24100.0,"volume":0},
        {"symbol":"BANKNIFTY","ltp":52340.0,"change_pct":0.78,  "change":404.5, "open":51935.0,"high":52450.0,"low":51900.0,"close":51935.0,"volume":0},
    ]
    gainers = sorted([q for q in quotes if q["change_pct"] > 0], key=lambda x: x["change_pct"], reverse=True)
    losers  = sorted([q for q in quotes if q["change_pct"] < 0], key=lambda x: x["change_pct"])
    return {
        "date":        datetime.now().strftime("%d %B %Y"),
        "market_mood": "Bullish",
        "quotes":      quotes,
        "top_gainer":  gainers[0] if gainers else None,
        "top_loser":   losers[0]  if losers  else None,
        "top_gainers": gainers[:3],
        "top_losers":  losers[:3],
        "nifty":       next(q for q in quotes if q["symbol"] == "NIFTY 50"),
        "banknifty":   next(q for q in quotes if q["symbol"] == "BANKNIFTY"),
        "sensex":      None,
        "sectors": {
            "Banking": [quotes[3], quotes[4]],
            "IT":      [quotes[1], quotes[2]],
            "Auto":    [quotes[6]],
            "Pharma":  [quotes[7]],
            "Energy":  [quotes[0]],
        },
        "candle_symbols": ["RELIANCE","TCS","INFY","HDFCBANK","MARUTI","SUNPHARMA"],
    }


def _mock_candles():
    import numpy as np, pandas as pd
    def _df(base, n=30):
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        close = base + np.cumsum(np.random.randn(n) * base * 0.008)
        open_ = close + np.random.randn(n) * base * 0.003
        high  = np.maximum(close, open_) + abs(np.random.randn(n) * base * 0.004)
        low   = np.minimum(close, open_) - abs(np.random.randn(n) * base * 0.004)
        vol   = np.random.randint(1_000_000, 15_000_000, n).astype(float)
        return pd.DataFrame({"open":open_,"high":high,"low":low,"close":close,"volume":vol}, index=dates)
    return {sym: _df(price) for sym, price in [
        ("RELIANCE",2878),("TCS",3779),("INFY",1459),
        ("HDFCBANK",1616),("MARUTI",12248),("SUNPHARMA",1696)
    ]}


# ── Core pipeline ─────────────────────────────────────────────
def run_pipeline(demo=False):
    console.rule("[bold blue]📊 Market Video Bot[/bold blue]")
    console.print(f"[dim]{datetime.now().strftime('%d %b %Y  %H:%M:%S IST')}[/dim]\n")

    exchange  = os.getenv("EXCHANGE", "NSE")
    language  = os.getenv("VIDEO_LANGUAGE", "both")
    yt_upload = os.getenv("YOUTUBE_UPLOAD", "false").lower() == "true"

    # ── Step 1: Dynamic stock selection ──────────────────────
    console.print("[bold cyan]Step 1/6 — Selecting stocks dynamically...[/bold cyan]")
    if demo:
        logger.info("🧪 DEMO mode — using mock data")
        summary     = _mock_summary()
        candle_data = _mock_candles()
    else:
        from src.stock_selector import select_stocks_for_today
        from src.data_fetcher import fetch_candles
        summary = select_stocks_for_today(exchange)
        console.print(f"  Selected [bold]{len(summary['quotes'])}[/bold] stocks | "
                      f"Mood: [bold]{summary['market_mood']}[/bold]")
        candle_data = {}
        for sym in summary.get("candle_symbols", []):
            try:
                time.sleep(1.5)
                candle_data[sym] = fetch_candles(sym, interval="ONE_DAY",
                                                  days_back=30, exchange=exchange)
            except Exception as e:
                logger.warning(f"Candles failed for {sym}: {e}")

    _print_table(summary)

    # ── Step 2: AI insights ───────────────────────────────────
    console.print("\n[bold cyan]Step 2/6 — Generating AI insights...[/bold cyan]")
    from src.ai_analyst import generate_insights
    insights = generate_insights(summary)
    console.print(f"  Mood: [bold]{insights.get('mood')}[/bold]  "
                  f"Score: [bold]{insights.get('score')}/100[/bold]")

    # ── Step 3: Thumbnail ─────────────────────────────────────
    console.print("\n[bold cyan]Step 3/6 — Generating thumbnail...[/bold cyan]")
    from src.thumbnail_generator import generate_thumbnail
    thumbnail_path = generate_thumbnail(summary, insights)

    # ── Step 4: Charts ────────────────────────────────────────
    console.print("\n[bold cyan]Step 4/6 — Generating charts...[/bold cyan]")
    from src.chart_generator import generate_all_charts
    chart_paths = generate_all_charts(summary, candle_data, insights)

    # ── Step 5: TTS ───────────────────────────────────────────
    console.print("\n[bold cyan]Step 5/6 — Generating TTS narration...[/bold cyan]")
    from src.tts_narrator import generate_narration
    audio_paths = generate_narration(summary, insights, language=language)

    # ── Step 6: Video ─────────────────────────────────────────
    console.print("\n[bold cyan]Step 6/6 — Composing final video...[/bold cyan]")
    from src.video_composer import compose_video
    video_path = compose_video(chart_paths, audio_paths, summary, language=language)

    # ── Step 7: YouTube upload ────────────────────────────────
    yt_url = ""
    if yt_upload:
        console.print("\n[bold cyan]Step 7/6 — Uploading to YouTube...[/bold cyan]")
        try:
            from src.youtube_uploader import upload_to_youtube
            yt_url = upload_to_youtube(video_path, summary, insights,
                                       thumbnail_path=thumbnail_path)
            console.print(f"  [green]✅ YouTube: {yt_url}[/green]")
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            console.print(f"  [red]YouTube upload failed: {e}[/red]")

    # ── Done ──────────────────────────────────────────────────
    msg = (f"[green bold]✅ Video ready![/green bold]\n"
           f"[white]Path: [cyan]{os.path.abspath(video_path)}[/cyan][/white]\n"
           f"[white]Thumbnail: [cyan]{os.path.abspath(thumbnail_path)}[/cyan][/white]")
    if yt_url:
        msg += f"\n[white]YouTube: [cyan]{yt_url}[/cyan][/white]"
    console.print(Panel(msg, title="Done", border_style="green"))
    return video_path


def _print_table(summary):
    t = Table(title=f"Market Summary — {summary.get('date','')}", style="bold")
    t.add_column("Symbol",   style="cyan",  no_wrap=True)
    t.add_column("LTP (₹)",  justify="right")
    t.add_column("Change %", justify="right")
    for q in summary.get("quotes", [])[:12]:
        p   = q["change_pct"]
        col = "green" if p >= 0 else "red"
        t.add_row(q["symbol"], f"{q['ltp']:,.2f}",
                  f"[{col}]{'+' if p>=0 else ''}{p:.2f}%[/{col}]")
    console.print(t)


def run_scheduled(demo=False):
    run_time = os.getenv("RUN_TIME", "16:05")
    console.print(f"[bold yellow]⏰ Scheduler — daily at {run_time} IST[/bold yellow]")
    schedule.every().day.at(run_time).do(run_pipeline, demo=demo)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--demo",     action="store_true")
    args = p.parse_args()
    if args.schedule:
        run_scheduled(demo=args.demo)
    else:
        run_pipeline(demo=args.demo)