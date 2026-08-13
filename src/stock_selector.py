"""
src/stock_selector.py
─────────────────────────────────────────────────────────────────
Dynamically selects stocks for the day:
  1. Top 3 gainers from NSE universe
  2. Top 3 losers from NSE universe
  3. Top 1-2 movers per sector (Banking, IT, Auto, Pharma, Energy, FMCG, Metals)
  4. Nifty 50 + BankNifty always included
No hardcoded watchlist needed.
"""

import time
from loguru import logger
from datetime import datetime

SECTOR_UNIVERSE = {
    "Banking":  ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","INDUSINDBK","FEDERALBNK"],
    "IT":       ["TCS","INFY","WIPRO","HCLTECH","TECHM","LTIM","MPHASIS","PERSISTENT"],
    "Auto":     ["MARUTI","TATAMOTORS","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","M&M","TVSMOTOR"],
    "Pharma":   ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","AUROPHARMA"],
    "Energy":   ["RELIANCE","ONGC","NTPC","POWERGRID","BPCL","IOC","GAIL"],
    "FMCG":     ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO"],
    "Metals":   ["TATASTEEL","JSWSTEEL","HINDALCO","VEDL","COALINDIA","SAIL"],
}

SYMBOL_TOKEN_MAP = {
    "HDFCBANK":"1333","ICICIBANK":"4963","SBIN":"3045","AXISBANK":"5900",
    "KOTAKBANK":"1922","INDUSINDBK":"5258","FEDERALBNK":"1571",
    "TCS":"11536","INFY":"1594","WIPRO":"3787","HCLTECH":"7229",
    "TECHM":"13538","LTIM":"17818","MPHASIS":"4503","PERSISTENT":"18365",
    "MARUTI":"10999","TATAMOTORS":"3456","BAJAJ-AUTO":"16669",
    "HEROMOTOCO":"1348","EICHERMOT":"910","M&M":"2031","TVSMOTOR":"3903",
    "SUNPHARMA":"3351","DRREDDY":"881","CIPLA":"694","DIVISLAB":"10940",
    "APOLLOHOSP":"157","AUROPHARMA":"236",
    "RELIANCE":"2885","ONGC":"2475","NTPC":"11630","POWERGRID":"14977",
    "BPCL":"526","IOC":"1624","GAIL":"1037",
    "HINDUNILVR":"1394","ITC":"1660","NESTLEIND":"17963",
    "BRITANNIA":"547","DABUR":"772","MARICO":"4067",
    "TATASTEEL":"3499","JSWSTEEL":"11723","HINDALCO":"1363",
    "VEDL":"3063","COALINDIA":"20374","SAIL":"2963",
    "NIFTY 50":"26000","BANKNIFTY":"26009",
}


def _quote(smart, symbol, exchange="NSE"):
    token = SYMBOL_TOKEN_MAP.get(symbol)
    if not token:
        return None
    try:
        time.sleep(0.4)
        r = smart.ltpData(exchange, symbol, token)
        if not r or r.get("status") is False:
            return None
        d    = r["data"]
        ltp  = float(d["ltp"])
        prev = float(d.get("close", ltp))
        chg  = round(ltp - prev, 2)
        pct  = round((chg / prev) * 100, 2) if prev else 0.0
        return {
            "symbol": symbol, "ltp": ltp,
            "open":   float(d.get("open", 0)),
            "high":   float(d.get("high", 0)),
            "low":    float(d.get("low",  0)),
            "close":  prev, "change": chg, "change_pct": pct,
            "volume": float(d.get("tradedQuantity", 0)),
        }
    except Exception as e:
        logger.debug(f"Quote failed {symbol}: {e}")
        return None


def select_stocks_for_today(exchange="NSE"):
    from src.data_fetcher import get_smart_api
    smart = get_smart_api()

    logger.info("🔍 Scanning market — fetching sector stocks...")

    # Fetch all sector stocks
    all_quotes    = {}
    sector_quotes = {}

    for sector, symbols in SECTOR_UNIVERSE.items():
        sector_quotes[sector] = []
        for sym in symbols:
            q = _quote(smart, sym, exchange)
            if q:
                all_quotes[sym] = q
                sector_quotes[sector].append(q)
        logger.info(f"  {sector}: fetched {len(sector_quotes[sector])} stocks")

    all_list = list(all_quotes.values())

    # Top 3 gainers & losers across entire universe
    top_gainers = sorted(all_list, key=lambda x: x["change_pct"], reverse=True)[:3]
    top_losers  = sorted(all_list, key=lambda x: x["change_pct"])[:3]

    # Top 2 movers per sector
    sector_picks = {}
    for sector, quotes in sector_quotes.items():
        if quotes:
            sector_picks[sector] = sorted(
                quotes, key=lambda x: abs(x["change_pct"]), reverse=True
            )[:2]

    # Indices
    nifty     = _quote(smart, "NIFTY 50")
    banknifty = _quote(smart, "BANKNIFTY")

    # Build unique final list: indices → gainers → losers → sector picks
    seen, final = set(), []
    for q in filter(None, [nifty, banknifty]):
        if q["symbol"] not in seen:
            final.append(q); seen.add(q["symbol"])
    for q in top_gainers + top_losers:
        if q["symbol"] not in seen:
            final.append(q); seen.add(q["symbol"])
    for picks in sector_picks.values():
        for q in picks:
            if q["symbol"] not in seen:
                final.append(q); seen.add(q["symbol"])

    # Market mood
    n_up = len([q for q in all_list if q["change_pct"] > 0])
    n_dn = len([q for q in all_list if q["change_pct"] < 0])
    if nifty:
        mood = "Bullish" if nifty["change_pct"] > 0.3 else \
               "Bearish" if nifty["change_pct"] < -0.3 else "Sideways"
    else:
        mood = "Bullish" if n_up > n_dn else "Bearish" if n_dn > n_up else "Sideways"

    # Candle symbols: top gainer + top loser + best mover per sector (max 8)
    candle_syms = [q["symbol"] for q in top_gainers[:2] + top_losers[:1]]
    for picks in sector_picks.values():
        if picks and picks[0]["symbol"] not in candle_syms:
            candle_syms.append(picks[0]["symbol"])
        if len(candle_syms) >= 8:
            break

    logger.success(
        f"✅ {len(final)} stocks selected | mood={mood} | "
        f"gainers={[q['symbol'] for q in top_gainers]} | "
        f"losers={[q['symbol'] for q in top_losers]}"
    )

    return {
        "date":           datetime.now().strftime("%d %B %Y"),
        "market_mood":    mood,
        "quotes":         final,
        "sectors":        sector_picks,
        "top_gainers":    top_gainers,
        "top_losers":     top_losers,
        "top_gainer":     top_gainers[0] if top_gainers else None,
        "top_loser":      top_losers[0]  if top_losers  else None,
        "nifty":          nifty,
        "banknifty":      banknifty,
        "sensex":         None,
        "candle_symbols": candle_syms,
    }