"""FastAPI application for FarmEasy model inference."""

from __future__ import annotations

import contextlib
import json
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import get_settings
from .image_utils import (
    ImageDecodeError,
    ImageTooLargeError,
    decode_base64_image,
    ensure_size_limit,
    image_from_bytes,
)
from .inference import BackendConfigurationError, get_service
from .schemas import (
    Base64PredictionRequest,
    ErrorResponse,
    HealthResponse,
    MetadataResponse,
    PredictionResponse,
    VideoPredictionResponse,
)
from .video import analyze_video_bytes


settings = get_settings()
mcp_server = None
if settings.mcp_enabled:
    try:
        from .mcp_tools import create_mcp_server

        mcp_server = create_mcp_server(streamable_http_path="/")
    except ImportError:
        mcp_server = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    service = get_service()
    if settings.load_model_on_startup:
        await run_in_threadpool(service.load)
    if mcp_server is not None:
        async with mcp_server.session_manager.run():
            yield
    else:
        yield


app = FastAPI(
    title="FarmEasy Corn Disease API",
    version=__version__,
    description=(
        "FastAPI backend for FarmEasy corn leaf validation and disease "
        "classification. Use /predict from Flutter/mobile clients and /mcp "
        "from MCP-compatible AI clients."
    ),
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

if mcp_server is not None:
    app.mount("/mcp", mcp_server.streamable_http_app())


@app.get("/", tags=["service"])
def root() -> dict:
    return {
        "service": "FarmEasy Corn Disease API",
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "metadata": "/metadata",
        "predict": "/predict",
        "predict_base64": "/predict/base64",
        "predict_video": "/predict/video",
        "live_websocket": "/ws/live",
        "mcp": "/mcp" if mcp_server is not None else None,
    }


@app.get("/health", response_model=HealthResponse, tags=["service"])
def health() -> dict:
    return get_service().health()


@app.get("/health/ready", response_model=HealthResponse, tags=["service"])
async def ready() -> dict:
    try:
        await run_in_threadpool(get_service().load)
        return get_service().health()
    except BackendConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/metadata", response_model=MetadataResponse, tags=["service"])
def metadata() -> dict:
    return get_service().metadata()


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["prediction"],
    summary="Predict from a multipart image upload",
)
async def predict_upload(
    file: UploadFile = File(..., description="Image file in JPEG, PNG, WEBP, BMP, or TIFF format"),
    gate_threshold: Optional[float] = Query(None, ge=0.0, le=1.0),
    conf_threshold: Optional[float] = Query(None, ge=0.0, le=1.0),
    tta: Optional[bool] = Query(None, description="Override test-time augmentation for this request"),
) -> dict:
    if file.content_type and not (
        file.content_type.startswith("image/") or file.content_type == "application/octet-stream"
    ):
        raise HTTPException(status_code=415, detail="file must be an image")

    data = await file.read(settings.max_upload_bytes + 1)
    return await _predict_bytes(
        data,
        filename=file.filename,
        content_type=file.content_type,
        gate_threshold=gate_threshold,
        conf_threshold=conf_threshold,
        tta=tta,
    )


@app.post(
    "/predict/base64",
    response_model=PredictionResponse,
    tags=["prediction"],
    summary="Predict from a JSON base64 image payload",
)
async def predict_base64(payload: Base64PredictionRequest) -> dict:
    try:
        data = decode_base64_image(payload.image_base64)
    except ImageDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _predict_bytes(
        data,
        filename=payload.filename,
        content_type=None,
        gate_threshold=payload.gate_threshold,
        conf_threshold=payload.conf_threshold,
        tta=payload.tta,
    )


@app.post(
    "/predict/video",
    response_model=VideoPredictionResponse,
    tags=["prediction"],
    summary="Predict from an uploaded video by sampling frames",
)
async def predict_video(
    file: UploadFile = File(..., description="Video file such as MP4, MOV, AVI, or WEBM"),
    sample_every_n_frames: int = Query(15, ge=1, le=300),
    max_frames: int = Query(120, ge=1, le=1000),
    gate_threshold: Optional[float] = Query(None, ge=0.0, le=1.0),
    conf_threshold: Optional[float] = Query(None, ge=0.0, le=1.0),
    tta: Optional[bool] = Query(None, description="Override test-time augmentation for sampled frames"),
) -> dict:
    if file.content_type and not (
        file.content_type.startswith("video/") or file.content_type == "application/octet-stream"
    ):
        raise HTTPException(status_code=415, detail="file must be a video")

    data = await file.read(settings.max_video_upload_bytes + 1)
    if len(data) > settings.max_video_upload_bytes:
        mb = settings.max_video_upload_bytes / (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"video is too large; max upload size is {mb:.0f} MB")

    try:
        return await run_in_threadpool(
            analyze_video_bytes,
            data,
            filename=file.filename,
            content_type=file.content_type,
            sample_every_n_frames=sample_every_n_frames,
            max_frames=max_frames,
            gate_threshold=gate_threshold,
            conf_threshold=conf_threshold,
            tta=tta,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except BackendConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.websocket("/ws/live")
async def live_detection(websocket: WebSocket) -> None:
    """WebSocket endpoint for live frame-by-frame detection.

    The client sends JSON text frames with an image_base64 field. Each frame is
    decoded, leaf-gated, and then classified only if it is accepted as a leaf.
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                image_base64 = payload.get("image_base64")
                if not image_base64:
                    raise ValueError("image_base64 is required")
                data = decode_base64_image(image_base64)
                ensure_size_limit(data, settings.max_upload_bytes)
                image, image_info = image_from_bytes(
                    data,
                    {
                        "filename": payload.get("filename"),
                        "content_type": payload.get("content_type"),
                    },
                )
                result = await run_in_threadpool(
                    get_service().analyze_image,
                    image,
                    gate_threshold=payload.get("gate_threshold"),
                    conf_threshold=payload.get("conf_threshold"),
                    tta=payload.get("tta"),
                    image_info=image_info,
                )
                result["frame_id"] = payload.get("frame_id")
                result["client_timestamp_ms"] = payload.get("timestamp_ms")
                await websocket.send_json(result)
            except (ImageDecodeError, ImageTooLargeError, ValueError, json.JSONDecodeError) as exc:
                await websocket.send_json({"error": str(exc)})
            except BackendConfigurationError as exc:
                await websocket.send_json({"error": str(exc)})
    except WebSocketDisconnect:
        return


async def _predict_bytes(
    data: bytes,
    *,
    filename: Optional[str],
    content_type: Optional[str],
    gate_threshold: Optional[float],
    conf_threshold: Optional[float],
    tta: Optional[bool],
) -> dict:
    try:
        ensure_size_limit(data, settings.max_upload_bytes)
        image, image_info = image_from_bytes(
            data,
            {"filename": filename, "content_type": content_type},
        )
        return await run_in_threadpool(
            get_service().analyze_image,
            image,
            gate_threshold=gate_threshold,
            conf_threshold=conf_threshold,
            tta=tta,
            image_info=image_info,
        )
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ImageDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BackendConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
