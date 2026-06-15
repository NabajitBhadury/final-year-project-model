"""Shared FarmEasy model service used by HTTP routes and MCP tools."""

from __future__ import annotations

import importlib
import json
import os
import sys
import threading
import time
import uuid
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from . import __version__
from .config import Settings, get_settings


def _configure_torch_runtime() -> None:
    """Keep CPU inference responsive on small hosted containers."""
    try:
        torch = importlib.import_module("torch")
    except Exception:
        return

    try:
        torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", "1")))
        torch.set_num_interop_threads(int(os.getenv("TORCH_NUM_INTEROP_THREADS", "1")))
    except Exception:
        return


class BackendConfigurationError(RuntimeError):
    """Raised when the model bundle cannot be loaded correctly."""


class FarmEasyModelService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._farm = None
        self._predict_module = None
        self._loaded_at: str | None = None
        self._manifest = self._read_json(self.settings.ensemble_dir / "manifest.json", default={})
        self._gate_manifest = self._read_json(
            self.settings.gate_dir / "leaf_gate_manifest.json", default={}
        )

    @property
    def loaded(self) -> bool:
        return self._farm is not None

    @property
    def class_names(self) -> list[str]:
        if self.loaded:
            return list(self._farm.class_names)
        idx_to_class = self._manifest.get("idx_to_class", {})
        return [idx_to_class[str(i)] for i in range(len(idx_to_class))]

    def load(self):
        """Load torch models once and return the high-level FarmEasy object."""
        if self._farm is not None:
            return self._farm
        with self._load_lock:
            if self._farm is not None:
                return self._farm
            self._validate_bundle_files()
            self._ensure_bundle_importable()
            _configure_torch_runtime()
            try:
                farm_module = importlib.import_module("farmeasy")
                self._predict_module = importlib.import_module("predict")
                farm_cls = getattr(farm_module, "FarmEasy")
                self._farm = farm_cls(
                    ensemble_dir=str(self.settings.ensemble_dir),
                    gate_dir=str(self.settings.gate_dir),
                    models=self.settings.models,
                    tta=self.settings.tta,
                    gate_threshold=self.settings.gate_threshold,
                    conf_threshold=self.settings.conf_threshold,
                )
                self._loaded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                return self._farm
            except Exception as exc:
                raise BackendConfigurationError(f"failed to load FarmEasy model: {exc}") from exc

    def health(self) -> dict[str, Any]:
        missing = self.missing_files()
        return {
            "status": "ok" if not missing else "degraded",
            "service": "FarmEasy Corn Disease API",
            "version": __version__,
            "model_loaded": self.loaded,
            "bundle_dir": str(self.settings.bundle_dir),
            "missing_files": missing,
            "mcp_enabled": self.settings.mcp_enabled,
        }

    def metadata(self) -> dict[str, Any]:
        selected_keys = self.settings.selected_model_keys
        available_models = [item["key"] for item in self._manifest.get("models", [])]
        runtime = {
            "models": self.settings.models,
            "tta": self.settings.tta,
            "gate_threshold": self.settings.gate_threshold,
            "conf_threshold": self.settings.conf_threshold,
        }
        return {
            "service": "FarmEasy Corn Disease API",
            "version": __version__,
            "classes": self.class_names,
            "runtime": runtime,
            "bundle": {
                "bundle_dir": str(self.settings.bundle_dir),
                "ensemble_dir": str(self.settings.ensemble_dir),
                "gate_dir": str(self.settings.gate_dir),
                "loaded": self.loaded,
                "loaded_at": self._loaded_at,
                "selected_model_keys": selected_keys or available_models,
            },
            "available_models": available_models,
            "leaf_gate": {
                "timm": self._gate_manifest.get("timm"),
                "img_size": self._gate_manifest.get("img_size"),
                "threshold": self._gate_manifest.get("threshold"),
                "val_acc": self._gate_manifest.get("val_acc"),
                "val_f1": self._gate_manifest.get("val_f1"),
            },
            "mcp": {
                "enabled": self.settings.mcp_enabled,
                "mounted_path": "/mcp",
                "standalone_module": "server.mcp_server",
            },
        }

    def analyze_image(
        self,
        image: Image.Image,
        *,
        gate_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        tta: Optional[bool] = None,
        image_info: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        farm = self.load()
        if self._predict_module is None:
            self._predict_module = importlib.import_module("predict")

        req_id = request_id or uuid.uuid4().hex
        gate_thr = self.settings.gate_threshold if gate_threshold is None else gate_threshold
        conf_thr = self.settings.conf_threshold if conf_threshold is None else conf_threshold
        use_tta = self.settings.tta if tta is None else tta
        context = self._inference_lock if self.settings.serialize_inference else nullcontext()
        start = time.perf_counter()

        with context:
            rgb = image.convert("RGB")
            is_leaf, leaf_prob = farm.gate.is_leaf(rgb, threshold=gate_thr)
            if not is_leaf:
                result = {
                    "is_leaf": False,
                    "leaf_prob": round(float(leaf_prob), 4),
                    "label": None,
                    "confidence": None,
                    "status": "not_leaf",
                    "probabilities": {},
                }
            else:
                label, probs = self._predict_module.predict_pil(rgb, farm.ens, tta=use_tta)
                top = max(probs.values())
                status = "ok" if top >= conf_thr else "uncertain"
                result = {
                    "is_leaf": True,
                    "leaf_prob": round(float(leaf_prob), 4),
                    "label": label if status == "ok" else None,
                    "confidence": round(float(top), 4),
                    "status": status,
                    "probabilities": {key: round(float(value), 4) for key, value in probs.items()},
                }

        result.update(
            {
                "request_id": req_id,
                "model": {
                    "models": self.settings.models,
                    "tta": use_tta,
                    "gate_threshold": gate_thr,
                    "conf_threshold": conf_thr,
                },
                "image": image_info,
                "processing_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        )
        return result

    def analyze_path(
        self,
        path: str,
        *,
        gate_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        tta: Optional[bool] = None,
    ) -> dict[str, Any]:
        resolved = Path(path).expanduser().resolve()
        allowed = self.settings.allowed_image_root.resolve()
        if not self._is_relative_to(resolved, allowed):
            raise PermissionError(
                f"image path must be inside FARMEASY_ALLOWED_IMAGE_ROOT ({allowed})"
            )
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"image file not found: {resolved}")
        with Image.open(resolved) as img:
            rgb = img.convert("RGB")
            image_info = {
                "width": rgb.width,
                "height": rgb.height,
                "mode": rgb.mode,
                "format": img.format,
                "filename": resolved.name,
                "content_type": None,
            }
            return self.analyze_image(
                rgb,
                gate_threshold=gate_threshold,
                conf_threshold=conf_threshold,
                tta=tta,
                image_info=image_info,
            )

    def missing_files(self) -> list[str]:
        missing = []
        ensemble_manifest = self.settings.ensemble_dir / "manifest.json"
        gate_manifest = self.settings.gate_dir / "leaf_gate_manifest.json"
        for path in (ensemble_manifest, gate_manifest):
            if not path.exists():
                missing.append(str(path))

        if missing:
            return missing

        for model in self._selected_model_entries():
            ckpt = self.settings.ensemble_dir / model.get("ckpt", "")
            if not ckpt.exists():
                missing.append(str(ckpt))

        gate_ckpt = self.settings.gate_dir / self._gate_manifest.get("ckpt", "leaf_gate.pth")
        if not gate_ckpt.exists():
            missing.append(str(gate_ckpt))
        return missing

    def _validate_bundle_files(self) -> None:
        missing = self.missing_files()
        if missing:
            joined = ", ".join(missing)
            raise BackendConfigurationError(f"missing required model files: {joined}")

    def _selected_model_entries(self) -> list[dict[str, Any]]:
        models = list(self._manifest.get("models", []))
        selected = self.settings.selected_model_keys
        if selected is None:
            return models
        selected_set = set(selected)
        entries = [model for model in models if model.get("key") in selected_set]
        found = {model.get("key") for model in entries}
        missing = selected_set - found
        if missing:
            raise BackendConfigurationError(
                f"unknown model key(s): {', '.join(sorted(missing))}"
            )
        return entries

    def _ensure_bundle_importable(self) -> None:
        bundle = str(self.settings.bundle_dir)
        if bundle not in sys.path:
            sys.path.insert(0, bundle)

    @staticmethod
    def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            return default

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False


_service: FarmEasyModelService | None = None
_service_lock = threading.Lock()


def get_service() -> FarmEasyModelService:
    global _service
    if _service is not None:
        return _service
    with _service_lock:
        if _service is None:
            _service = FarmEasyModelService(get_settings())
        return _service
