"""
src/tts_narrator.py  —  Hindi + English TTS with per-section audio
Uses gTTS (Google TTS, FREE). Generates audio per chart section
so narration plays while the matching visual is shown.
"""

import os
from gtts import gTTS
from pydub import AudioSegment
from loguru import logger

AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

SILENCE_500  = AudioSegment.silent(duration=500)
SILENCE_1000 = AudioSegment.silent(duration=1000)


def _tts(text: str, lang: str, fname: str) -> str:
    """Convert text → MP3. Returns path or empty string."""
    out = os.path.join(AUDIO_DIR, f"{fname}.mp3")
    if not text or not text.strip():
        return ""
    try:
        gTTS(text=text, lang=lang, slow=False).save(out)
        logger.success(f"🎙️  {fname}.mp3  (lang={lang})")
        return out
    except Exception as e:
        logger.warning(f"TTS failed for {fname}: {e}")
        return ""


def _merge(paths: list, out_name: str) -> str:
    """Merge a list of MP3 paths (with 0.5s gaps) into one file."""
    out  = os.path.join(AUDIO_DIR, out_name)
    merged = AudioSegment.empty()
    for p in paths:
        if p and os.path.exists(p):
            merged += AudioSegment.from_mp3(p) + SILENCE_500
    if len(merged) == 0:
        return ""
    merged.export(out, format="mp3")
    logger.success(f"🎵 Merged → {out}")
    return out


# ── Script builders ───────────────────────────────────────────

def build_intro_script(summary: dict) -> dict:
    date  = summary.get("date", "today")
    mood  = summary.get("market_mood", "Mixed")
    nifty = summary.get("nifty", {})
    mood_hi = {"Bullish":"तेजी","Bearish":"मंदी","Sideways":"मिला-जुला"}.get(mood, mood)
    ltp_str = f"{nifty.get('ltp', 0):,.0f}" if nifty else ""

    return {
        "en": (
            f"Welcome to your daily Indian stock market update for {date}. "
            f"Today's market was {mood}. "
            + (f"The Nifty 50 closed at {ltp_str} points. " if ltp_str else "")
            + "Let's dive into what happened today."
        ),
        "hi": (
            f"नमस्ते! {date} का दैनिक शेयर बाजार अपडेट में आपका स्वागत है। "
            f"आज का बाजार {mood_hi} रहा। "
            + (f"निफ्टी 50 {ltp_str} अंकों पर बंद हुआ। " if ltp_str else "")
            + "आइए जानते हैं आज क्या हुआ।"
        ),
    }


def build_summary_script(summary: dict) -> dict:
    nifty  = summary.get("nifty", {})
    sensex = summary.get("sensex", {})
    gainer = summary.get("top_gainer", {})
    loser  = summary.get("top_loser", {})
    mood   = summary.get("market_mood", "Mixed")

    en_parts, hi_parts = [], []

    if nifty:
        d  = "gained" if nifty["change_pct"] >= 0 else "fell"
        dh = "बढ़ा" if nifty["change_pct"] >= 0 else "गिरा"
        en_parts.append(
            f"The Nifty 50 {d} by {abs(nifty['change_pct']):.2f} percent, "
            f"closing at {nifty['ltp']:,.0f}. "
            f"It opened at {nifty.get('open',0):,.0f} and hit a high of {nifty.get('high',0):,.0f}."
        )
        hi_parts.append(
            f"निफ्टी 50 आज {abs(nifty['change_pct']):.2f} प्रतिशत {dh}, "
            f"{nifty['ltp']:,.0f} अंकों पर बंद हुआ।"
        )

    if sensex:
        d  = "rose" if sensex["change_pct"] >= 0 else "dropped"
        dh = "चढ़ा" if sensex["change_pct"] >= 0 else "लुढ़का"
        en_parts.append(
            f"The Sensex {d} {abs(sensex['change_pct']):.2f} percent to {sensex['ltp']:,.0f}."
        )
        hi_parts.append(
            f"सेंसेक्स {abs(sensex['change_pct']):.2f} प्रतिशत {dh}, {sensex['ltp']:,.0f} पर बंद हुआ।"
        )

    if gainer:
        en_parts.append(
            f"Top gainer was {gainer['symbol']}, up {gainer['change_pct']:.2f} percent "
            f"to rupees {gainer['ltp']:,.2f}."
        )
        hi_parts.append(
            f"सबसे ज्यादा बढ़ने वाला शेयर {gainer['symbol']} रहा, "
            f"{gainer['change_pct']:.2f} प्रतिशत की बढ़त के साथ।"
        )

    if loser:
        en_parts.append(
            f"Biggest loser was {loser['symbol']}, down {abs(loser['change_pct']):.2f} percent "
            f"to rupees {loser['ltp']:,.2f}."
        )
        hi_parts.append(
            f"सबसे ज्यादा गिरने वाला शेयर {loser['symbol']} था, "
            f"{abs(loser['change_pct']):.2f} प्रतिशत की गिरावट के साथ।"
        )

    return {
        "en": " ".join(en_parts),
        "hi": " ".join(hi_parts),
    }


def build_chart_scripts(insights: dict) -> dict:
    """Per-chart narration scripts from AI insights."""
    cc = insights.get("chart_commentary", {})
    return {
        "gainers_en":  cc.get("gainers_losers", "Let's look at today's top movers."),
        "heatmap_en":  cc.get("heatmap",        "Here's how different sectors performed today."),
        "volume_en":   cc.get("volume",          "Now let's check the volume leaders of the day."),
        "gainers_hi":  "आइए देखते हैं आज के शीर्ष प्रदर्शन करने वाले शेयर।",
        "heatmap_hi":  "यहाँ देखते हैं आज किस सेक्टर ने कैसा प्रदर्शन किया।",
        "volume_hi":   "अब देखते हैं आज के वॉल्यूम लीडर्स।",
    }


def build_ai_script(insights: dict) -> dict:
    return {
        "en": insights.get("english_narration", ""),
        "hi": insights.get("hindi_narration",   ""),
        "outlook_en": (
            "Before we wrap up, here's the AI-powered outlook for tomorrow. "
            + insights.get("tomorrow_outlook", "")
            + " Remember, this is for educational purposes only. Always do your own research before investing."
        ),
        "outlook_hi": (
            "अब एक नज़र कल के लिए AI विश्लेषण पर। "
            + "याद रखें, यह सिर्फ शैक्षिक उद्देश्य के लिए है। निवेश से पहले खुद रिसर्च करें।"
        ),
    }


def build_outro_script() -> dict:
    return {
        "en": (
            "That's your complete market summary for today. "
            "Like and share this video if you found it helpful. "
            "Stay informed, stay invested, and we'll see you tomorrow!"
        ),
        "hi": (
            "यह था आज का पूरा बाजार सारांश। "
            "अगर यह वीडियो उपयोगी लगी तो लाइक और शेयर करें। "
            "जागरूक रहें, निवेश करते रहें!"
        ),
    }


# ── Main generator ────────────────────────────────────────────

def generate_narration(summary: dict, insights: dict, language: str = "both") -> dict:
    """
    Generate ALL audio clips, keyed by segment name.
    Returns dict: {segment_key: mp3_path}
    """
    do_en = language in ("english", "both")
    do_hi = language in ("hindi",   "both")

    intro   = build_intro_script(summary)
    summ    = build_summary_script(summary)
    charts  = build_chart_scripts(insights)
    ai      = build_ai_script(insights)
    outro   = build_outro_script()

    result = {}

    def _make(key, text, lang):
        p = _tts(text, lang, key)
        if p:
            result[key] = p

    # Intro
    if do_en: _make("intro_en",        intro["en"],        "en")
    if do_hi: _make("intro_hi",        intro["hi"],        "hi")

    # Summary (Nifty/Sensex/Top gainer/loser)
    if do_en: _make("summary_en",      summ["en"],         "en")
    if do_hi: _make("summary_hi",      summ["hi"],         "hi")

    # Per-chart commentary
    if do_en: _make("gainers_en",      charts["gainers_en"], "en")
    if do_hi: _make("gainers_hi",      charts["gainers_hi"], "hi")
    if do_en: _make("heatmap_en",      charts["heatmap_en"], "en")
    if do_hi: _make("heatmap_hi",      charts["heatmap_hi"], "hi")
    if do_en: _make("volume_en",       charts["volume_en"],  "en")
    if do_hi: _make("volume_hi",       charts["volume_hi"],  "hi")

    # AI insights narration
    if do_en: _make("ai_en",           ai["en"],             "en")
    if do_hi: _make("ai_hi",           ai["hi"],             "hi")
    if do_en: _make("outlook_en",      ai["outlook_en"],     "en")
    if do_hi: _make("outlook_hi",      ai["outlook_hi"],     "hi")

    # Outro
    if do_en: _make("outro_en",        outro["en"],          "en")
    if do_hi: _make("outro_hi",        outro["hi"],          "hi")

    # Also create merged full tracks (for backward compat)
    if do_en:
        result["full_english"] = _merge(
            [result.get(k) for k in
             ["intro_en","summary_en","gainers_en","heatmap_en",
              "volume_en","ai_en","outlook_en","outro_en"]],
            "full_english.mp3"
        )
    if do_hi:
        result["full_hindi"] = _merge(
            [result.get(k) for k in
             ["intro_hi","summary_hi","gainers_hi","heatmap_hi",
              "volume_hi","ai_hi","outlook_hi","outro_hi"]],
            "full_hindi.mp3"
        )

    return result
