#!/usr/bin/env python3
"""Generate the animated GIF avatar templates bundled with the dashboard.

Renders emoji on a transparent 512x512 canvas with simple deterministic
animations (bounce / pulse / wiggle / flash) and saves them as looped GIFs
under `frontend/public/avatars/templates/`. Keep the file list in sync with
`src/utils/avatarTemplates.ts`.

Requires Pillow + the Apple Color Emoji font (macOS):
    cd backend && uv run python ../frontend/scripts/generate-avatar-templates.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
OUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "public", "avatars", "templates")
)
SIZE = 512
EMOJI_PX = 300  # emoji height on the canvas

FONT = ImageFont.truetype(EMOJI_FONT, 160)  # 160 is a native bitmap size


def _render_emoji(emoji: str) -> Image.Image:
    """Render an emoji centered on a 512x512 transparent canvas."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), emoji, font=FONT, embedded_color=True)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    scale = EMOJI_PX / max(img.size)
    img = img.resize(
        (int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS
    )
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2), img)
    return canvas


def _frames_bounce(base: Image.Image, n=6, amp=34, dur=110) -> tuple[list[Image.Image], int]:
    frames = []
    for i in range(n):
        f = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        dy = int(round(amp * math.sin(2 * math.pi * i / n)))
        f.paste(base, (0, dy), base)
        frames.append(f)
    return frames, dur


def _frames_pulse(base: Image.Image, n=6, amount=0.13, dur=130) -> tuple[list[Image.Image], int]:
    frames = []
    for i in range(n):
        s = 1.0 + amount * math.sin(2 * math.pi * i / n)
        w = h = int(SIZE * s)
        scaled = base.resize((w, h), Image.Resampling.LANCZOS)
        f = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        f.paste(scaled, ((SIZE - w) // 2, (SIZE - h) // 2), scaled)
        frames.append(f)
    return frames, dur


def _frames_wiggle(base: Image.Image, n=6, angle=14, dur=100) -> tuple[list[Image.Image], int]:
    frames = []
    for i in range(n):
        a = angle * math.sin(2 * math.pi * i / n)
        frames.append(base.rotate(a, resample=Image.Resampling.BICUBIC))
    return frames, dur


def _frames_flash(base: Image.Image, n=4, dim=0.35, dur=150) -> tuple[list[Image.Image], int]:
    frames = []
    for i in range(n):
        if i % 2 == 0:
            frames.append(base)
        else:
            dimmed = base.copy()
            dimmed.putalpha(base.getchannel("A").point(lambda v: int(v * dim)))
            frames.append(dimmed)
    return frames, dur


def _save_gif(frames: list[Image.Image], dur: int, path: str) -> None:
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=dur,
        loop=0,
        disposal=2,
    )


# id, label, emoji, animation
TEMPLATES = [
    ("rocket", "Rocket", "🚀", _frames_bounce),
    ("robot", "Robot", "🤖", _frames_bounce),
    ("heart", "Heart", "❤️", _frames_pulse),
    ("chat", "Chat", "💬", _frames_pulse),
    ("brain", "Brain", "🧠", _frames_pulse),
    ("wave", "Wave", "👋", _frames_wiggle),
    ("star", "Star", "🌟", _frames_wiggle),
    ("owl", "Owl", "🦉", _frames_wiggle),
    ("bolt", "Bolt", "⚡", _frames_flash),
    ("sparkles", "Sparkles", "✨", _frames_flash),
]


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for tpl_id, label, emoji, anim in TEMPLATES:
        base = _render_emoji(emoji)
        frames, dur = anim(base)
        path = os.path.join(OUT_DIR, f"{tpl_id}.gif")
        _save_gif(frames, dur, path)
        size_kb = os.path.getsize(path) / 1024
        print(f"  {tpl_id:10s} {label:8s} {len(frames)} frames, {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
