# FarmEasy API Documentation

This backend exposes the FarmEasy corn disease model through a normal HTTP API
for Flutter/mobile apps and through MCP for AI-agent clients.

## Base URLs

Local development:

```text
http://localhost:8000
```

On a phone connected to the same Wi-Fi, use your computer's LAN IP instead:

```text
http://192.168.x.x:8000
```

## Run

```bash
pip install -r server/requirements.txt
python -m server --host 0.0.0.0 --port 8000
```

Generated docs:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FARMEASY_HOST` | `0.0.0.0` | HTTP bind host. |
| `FARMEASY_PORT` | `8000` | HTTP port. |
| `FARMEASY_BUNDLE_DIR` | auto-detect | Model bundle directory. Checks `./FarmEasy_Integration_Bundle`, then `./model`. |
| `FARMEASY_ENSEMBLE_DIR` | `bundle/ensemble_out_v2` | Disease classifier weights and manifest. |
| `FARMEASY_GATE_DIR` | `bundle/leaf_gate_out` | Leaf gate weights and manifest. |
| `FARMEASY_MODELS` | `effb3` | `effb3`, comma list, or `all`. |
| `FARMEASY_TTA` | `0` | Enable slower test-time augmentation. |
| `FARMEASY_GATE_THRESHOLD` | `0.5` | Minimum probability to accept corn leaf. |
| `FARMEASY_CONF_THRESHOLD` | `0.45` | Minimum disease confidence to return a label. |
| `FARMEASY_MAX_UPLOAD_MB` | `10` | Max image upload size. |
| `FARMEASY_MAX_VIDEO_UPLOAD_MB` | `100` | Max video upload size. |
| `FARMEASY_CORS_ORIGINS` | `*` | Comma-separated CORS origins. |
| `FARMEASY_MCP_ENABLED` | `1` | Mount MCP endpoint at `/mcp`. |
| `FARMEASY_MCP_HOST` | `127.0.0.1` | Host for standalone MCP HTTP mode. |
| `FARMEASY_MCP_PORT` | `8001` | Port for standalone MCP HTTP mode. |
| `FARMEASY_ALLOWED_IMAGE_ROOT` | project root | Local root allowed for MCP path reads. |

## Response Contract

All prediction endpoints return this shape:

```json
{
  "request_id": "cde49c7a5b7d4fd4b42c13d40964e42e",
  "is_leaf": true,
  "leaf_prob": 0.9718,
  "label": "Gray_Leaf_Spot",
  "confidence": 0.9484,
  "status": "ok",
  "probabilities": {
    "Blight": 0.011,
    "Common_Rust": 0.01,
    "Gray_Leaf_Spot": 0.948,
    "Healthy": 0.015,
    "Insects_damage": 0.015
  },
  "model": {
    "models": "effb3",
    "tta": false,
    "gate_threshold": 0.5,
    "conf_threshold": 0.45
  },
  "image": {
    "width": 1280,
    "height": 720,
    "mode": "RGB",
    "format": "JPEG",
    "filename": "leaf.jpg",
    "content_type": "image/jpeg"
  },
  "processing_ms": 82.4
}
```

`status` meanings:

| Status | Meaning |
| --- | --- |
| `ok` | Corn leaf accepted and a disease/healthy label is confident enough. |
| `not_leaf` | Leaf gate rejected the image. `label` and `confidence` are `null`. |
| `uncertain` | Image is a leaf, but top disease confidence is below the threshold. |

Important: the backend always runs the leaf gate first. If `is_leaf=false`, the
disease classifier is skipped and `status` is `not_leaf`. For video and live
detection, this rule is applied per sampled frame.

## Endpoints

### `GET /health`

Checks that the API process and model bundle paths are visible. It does not run
inference.

```bash
curl http://localhost:8000/health
```

### `GET /health/ready`

Loads the model if needed and returns readiness. Use this in deployments.

```bash
curl http://localhost:8000/health/ready
```

### `GET /metadata`

Returns classes, available model keys, selected runtime settings, and MCP info.

```bash
curl http://localhost:8000/metadata
```

### `POST /predict`

Multipart upload for Flutter/mobile apps.

Query parameters:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `gate_threshold` | float | no | Override leaf gate threshold for one request. |
| `conf_threshold` | float | no | Override disease confidence threshold for one request. |
| `tta` | bool | no | Override test-time augmentation for one request. |

Example:

```bash
curl -F "file=@leaf.jpg" "http://localhost:8000/predict"
```

With overrides:

```bash
curl -F "file=@leaf.jpg" \
  "http://localhost:8000/predict?gate_threshold=0.55&conf_threshold=0.5&tta=false"
```

### `POST /predict/base64`

JSON upload for clients that already have image bytes as base64.

```bash
curl -X POST http://localhost:8000/predict/base64 \
  -H "Content-Type: application/json" \
  -d '{"filename":"leaf.jpg","image_base64":"..."}'
```

### `POST /predict/video`

Multipart video upload. The backend samples frames and returns one normal
prediction object per sampled frame.

Query parameters:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `sample_every_n_frames` | int | `15` | Run inference every N frames. |
| `max_frames` | int | `120` | Maximum sampled frames to analyze. |
| `gate_threshold` | float | env default | Override leaf gate threshold. |
| `conf_threshold` | float | env default | Override disease confidence threshold. |
| `tta` | bool | env default | Override test-time augmentation. |

Example:

```bash
curl -F "file=@field_scan.mp4" \
  "http://localhost:8000/predict/video?sample_every_n_frames=15&max_frames=120"
```

Response summary:

```json
{
  "request_id": "a85f00ddba5b4b978ad9936d51e71009",
  "filename": "field_scan.mp4",
  "total_frames": 300,
  "fps": 30.0,
  "duration_sec": 10.0,
  "sample_every_n_frames": 15,
  "max_frames": 120,
  "sampled_frames": 20,
  "status_counts": {"ok": 18, "not_leaf": 1, "uncertain": 1},
  "label_counts": {"Healthy": 12, "Common_Rust": 6},
  "frames": [
    {
      "frame_index": 0,
      "timestamp_ms": 0.0,
      "prediction": {
        "is_leaf": true,
        "label": "Healthy",
        "status": "ok"
      }
    }
  ]
}
```

### `WS /ws/live`

WebSocket endpoint for live detection. Your Flutter app captures camera frames,
encodes each frame as JPEG/PNG base64, sends it to the socket, and receives a
prediction response for that frame.

Client message:

```json
{
  "frame_id": "42",
  "timestamp_ms": 1718451000000,
  "filename": "frame.jpg",
  "content_type": "image/jpeg",
  "image_base64": "/9j/4AAQSkZJRgABAQ..."
}
```

Server response: same prediction contract as `/predict`, plus `frame_id` and
`client_timestamp_ms`.

Use this for live detection instead of uploading a full video repeatedly.

## Flutter Example

Add the `http` package:

```yaml
dependencies:
  http: ^1.2.0
  web_socket_channel: ^3.0.0
```

Multipart upload:

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> predictLeaf(String imagePath) async {
  final request = http.MultipartRequest(
    'POST',
    Uri.parse('http://YOUR_SERVER_IP:8000/predict'),
  );

  request.files.add(await http.MultipartFile.fromPath('file', imagePath));

  final response = await request.send();
  final body = await response.stream.bytesToString();

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception('FarmEasy API error ${response.statusCode}: $body');
  }

  return jsonDecode(body) as Map<String, dynamic>;
}
```

Live WebSocket sketch:

```dart
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

final channel = WebSocketChannel.connect(
  Uri.parse('ws://YOUR_SERVER_IP:8000/ws/live'),
);

void sendFrame(String jpegBase64, int frameId) {
  channel.sink.add(jsonEncode({
    'frame_id': frameId.toString(),
    'content_type': 'image/jpeg',
    'image_base64': jpegBase64,
  }));
}

void listenForPredictions() {
  channel.stream.listen((message) {
    final result = jsonDecode(message as String) as Map<String, dynamic>;
    // result['is_leaf'], result['status'], result['label'], result['probabilities']
  });
}
```

For Android emulator, use `http://10.0.2.2:8000`. For a physical phone, use
your computer's LAN IP and run the backend with `--host 0.0.0.0`.

## MCP

The FastAPI app mounts a Streamable HTTP MCP server at:

```text
http://localhost:8000/mcp
```

Tools exposed:

| Tool | Purpose |
| --- | --- |
| `model_metadata` | Return classes, selected weights, thresholds, and paths. |
| `predict_image_base64` | Predict from raw base64 or a data URL. |
| `predict_image_path` | Predict from a local file inside `FARMEASY_ALLOWED_IMAGE_ROOT`. |
| `predict_video_path` | Sample and predict frames from a local video inside `FARMEASY_ALLOWED_IMAGE_ROOT`. |

Standalone stdio MCP:

```bash
python -m server.mcp_server --transport stdio
```

Standalone HTTP MCP:

```bash
python -m server.mcp_server --transport streamable-http
```

By default, standalone HTTP MCP listens at:

```text
http://127.0.0.1:8001/mcp
```

When using an MCP inspector or MCP-compatible client, connect to:

```text
http://localhost:8000/mcp
```

## Error Responses

Common errors:

| Code | Cause |
| --- | --- |
| `400` | Invalid base64 or unreadable image. |
| `413` | Image or video exceeds the configured upload size. |
| `415` | Multipart file has the wrong content type. |
| `500` | Model bundle missing files or dependencies. |

Note: if `FARMEASY_MODELS=all`, all checkpoint files listed in
`ensemble_out_v2/manifest.json` must exist. This bundle currently includes the
lightweight `effb3_best.pth`, so the default is `FARMEASY_MODELS=effb3`.
