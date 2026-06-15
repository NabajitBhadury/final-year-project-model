"""MCP tool definitions for FarmEasy model inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .image_utils import (
    ImageDecodeError,
    ImageTooLargeError,
    decode_base64_image,
    ensure_size_limit,
    image_from_bytes,
)
from .inference import get_service
from .video import analyze_video_bytes


INSTRUCTIONS = """
FarmEasy exposes corn leaf disease inference tools. Use predict_image_base64
when an image is available as bytes/base64, predict_image_path or
predict_video_path when the MCP client can reference local media on this
machine, and model_metadata to inspect classes and runtime configuration.
""".strip()


def create_mcp_server(streamable_http_path: str = "/") -> FastMCP:
    settings = get_settings()
    mcp = FastMCP(
        "FarmEasy Model MCP",
        instructions=INSTRUCTIONS,
        stateless_http=True,
        json_response=True,
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path=streamable_http_path,
    )

    @mcp.tool()
    def model_metadata() -> dict[str, Any]:
        """Return model classes, selected weights, thresholds, and server paths."""
        return get_service().metadata()

    @mcp.tool()
    def predict_image_base64(
        image_base64: str,
        filename: Optional[str] = None,
        gate_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        tta: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Analyze an image supplied as raw base64 or a data URL."""
        try:
            data = decode_base64_image(image_base64)
            ensure_size_limit(data, settings.max_upload_bytes)
            image, image_info = image_from_bytes(data, {"filename": filename})
            return get_service().analyze_image(
                image,
                gate_threshold=gate_threshold,
                conf_threshold=conf_threshold,
                tta=tta,
                image_info=image_info,
            )
        except (ImageDecodeError, ImageTooLargeError) as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def predict_image_path(
        path: str,
        gate_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        tta: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Analyze a local image path inside FARMEASY_ALLOWED_IMAGE_ROOT."""
        try:
            return get_service().analyze_path(
                path,
                gate_threshold=gate_threshold,
                conf_threshold=conf_threshold,
                tta=tta,
            )
        except (FileNotFoundError, PermissionError, OSError, ImageDecodeError, ValueError) as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def predict_video_path(
        path: str,
        sample_every_n_frames: int = 15,
        max_frames: int = 120,
        gate_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        tta: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Analyze a local video path by sampling frames inside FARMEASY_ALLOWED_IMAGE_ROOT."""
        try:
            resolved = Path(path).expanduser().resolve()
            allowed = settings.allowed_image_root.resolve()
            try:
                resolved.relative_to(allowed)
            except ValueError as exc:
                raise PermissionError(
                    f"video path must be inside FARMEASY_ALLOWED_IMAGE_ROOT ({allowed})"
                ) from exc
            if not resolved.exists() or not resolved.is_file():
                raise FileNotFoundError(f"video file not found: {resolved}")
            data = resolved.read_bytes()
            if len(data) > settings.max_video_upload_bytes:
                mb = settings.max_video_upload_bytes / (1024 * 1024)
                raise ValueError(f"video is too large; max upload size is {mb:.0f} MB")
            return analyze_video_bytes(
                data,
                filename=resolved.name,
                content_type=None,
                sample_every_n_frames=sample_every_n_frames,
                max_frames=max_frames,
                gate_threshold=gate_threshold,
                conf_threshold=conf_threshold,
                tta=tta,
            )
        except (FileNotFoundError, PermissionError, OSError, RuntimeError, ValueError) as exc:
            return {"error": str(exc)}

    return mcp
