"""Runtime configuration for the FarmEasy backend.

The backend intentionally uses environment variables instead of a settings
framework so it stays easy to run on a laptop, VPS, or Flutter dev machine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_CANDIDATES = (
    PROJECT_ROOT / "FarmEasy_Integration_Bundle",
    PROJECT_ROOT / "model",
)


def _default_bundle_dir() -> Path:
    for candidate in DEFAULT_BUNDLE_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_BUNDLE_CANDIDATES[0]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float") from exc


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _path_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default.resolve()


def _bounded_probability(name: str, value: float) -> float:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


@dataclass(frozen=True)
class Settings:
    project_root: Path
    bundle_dir: Path
    ensemble_dir: Path
    gate_dir: Path
    allowed_image_root: Path
    host: str
    port: int
    reload: bool
    models: str
    tta: bool
    gate_threshold: float
    conf_threshold: float
    max_upload_mb: int
    max_video_upload_mb: int
    cors_origins: tuple[str, ...]
    load_model_on_startup: bool
    serialize_inference: bool
    mcp_enabled: bool
    mcp_host: str
    mcp_port: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_video_upload_bytes(self) -> int:
        return self.max_video_upload_mb * 1024 * 1024

    @property
    def selected_model_keys(self) -> list[str] | None:
        if self.models.strip().lower() == "all":
            return None
        return [key.strip() for key in self.models.split(",") if key.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    bundle_dir = _path_env("FARMEASY_BUNDLE_DIR", _default_bundle_dir())
    ensemble_dir = _path_env("FARMEASY_ENSEMBLE_DIR", bundle_dir / "ensemble_out_v2")
    gate_dir = _path_env("FARMEASY_GATE_DIR", bundle_dir / "leaf_gate_out")

    gate_threshold = _bounded_probability(
        "FARMEASY_GATE_THRESHOLD", _float_env("FARMEASY_GATE_THRESHOLD", 0.5)
    )
    conf_threshold = _bounded_probability(
        "FARMEASY_CONF_THRESHOLD", _float_env("FARMEASY_CONF_THRESHOLD", 0.45)
    )

    return Settings(
        project_root=PROJECT_ROOT,
        bundle_dir=bundle_dir,
        ensemble_dir=ensemble_dir,
        gate_dir=gate_dir,
        allowed_image_root=_path_env("FARMEASY_ALLOWED_IMAGE_ROOT", PROJECT_ROOT),
        host=os.getenv("FARMEASY_HOST", "0.0.0.0"),
        port=_int_env("FARMEASY_PORT", 8000),
        reload=_bool_env("FARMEASY_RELOAD", False),
        models=os.getenv("FARMEASY_MODELS", "effb3"),
        tta=_bool_env("FARMEASY_TTA", False),
        gate_threshold=gate_threshold,
        conf_threshold=conf_threshold,
        max_upload_mb=_int_env("FARMEASY_MAX_UPLOAD_MB", 10),
        max_video_upload_mb=_int_env("FARMEASY_MAX_VIDEO_UPLOAD_MB", 100),
        cors_origins=_csv_env("FARMEASY_CORS_ORIGINS", ("*",)),
        load_model_on_startup=_bool_env("FARMEASY_LOAD_ON_STARTUP", True),
        serialize_inference=_bool_env("FARMEASY_SERIALIZE_INFERENCE", True),
        mcp_enabled=_bool_env("FARMEASY_MCP_ENABLED", True),
        mcp_host=os.getenv("FARMEASY_MCP_HOST", "127.0.0.1"),
        mcp_port=_int_env("FARMEASY_MCP_PORT", 8001),
    )
