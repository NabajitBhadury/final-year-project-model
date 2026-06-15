"""Image validation and decoding helpers shared by REST and MCP paths."""

from __future__ import annotations

import base64
import binascii
import io
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageDecodeError(ValueError):
    """Raised when bytes cannot be decoded into a supported image."""


class ImageTooLargeError(ImageDecodeError):
    """Raised when an upload exceeds the configured size limit."""


def ensure_size_limit(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise ImageTooLargeError(f"image is too large; max upload size is {mb:.0f} MB")


def decode_base64_image(payload: str) -> bytes:
    """Decode raw base64 or a data URL payload into image bytes."""
    if "," in payload and payload.strip().lower().startswith("data:"):
        payload = payload.split(",", 1)[1]
    compact = "".join(payload.split())
    try:
        return base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImageDecodeError("image_base64 is not valid base64") from exc


def image_from_bytes(data: bytes, metadata: dict[str, Any] | None = None) -> tuple[Image.Image, dict[str, Any]]:
    """Load bytes into an RGB PIL image and return normalized image metadata."""
    metadata = dict(metadata or {})
    try:
        with Image.open(io.BytesIO(data)) as opened:
            image_format = opened.format
            img = ImageOps.exif_transpose(opened)
            img.load()
            rgb = img.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageDecodeError("could not read image") from exc

    info = {
        "width": rgb.width,
        "height": rgb.height,
        "mode": rgb.mode,
        "format": image_format,
        "filename": metadata.get("filename"),
        "content_type": metadata.get("content_type"),
    }
    return rgb, info
