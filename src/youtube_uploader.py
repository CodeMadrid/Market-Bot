"""
src/youtube_uploader.py
─────────────────────────────────────────────────────────────────
Auto-uploads video + custom thumbnail to YouTube.
"""

import os
import pickle
from datetime import datetime
from loguru import logger

SCOPES        = ["https://www.googleapis.com/auth/youtube.upload",
                 "https://www.googleapis.com/auth/youtube"]
TOKEN_FILE    = "youtube_token.pickle"
CLIENT_SECRET = "client_secret.json"


def _get_credentials():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        raise ImportError("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        logger.info("🔄 YouTube token refreshed")
        return creds

    if not creds or not creds.valid:
        if not os.path.exists(CLIENT_SECRET):
            raise FileNotFoundError("client_secret.json not found in project root!")
        flow  = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        logger.success("✅ YouTube authenticated — token saved")

    return creds


def upload_to_youtube(
    video_path: str,
    summary: dict,
    insights: dict,
    thumbnail_path: str = None,
) -> str:
    try:
        import googleapiclient.discovery
        import googleapiclient.http
    except ImportError:
        raise ImportError("pip install google-api-python-client")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    creds   = _get_credentials()
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    date  = summary.get("date", datetime.now().strftime("%d %B %Y"))
    mood  = summary.get("market_mood", "Mixed")
    nifty = summary.get("nifty") or {}

    # ── Auto title ────────────────────────────────────────────
    mood_emoji = {"Bullish": "🟢", "Bearish": "🔴", "Sideways": "🟡"}.get(mood, "📊")
    nifty_str  = f"Nifty {nifty.get('ltp', ''):,.0f}" if nifty.get("ltp") else ""
    title      = f"{mood_emoji} Stock Market Today {date} | {nifty_str} | Hindi & English Analysis"

    # ── Auto description ──────────────────────────────────────
    gainer     = summary.get("top_gainer") or {}
    loser      = summary.get("top_loser")  or {}
    ai_summary = insights.get("summary", "")
    outlook    = insights.get("tomorrow_outlook", "")
    buy_list   = ", ".join(i["symbol"] for i in insights.get("buy",  [])[:3])
    sell_list  = ", ".join(i["symbol"] for i in insights.get("sell", [])[:3])

    description = f"""📊 Daily Indian Stock Market Analysis — {date}

{ai_summary}

🟢 Market Mood: {mood}
📈 Nifty 50: ₹{nifty.get('ltp', 0):,.2f} ({'+' if nifty.get('change_pct',0)>=0 else ''}{nifty.get('change_pct', 0):.2f}%)
🏆 Top Gainer: {gainer.get('symbol', 'N/A')} (+{gainer.get('change_pct', 0):.2f}%)
📉 Top Loser:  {loser.get('symbol', 'N/A')} ({loser.get('change_pct', 0):.2f}%)

🤖 AI Insights:
• Buy candidates: {buy_list or 'None today'}
• Avoid: {sell_list or 'None today'}

📅 Tomorrow's Outlook:
{outlook}

⏱️ Timestamps:
00:00 — Intro & Market Mood
00:30 — Nifty & Sensex Analysis
02:00 — Gainers & Losers
03:30 — Sector Heatmap
05:00 — Volume Analysis
06:30 — Candlestick Charts
09:00 — AI Insights & Recommendations
11:00 — Tomorrow's Outlook

⚠️ DISCLAIMER: For educational purposes only. Not financial advice. Always do your own research before investing.

#StockMarket #Nifty #NSE #BSE #IndianStockMarket #MarketAnalysis #NiftyAnalysis #SensexToday #TradingIndia #InvestmentIndia #StockMarketHindi #sharemarket
"""

    tags = [
        "stock market", "nifty", "sensex", "NSE", "BSE",
        "Indian stock market", "share market", "market analysis today",
        "nifty analysis", "stock market today", "trading india",
        "investment", "share market hindi", mood.lower(), date,
    ]
    if gainer.get("symbol"): tags.append(gainer["symbol"].lower())
    if loser.get("symbol"):  tags.append(loser["symbol"].lower())

    body = {
        "snippet": {
            "title":       title[:100],
            "description": description,
            "tags":        tags,
            "categoryId":  "25",
        },
        "status": {
            "privacyStatus":           os.getenv("YT_PRIVACY", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }

    # ── Upload video ──────────────────────────────────────────
    logger.info(f"📤 Uploading video: {title}")
    media    = googleapiclient.http.MediaFileUpload(
        video_path, mimetype="video/mp4",
        resumable=True, chunksize=1024 * 1024,
    )
    request  = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"  Uploading... {int(status.progress()*100)}%")

    video_id  = response["id"]
    video_url = f"https://youtu.be/{video_id}"
    logger.success(f"✅ Video uploaded → {video_url}")

    # ── Upload thumbnail ──────────────────────────────────────
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            logger.info("🖼️  Uploading thumbnail...")
            youtube.thumbnails().set(
                videoId   = video_id,
                media_body= googleapiclient.http.MediaFileUpload(
                    thumbnail_path,
                    mimetype="image/png",
                )
            ).execute()
            logger.success("✅ Thumbnail uploaded")
        except Exception as e:
            logger.warning(f"⚠️  Thumbnail upload failed: {e}")
            logger.info("   Note: You need YouTube channel verification to upload custom thumbnails.")
            logger.info("   Go to youtube.com/verify to verify your channel (takes ~1 min).")
    else:
        logger.warning("⚠️  No thumbnail path provided — skipping")

    return video_url