"""
src/shorts/base_short.py
─────────────────────────────────────────────────────────────────
Base class and shared utilities for all 5 shorts.
All shorts are 1080x1920 (vertical), 60s max, 30fps.
Premium design system — consistent across all shorts.
"""

import os
import subprocess
import shutil
import tempfile
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from loguru import logger

# ── Dimensions ────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
BG     = (6, 10, 18)

# ── Premium color palette ─────────────────────────────────────
BULL      = (0, 220, 120)
BEAR      = (220, 50, 80)
GOLD      = (255, 200, 50)
ACCENT    = (88, 160, 255)
TEXT      = (230, 237, 243)
MUTED     = (100, 115, 140)
CARD_BG   = (14, 20, 36)
CARD_BG2  = (18, 26, 44)
GLOW_G    = (0, 255, 120, 60)
GLOW_R    = (255, 50, 80, 60)

MOOD_COL  = {
    "Bullish":  (0, 220, 120),
    "Bearish":  (220, 50, 80),
    "Sideways": (255, 165, 0),
}

SHORTS_DIR = "output/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)


# ── Font loader ───────────────────────────────────────────────
def font(size, bold=False):
    for p in [
        r"C:\Windows\Fonts\arialbd.ttf"  if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\impact.ttf"   if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()


# ── Drawing helpers ───────────────────────────────────────────
def cx(draw, text, y, f, color=TEXT, img=None):
    """Centered text."""
    bb = draw.textbbox((0, 0), text, font=f)
    x  = (W - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)
    return x


def text_w(draw, text, f):
    bb = draw.textbbox((0, 0), text, font=f)
    return bb[2] - bb[0]


def new_frame():
    """Create a fresh dark frame."""
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_grid(draw, alpha=8):
    """Subtle background grid."""
    col = tuple(max(0, min(255, c + alpha)) for c in BG)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=col, width=1)
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=col, width=1)


def draw_glow(img, cx, cy, radius, color):
    """Draw a radial glow effect."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for r in range(radius, 0, -20):
        alpha = int(color[3] * (1 - r / radius)) if len(color) > 3 else 30
        col   = (*color[:3], alpha)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    blurred = glow.filter(ImageFilter.GaussianBlur(radius // 4))
    img.paste(Image.new("RGB", (W, H), BG), mask=None)
    base = img.convert("RGBA")
    base.alpha_composite(blurred)
    return base.convert("RGB")


def draw_channel_badge(draw, mood="Bullish"):
    """Draw Dalal Street AI badge at top."""
    mc = MOOD_COL.get(mood, ACCENT)
    draw.rectangle([0, 0, W, 100], fill=(10, 16, 30))
    draw.rectangle([0, 96, W, 100], fill=mc)
    # Logo circle
    draw.ellipse([24, 14, 76, 66], fill=mc)
    draw.text((50, 40), "D", font=font(32, True), fill=BG, anchor="mm")
    draw.text((90, 16), "DALAL STREET AI", font=font(36, True), fill=TEXT)
    draw.text((92, 56), "Premium Market Shorts", font=font(20), fill=MUTED)


def draw_bottom_bar(draw, text="Not financial advice  •  dalal street ai"):
    """Bottom disclaimer bar."""
    draw.rectangle([0, H - 80, W, H], fill=(10, 14, 24))
    draw.rectangle([0, H - 80, W, H - 76], fill=ACCENT)
    cx(draw, text, H - 52, font(22), MUTED)


def easing_out(t):
    """Ease-out cubic — smooth deceleration."""
    return 1 - (1 - t) ** 3


def easing_in_out(t):
    """Ease in-out sine."""
    return -(math.cos(math.pi * t) - 1) / 2


def lerp(a, b, t):
    return a + (b - a) * t


# ── FFmpeg encoder ────────────────────────────────────────────
def _absp(p):
    return os.path.abspath(p).replace("\\", "/")


def _run(cmd, label="ffmpeg"):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f"{label}:\n{r.stderr[-2000:]}")
        raise RuntimeError(f"{label} failed")


def encode_frames_to_video(frames, audio_path, out_path, fps=FPS):
    """
    Encode list of PIL frames + audio into MP4.
    frames: list of PIL.Image (1080x1920)
    """
    tmp = tempfile.mkdtemp(prefix="short_")
    try:
        # Save frames
        concat = os.path.join(tmp, "concat.txt")
        with open(concat, "w") as f:
            for i, frame in enumerate(frames):
                p = os.path.join(tmp, f"f{i:05d}.png")
                frame.save(p, "PNG")
                f.write(f"file '{_absp(p)}'\n")
                f.write(f"duration {1/fps:.6f}\n")

        # Encode video
        silent = os.path.join(tmp, "silent.mp4")
        _run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat,
            "-vf", f"scale={W}:{H},format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-r", str(fps), silent
        ], "encode")

        # Mux audio
        if audio_path and os.path.exists(audio_path):
            _run([
                "ffmpeg", "-y",
                "-i", _absp(silent),
                "-i", _absp(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", out_path
            ], "mux")
        else:
            shutil.copy(silent, out_path)

        mb = os.path.getsize(out_path) / (1024 * 1024)
        logger.success(f"✅ Short → {out_path}  ({mb:.1f} MB)")
        return out_path

    finally:
        shutil.rmtree(tmp, ignore_errors=True)