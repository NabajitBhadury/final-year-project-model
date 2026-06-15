# FarmEasy — App Integration Guide

This document tells an app developer how to integrate the trained corn-leaf
disease detection system (leaf-gate + 5-model ensemble) into an application.

The model is already trained and verified. **You do not need to retrain
anything or touch the dataset.** You consume the saved models through a small,
stable API.

---

## 1. What the system does

For any input image (or video frame) the pipeline:

1. **Leaf gate** — decides "is this a corn leaf?" (rejects hands, soil, faces,
   random objects). MobileNetV3, validated F1 = 1.00.
2. **Disease classifier** — if it is a leaf, classifies it into one of **5
   classes** with calibrated probabilities (soft-vote ensemble, 98.9% test acc):

   `Blight`, `Common_Rust`, `Gray_Leaf_Spot`, `Healthy`, `Insects_damage`

---

## 2. Files to copy into the app project (the "inference bundle")

**Code (repo root):**
- `farmeasy.py`  ← the single high-level API class (use this)
- `predict.py`   ← ensemble loader (used by farmeasy)
- `leaf_gate.py` ← leaf-gate loader (used by farmeasy)
- `live_video.py`← optional: ready-made desktop live-video app
- `serve.py`     ← optional: ready-made REST backend
- `mcp_server.py`← optional: ready-made MCP server (LLM/agent tool)
- `export_onnx.py` ← optional: mobile export

**Model weights:**
- `leaf_gate_out/`  (leaf_gate.pth + manifest — 6 MB)
- `ensemble_out_v2/`  — keep `manifest.json` + the `*_best.pth` you use:
  - **Lightweight (recommended for app):** `effb3_best.pth` only (42 MB)
  - **Maximum accuracy:** all five `*_best.pth` (333 MB)
  - You can delete the `*_probs.npz` files — they are not used at inference.

> Do **NOT** ship: `data/`, `Archive/`, `train_*.py`, `build_dataset.py`,
> `make_*figures.py`, `report/`, `Documentation/`. They are for training/reporting only.

---

## 3. Environment

```
Python 3.10+
pip install torch torchvision timm pillow numpy
# plus, depending on path:
pip install opencv-python              # desktop live video (GUI window)
pip install fastapi "uvicorn[standard]" python-multipart   # REST backend
pip install onnx onnxruntime           # mobile / ONNX export
```
A CUDA GPU is optional — it speeds inference but the models run on CPU too.
(`torch` auto-uses CUDA if present.)

---

## 4. Choose an integration path

### Path A — Desktop app in Python (simplest)
Import the one class and call `analyze()`:

```python
from farmeasy import FarmEasy
from PIL import Image

fe = FarmEasy(models="effb3")          # load once at startup (slow); reuse fe
result = fe.analyze(Image.open("leaf.jpg"))
print(result)
```

Output contract (JSON-friendly dict):
```json
{
  "is_leaf": true,
  "leaf_prob": 0.9718,
  "label": "Gray_Leaf_Spot",
  "confidence": 0.9484,
  "status": "ok",                       // "ok" | "not_leaf" | "uncertain"
  "probabilities": {"Blight":0.011,"Common_Rust":0.010,
                    "Gray_Leaf_Spot":0.948,"Healthy":0.015,"Insects_damage":0.015}
}
```
- `is_leaf=false`  → show "Not a corn leaf"; `label` is null.
- `status="uncertain"` → confidence below threshold; show "uncertain".
- Knobs: `FarmEasy(models="all", tta=True, gate_threshold=0.5, conf_threshold=0.45)`.

### Path B — Any app via REST backend (web / mobile / cross-language)
Run the model on a server/PC; the app just makes HTTP calls — no PyTorch in the app.

```
uvicorn serve:app --host 0.0.0.0 --port 8000
# configure with env vars: FARMEASY_MODELS=effb3  FARMEASY_TTA=0
```
```
GET  /health   -> {"status":"ok","classes":[...]}
POST /predict  (multipart form field "file" = image)  -> the dict from §4A
```
Example:
```
curl -F "file=@leaf.jpg" http://localhost:8000/predict
```
The mobile/web frontend uploads the photo (or a captured frame) and renders the
returned label + probabilities. This is the recommended path for a phone app
that should stay small.

### Path C — Mobile on-device (no server, offline)
Export to ONNX, bundle the `.onnx` files, run with ONNX Runtime Mobile / TFLite:

```
python export_onnx.py --models effb3      # -> onnx_out/leaf_gate.onnx, effb3.onnx, preprocess.json
```
On device, per frame:
1. Preprocess exactly as `preprocess.json` says (per-model **resize → center-crop
   → normalize with the given mean/std**). This must match exactly or accuracy drops.
2. Run `leaf_gate.onnx`; softmax; if `prob[leaf_index] < threshold` → "Not a leaf".
3. Else run the disease model(s); softmax each; weight-average; `argmax` over `classes`.

(Verified: ONNX output matches PyTorch exactly.)

### Path D — MCP server (expose the model as a tool to an LLM/agent)
Everything runs **locally** — no training, no GPU, no remote host. The trained
weights are in the bundle (`ensemble_out_v2/`, `leaf_gate_out/`). On Apple Silicon
(M-series) inference runs on CPU automatically and effb3 is fast there.

```
pip install "mcp[cli]" torch torchvision timm pillow numpy
python mcp_server.py          # stdio MCP server
```
It exposes two tools:
- `analyze_corn_leaf(image_path="" , image_base64="")` → the dict from §4A
- `list_disease_classes()` → the class names

Register it with an MCP client (e.g. Claude Desktop `claude_desktop_config.json`):
```json
{ "mcpServers": { "farmeasy": {
    "command": "python", "args": ["/absolute/path/to/mcp_server.py"] } } }
```
`mcp_server.py` is a thin wrapper over `FarmEasy.analyze()` — copy/adapt it for
any other agent framework.

> **On hardware:** an Apple M4 (or any modern laptop) easily *runs* this model —
> it only cannot reasonably *train* it, and you don't need to: training is done
> and the weights ship in this bundle. The same is true for Paths A–C: all run on
> CPU if no NVIDIA GPU is present.

---

## 5. Live video (desktop, ready to run)

`live_video.py` already implements the full live experience: it locates leaf
region(s), runs the gate, classifies, and draws colored boxes
(**green=Healthy, red=disease, grey=Not a leaf, orange=uncertain**) with
temporal smoothing.

```
pip install opencv-python
python live_video.py --source 0                 # webcam (fast, EffNet-B3)
python live_video.py --source 0 --models all    # full ensemble
python live_video.py --source clip.mp4 --save out.mp4
python live_video.py --source folder_of_images/ --save annotated/
```
Useful flags: `--every N` (run heavy inference every N frames), `--conf`,
`--gate-thr`, `--roi` (single centre box instead of contour detection).

For a custom UI, reuse the building blocks in `live_video.py`
(`detect_leaf_boxes`, `Tracker`, `draw_label`) or just call `FarmEasy.analyze()`
on each captured frame and draw your own overlay.

> Note: the live GUI window needs the full `opencv-python` build. The
> `opencv-python-headless` build (e.g. in WSL/servers) processes frames but
> cannot open a window — use `--save` to write output there.

---

## 6. Important notes / gotchas

- **Preprocessing must match.** If you do your own preprocessing (Path C or a
  custom pipeline), use each model's `mean`/`std`/`img_size`/`crop_pct` from the
  manifest (or `preprocess.json`). `farmeasy.py`/`predict.py` already do this.
- **Load once.** Constructing `FarmEasy()` loads weights (slow). Do it once at
  startup and reuse the instance for every request/frame.
- **Speed.** Single `effb3` is fast and ~as accurate (98.1%); the full 5-model
  ensemble is ~5× slower for +0 to +0.x% — use `effb3` for live/mobile.
- **Leaf-gate hardening (optional).** The gate was trained against generic
  photos; it reliably rejects real-world non-leaf photos but is not bulletproof
  on unusual inputs. To harden for field use, collect real non-leaf photos
  (soil, hands, sky, machinery) into a folder and retrain:
  `python train_leaf_gate.py --neg-dir my_nonleaf` (produces a new `leaf_gate_out/`).
- **Boxes** in live video come from color/contour segmentation, not a trained
  detector — great for a leaf on a contrasting background; for cluttered
  multi-leaf scenes, a trained object detector (e.g. YOLO) would localize tighter.
- **Classes are fixed** and ordered by the manifest's `idx_to_class`; always read
  names from there rather than hard-coding, in case the model is retrained.

---

## 7. Quick checklist for your friend

1. Copy the inference bundle (§2) into the app repo.
2. `pip install` the deps for the chosen path (§3).
3. Pick a path: A (embed Python), B (REST), or C (mobile ONNX).
4. Call `analyze()` / `POST /predict` / run the ONNX flow per image or frame.
5. Render: `is_leaf` → label + `confidence` + per-class `probabilities`.
6. (Optional) Use `live_video.py` for the desktop live-camera feature.
