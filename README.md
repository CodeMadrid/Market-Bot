# 📊 Market Video Bot
### Automated Daily Indian Stock Market Videos — NSE/BSE/MCX
**Angel One SmartAPI (FREE) • Hindi + English TTS • Candlestick Charts • Auto Video**

---

## 🗂️ Project Structure

```
market_video_bot/
│
├── main.py                  ← Entry point / orchestrator
├── requirements.txt         ← All dependencies
├── .env.example             ← Credentials template
│
├── src/
│   ├── data_fetcher.py      ← Angel One SmartAPI (NSE/BSE data)
│   ├── chart_generator.py   ← Candlestick + bar charts
│   ├── tts_narrator.py      ← Hindi + English TTS (gTTS)
│   └── video_composer.py    ← MoviePy video assembly
│
├── charts/                  ← Generated chart PNGs (auto-created)
├── audio/                   ← Generated MP3 files (auto-created)
├── output/                  ← Final MP4 videos (auto-created)
└── logs/                    ← Daily log files (auto-created)
```

---

## 🛠️ Step-by-Step Setup

### Step 1 — Prerequisites

Make sure you have:
- **Python 3.10+** installed  
- **FFmpeg** installed (required by MoviePy)

**Install FFmpeg:**

```bash
# Ubuntu / Debian / WSL
sudo apt update && sudo apt install ffmpeg -y

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Add to PATH
```

Verify: `ffmpeg -version`

---

### Step 2 — Clone / Download the project

```bash
# If using git
git clone <your-repo>
cd market_video_bot

# OR just place the folder anywhere and cd into it
cd market_video_bot
```

---

### Step 3 — Create Python virtual environment

```bash
python -m venv venv

# Activate:
# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

---

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ `smartapi-python` installs the Angel One SDK.  
> `gtts` uses Google Translate TTS — **free**, works for Hindi & English.  
> `moviepy` handles video — it auto-downloads `ffmpeg-python` bindings.

---

### Step 5 — Register on Angel One SmartAPI (FREE)

1. Go to → **https://smartapi.angelbroking.com/**
2. Sign up with your Angel One trading account
3. Click **"Create App"**
4. Fill in:
   - App Name: `MarketVideoBot` (anything)
   - Redirect URL: `http://localhost` (doesn't matter)
5. You'll get:
   - **API Key** ← copy this
   - Your Client ID = your Angel One login ID

---

### Step 6 — Enable TOTP on Angel One

Angel One requires TOTP (Time-based One-Time Password) for API login.

1. Open **Angel One mobile app**
2. Go to → Profile → Settings → Enable TOTP
3. You'll get a **TOTP Secret Key** (32-character code)
4. Copy it — you'll paste it in `.env`

> ℹ️ You can also use any authenticator app (Google Authenticator etc.)
> and the `pyotp` library generates the 6-digit code automatically at login time.

---

### Step 7 — Create your `.env` file

```bash
cp .env.example .env
```

Now edit `.env`:

```env
ANGEL_API_KEY=abc123xyz          # From SmartAPI dashboard
ANGEL_CLIENT_ID=A123456          # Your Angel One login ID
ANGEL_PASSWORD=yourpassword      # Your Angel One password
ANGEL_TOTP_SECRET=BASE32SECRETXX # From Angel One app (TOTP setup)

VIDEO_LANGUAGE=both              # english | hindi | both
OUTPUT_FOLDER=output
VIDEO_FPS=24
VIDEO_RESOLUTION=1920x1080

WATCHLIST=RELIANCE,TCS,INFY,HDFCBANK,SBIN,NIFTY 50
EXCHANGE=NSE
CANDLE_INTERVAL=ONE_DAY

RUN_TIME=16:05                   # 4:05 PM IST (after market close)
```

---

### Step 8 — Test with Demo Mode (no login needed)

Before connecting to Angel One, test the full pipeline with mock data:

```bash
python main.py --demo
```

This will:
- Use fake OHLCV data
- Generate real charts
- Generate real Hindi + English TTS audio
- Compose a real MP4 video
- Save to `output/market_video_YYYYMMDD.mp4`

**Check the output folder for your video!** ✅

---

### Step 9 — Run with real Angel One data

```bash
python main.py
```

This runs the full pipeline once:
1. Logs into Angel One SmartAPI
2. Fetches live/EOD data for your WATCHLIST
3. Generates candlestick charts
4. Creates TTS narration in Hindi + English
5. Composes and saves the final MP4

---

### Step 10 — Schedule daily auto-generation

```bash
python main.py --schedule
```

This keeps the script running and auto-generates the video every day at `RUN_TIME` (default 4:05 PM IST).

> 💡 To run in background on Linux:
> ```bash
> nohup python main.py --schedule > logs/scheduler.log 2>&1 &
> ```

---

## 📦 What Each File Does

| File | Purpose |
|------|---------|
| `src/data_fetcher.py` | Angel One login + fetch candles + quotes + market summary |
| `src/chart_generator.py` | Candlestick charts, gainers/losers bar chart, summary card |
| `src/tts_narrator.py` | Build Hindi + English scripts, convert to MP3 with gTTS |
| `src/video_composer.py` | Combine images + audio into final MP4 with MoviePy |
| `main.py` | Orchestrates everything, handles CLI args & scheduler |

---

## 🔧 Customization

### Change the watchlist
Edit `.env`:
```env
WATCHLIST=WIPRO,MARUTI,ICICIBANK,BAJFINANCE,AXISBANK,NIFTY 50,BANKNIFTY
```
Supported symbols are in `src/data_fetcher.py → SYMBOL_TOKEN_MAP`.  
For more symbols, download the full token list:
```
https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
```

### Change candle interval
```env
CANDLE_INTERVAL=ONE_HOUR        # Intraday hourly chart
CANDLE_INTERVAL=FIFTEEN_MINUTE  # 15-min chart
CANDLE_INTERVAL=ONE_DAY         # Daily chart (default)
```

### Change video language
```env
VIDEO_LANGUAGE=english   # English only
VIDEO_LANGUAGE=hindi     # Hindi only
VIDEO_LANGUAGE=both      # English section then Hindi section (default)
```

### Add more symbols to token map
In `src/data_fetcher.py`, add to `SYMBOL_TOKEN_MAP`:
```python
"TATAMOTORS": "3456",
"BAJAJFINSV": "16675",
```
Get token numbers from the Angel One scrip master JSON above.

---

## 📺 Video Structure (output)

```
[Intro Title Card — 3s]
    ↓
[Market Summary Card + English Narration]
    ↓
[Market Summary Card + Hindi Narration]
    ↓
[Gainers / Losers Bar Chart — 6s]
    ↓
[Candlestick Chart: RELIANCE — 5s]
[Candlestick Chart: TCS — 5s]
[Candlestick Chart: INFY — 5s]
... (one per symbol in watchlist)
    ↓
[Outro Title Card — 3s]
```

---

## ⚠️ Important Notes

1. **Angel One SmartAPI is free** — no monthly charges for historical data.
   Live streaming (WebSocket) is also free but requires a trading account.

2. **gTTS requires internet** — it calls Google Translate API.
   For fully offline TTS, replace with [Coqui TTS](https://github.com/coqui-ai/TTS)
   (requires more setup and GPU for best quality).

3. **Market hours** — NSE closes at 3:30 PM IST.
   Set `RUN_TIME=16:05` to ensure EOD data is available.

4. **This is not financial advice** — the video includes a disclaimer.

5. **Token map** — If a symbol fetch fails, it's likely missing from `SYMBOL_TOKEN_MAP`.
   Look up the token in Angel One's scrip master JSON and add it.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| `SmartAPI login failed` | Check TOTP secret, client ID, password in `.env` |
| `Symbol not found in token map` | Add token to `SYMBOL_TOKEN_MAP` in `data_fetcher.py` |
| `ffmpeg not found` | Install FFmpeg and add to PATH |
| `gTTS connection error` | Check your internet connection |
| `MoviePy error` | Run `pip install imageio-ffmpeg` |
| Empty video / no audio | Run `python main.py --demo` first to isolate the issue |

---

## 🚀 Future Improvements (let me know!)

- [ ] Add Upstox / Zerodha Kite support
- [ ] Offline Hindi TTS (Coqui or AI4Bharat)
- [ ] WhatsApp / Telegram auto-send
- [ ] MCX commodities (Gold, Silver, Crude)
- [ ] Sector heatmap chart
- [ ] Animated chart bars (growing effect)
- [ ] Custom background music
- [ ] AI-generated market commentary (LLM)
