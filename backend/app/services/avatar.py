"""Agent avatar (photo/logo) processing: validate + compress with Pillow.

The raw upload is checked on the router (content type + size); this module
runs the CPU-heavy Pillow work off the event loop (`asyncio.to_thread`) and
returns a compressed WebP payload ready for the storage backend.

- PNG / JPG / WebP stills are downscaled and re-encoded as WebP (alpha kept).
- Animated GIFs are converted to ANIMATED WebP (same frame timing), so the
  avatar keeps moving on the button.
- Transparency is preserved (RGBA) — the widget draws the avatar on the
  header-colored button/circle, so transparent PNGs/GIFs follow the theme
  color.
"""
import io

from PIL import Image, ImageSequence, UnidentifiedImageError

from ..config import (
    AVATAR_MAX_DIM,
    AVATAR_MAX_FRAMES,
    AVATAR_MAX_PIXELS,
    AVATAR_QUALITY,
)


class AvatarError(ValueError):
    """Raised when the uploaded bytes cannot be turned into an avatar."""


# Formats we accept (Pillow's `format` names). Anything else — BMP, TIFF,
# HEIC, … — is rejected even if the declared content type is fine.
ALLOWED_FORMATS = ("PNG", "JPEG", "GIF", "WEBP")


def _still_webp(img: Image.Image) -> bytes:
    """Single-frame image → downscaled WebP (RGBA keeps transparency)."""
    try:
        img.load()  # full decode — raises on truncated/corrupt data
    except Exception as exc:
        raise AvatarError("File is not a valid image") from exc

    img = img.convert("RGBA")
    img.thumbnail((AVATAR_MAX_DIM, AVATAR_MAX_DIM), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="WEBP", quality=AVATAR_QUALITY, method=6)
    return out.getvalue()


def _animated_webp(img: Image.Image) -> bytes:
    """Animated GIF → animated WebP (same per-frame timing, downscaled)."""
    frames: list[Image.Image] = []
    try:
        for i, frame in enumerate(ImageSequence.Iterator(img)):
            if i >= AVATAR_MAX_FRAMES:
                raise AvatarError(f"GIF has too many frames (max {AVATAR_MAX_FRAMES})")
            f = frame.convert("RGBA")
            if f.width * f.height > AVATAR_MAX_PIXELS:
                raise AvatarError(
                    f"Image is too large (max {AVATAR_MAX_PIXELS:,} pixels)"
                )
            f.thumbnail((AVATAR_MAX_DIM, AVATAR_MAX_DIM), Image.Resampling.LANCZOS)
            frames.append(f)
    except AvatarError:
        raise
    except Exception as exc:
        raise AvatarError("File is not a valid image") from exc

    if not frames:
        raise AvatarError("File is not a valid image")

    # GIF stores duration in ms per frame (int, or a list for per-frame timing).
    duration = img.info.get("duration") or 100
    out = io.BytesIO()
    frames[0].save(
        out,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        quality=AVATAR_QUALITY,
        method=6,
    )
    return out.getvalue()


def compress_avatar(data: bytes) -> bytes:
    """Decode, downscale and re-encode an image as WebP (possibly animated).

    Raises AvatarError for non-image / corrupt / oversized inputs.
    """
    try:
        img = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise AvatarError("File is not a valid image") from exc

    if img.format not in ALLOWED_FORMATS:
        raise AvatarError("Only GIF, PNG or JPG images are supported")

    # Guard against decompression bombs before decoding the full bitmap.
    if img.width * img.height > AVATAR_MAX_PIXELS:
        raise AvatarError(f"Image is too large (max {AVATAR_MAX_PIXELS:,} pixels)")

    if getattr(img, "is_animated", False):
        return _animated_webp(img)
    return _still_webp(img)
