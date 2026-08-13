"""
main_shorts.py  —  Generate & upload all 5 YouTube Shorts
Run: python main_shorts.py
     python main_shorts.py --demo
     python main_shorts.py --short 1      (only short 1)
     python main_shorts.py --schedule     (daily at 4:15 PM IST)
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
os.makedirs("output/shorts", exist_ok=True)
logger.add(f"logs/shorts_{datetime.now().strftime('%Y%m%d')}.log",
           rotation="1 day", retention="7 days", level="DEBUG")

console = Console()


# ── Reuse mock data from main.py ──────────────────────────────
def _get_mock():
    from main import _mock_summary, _mock_candles
    return _mock_summary(), _mock_candles()


def _get_real():
    from src.stock_selector import select_stocks_for_today
    from src.data_fetcher import fetch_candles
    import time as t
    summary = select_stocks_for_today()
    candle_data = {}
    for sym in summary.get("candle_symbols", []):
        try:
            t.sleep(1.5)
            candle_data[sym] = fetch_candles(sym, interval="ONE_DAY", days_back=30)
        except Exception as e:
            logger.warning(f"Candles failed {sym}: {e}")
    return summary, candle_data


def _get_insights(summary):
    from src.ai_analyst import generate_insights
    return generate_insights(summary)


def _upload_short(video_path, summary, insights, title_suffix=""):
    """Upload a short to YouTube."""
    try:
        from src.youtube_uploader import upload_to_youtube
        from src.thumbnail_generator import generate_thumbnail

        # Each short gets its own thumbnail
        thumb = generate_thumbnail(summary, insights)

        # Customize title per short
        date  = summary.get("date", "")
        mood  = summary.get("market_mood", "")
        nifty = (summary.get("nifty") or {}).get("ltp", 0)
        emoji = {"Bullish":"🟢","Bearish":"🔴","Sideways":"🟡"}.get(mood,"📊")

        # Override title for shorts
        import googleapiclient.discovery, googleapiclient.http, pickle
        creds = None
        if os.path.exists("youtube_token.pickle"):
            with open("youtube_token.pickle","rb") as f:
                creds = pickle.load(f)

        url = upload_to_youtube(video_path, summary, insights,
                                thumbnail_path=thumb)
        return url
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return ""


def run_shorts(demo=False, only_short=None):
    console.rule("[bold magenta]📱 Dalal Street AI — Shorts Generator[/bold magenta]")
    console.print(f"[dim]{datetime.now().strftime('%d %b %Y  %H:%M:%S IST')}[/dim]\n")

    yt_upload = os.getenv("YOUTUBE_UPLOAD", "false").lower() == "true"

    # ── Get data ──────────────────────────────────────────────
    console.print("[bold cyan]Fetching market data...[/bold cyan]")
    if demo:
        summary, candle_data = _get_mock()
        logger.info("🧪 DEMO mode")
    else:
        summary, candle_data = _get_real()

    console.print("[bold cyan]Generating AI insights...[/bold cyan]")
    insights = _get_insights(summary)

    language = os.getenv("VIDEO_LANGUAGE", "both")
    lang     = "hi" if language == "hindi" else "en"

    # ── Build shorts ──────────────────────────────────────────
    shorts_config = {
        1: ("Market in 60 Seconds",    "short1_market60"),
        2: ("Sector Spotlight",        "short2_sector"),
        3: ("Tomorrow's Prediction",   "short3_tomorrow"),
        4: ("Candlestick Story",       "short4_candle"),
        5: ("Top Gainer Deep Dive",    "short5_topgainer"),
    }

    results = {}

    for num, (title, fname) in shorts_config.items():
        if only_short and num != only_short:
            continue

        console.print(f"\n[bold cyan]Building Short {num}: {title}...[/bold cyan]")
        try:
            if num == 1:
                from src.shorts.short1_market60 import build_short1
                path = build_short1(summary, insights, lang)
            elif num == 2:
                from src.shorts.short2_sector import build_short2
                path = build_short2(summary, insights, lang)
            elif num == 3:
                from src.shorts.short3_tomorrow import build_short3
                path = build_short3(summary, insights, lang)
            elif num == 4:
                from src.shorts.short4_candle import build_short4
                path = build_short4(summary, insights, candle_data, lang)
            elif num == 5:
                from src.shorts.short5_topgainer import build_short5
                path = build_short5(summary, insights, candle_data, lang)

            results[num] = {"title": title, "path": path, "url": ""}
            console.print(f"  [green]✅ {title} → {path}[/green]")

            # Upload
            if yt_upload:
                console.print(f"  [cyan]📤 Uploading Short {num}...[/cyan]")
                url = _upload_short(path, summary, insights, title)
                results[num]["url"] = url
                if url:
                    console.print(f"  [green]✅ {url}[/green]")

        except Exception as e:
            logger.error(f"Short {num} failed: {e}")
            console.print(f"  [red]❌ Short {num} failed: {e}[/red]")

    # ── Summary ───────────────────────────────────────────────
    t = Table(title="Shorts Generated", style="bold")
    t.add_column("#",     style="cyan", width=4)
    t.add_column("Title", style="white")
    t.add_column("File",  style="dim")
    t.add_column("YouTube", style="green")

    for num, r in results.items():
        t.add_row(
            str(num), r["title"],
            os.path.basename(r.get("path","")),
            r.get("url","") or "—"
        )
    console.print(t)

    msg = f"[green bold]✅ {len(results)} shorts ready![/green bold]\n"
    msg += f"[white]Folder: [cyan]output/shorts/[/cyan][/white]"
    console.print(Panel(msg, title="Done", border_style="magenta"))
    return results


def run_scheduled(demo=False):
    run_time = os.getenv("SHORTS_TIME", "16:15")
    console.print(f"[bold yellow]⏰ Shorts scheduler — daily at {run_time} IST[/bold yellow]")
    schedule.every().day.at(run_time).do(run_shorts, demo=demo)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Dalal Street AI — Shorts Generator")
    p.add_argument("--demo",     action="store_true", help="Use mock data")
    p.add_argument("--schedule", action="store_true", help="Run daily at SHORTS_TIME")
    p.add_argument("--short",    type=int, choices=[1,2,3,4,5],
                   help="Build only one specific short (1-5)")
    args = p.parse_args()

    if args.schedule:
        run_scheduled(demo=args.demo)
    else:
        run_shorts(demo=args.demo, only_short=args.short)