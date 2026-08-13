"""
src/data_fetcher.py
────────────────────────────────────────────────────────────────
Fetches market data from Angel One SmartAPI (FREE, NSE/BSE/MCX).
Handles login with TOTP, fetches OHLCV candles & LTP quotes.
"""

import os
import pyotp
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ── Angel One token map for common symbols ───────────────────
# Full list: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
SYMBOL_TOKEN_MAP = {
    "HDFCBANK": "1333",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "AXISBANK": "5900",
    "KOTAKBANK": "1922",
    "INDUSINDBK": "5258",
    "FEDERALBNK": "1571",

    "TCS": "11536",
    "INFY": "1594",
    "WIPRO": "3787",
    "HCLTECH": "7229",
    "TECHM": "13538",
    "LTIM": "17818",
    "MPHASIS": "4503",
    "PERSISTENT": "18365",

    "MARUTI": "10999",
    "TATAMOTORS": "3456",
    "BAJAJ-AUTO": "16669",
    "HEROMOTOCO": "1348",
    "EICHERMOT": "910",
    "M&M": "2031",
    "TVSMOTOR": "3903",

    "SUNPHARMA": "3351",
    "DRREDDY": "881",
    "CIPLA": "694",
    "DIVISLAB": "10940",
    "APOLLOHOSP": "157",
    "AUROPHARMA": "236",

    "RELIANCE": "2885",
    "ONGC": "2475",
    "NTPC": "11630",
    "POWERGRID": "14977",
    "BPCL": "526",
    "IOC": "1624",
    "GAIL": "1037",

    "HINDUNILVR": "1394",
    "ITC": "1660",
    "NESTLEIND": "17963",
    "BRITANNIA": "547",
    "DABUR": "772",
    "MARICO": "4067",

    "TATASTEEL": "3499",
    "JSWSTEEL": "11723",
    "HINDALCO": "1363",
    "VEDL": "3063",
    "COALINDIA": "20374",
    "SAIL": "2963",

    "NIFTY 50": "26000",
    "BANKNIFTY": "26009",

    # Keep this because data_fetcher.py already supports SENSEX
    "SENSEX": "1",
}


INTERVAL_MAP = {
    "ONE_DAY":         "ONE_DAY",
    "ONE_HOUR":        "ONE_HOUR",
    "FIFTEEN_MINUTE":  "FIFTEEN_MINUTE",
    "FIVE_MINUTE":     "FIVE_MINUTE",
    "ONE_MINUTE":      "ONE_MINUTE",
}


def get_smart_api():
    """Login to Angel One SmartAPI and return authenticated obj."""
    try:
        from SmartApi import SmartConnect  # smartapi-python package
    except ImportError:
        raise ImportError(
            "SmartAPI not installed. Run: pip install smartapi-python pyotp"
        )

    api_key   = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password  = os.getenv("ANGEL_PASSWORD")
    totp_key  = os.getenv("ANGEL_TOTP_SECRET")

    if not all([api_key, client_id, password, totp_key]):
        raise ValueError(
            "Missing Angel One credentials in .env file!\n"
            "Set: ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET"
        )

    smart = SmartConnect(api_key=api_key)

    # Generate current TOTP from secret
    totp = pyotp.TOTP(totp_key).now()

    data = smart.generateSession(client_id, password, totp)

    if data["status"] is False:
        raise ConnectionError(f"Angel One login failed: {data['message']}")

    logger.success(f"✅ Logged in to Angel One as {client_id}")
    return smart


def fetch_candles(
    symbol: str,
    interval: str = "ONE_DAY",
    days_back: int = 30,
    exchange: str = "NSE",
) -> pd.DataFrame:
    """
    Fetch OHLCV candlestick data for a symbol.

    Parameters
    ----------
    symbol    : e.g. "RELIANCE", "NIFTY 50"
    interval  : ONE_DAY | ONE_HOUR | FIFTEEN_MINUTE | FIVE_MINUTE
    days_back : how many days of history to pull
    exchange  : NSE | BSE | MCX

    Returns
    -------
    pd.DataFrame with columns: [datetime, open, high, low, close, volume]
    """
    smart = get_smart_api()

    token = SYMBOL_TOKEN_MAP.get(symbol.upper())
    if token is None:
        raise ValueError(
            f"Symbol '{symbol}' not found in token map.\n"
            f"Available: {list(SYMBOL_TOKEN_MAP.keys())}\n"
            f"Or download the full token list from Angel One docs."
        )

    to_date   = datetime.now()
    from_date = to_date - timedelta(days=days_back)

    params = {
        "exchange":    exchange,
        "symboltoken": token,
        "interval":    INTERVAL_MAP.get(interval, "ONE_DAY"),
        "fromdate":    from_date.strftime("%Y-%m-%d %H:%M"),
        "todate":      to_date.strftime("%Y-%m-%d %H:%M"),
    }

    logger.info(f"📡 Fetching {interval} candles for {symbol} ({days_back}d)...")
    response = smart.getCandleData(params)

    if response["status"] is False:
        raise RuntimeError(f"API error for {symbol}: {response['message']}")

    candles = response["data"]
    df = pd.DataFrame(
        candles,
        columns=["datetime", "open", "high", "low", "close", "volume"]
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    df = df.astype({"open": float, "high": float, "low": float,
                    "close": float, "volume": float})

    logger.success(f"✅ Got {len(df)} candles for {symbol}")
    return df


def fetch_quote(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch live / last traded price (LTP) and basic quote info.

    Returns dict with: ltp, open, high, low, close, change, change_pct
    """
    smart = get_smart_api()

    token = SYMBOL_TOKEN_MAP.get(symbol.upper())
    if token is None:
        raise ValueError(f"Symbol '{symbol}' not found in token map.")

    response = smart.ltpData(exchange, symbol.upper(), token)

    if response["status"] is False:
        raise RuntimeError(f"Quote error for {symbol}: {response['message']}")

    d = response["data"]
    ltp   = float(d["ltp"])
    close = float(d.get("close", ltp))
    change     = round(ltp - close, 2)
    change_pct = round((change / close) * 100, 2) if close else 0.0

    quote = {
        "symbol":     symbol.upper(),
        "ltp":        ltp,
        "open":       float(d.get("open", 0)),
        "high":       float(d.get("high", 0)),
        "low":        float(d.get("low", 0)),
        "close":      close,
        "change":     change,
        "change_pct": change_pct,
    }

    logger.info(
        f"📊 {symbol}: ₹{ltp} | {'+' if change >= 0 else ''}{change} ({change_pct}%)"
    )
    return quote


def fetch_all_quotes(symbols: list[str], exchange: str = "NSE") -> list[dict]:
    """Fetch LTP quotes for a list of symbols."""
    quotes = []
    for sym in symbols:
        try:
            q = fetch_quote(sym, exchange)
            quotes.append(q)
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch {sym}: {e}")
    return quotes


def get_market_summary(symbols: list[str], exchange: str = "NSE") -> dict:
    """
    Build a high-level market summary dict used by the narrator & video.

    Returns
    -------
    {
        "date": "25 March 2025",
        "quotes": [...],
        "top_gainer": {...},
        "top_loser":  {...},
        "nifty": {...},       # if NIFTY 50 in symbols
        "sensex": {...},      # if SENSEX in symbols
        "market_mood": "Bullish" | "Bearish" | "Sideways"
    }
    """
    quotes = fetch_all_quotes(symbols, exchange)

    gainers = [q for q in quotes if q["change_pct"] > 0]
    losers  = [q for q in quotes if q["change_pct"] < 0]

    top_gainer = max(gainers, key=lambda x: x["change_pct"]) if gainers else None
    top_loser  = min(losers,  key=lambda x: x["change_pct"]) if losers  else None

    nifty  = next((q for q in quotes if q["symbol"] == "NIFTY 50"), None)
    sensex = next((q for q in quotes if q["symbol"] == "SENSEX"),   None)

    # Simple mood logic based on Nifty or majority gainers
    if nifty:
        mood = "Bullish" if nifty["change_pct"] > 0.3 else \
               "Bearish" if nifty["change_pct"] < -0.3 else "Sideways"
    else:
        mood = "Bullish" if len(gainers) > len(losers) else \
               "Bearish" if len(losers) > len(gainers) else "Sideways"

    return {
        "date":        datetime.now().strftime("%d %B %Y"),
        "quotes":      quotes,
        "top_gainer":  top_gainer,
        "top_loser":   top_loser,
        "nifty":       nifty,
        "sensex":      sensex,
        "market_mood": mood,
    }
