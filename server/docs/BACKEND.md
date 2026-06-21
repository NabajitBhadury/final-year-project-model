# FarmEasy Backend — Complete Documentation

> FastAPI + MCP backend that serves the **FarmEasy corn leaf disease classifier** (leaf-gate + 5-class ensemble) to Flutter/mobile apps and MCP-compatible AI clients.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Runtime Requirements](#4-runtime-requirements)
5. [Installation & Setup](#5-installation--setup)
6. [Environment Variables](#6-environment-variables)
7. [Configuration Module (`config.py`)](#7-configuration-module-configpy)
8. [Model Bundle & How the Backend Connects to the Model](#8-model-bundle--how-the-backend-connects-to-the-model)
9. [Inference Service (`inference.py`)](#9-inference-service-inferencepy)
10. [HTTP API Layer (`app.py`)](#10-http-api-layer-apppy)
11. [WebSocket Live Detection](#11-websocket-live-detection)
12. [MCP Server Layer (`mcp_tools.py`, `mcp_server.py`)](#12-mcp-server-layer-mcp_toolspymcp_serverpy)
13. [Image Utilities (`image_utils.py`)](#13-image-utilities-image_utilspy)
14. [Video Pipeline (`video.py`)](#14-video-pipeline-videopy)
15. [Schemas / API Contracts (`schemas.py`)](#15-schemas--api-contracts-schemaspy)
16. [Request → Response Flow](#16-request--response-flow)
17. [API Endpoint Reference](#17-api-endpoint-reference)
18. [Response Contract & Status Semantics](#18-response-contract--status-semantics)
19. [Error Handling](#19-error-handling)
20. [Threading, Locks & Concurrency](#20-threading-locks--concurrency)
21. [Docker & Deployment](#21-docker--deployment)
22. [Flutter Client Integration](#22-flutter-client-integration)
23. [Troubleshooting & Gotchas](#23-troubleshooting--gotchas)
24. [Glossary](#24-glossary)

---

## 1. Overview

- **Purpose**: Exposes the trained corn leaf disease model (PyTorch + timm) over both REST/WebSocket and MCP transports.
- **Two-stage pipeline**:
  1. **Leaf Gate** (MobileNetV3) — decides whether the input is a corn leaf.
  2. **Disease Classifier** (Ensemble of EfficientNet, ConvNeXt, DenseNet, ResNet50) — if leaf, classifies into 5 classes.
- **5 output classes**: `Blight`, `Common_Rust`, `Gray_Leaf_Spot`, `Healthy`, `Insects_damage`.
- **Default model**: `effb3` (lightweight, 98.1% accuracy, fast on CPU).
- **Service name**: `FarmEasy Corn Disease API` (`server.__version__ = "1.0.0"`).

---

## 2. Tech Stack

### 2.1 Language & Runtime
- **Python**: 3.10+ (Dockerfile uses `python:3.11-slim`).
- **Concurrency**: asyncio + threadpool offloading for CPU-bound inference.

### 2.2 Web Framework
- **FastAPI** `>=0.115` — REST API, WebSocket support, auto OpenAPI docs.
- **Uvicorn[standard]** `>=0.30` — ASGI server entry point.
- **python-multipart** `>=0.0.9` — multipart form parsing.
- **Pydantic** — request/response validation (transitive via FastAPI).

### 2.3 ML / Computer Vision
- **PyTorch** `>=2.2` (Docker pins `torch==2.12.0` CPU build).
- **torchvision** `>=0.17`.
- **timm** `>=1.0` — model architectures (EfficientNet, ConvNeXt, DenseNet, ResNet, MobileNetV3).
- **Pillow** `>=10.0` — image loading, EXIF transpose, RGB conversion.
- **NumPy** `>=1.26`.
- **opencv-python-headless** `>=4.9` — video frame decoding (headless = no GUI dependency).

### 2.4 MCP Layer
- **mcp[cli]** `>=1.27,<2` — Model Context Protocol server (`FastMCP`) with Streamable HTTP + stdio transports.

### 2.5 Containerization
- **Docker** — multi-stage-free single-stage image based on `python:3.11-slim`.
- OS packages: `libglib2.0-0`, `libgomp1` (OpenCV runtime).

### 2.6 Optional / Client
- **Flutter** (mobile client) — uses `http` and `web_socket_channel` packages.
- **MCP Inspector / Claude Desktop** — for MCP testing.

---

## 3. Project Structure

```
final_year_project/
├── server/                        # FastAPI + MCP backend
│   ├── __init__.py                # Package marker, __version__ = "1.0.0"
│   ├── __main__.py                # Entry: `python -m server`
│   ├── main.py                    # Uvicorn launcher with CLI args
│   ├── app.py                     # FastAPI app, routes, WebSocket, MCP mount
│   ├── config.py                  # Settings dataclass + env loading
│   ├── inference.py               # FarmEasyModelService (model loader + analyze)
│   ├── image_utils.py             # decode base64 / bytes → PIL.Image
│   ├── video.py                   # OpenCV frame sampling + inference
│   ├── schemas.py                 # Pydantic models (request/response)
│   ├── mcp_tools.py               # MCP tool definitions
│   ├── mcp_server.py              # Standalone MCP CLI (stdio / streamable-http)
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Container build
│   ├── .env.example               # Sample env vars
│   ├── README.md                  # Quick start
│   ├── DEPLOYMENT.md              # Docker/VPS deployment
│   └── docs/
│       └── API.md                 # Existing API reference
│
├── model/                         # Inference bundle (the "ML package")
│   ├── farmeasy.py                # High-level API class `FarmEasy`
│   ├── predict.py                 # Ensemble loader + predict_pil
│   ├── leaf_gate.py               # MobileNetV3 leaf gate
│   ├── live_video.py              # Optional desktop live camera
│   ├── serve.py                   # Optional standalone REST (legacy)
│   ├── mcp_server.py              # Optional standalone MCP (legacy)
│   ├── export_onnx.py             # ONNX export for mobile
│   ├── ensemble_out_v2/           # Disease classifier weights
│   │   ├── manifest.json          # Model registry (effb3, effb4, convnext, …)
│   │   └── effb3_best.pth         # Default checkpoint
│   └── leaf_gate_out/             # Leaf gate weights
│       ├── leaf_gate_manifest.json
│       └── leaf_gate.pth
│
└── farm_easy_app/                 # Flutter client (out of scope here)
```

---

## 4. Runtime Requirements

### 4.1 Hardware (CPU-only deployment)
- **RAM**: ≥ 1–2 GB minimum; 2+ GB recommended for concurrent video predictions.
- **CPU**: any modern x86_64 / arm64 (Docker base = `python:3.11-slim`).
- **Disk**: ~600 MB for Python image + PyTorch + OpenCV + ~50 MB model weights.
- **GPU**: optional — PyTorch auto-uses CUDA if present; otherwise CPU.

### 4.2 System Libraries (Docker handles)
- `libglib2.0-0`, `libgomp1` (OpenCV transitive deps).

### 4.3 Network
- Port `8000` (HTTP/WebSocket), `8001` (standalone MCP HTTP, optional).

---

## 5. Installation & Setup

### 5.1 Local Dev

```bash
# From project root
python -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

# Run API
python -m server --host 0.0.0.0 --port 8000
```

### 5.2 Docker

```bash
docker build -f server/Dockerfile -t farmeasy-backend .
docker run --rm -p 8000:8000 farmeasy-backend
```

### 5.3 Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata
```

Open `http://localhost:8000/docs` (Swagger UI) or `/redoc`.

---

## 6. Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FARMEASY_HOST` | `0.0.0.0` | HTTP bind host |
| `FARMEASY_PORT` | `8000` | HTTP port |
| `FARMEASY_RELOAD` | `0` | Uvicorn auto-reload (dev) |
| `FARMEASY_BUNDLE_DIR` | auto-detect (`FarmEasy_Integration_Bundle/` → `model/`) | Root of inference bundle |
| `FARMEASY_ENSEMBLE_DIR` | `<bundle>/ensemble_out_v2` | Disease classifier dir |
| `FARMEASY_GATE_DIR` | `<bundle>/leaf_gate_out` | Leaf gate dir |
| `FARMEASY_MODELS` | `effb3` | `effb3`, comma list, or `all` |
| `FARMEASY_TTA` | `0` | Test-time augmentation (slower) |
| `FARMEASY_GATE_THRESHOLD` | `0.5` | Min P(leaf) to accept |
| `FARMEASY_CONF_THRESHOLD` | `0.45` | Min top-class prob to return label |
| `FARMEASY_LOAD_ON_STARTUP` | `1` | Eager-load model on lifespan startup |
| `FARMEASY_SERIALIZE_INFERENCE` | `1` | Single inference lock (CPU safety) |
| `FARMEASY_MAX_UPLOAD_MB` | `10` | Max image upload |
| `FARMEASY_MAX_VIDEO_UPLOAD_MB` | `100` | Max video upload |
| `FARMEASY_CORS_ORIGINS` | `*` | Comma-separated origins |
| `FARMEASY_MCP_ENABLED` | `1` | Mount `/mcp` and create standalone MCP |
| `FARMEASY_MCP_HOST` | `127.0.0.1` | Standalone MCP HTTP host |
| `FARMEASY_MCP_PORT` | `8001` | Standalone MCP HTTP port |
| `FARMEASY_ALLOWED_IMAGE_ROOT` | project root | Sandbox for MCP path-based tools |
| `TORCH_NUM_THREADS` | `1` | PyTorch intra-op threads (CPU) |
| `TORCH_NUM_INTEROP_THREADS` | `1` | PyTorch inter-op threads |

---

## 7. Configuration Module (`config.py`)

- **Frozen dataclass** `Settings` holding all runtime options.
- **`@lru_cache(maxsize=1)`** on `get_settings()` — singleton loader.
- **`_bool_env`, `_float_env`, `_int_env`, `_csv_env`, `_path_env`** — typed env parsers with validation.
- **`_bounded_probability`** — enforces `0 ≤ x ≤ 1` for thresholds.
- **Auto-detect bundle directory**: scans `FarmEasy_Integration_Bundle/` then `model/` in project root.
- **Computed properties**:
  - `max_upload_bytes`, `max_video_upload_bytes` (MB → bytes).
  - `selected_model_keys` — `None` means "all", else a list of keys from `FARMEASY_MODELS`.

---

## 8. Model Bundle & How the Backend Connects to the Model

### 8.1 Bundle Layout

```
model/
├── farmeasy.py            # High-level `FarmEasy` class
├── predict.py             # `load_ensemble()`, `predict_pil()`
├── leaf_gate.py           # `load_leaf_gate()`
├── ensemble_out_v2/
│   ├── manifest.json      # Registry: keys, timm names, ckpts, mean/std, img_size
│   └── effb3_best.pth     # Checkpoint(s)
└── leaf_gate_out/
    ├── leaf_gate_manifest.json  # MobileNetV3 config
    └── leaf_gate.pth            # Leaf gate weights
```

### 8.2 `farmeasy.FarmEasy` — the integration point

- **Constructor** (`model/farmeasy.py:34`):
  - Calls `predict.load_ensemble(ensemble_dir, keys=…)` — reads `manifest.json`, instantiates each timm model, loads its `.pth`.
  - Calls `leaf_gate.load_leaf_gate(gate_dir)` — instantiates MobileNetV3 and loads `leaf_gate.pth`.
  - Stores `tta`, `gate_threshold`, `conf_threshold`, `class_names`.
- **`analyze(pil_img)`** (`model/farmeasy.py:49`):
  - Converts to RGB.
  - Calls `gate.is_leaf(img, threshold)` → `(is_leaf, leaf_prob)`.
  - If not leaf → returns `not_leaf` status.
  - Else calls `predict.predict_pil(img, ens, tta)` → `(label, probs_dict)`.
  - Returns dict with `is_leaf`, `leaf_prob`, `label`, `confidence`, `status`, `probabilities`.

### 8.3 Connection Sequence (backend boot)

1. `app.py` lifespan calls `get_service()` → constructs `FarmEasyModelService(settings)`.
2. Service reads `ensemble_out_v2/manifest.json` and `leaf_gate_out/leaf_gate_manifest.json` (metadata only).
3. If `FARMEASY_LOAD_ON_STARTUP=1`, calls `service.load()` in a threadpool.
4. `service.load()`:
   - Acquires `_load_lock`.
   - Calls `_validate_bundle_files()` — ensures manifests + every selected checkpoint + leaf gate ckpt exist.
   - Calls `_ensure_bundle_importable()` — prepends `FARMEASY_BUNDLE_DIR` to `sys.path`.
   - Calls `_configure_torch_runtime()` — sets `torch.set_num_threads(1)` for small containers.
   - `importlib.import_module("farmeasy")` and `importlib.import_module("predict")`.
   - `farm_cls(ensemble_dir, gate_dir, models, tta, gate_threshold, conf_threshold)` → real `FarmEasy()` instance.
   - Stores `_loaded_at` timestamp; the singleton `farm` instance is reused for every request.

### 8.4 Inference Call Chain

```
HTTP request
  └─> app.py route handler
       └─> FarmEasyModelService.analyze_image(pil, ...)
            ├─> farm.gate.is_leaf(rgb, threshold)   [MobileNetV3]
            ├─> if not leaf → return "not_leaf"
            └─> predict.predict_pil(rgb, farm.ens, tta)
                 └─> for each timm model: forward pass → softmax
                      └─> weighted-average → argmax → {class: prob}
```

### 8.5 Available Models (from `manifest.json`)

| Key | timm name | Img size | Notes |
| --- | --- | --- | --- |
| `effb3` | `tf_efficientnet_b3.ns_jft_in1k` | 256 | **Default**, ships in repo |
| `effb4` | `tf_efficientnet_b4.ns_jft_in1k` | 256 | Not shipped |
| `convnext` | `convnext_tiny.fb_in22k_ft_in1k` | 256 | Not shipped |
| `densenet` | `densenet121.ra_in1k` | 256 | Not shipped |
| `resnet50` | `resnet50.a1_in1k` | 256 | Not shipped |

> Setting `FARMEASY_MODELS=all` requires **all five** checkpoints; only `effb3_best.pth` is currently included.

---

## 9. Inference Service (`inference.py`)

- **`BackendConfigurationError`** — raised on bundle/load failures.
- **`FarmEasyModelService`** — thread-safe wrapper around `FarmEasy`:
  - **Locks**:
    - `_load_lock` — guards one-time model load.
    - `_inference_lock` — serializes CPU inference when `FARMEASY_SERIALIZE_INFERENCE=1`.
  - **`load()`** — idempotent; loads model bundle on first call.
  - **`health()`** — returns status, model_loaded flag, missing files.
  - **`metadata()`** — returns classes, runtime, bundle info, leaf gate stats, MCP info.
  - **`analyze_image(pil, ...)`** — the core path:
    - Resolves thresholds (per-request overrides → settings defaults).
    - Inside `_inference_lock` (or `nullcontext` if disabled):
      - `is_leaf, leaf_prob = farm.gate.is_leaf(rgb, gate_thr)`
      - If leaf: `label, probs = predict.predict_pil(rgb, farm.ens, tta)`
      - Computes `status = "ok" if top >= conf_thr else "uncertain"`.
    - Decorates with `request_id`, model info, image info, `processing_ms`.
  - **`analyze_path(path, ...)`** — sandboxed local file path (must be inside `FARMEASY_ALLOWED_IMAGE_ROOT`).
  - **`missing_files()`** — diffs manifest vs filesystem.
  - **`_selected_model_entries()`** — filters `manifest.models` by `FARMEASY_MODELS`.
- **Module-level singleton** `_service` + `_service_lock` — first call constructs it lazily.

---

## 10. HTTP API Layer (`app.py`)

- **FastAPI app** titled "FarmEasy Corn Disease API", lifespan-managed.
- **CORS**: `allow_origins=settings.cors_origins`, methods `GET/POST/DELETE/OPTIONS`, exposes `Mcp-Session-Id`.
- **Error responses**: 400, 413, 415, 500 mapped to `ErrorResponse` schema.
- **Endpoints** (all under `/`):
  - `GET /` — service banner + endpoint URLs.
  - `GET /health` — liveness (no inference).
  - `GET /health/ready` — readiness (forces model load).
  - `GET /metadata` — classes, runtime, bundle, MCP info.
  - `POST /predict` — multipart image upload.
  - `POST /predict/base64` — JSON with base64 image.
  - `POST /predict/video` — multipart video upload (frame-sampled).
  - `WS /ws/live` — WebSocket frame-by-frame.
  - `/mcp` — mounted Streamable HTTP MCP server (if enabled).
- **`_predict_bytes()` helper** — shared size-check → decode → `analyze_image` in threadpool, with typed exception mapping to HTTP errors.

---

## 11. WebSocket Live Detection

- **Endpoint**: `ws://<host>:<port>/ws/live`.
- **Client → server**: JSON `{ frame_id, timestamp_ms, filename?, content_type?, image_base64, gate_threshold?, conf_threshold?, tta? }`.
- **Server → client**: prediction dict (same contract as `/predict`) plus echoed `frame_id` and `client_timestamp_ms`.
- **Error frames**: `{"error": "<message>"}` for decode/size/JSON/value errors.
- **Use case**: Flutter camera stream — encode each frame as JPEG base64 and push in real time.

---

## 12. MCP Server Layer (`mcp_tools.py`, `mcp_server.py`)

### 12.1 Tools (mounted at `/mcp` and as standalone)

| Tool | Args | Returns |
| --- | --- | --- |
| `model_metadata` | — | Service metadata dict |
| `predict_image_base64` | `image_base64`, `filename?`, `gate_threshold?`, `conf_threshold?`, `tta?` | Prediction dict |
| `predict_image_path` | `path` (must be inside `FARMEASY_ALLOWED_IMAGE_ROOT`), thresholds, tta | Prediction dict |
| `predict_video_path` | `path` (sandboxed), `sample_every_n_frames`, `max_frames`, thresholds, tta | Video prediction dict |

### 12.2 Transports
- **Streamable HTTP** (mounted): `http://localhost:8000/mcp` (stateless_http, JSON responses, session manager lifespan).
- **stdio**: `python -m server.mcp_server --transport stdio`.
- **Standalone HTTP**: `python -m server.mcp_server --transport streamable-http` → `http://127.0.0.1:8001/mcp`.

### 12.3 Security
- Path-based tools are sandboxed under `FARMEASY_ALLOWED_IMAGE_ROOT` (default = project root).
- Errors are returned as `{"error": "..."}` rather than raised, so MCP clients see a stable contract.

---

## 13. Image Utilities (`image_utils.py`)

- **`ImageDecodeError`** — base64 or bytes can't decode.
- **`ImageTooLargeError`** — exceeds `max_bytes`.
- **`ensure_size_limit(data, max_bytes)`** — raises `ImageTooLargeError` if too big.
- **`decode_base64_image(payload)`** — accepts raw base64 **or** `data:image/...;base64,…` URLs; strips whitespace; strict-decode.
- **`image_from_bytes(data, metadata)`**:
  - Opens via PIL `Image.open(BytesIO)`.
  - Applies `ImageOps.exif_transpose` (fixes phone camera orientation).
  - Converts to RGB.
  - Returns `(rgb_image, info_dict)` with width/height/mode/format/filename/content_type.

---

## 14. Video Pipeline (`video.py`)

- **Endpoint**: `POST /predict/video`.
- **Query params**: `sample_every_n_frames` (default 15), `max_frames` (default 120), optional overrides.
- **Steps** (`analyze_video_bytes`):
  1. Write upload bytes to a temp file (suffix inferred from filename).
  2. `cv2.VideoCapture(temp_path)`; verify it opens.
  3. Read FPS, total frames, duration.
  4. Loop up to `max_frames`, sample every Nth frame:
     - `cv2.cvtColor(BGR → RGB)` → `Image.fromarray`.
     - Call `service.analyze_image(...)` (still leaf-gated first).
     - Tally `status_counts`, `label_counts`.
     - Append `{frame_index, timestamp_ms, prediction}`.
  5. Cleanup `capture.release()` and `os.unlink(temp_path)`.
- **Requires** `opencv-python-headless` — import error → `RuntimeError` → HTTP 500.
- **Response**: per-frame predictions + aggregate counts + `processing_ms`.

---

## 15. Schemas / API Contracts (`schemas.py`)

- **`DiseaseStatus`** = `Literal["ok", "not_leaf", "uncertain"]`.
- **`PredictionResponse`** — full contract with examples.
- **`VideoPredictionResponse`** — aggregates + frames list.
- **`Base64PredictionRequest`** — JSON body for `/predict/base64`.
- **`HealthResponse`**, **`MetadataResponse`**, **`ErrorResponse`** — supporting contracts.
- All fields use `Field(...)` with `example`/`ge`/`le` for OpenAPI docs.

---

## 16. Request → Response Flow

```
Client (Flutter / curl / MCP)
  │
  ├─ HTTP POST /predict  ──> app.predict_upload()
  │                              ├─ read UploadFile (size-capped)
  │                              ├─ _predict_bytes()
  │                              │    ├─ ensure_size_limit()
  │                              │    ├─ image_from_bytes()  [EXIF → RGB]
  │                              │    └─ run_in_threadpool(service.analyze_image)
  │                              │         ├─ farm.gate.is_leaf()
  │                              │         └─ predict.predict_pil()  (if leaf)
  │                              └─ return PredictionResponse
  │
  ├─ WS /ws/live         ──> app.live_detection()
  │                              ├─ receive_text() → JSON
  │                              ├─ decode_base64_image()
  │                              ├─ ensure_size_limit()
  │                              ├─ image_from_bytes()
  │                              ├─ run_in_threadpool(service.analyze_image)
  │                              └─ send_json(result + frame_id + timestamp)
  │
  └─ MCP tool call       ──> mcp_tools.<tool>()
                                 ├─ decode + sandbox check (path tools)
                                 └─ service.analyze_image / analyze_path / video
```

---

## 17. API Endpoint Reference

### 17.1 `GET /`
Returns service banner + endpoint map.

### 17.2 `GET /health`
- **Purpose**: liveness only.
- **Returns**: `{status, service, version, model_loaded, bundle_dir, missing_files, mcp_enabled}`.

### 17.3 `GET /health/ready`
- **Purpose**: forces `service.load()` then returns health. Use in container readiness probes.

### 17.4 `GET /metadata`
- **Returns**: classes, runtime, bundle info, leaf gate stats, MCP info, available model keys.

### 17.5 `POST /predict`
- **Body**: `multipart/form-data` with field `file` (image: JPEG/PNG/WEBP/BMP/TIFF).
- **Query**: `gate_threshold?`, `conf_threshold?`, `tta?`.
- **Errors**: 415 (wrong content type), 413 (too large), 400 (decode), 500 (bundle).

### 17.6 `POST /predict/base64`
- **Body**: JSON `{"image_base64": "...", "filename": "...", ...}`.
- **Accepts**: raw base64 or `data:image/...;base64,…` URLs.

### 17.7 `POST /predict/video`
- **Body**: multipart `file` (MP4/MOV/AVI/WEBM).
- **Query**: `sample_every_n_frames=15`, `max_frames=120`, overrides.

### 17.8 `WS /ws/live`
- See [WebSocket Live Detection](#11-websocket-live-detection).

### 17.9 `/mcp` (Streamable HTTP MCP)
- See [MCP Server Layer](#12-mcp-server-layer-mcp_toolspymcp_serverpy).

---

## 18. Response Contract & Status Semantics

```json
{
  "request_id": "uuid",
  "is_leaf": true,
  "leaf_prob": 0.9718,
  "label": "Gray_Leaf_Spot",
  "confidence": 0.9484,
  "status": "ok",
  "probabilities": {
    "Blight": 0.011, "Common_Rust": 0.010, "Gray_Leaf_Spot": 0.948,
    "Healthy": 0.015, "Insects_damage": 0.015
  },
  "model": {"models": "effb3", "tta": false, "gate_threshold": 0.5, "conf_threshold": 0.45},
  "image": {"width": 1280, "height": 720, "mode": "RGB", "format": "JPEG", "filename": "leaf.jpg", "content_type": "image/jpeg"},
  "processing_ms": 82.4
}
```

| `status` | Meaning | `label` | `confidence` |
| --- | --- | --- | --- |
| `ok` | Leaf accepted and top class ≥ `conf_threshold` | class name | float |
| `not_leaf` | Leaf gate rejected the image | `null` | `null` |
| `uncertain` | Leaf, but top class < `conf_threshold` | `null` | float (top) |

> **Always leaf-gate first.** The disease classifier is **only** invoked when `is_leaf=true`. This applies to images, video frames, WebSocket frames, and MCP image tools.

---

## 19. Error Handling

| HTTP | When |
| --- | --- |
| `400` | Invalid base64, unreadable image, bad video query |
| `413` | Image > `FARMEASY_MAX_UPLOAD_MB` or video > `FARMEASY_MAX_VIDEO_UPLOAD_MB` |
| `415` | Multipart `content_type` not image/video |
| `500` | Missing bundle files, failed model load, OpenCV import error |

MCP errors are returned as `{"error": "<msg>"}` instead of HTTP codes.

---

## 20. Threading, Locks & Concurrency

- **Model load**: `_load_lock` ensures single load.
- **Inference**: `_inference_lock` (if `FARMEASY_SERIALIZE_INFERENCE=1`) prevents PyTorch CPU contention; safe for small containers.
- **Threadpool offloading**: `starlette.concurrency.run_in_threadpool` keeps the event loop responsive during CPU-bound inference.
- **Torch runtime**: `torch.set_num_threads(1)`, `torch.set_num_interop_threads(1)` by default; tune via env if you have cores to spare.

---

## 21. Docker & Deployment

### 21.1 Image Build
- Base: `python:3.11-slim`.
- PyTorch installed from CPU wheel index (`https://download.pytorch.org/whl/cpu`), pinned to `torch==2.12.0 torchvision==0.27.0`.
- Other deps from `server/requirements.txt`.
- Copies `model/` and `server/` into `/app/`.
- Exposes port `8000`.
- CMD honors host-injected `PORT`.

### 21.2 Host Settings (VPS / Render / Railway / Fly.io)
- Build context: project root; Dockerfile path: `server/Dockerfile`.
- Recommended env: `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `TORCH_NUM_THREADS=1`, etc. (set in Dockerfile).
- Health check path: `/health` (or `/health/ready` for stronger guarantee).

### 21.3 HTTPS
- Put Nginx/Caddy in front of the container, proxy to `http://127.0.0.1:8000`.

---

## 22. Flutter Client Integration

- **Config**: `farm_easy_app/lib/core/app_constants.dart` reads `FARMEASY_API_BASE_URL` via `--dart-define`.
- **Multipart**: `package:http` `MultipartRequest`.
- **WebSocket**: `package:web_socket_channel`.
- **Localhost quirks**:
  - Android emulator → `http://10.0.2.2:8000`.
  - Physical device → LAN IP, run backend with `--host 0.0.0.0`.
- See `server/docs/API.md` for full Dart snippets.

---

## 23. Troubleshooting & Gotchas

- **`/predict` returns 500 / `missing required model files`** → checkpoints missing; only `effb3_best.pth` ships. Use `FARMEASY_MODELS=effb3` (default) or ship the others.
- **`BackendConfigurationError: failed to load FarmEasy model`** → torch/timm install issue or bad checkpoint. Check `pip install` output.
- **PyTorch CPU slowness on small VPS** → keep `TORCH_NUM_THREADS=1`; consider `FARMEASY_MODELS=effb3` (fastest).
- **`/predict/video` 500 with "video analysis requires opencv-python-headless"** → install full requirements.
- **`is_leaf=false` for valid leaves** → lower `FARMEASY_GATE_THRESHOLD`.
- **`status="uncertain"` for clear diseases** → lower `FARMEASY_CONF_THRESHOLD`.
- **`FARMEASY_MODELS=all` fails on boot** → missing checkpoint(s); verify with `/health` `missing_files`.
- **WebSocket frame rejected** → ensure JSON includes `image_base64`; frame must be ≤ `FARMEASY_MAX_UPLOAD_MB`.
- **EXIF orientation wrong** → `image_utils.image_from_bytes` already applies `ImageOps.exif_transpose`.
- **CORS errors from Flutter web** → set `FARMEASY_CORS_ORIGINS` explicitly (not `*` if using credentials).

---

## 24. Glossary

- **Leaf Gate** — binary MobileNetV3 classifier: "is this a corn leaf?" (val F1 = 1.00).
- **Ensemble** — soft-vote of 5 timm models for disease classification (98.9% test acc).
- **TTA** — test-time augmentation (horizontal/vertical flips) for a small accuracy boost at 2× compute.
- **`manifest.json`** — JSON registry of model checkpoints, preprocessing params, class maps.
- **Streamable HTTP MCP** — MCP transport that speaks HTTP + JSON-RPC over a single endpoint (`/mcp`).
- **Sandbox** — `FARMEASY_ALLOWED_IMAGE_ROOT` restricts MCP `predict_*_path` tools to a directory tree.
- **processing_ms** — wall-clock inference time measured inside `service.analyze_image`.

---

## Appendix A — File-by-File Cheat Sheet

| File | Responsibility |
| --- | --- |
| `server/__init__.py` | Package marker + `__version__` |
| `server/__main__.py` | `python -m server` → `main()` |
| `server/main.py` | Uvicorn launcher + CLI args |
| `server/app.py` | FastAPI app, routes, WebSocket, MCP mount, lifespan |
| `server/config.py` | `Settings` dataclass + env loading (cached) |
| `server/inference.py` | `FarmEasyModelService`, locks, `analyze_image`/`analyze_path` |
| `server/image_utils.py` | base64 + bytes → PIL.Image + size checks |
| `server/video.py` | OpenCV frame sampling + per-frame inference |
| `server/schemas.py` | Pydantic request/response models |
| `server/mcp_tools.py` | `FastMCP` server factory + 4 tools |
| `server/mcp_server.py` | Standalone MCP CLI (stdio / streamable-http) |
| `server/requirements.txt` | Python deps |
| `server/Dockerfile` | Container image |
| `server/.env.example` | Sample env vars |
| `model/farmeasy.py` | `FarmEasy` high-level class (the integration point) |
| `model/predict.py` | Ensemble loader + `predict_pil` |
| `model/leaf_gate.py` | MobileNetV3 leaf gate loader + `is_leaf` |
| `model/ensemble_out_v2/manifest.json` | Model registry |
| `model/leaf_gate_out/leaf_gate_manifest.json` | Leaf gate config |

---

## Appendix B — Quick curl Recipes

```bash
# Health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# Metadata
curl http://localhost:8000/metadata

# Image (multipart)
curl -F "file=@leaf.jpg" http://localhost:8000/predict

# Image (base64)
curl -X POST http://localhost:8000/predict/base64 \
  -H "Content-Type: application/json" \
  -d '{"filename":"leaf.jpg","image_base64":"<BASE64>"}'

# Video
curl -F "file=@scan.mp4" \
  "http://localhost:8000/predict/video?sample_every_n_frames=15&max_frames=120"
```

---

## Appendix C — Run Modes Summary

| Mode | Command | Endpoint |
| --- | --- | --- |
| REST + WebSocket + MCP mounted | `python -m server --host 0.0.0.0 --port 8000` | `http://host:8000/{docs, predict, ws/live, mcp}` |
| Standalone MCP (stdio) | `python -m server.mcp_server --transport stdio` | local stdio |
| Standalone MCP (HTTP) | `python -m server.mcp_server --transport streamable-http` | `http://127.0.0.1:8001/mcp` |
| Docker | `docker build -f server/Dockerfile -t farmeasy-backend . && docker run -p 8000:8000 farmeasy-backend` | `http://localhost:8000` |

---

**End of documentation.**