"""Pydantic schemas used by the HTTP API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DiseaseStatus = Literal["ok", "not_leaf", "uncertain"]


class ImageInfo(BaseModel):
    width: int = Field(..., example=1280)
    height: int = Field(..., example=720)
    mode: str = Field(..., example="RGB")
    format: Optional[str] = Field(None, example="JPEG")
    filename: Optional[str] = Field(None, example="leaf.jpg")
    content_type: Optional[str] = Field(None, example="image/jpeg")


class RuntimeModelInfo(BaseModel):
    models: str = Field(..., example="effb3")
    tta: bool = Field(..., example=False)
    gate_threshold: float = Field(..., ge=0.0, le=1.0, example=0.5)
    conf_threshold: float = Field(..., ge=0.0, le=1.0, example=0.45)


class PredictionResponse(BaseModel):
    request_id: str = Field(..., example="cde49c7a5b7d4fd4b42c13d40964e42e")
    is_leaf: bool = Field(..., example=True)
    leaf_prob: float = Field(..., ge=0.0, le=1.0, example=0.9718)
    label: Optional[str] = Field(None, example="Gray_Leaf_Spot")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, example=0.9484)
    status: DiseaseStatus = Field(..., example="ok")
    probabilities: Dict[str, float] = Field(
        default_factory=dict,
        example={
            "Blight": 0.011,
            "Common_Rust": 0.010,
            "Gray_Leaf_Spot": 0.948,
            "Healthy": 0.015,
            "Insects_damage": 0.015,
        },
    )
    model: RuntimeModelInfo
    image: Optional[ImageInfo] = None
    processing_ms: float = Field(..., example=82.4)


class VideoFramePrediction(BaseModel):
    frame_index: int = Field(..., example=30)
    timestamp_ms: float = Field(..., example=1000.0)
    prediction: PredictionResponse


class VideoPredictionResponse(BaseModel):
    request_id: str = Field(..., example="a85f00ddba5b4b978ad9936d51e71009")
    filename: Optional[str] = Field(None, example="field_scan.mp4")
    content_type: Optional[str] = Field(None, example="video/mp4")
    total_frames: Optional[int] = Field(None, example=300)
    fps: Optional[float] = Field(None, example=30.0)
    duration_sec: Optional[float] = Field(None, example=10.0)
    sample_every_n_frames: int = Field(..., example=15)
    max_frames: int = Field(..., example=120)
    sampled_frames: int = Field(..., example=20)
    status_counts: Dict[str, int] = Field(..., example={"ok": 18, "not_leaf": 1, "uncertain": 1})
    label_counts: Dict[str, int] = Field(..., example={"Healthy": 12, "Common_Rust": 6})
    frames: List[VideoFramePrediction]
    processing_ms: float = Field(..., example=1750.5)


class Base64PredictionRequest(BaseModel):
    image_base64: str = Field(
        ...,
        description="Raw base64 image bytes or a data URL like data:image/jpeg;base64,...",
    )
    filename: Optional[str] = Field(None, example="leaf.jpg")
    gate_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, example=0.5)
    conf_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, example=0.45)
    tta: Optional[bool] = Field(None, example=False)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = Field(..., example="ok")
    service: str = Field(..., example="FarmEasy Corn Disease API")
    version: str = Field(..., example="1.0.0")
    model_loaded: bool = Field(..., example=True)
    bundle_dir: str
    missing_files: List[str] = Field(default_factory=list)
    mcp_enabled: bool = Field(..., example=True)


class MetadataResponse(BaseModel):
    service: str
    version: str
    classes: List[str]
    runtime: RuntimeModelInfo
    bundle: Dict[str, Any]
    available_models: List[str]
    leaf_gate: Dict[str, Any]
    mcp: Dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str = Field(..., example="could not read image")
