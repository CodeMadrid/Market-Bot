"""
src/ai_analyst.py
─────────────────────────────────────────────────────────────────
Uses Claude API (claude-sonnet) to generate AI market insights:
  - Buy / Sell / Watch recommendations
  - Technical level analysis
  - Tomorrow's outlook
  - Narration scripts (Hindi + English) for each chart section
"""

import os
import json
import requests
from loguru import logger


ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
MODEL         = "claude-sonnet-4-20250514"


OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"


def _call_claude(prompt: str, max_tokens: int = 1000) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model   = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5")

    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — using fallback")
        return ""

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer":  "https://github.com/market-video-bot",
        "X-Title":       "Market Video Bot",
    }
    body = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        r = requests.post(OPENROUTER_API, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"OpenRouter API call failed: {e}")
        return ""
def generate_insights(summary: dict) -> dict:
    """
    Ask Claude to analyse the market data and return structured insights.
    Returns a dict ready for make_ai_insight_card() and TTS narration.
    """
    quotes     = summary.get("quotes", [])
    mood       = summary.get("market_mood", "Sideways")
    date       = summary.get("date", "today")
    nifty      = summary.get("nifty", {})
    top_gainer = summary.get("top_gainer", {})
    top_loser  = summary.get("top_loser",  {})

    quote_lines = "\n".join(
        f"  {q['symbol']}: LTP={q['ltp']}, Open={q.get('open',0)}, "
        f"High={q.get('high',0)}, Low={q.get('low',0)}, Change={q['change_pct']}%"
        for q in quotes
    )

    prompt = f"""You are a professional Indian stock market analyst. 
Today is {date}. Market mood is {mood}.

Market data:
{quote_lines}

Nifty 50: {nifty.get('ltp', 'N/A')} ({nifty.get('change_pct', 0)}%)
Top gainer: {top_gainer.get('symbol', 'N/A')} (+{top_gainer.get('change_pct', 0)}%)
Top loser:  {top_loser.get('symbol',  'N/A')} ({top_loser.get('change_pct', 0)}%)

Based on today's price action, provide a JSON response with EXACTLY this structure:
{{
  "mood": "Bullish" | "Bearish" | "Neutral",
  "score": <0-100 bullish sentiment score>,
  "summary": "<one sentence market summary under 120 chars>",
  "buy": [
    {{"symbol": "X", "reason": "<short reason under 40 chars>", "ltp": 0, "change_pct": 0}},
    ...up to 4 items
  ],
  "sell": [
    {{"symbol": "X", "reason": "<short reason under 40 chars>", "ltp": 0, "change_pct": 0}},
    ...up to 4 items
  ],
  "watch": [
    {{"symbol": "X", "reason": "<short reason under 40 chars>", "ltp": 0, "change_pct": 0}},
    ...up to 4 items
  ],
  "levels": [
    {{"label": "Nifty Support", "value": "24000", "note": "Key demand zone"}},
    {{"label": "Nifty Resistance", "value": "24500", "note": "Previous high"}},
    {{"label": "Bank Nifty", "value": "52000", "note": "Watch closely"}},
    {{"label": "FII Activity", "value": "Net Buyers", "note": "Positive signal"}}
  ],
  "tomorrow_outlook": "<2-3 sentence outlook for tomorrow>",
  "english_narration": "<60-90 second spoken English narration of the AI insights for a YouTube video, conversational tone>",
  "hindi_narration": "<60-90 second spoken Hindi narration of the AI insights, conversational tone in Hindi>",
  "chart_commentary": {{
    "gainers_losers": "<20 seconds English narration while showing the gainers/losers chart>",
    "heatmap": "<20 seconds English narration while showing sector heatmap>",
    "volume": "<15 seconds English narration while showing volume chart>"
  }}
}}

Fill in actual ltp and change_pct values from the data above for buy/sell/watch items.
Respond with ONLY the JSON, no other text."""

    logger.info("🤖 Calling Claude AI for market insights...")
    raw = _call_claude(prompt, max_tokens=2000)

    if not raw:
        return _fallback_insights(summary)

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        data["date"] = date
        # Fill ltp/change_pct from quotes for buy/sell/watch
        quote_map = {q["symbol"]: q for q in quotes}
        for section in ("buy", "sell", "watch"):
            for item in data.get(section, []):
                q = quote_map.get(item.get("symbol", ""), {})
                if q:
                    item["ltp"]        = q.get("ltp", item.get("ltp", 0))
                    item["change_pct"] = q.get("change_pct", item.get("change_pct", 0))
        logger.success("✅ AI insights generated")
        return data
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}\nRaw: {raw[:300]}")
        return _fallback_insights(summary)


def _fallback_insights(summary: dict) -> dict:
    """Simple rule-based fallback when Claude API is unavailable."""
    quotes    = summary.get("quotes", [])
    gainers   = [q for q in quotes if q["change_pct"] > 0.5]
    losers    = [q for q in quotes if q["change_pct"] < -0.5]
    mood      = summary.get("market_mood", "Sideways")
    nifty     = summary.get("nifty", {})
    score     = 60 if mood == "Bullish" else 35 if mood == "Bearish" else 50

    buy_items = [{"symbol": q["symbol"], "reason": "Strong momentum today",
                  "ltp": q["ltp"], "change_pct": q["change_pct"]}
                 for q in sorted(gainers, key=lambda x: x["change_pct"], reverse=True)[:4]]
    sell_items = [{"symbol": q["symbol"], "reason": "Weakness, monitor closely",
                   "ltp": q["ltp"], "change_pct": q["change_pct"]}
                  for q in sorted(losers, key=lambda x: x["change_pct"])[:4]]

    nifty_ltp = nifty.get("ltp", 24000)
    return {
        "date":    summary.get("date", ""),
        "mood":    mood,
        "score":   score,
        "summary": f"Market ended {mood.lower()} with Nifty at {nifty_ltp:,.0f}.",
        "buy":     buy_items,
        "sell":    sell_items,
        "watch":   [],
        "levels": [
            {"label": "Nifty Support",    "value": f"{int(nifty_ltp*0.985):,}", "note": "1.5% below LTP"},
            {"label": "Nifty Resistance", "value": f"{int(nifty_ltp*1.015):,}", "note": "1.5% above LTP"},
            {"label": "Key Level",        "value": f"{int(nifty_ltp):,}",       "note": "Current close"},
            {"label": "Trend",            "value": mood,                         "note": "Today's bias"},
        ],
        "tomorrow_outlook": (
            f"Markets are showing {mood.lower()} momentum. "
            f"Watch Nifty around {int(nifty_ltp):,} for direction. "
            f"Global cues and FII activity will be key tomorrow."
        ),
        "english_narration": (
            f"Based on today's market action, the mood is {mood}. "
            f"The Nifty 50 closed at {nifty_ltp:,.0f}. "
            f"{'Strong gainers suggest buying interest.' if mood == 'Bullish' else 'Caution is advised as selling pressure persists.'} "
            f"Keep an eye on global markets overnight for tomorrow's direction."
        ),
        "hindi_narration": (
            f"आज के बाजार के हिसाब से माहौल {mood} है। "
            f"निफ्टी 50 {nifty_ltp:,.0f} पर बंद हुआ। "
            f"कल के लिए वैश्विक संकेतों पर नजर रखें।"
        ),
        "chart_commentary": {
            "gainers_losers": (
                f"Looking at today's performance chart, {len(gainers)} stocks gained "
                f"while {len(losers)} declined. "
                + (f"{gainers[0]['symbol']} led the rally." if gainers else "")
            ),
            "heatmap": (
                "The sector heatmap shows which industries drove today's market. "
                "Green sectors indicate buying interest, red shows selling pressure."
            ),
            "volume": (
                "High volume stocks are important — they confirm price moves. "
                "Let's see which stocks had the most activity today."
            ),
        },
    }
