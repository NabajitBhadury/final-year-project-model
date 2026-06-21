# FarmEasy — Complete App Documentation

> A Flutter-based mobile application that combines a custom corn-leaf disease detection ML backend with a conversational AI assistant, giving farmers an end-to-end tool for crop health assessment and on-demand agricultural guidance.

---

## Table of Contents

1. [App Overview](#1-app-overview)
2. [Feature Set](#2-feature-set)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Frontend (Flutter) — Tech Stack](#4-frontend-flutter--tech-stack)
5. [Project Structure](#5-project-structure)
6. [Application Flow](#6-application-flow)
7. [Authentication Module](#7-authentication-module)
8. [User Profile Module](#8-user-profile-module)
9. [Crop Health Scan (Disease Detection) Module](#9-crop-health-scan-disease-detection-module)
10. [AI Farming Assistant (Chat) Module](#10-ai-farming-assistant-chat-module)
11. [Model Connectivity — How the App Talks to the ML Backend](#11-model-connectivity--how-the-app-talks-to-the-ml-backend)
12. [WebSocket Live Detection — End-to-End Data Path](#12-websocket-live-detection--end-to-end-data-path)
13. [Backend Requirements (Disease Detection API)](#13-backend-requirements-disease-detection-api)
14. [Backend Tech Stack — Recommended](#14-backend-tech-stack--recommended)
15. [OpenRouter / LLM API — Tech Stack](#15-openrouter--llm-api--tech-stack)
16. [Firebase Tech Stack (Auth + Firestore)](#16-firebase-tech-stack-auth--firestore)
17. [Environment Variables & Secrets](#17-environment-variables--secrets)
18. [Supported Platforms](#18-supported-platforms)
19. [Build, Run, and Deployment](#19-build-run-and-deployment)
20. [Error Handling & Timeouts](#20-error-handling--timeouts)
21. [Data Models](#21-data-models)
22. [Theming & UX System](#22-theming--ux-system)
23. [Dependencies (pubspec.yaml)](#23-dependencies-pubspecyaml)
24. [Known Limitations & Future Work](#24-known-limitations--future-work)

---

## 1. App Overview

- **Name:** FarmEasy
- **Type:** Cross-platform mobile app (Android, iOS, Web, macOS, Windows, Linux)
- **Framework:** Flutter (Dart, SDK ^3.9.2)
- **Target Users:** Farmers / field agronomists
- **Core Promise:**
  - Detect corn (and other crop) leaf diseases from an image, video, or live camera feed using a custom ML model.
  - Get AI-generated precautions and treatments for detected diseases.
  - Chat with an LLM-powered farming assistant for general agronomic Q&A.

---

## 2. Feature Set

### A. Authentication
- Email/password sign-up
- Email/password sign-in
- Password reset via email
- Persistent auth state (auto-login on app launch)
- Firestore user profile document auto-created on sign-up

### B. User Profile
- View profile (name, email, phone, location, farm size, main crops)
- Edit profile (updates Firestore `users/{uid}`)
- Sign out

### C. Crop Health Scan (Disease Detection)
- **Image scan:** pick from camera or gallery → multipart upload → prediction
- **Video scan:** record/select a video → server samples frames → aggregated result
- **Live scan:** real-time camera feed → WebSocket frame-by-frame inference
- Results show:
  - Disease label and confidence
  - Leaf probability
  - Per-class probability bars
  - Status (ok / not_leaf / uncertain)
  - Processing time
  - Model metadata

### D. AI Farming Assistant (Chat)
- Streaming chat UI with OpenRouter LLM (Gemini 2.5 Flash Lite)
- Multi-turn conversation with persistent history
- Markdown-rendered assistant replies
- Chat reset

### E. Precautions & Treatment
- Auto-generated precautions for any detected disease
- Streamed from the same LLM endpoint

---

## 3. High-Level Architecture

```
+--------------------------+
|   Flutter Mobile App     |
|  (Android / iOS / Web)   |
+------------+-------------+
             |
             |  Firebase Auth SDK
             v
+--------------------------+
|   Firebase Authentication|
+--------------------------+

             |
             |  cloud_firestore SDK
             v
+--------------------------+
|   Cloud Firestore        |
|   (users/{uid} profile)  |
+--------------------------+

             |
             |  HTTP (multipart / JSON)  +  WebSocket (base64 frames)
             v
+-----------------------------------------------------------------+
|  FarmEasy ML Backend (FastAPI)                                  |
|  https://final-year-project-model-production.up.railway.app      |
|                                                                 |
|   /health, /metadata, /predict, /predict/base64, /predict/video,|
|   /ws/live                                                      |
+-----------------------------------------------------------------+

             |
             |  HTTPS streaming (SSE-style)
             v
+--------------------------+
|   OpenRouter API         |
|   google/gemini-2.5-     |
|   flash-lite             |
+--------------------------+
```

Three independent external integrations:
1. **Firebase** — Auth + Firestore.
2. **Custom ML backend** — disease detection over HTTP + WebSocket.
3. **OpenRouter** — LLM chat and precautions.

---

## 4. Frontend (Flutter) — Tech Stack

| Layer | Technology |
|---|---|
| Language | Dart (SDK `^3.9.2`) |
| Framework | Flutter (Material 3) |
| State Management | `provider` (ChangeNotifier) |
| Routing | Built-in `Navigator` |
| Theming | Material 3 + `google_fonts` (Outfit) |
| Animation | `flutter_animate` |
| Markdown rendering | `flutter_markdown` |
| Image picking | `image_picker` |
| Camera (live) | `camera` |
| HTTP | `http`, `http_parser` |
| WebSocket | `web_socket_channel` |
| Environment config | `flutter_dotenv` |
| Date formatting | `intl` |
| Firebase | `firebase_core`, `firebase_auth`, `cloud_firestore`, `firebase_storage` (declared, not yet used) |
| AI/ML (declared) | `firebase_ai` (declared, not yet used) |

---

## 5. Project Structure

```
farm_easy_app/
├── .env                              # OPENROUTER_API_KEY
├── firebase.json                     # Firebase project config
├── pubspec.yaml                      # Flutter dependencies
├── lib/
│   ├── main.dart                     # App entry, theming, AuthWrapper
│   ├── firebase_options.dart         # Generated Firebase config
│   ├── core/
│   │   └── app_constants.dart        # API base URL, paths, timeouts
│   ├── models/
│   │   ├── user_model.dart           # User profile model
│   │   ├── disease_prediction_model.dart   # Barrel export
│   │   └── disease_prediction/
│   │       ├── disease_prediction.dart      # Single image prediction
│   │       ├── video_prediction_result.dart # Video aggregated result
│   │       ├── prediction_image_info.dart
│   │       ├── runtime_model_info.dart
│   │       └── model_parsing.dart
│   ├── providers/
│   │   ├── auth_provider.dart
│   │   ├── user_provider.dart
│   │   ├── chat_provider.dart
│   │   ├── disease_detection_provider.dart
│   │   └── live_detection_provider.dart
│   ├── services/
│   │   ├── auth_service.dart
│   │   ├── database_service.dart
│   │   ├── chat_service.dart
│   │   └── farmeasy_api_service.dart
│   └── screens/
│       ├── auth/   (login, register, forgot_password)
│       ├── home/   (home_screen — bottom nav)
│       ├── chat/   (chat_screen)
│       ├── disease_detection/  (upload_screen, live_detection_screen, widgets/)
│       └── profile/ (profile_screen, edit_profile_screen)
├── android/  ios/  web/  macos/  windows/  linux/  # platform shells
└── docs/                              # This documentation
```

---

## 6. Application Flow

1. **App boot** (`main.dart`):
   - `WidgetsFlutterBinding.ensureInitialized()`
   - `dotenv.load(fileName: ".env")` → loads `OPENROUTER_API_KEY`
   - `Firebase.initializeApp(...)`
   - `runApp(FarmerApp)`
2. **Root widget** wraps `MaterialApp` in `MultiProvider` (Auth, User, Chat).
3. **`AuthWrapper`** subscribes to `FirebaseAuth.instance.authStateChanges`:
   - No user → `LoginScreen`
   - User present → load Firestore profile, then `HomeScreen`
4. **`HomeScreen`** is a bottom-navigation shell with 3 tabs:
   - **Assistant** → `ChatScreen` (LLM chat)
   - **Scan Crop** → `UploadScreen` (image / video / live)
   - **Profile** → `ProfileScreen`

---

## 7. Authentication Module

**Files**
- `lib/services/auth_service.dart` — wraps `FirebaseAuth` + Firestore user doc creation
- `lib/providers/auth_provider.dart` — `ChangeNotifier` exposing `login`, `register`, `resetPassword`, `logout`
- `lib/screens/auth/login_screen.dart`, `register_screen.dart`, `forgot_password_screen.dart`

**Capabilities**
- `signUp({email, password, name})` — creates user, then writes:
  ```json
  users/{uid}: {
    uid, name, email,
    createdAt: serverTimestamp(),
    role: "farmer"
  }
  ```
- `signIn({email, password})`
- `sendPasswordResetEmail(email)`
- `signOut()`
- Stream-based session listening via `authStateChanges`

**Error mapping** in `AuthProvider._parseFirebaseAuthError`:
- `user-not-found`, `wrong-password`, `email-already-in-use`, `invalid-email`, `weak-password` → human-readable strings.

---

## 8. User Profile Module

**Files**
- `lib/models/user_model.dart`
- `lib/services/database_service.dart`
- `lib/providers/user_provider.dart`
- `lib/screens/profile/profile_screen.dart`, `edit_profile_screen.dart`

**Fields**
- `uid`, `email`, `name` (required)
- `phone`, `location`, `farmSize`, `mainCrops[]`, `profileImageUrl` (optional)
- `createdAt` (Timestamp)

**Operations**
- `DatabaseService.getUser(uid)` — fetch by id
- `DatabaseService.updateUser(UserModel)` — update or merge
- `UserProvider.updateProfile(...)` — applies `copyWith` and persists

---

## 9. Crop Health Scan (Disease Detection) Module

Three modes, controlled by the `ScanMode` enum (`image | video | live`) in `disease_detection_provider.dart`.

### Mode 1: Image
- User picks/captures an image (`image_picker`, max width 1600, JPEG quality 88).
- `FarmEasyApiService.predictImage(file)` → `POST /predict` (multipart, key `file`).
- Query params supported: `gate_threshold`, `conf_threshold`, `tta`.
- Renders `PredictionResultPanel` with:
  - Status icon + display label
  - Leaf / confidence / processing-time chips
  - Class probability bars
  - Auto-fetched precautions (`ChatService.getPrecautionsStream`)

### Mode 2: Video
- User picks/records a video (max 2 minutes).
- `FarmEasyApiService.predictVideo(file)` → `POST /predict/video`.
- Query params: `sample_every_n_frames` (default 15), `max_frames` (default 120), `gate_threshold`, `conf_threshold`, `tta`.
- Server samples frames, returns per-frame predictions, status/label counts, and the best (highest-confidence `ok`) prediction.
- Renders `VideoResultPanel` (summary chips + best result + expandable frame list).

### Mode 3: Live
- Opens `LiveDetectionScreen` with the device camera (`camera` plugin, back lens, `ResolutionPreset.medium`, JPEG).
- On Start:
  - Opens WebSocket to `/ws/live`.
  - Every 2 seconds (`AppConstants.liveFrameInterval`):
    1. `controller.takePicture()`
    2. Read bytes
    3. Encode to base64
    4. Send JSON frame payload over WS
- Receives `DiseasePrediction` JSON per frame; UI updates with the latest result.

---

## 10. AI Farming Assistant (Chat) Module

**Files**
- `lib/services/chat_service.dart`
- `lib/providers/chat_provider.dart`
- `lib/screens/chat/chat_screen.dart`

**Behavior**
- Sends `POST https://openrouter.ai/api/v1/chat/completions`
- Model: `google/gemini-2.5-flash-lite`
- Streaming enabled (`stream: true`)
- Maintains a rolling `List<Map<String,String>>` history (system + user + assistant turns)
- System prompt scopes the model strictly to agriculture (crops, livestock, pests, soil, farm management); refuses off-topic questions.
- Headers:
  ```
  Content-Type: application/json
  Authorization: Bearer $OPENROUTER_API_KEY
  HTTP-Referer: https://farmeasy.com
  X-Title: Farmers Companion
  ```
- Parses SSE-style `data: {...}\n\n` chunks, yields `delta.content` strings.
- `clearHistory()` resets but keeps the system prompt.

A second method, `getPrecautionsStream(disease)`, hits the same endpoint with a one-off system/user prompt scoped to the detected disease.

---

## 11. Model Connectivity — How the App Talks to the ML Backend

### 11.1 Configuration

`lib/core/app_constants.dart`:
```dart
static const String apiBaseUrl = String.fromEnvironment(
  'FARMEASY_API_BASE_URL',
  defaultValue: 'https://final-year-project-model-production.up.railway.app',
);
```

The base URL is resolved at compile time from the `--dart-define=FARMEASY_API_BASE_URL=...` flag; otherwise the default Railway URL is used.

### 11.2 Single Service for All Model Calls

`lib/services/farmeasy_api_service.dart` is the only place that talks to the ML backend. It exposes:

| Method | HTTP | Endpoint | Purpose |
|---|---|---|---|
| `health()` | GET | `/health` | Liveness check |
| `metadata()` | GET | `/metadata` | Model class list / thresholds |
| `predictImage(File)` | POST (multipart) | `/predict` | Image inference |
| `predictBase64(String)` | POST (JSON) | `/predict/base64` | Image inference (base64) |
| `predictVideo(File)` | POST (multipart) | `/predict/video` | Video frame-sampled inference |
| `connectLiveDetection()` | WS | `/ws/live` | Real-time frame inference |
| `liveFramePayload(bytes, frameId)` | helper | — | Builds WS JSON envelope |

### 11.3 HTTP Request Construction

For image (multipart):
```
POST {apiBaseUrl}/predict?gate_threshold=...&conf_threshold=...&tta=...
Content-Type: multipart/form-data
file: <binary JPEG/PNG>
```

For base64 (JSON):
```
POST {apiBaseUrl}/predict/base64
Content-Type: application/json
{
  "image_base64": "<base64>",
  "filename": "optional.jpg"
}
```

For video (multipart):
```
POST {apiBaseUrl}/predict/video?sample_every_n_frames=15&max_frames=120&gate_threshold=...&conf_threshold=...&tta=...
file: <binary video>
```

### 11.4 WebSocket Frame Envelope

The app opens `wss://...railway.app/ws/live` and sends one JSON message per captured frame:
```json
{
  "frame_id": "1",
  "timestamp_ms": 1718900000000,
  "filename": "frame_1.jpg",
  "content_type": "image/jpeg",
  "image_base64": "<base64>"
}
```

The server replies with the same `DiseasePrediction` shape used by `/predict`.

### 11.5 Response Decoding

All HTTP responses are decoded into strongly-typed Dart models via `DiseasePrediction.fromJson` and `VideoPredictionResult.fromJson`. Errors raise a `FarmEasyApiException` containing the server's `detail` field and HTTP status code.

### 11.6 Sequence Diagram — Image Scan

```
[Flutter UI]  --pick image-->  [DiseaseDetectionProvider]
                                     |
                                     |  predictImage(file)
                                     v
                       [FarmEasyApiService]
                                     |
                                     |  POST /predict (multipart)
                                     v
                       [FastAPI Backend] --> [PyTorch/TF Model] --> [Postprocess]
                                     |
                                     |  JSON DiseasePrediction
                                     v
                       [DiseaseDetectionProvider] --notify-->  [UI rebuild]
```

---

## 12. WebSocket Live Detection — End-to-End Data Path

1. User taps **Start** on `LiveDetectionScreen`.
2. `LiveDetectionProvider.startLive()`:
   - Connects to `wss://{apiBaseUrl}/ws/live`.
   - Sends the first frame immediately.
   - Starts a 2-second `Timer.periodic` that calls `_sendFrame()`.
3. `_sendFrame()`:
   - Calls `cameraController.takePicture()` (JPEG).
   - Reads bytes, encodes to base64.
   - Increments `_frameCounter` and pushes the JSON envelope.
   - Deletes the temporary photo file.
4. Server responds with a `DiseasePrediction` JSON.
5. `_handleSocketMessage` decodes and updates `latestPrediction`.
6. UI re-renders `LiveResultPanel`.
7. On **Stop**, timer and socket are cancelled and camera is released.

---

## 13. Backend Requirements (Disease Detection API)

The deployed FastAPI backend (Railway) must expose the following contract.

### 13.1 `GET /health`
- **Response 200:**
  ```json
  { "status": "ok", "model": "effb3", "version": "1.0.0" }
  ```

### 13.2 `GET /metadata`
- **Response 200:**
  ```json
  {
    "models": ["effb3", "convnext_tiny"],
    "default_model": "effb3",
    "labels": ["Healthy", "Blight", "Rust", "Leaf_Spot"],
    "gate_threshold": 0.5,
    "conf_threshold": 0.45,
    "supports_tta": true,
    "supports_video": true,
    "supports_live": true
  }
  ```

### 13.3 `POST /predict`  (multipart, field `file`)
- **Query params (all optional):**
  - `gate_threshold` (float, default 0.5) — leaf gate probability.
  - `conf_threshold` (float, default 0.45) — minimum class confidence.
  - `tta` (bool, default false) — test-time augmentation.
- **Request body:** image file (JPEG/PNG, multipart/form-data).
- **Response 200:**
  ```json
  {
    "request_id": "uuid",
    "is_leaf": true,
    "leaf_prob": 0.97,
    "label": "Blight",
    "confidence": 0.91,
    "status": "ok",
    "probabilities": {
      "Healthy": 0.04,
      "Blight": 0.91,
      "Rust": 0.03,
      "Leaf_Spot": 0.02
    },
    "model": {
      "models": "effb3",
      "tta": false,
      "gate_threshold": 0.5,
      "conf_threshold": 0.45
    },
    "image": {
      "width": 1600,
      "height": 1200,
      "mode": "RGB",
      "format": "JPEG",
      "filename": "leaf.jpg",
      "content_type": "image/jpeg"
    },
    "processing_ms": 142.7
  }
  ```
- **Status values:** `ok`, `not_leaf`, `uncertain`.
- **Error responses:** FastAPI's standard `{"detail": "..."}` with appropriate 4xx/5xx codes.

### 13.4 `POST /predict/base64`  (JSON)
- **Request:**
  ```json
  { "image_base64": "<base64>", "filename": "leaf.jpg" }
  ```
- **Response:** same shape as `/predict`.

### 13.5 `POST /predict/video`  (multipart, field `file`)
- **Query params (all optional):**
  - `sample_every_n_frames` (int, default 15)
  - `max_frames` (int, default 120)
  - `gate_threshold`, `conf_threshold`, `tta`
- **Response 200:**
  ```json
  {
    "request_id": "uuid",
    "filename": "clip.mp4",
    "content_type": "video/mp4",
    "total_frames": 600,
    "fps": 30.0,
    "duration_sec": 20.0,
    "sample_every_n_frames": 15,
    "max_frames": 120,
    "sampled_frames": 40,
    "status_counts": { "ok": 35, "not_leaf": 3, "uncertain": 2 },
    "label_counts": { "Healthy": 30, "Blight": 5 },
    "frames": [
      {
        "frame_index": 0,
        "timestamp_ms": 0.0,
        "prediction": { /* DiseasePrediction */ }
      }
    ],
    "processing_ms": 4200.0
  }
  ```

### 13.6 `WS /ws/live`
- **Client → Server messages** (one per captured frame):
  ```json
  {
    "frame_id": "1",
    "timestamp_ms": 1718900000000,
    "filename": "frame_1.jpg",
    "content_type": "image/jpeg",
    "image_base64": "<base64>"
  }
  ```
- **Server → Client messages** (one per frame): the same `DiseasePrediction` JSON, plus optional `{"error": "..."}` envelopes on failure.

### 13.7 CORS
- Must allow the Flutter web build origin (and any dev origin).

### 13.8 Reliability Requirements
- Request handling timeout budget: at least **60 s** for image, **300 s** for video.
- WebSocket must support bi-directional streaming, low per-frame latency, and at least 1 frame every 2 s.
- Use of a GPU/CPU pool is expected (the app assumes sub-second image inference).

---

## 14. Backend Tech Stack — Recommended

| Layer | Recommendation |
|---|---|
| Language | Python 3.10+ |
| Web framework | **FastAPI** (matches existing deployment) |
| ASGI server | Uvicorn (with `websockets` support) |
| Deep learning | **PyTorch** (preferred) or TensorFlow / Keras |
| Pretrained backbones | `timm`: EfficientNet-B3, ConvNeXt-Tiny, ResNet50, ViT-Small |
| Image processing | Pillow, OpenCV (`opencv-python`), `albumentations` |
| TTA | `torchvision` TTA wrapper or custom flip/crop ensemble |
| Numerical | NumPy |
| Video I/O | `decord` or PyAV (OpenCV) for frame sampling |
| Validation | Pydantic v2 |
| Config | `pydantic-settings` or `.env` via `python-dotenv` |
| Logging | `loguru` or stdlib logging |
| Container | Docker (slim Python base + CUDA runtime if GPU) |
| Deployment | Railway / Render / Fly.io / AWS ECS / GCP Cloud Run |
| Process manager | Uvicorn workers behind a reverse proxy (Nginx / Caddy) |
| Reverse proxy | Nginx with HTTP/1.1 + WebSocket upgrade |
| HTTPS | Caddy or Nginx + Let's Encrypt / managed certs |

### Why these choices
- **FastAPI** is the only framework that natively supports async HTTP + WebSocket + Pydantic models in one place.
- **`timm`** gives battle-tested image classification backbones with consistent APIs for ensembling and TTA.
- **Pillow + OpenCV** covers both static image decoding and video frame extraction.
- **Docker** ensures reproducibility; the existing Railway URL suggests the backend is already containerized.

---

## 15. OpenRouter / LLM API — Tech Stack

| Component | Value |
|---|---|
| Provider | **OpenRouter.ai** |
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Model | `google/gemini-2.5-flash-lite` |
| Streaming | SSE-style `data: {...}` lines, terminated by `data: [DONE]` |
| Auth | `Authorization: Bearer $OPENROUTER_API_KEY` |
| Optional headers | `HTTP-Referer`, `X-Title` (for OpenRouter attribution) |
| Required env var | `OPENROUTER_API_KEY` (loaded via `flutter_dotenv`) |

The Flutter app performs no SDK-level abstraction — it is a thin `http.Client().send(request)` over a streaming response.

---

## 16. Firebase Tech Stack (Auth + Firestore)

| Component | Detail |
|---|---|
| Product | Firebase |
| Auth provider | Email/Password (no OAuth providers configured) |
| Auth SDK | `firebase_auth: ^5.3.1` |
| Database | Cloud Firestore (Native mode) |
| DB SDK | `cloud_firestore: ^5.4.4` |
| Project ID | `final-year-project-perfecto` |
| Platform apps | Android, iOS, macOS, Web, Windows |
| Configured in | `lib/firebase_options.dart` (auto-generated by FlutterFire CLI) and `firebase.json` |
| Collection layout | `users/{uid}` — single document per user |
| Document fields | `uid, name, email, createdAt, role, phone?, location?, farmSize?, mainCrops?, profileImageUrl?` |

`firebase_storage` and `firebase_ai` are declared in `pubspec.yaml` but not currently used in code.

---

## 17. Environment Variables & Secrets

| Variable | Where | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | `.env` (loaded by `flutter_dotenv`) | LLM API key |
| `FARMEASY_API_BASE_URL` | `--dart-define` at build time | Override ML backend base URL |
| `android/app/google-services.json` | `firebase.json` + FlutterFire | Firebase Android config |
| `ios/Runner/GoogleService-Info.plist` | (auto) | Firebase iOS config |

`.env` is registered as a Flutter asset (`pubspec.yaml` → `assets: - .env`) and excluded from version control by `.gitignore`.

---

## 18. Supported Platforms

Flutter is configured for:
- Android (`android/`)
- iOS (`ios/`)
- Web (`web/`)
- macOS (`macos/`)
- Windows (`windows/`)
- Linux (`linux/`)

Web is supported for the auth/profile/chat flows, but the live-camera mode uses the `camera` plugin which is primarily a mobile feature.

---

## 19. Build, Run, and Deployment

### Local development
```bash
flutter pub get
flutter run                       # auto-detects connected device
flutter run -d chrome             # web
flutter run --dart-define=FARMEASY_API_BASE_URL=http://localhost:8000
```

### Secrets
- Place `OPENROUTER_API_KEY` in `.env` at project root.
- Place Firebase config files under `android/app/google-services.json` and `ios/Runner/GoogleService-Info.plist`.

### Production build
```bash
flutter build apk --release \
  --dart-define=FARMEASY_API_BASE_URL=https://your-backend.example.com
flutter build appbundle --release
flutter build ipa --release
flutter build web --release
```

### Recommended deployment topology
```
Users → App Store / Play Store / Web hosting
            │
            ├──> Firebase (Auth + Firestore)
            └──> Railway / Render / Cloud Run  ←→  OpenRouter
                  (FastAPI + PyTorch model)
```

---

## 20. Error Handling & Timeouts

- **Image / base64 requests:** `AppConstants.requestTimeout` = 60 s.
- **Video requests:** `AppConstants.videoRequestTimeout` = 5 min.
- **Live frame interval:** `AppConstants.liveFrameInterval` = 2 s.
- All non-2xx responses throw `FarmEasyApiException(message, statusCode)` with the server's `detail` message when present.
- WebSocket errors populate `LiveDetectionProvider.error` and surface an `ErrorPanel` in the UI.
- Firebase auth errors are mapped to user-friendly strings in `AuthProvider._parseFirebaseAuthError`.
- OpenRouter failures are streamed as `"Error: <status> - <body>"` chunks so the chat UI never silently breaks.

---

## 21. Data Models

### `UserModel`
| Field | Type |
|---|---|
| uid | String |
| email | String |
| name | String |
| phone | String? |
| location | String? |
| farmSize | String? |
| mainCrops | List<String>? |
| profileImageUrl | String? |
| createdAt | DateTime |

### `DiseasePrediction`
| Field | Type |
|---|---|
| requestId | String |
| isLeaf | bool |
| leafProb | double |
| label | String? |
| confidence | double? |
| status | String (`ok` / `not_leaf` / `uncertain`) |
| probabilities | Map<String, double> |
| model | RuntimeModelInfo? |
| image | PredictionImageInfo? |
| processingMs | double? |
| frameId | String? |
| clientTimestampMs | int? |

### `VideoPredictionResult`
- Aggregates per-frame predictions, `statusCounts`, `labelCounts`, `bestPrediction` helper.

### `RuntimeModelInfo`
- `models`, `tta`, `gateThreshold`, `confThreshold`.

### `PredictionImageInfo`
- `width`, `height`, `mode`, `format`, `filename`, `contentType`.

---

## 22. Theming & UX System

- **Material 3** with a custom organic-green palette:
  - Primary `#2E7D32`
  - Secondary `#81C784`
  - Surface light `#F1F8E9`
- **Typography:** Google Fonts → `Outfit`.
- **Light + Dark** themes with `ThemeMode.system`.
- **Animations:** `flutter_animate` for fades, slides, scaling on auth and chat bubbles.
- **Bottom navigation:** Assistant / Scan Crop / Profile.
- **Custom segmented control** for Image/Video/Live modes.
- **Reusable widgets:** `MetricChip`, `ErrorPanel`, `MediaPickerPanel`, `MediaAction`.

---

## 23. Dependencies (pubspec.yaml)

**Runtime**
- `firebase_core: ^3.15.2`
- `firebase_auth: ^5.3.1`
- `cloud_firestore: ^5.4.4`
- `firebase_storage: ^12.3.2` *(declared, unused)*
- `provider: ^6.1.2`
- `image_picker: ^1.1.2`
- `google_fonts: ^6.2.1`
- `flutter_animate: ^4.5.0`
- `intl: ^0.19.0`
- `firebase_ai: ^2.3.0` *(declared, unused)*
- `flutter_markdown: ^0.7.7+1`
- `http: ^1.6.0`
- `image: ^4.5.4`
- `http_parser: ^4.1.2`
- `camera: ^0.12.0+1`
- `web_socket_channel: ^3.0.3`
- `flutter_dotenv: ^6.0.1`
- `cupertino_icons: ^1.0.8`

**Dev**
- `flutter_test`
- `flutter_lints: ^5.0.0`
- `flutter_launcher_icons: ^0.14.4`
- `flutter_native_splash: ^2.4.7`

---

## 24. Known Limitations & Future Work

- `firebase_storage` and `firebase_ai` are declared but not yet integrated.
- Offline mode is not supported — both backend calls require network.
- Web build does not use the `camera` plugin for live detection.
- No image storage or scan history is persisted to Firestore.
- Single LLM model is used; no fallback or model switching.
- No analytics, crash reporting, or push notifications.
- Image/video uploads have no client-side compression beyond `image_picker` defaults.
- The `.env` key is bundled with the app on web (use `--dart-define` for production).

---

*End of documentation.*
