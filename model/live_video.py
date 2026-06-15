# ============================================================
#  FarmEasy — LIVE CORN-LEAF DISEASE DETECTION
# ============================================================
#  Per frame:
#     1. locate candidate leaf region(s)  (HSV colour + contours, ROI fallback)
#     2. LEAF GATE  -> is this a corn leaf?   (grey box + "Not a leaf" if not)
#     3. DISEASE CLASSIFIER on accepted leaves -> coloured box + label
#  with frame-skipping + temporal smoothing for smooth, stable real-time output.
#
#  Sources:
#     --source 0              webcam (index)
#     --source clip.mp4       video file
#     --source leaf.jpg       single image
#     --source some_folder/   every image in a folder
#
#  Examples:
#     python live_video.py --source 0                 # webcam, fast (effb3)
#     python live_video.py --source 0 --models all    # full 5-model ensemble
#     python live_video.py --source clip.mp4 --save out.mp4
#     python live_video.py --source samples/ --save live_out
# ============================================================
import os
import argparse
from collections import deque

import numpy as np
import cv2
from PIL import Image

import predict as P
from leaf_gate import load_leaf_gate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

# BGR colours
C_HEALTHY = (60, 170, 60)
C_DISEASE = (40, 40, 210)
C_NOTLEAF = (140, 140, 140)
C_UNCERT = (0, 165, 255)


def parse_args():
    p = argparse.ArgumentParser(description="FarmEasy live corn-leaf disease detection")
    p.add_argument("--source", default="0", help="webcam index, video file, image, or folder")
    p.add_argument("--out-dir", default=os.path.join(BASE_DIR, "ensemble_out_v2"),
                   help="disease ensemble manifest dir")
    p.add_argument("--gate-dir", default=os.path.join(BASE_DIR, "leaf_gate_out"))
    p.add_argument("--models", default="effb3",
                   help="'effb3' (fast, default), 'all', or comma list e.g. effb3,effb4")
    p.add_argument("--every", type=int, default=3, help="run heavy inference every N frames")
    p.add_argument("--conf", type=float, default=0.45, help="min disease confidence to label")
    p.add_argument("--gate-thr", type=float, default=0.5, help="min p(leaf) to accept a region")
    p.add_argument("--roi", action="store_true", help="single centre ROI instead of contour detection")
    p.add_argument("--max-boxes", type=int, default=3)
    p.add_argument("--save", default=None, help="output video file or folder for annotated frames")
    p.add_argument("--no-display", action="store_true", help="never open a GUI window")
    return p.parse_args()


# ------------------------------------------------------------
# Leaf-region detection (no trained detector: HSV colour + contours)
# ------------------------------------------------------------
def detect_leaf_boxes(frame, max_boxes=3, min_area_frac=0.02):
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # green foliage + yellow/brown diseased tissue
    green = cv2.inRange(hsv, (25, 30, 30), (95, 255, 255))
    brown = cv2.inRange(hsv, (10, 30, 20), (25, 255, 220))
    mask = cv2.bitwise_or(green, brown)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    min_area = min_area_frac * h * w
    for c in sorted(cnts, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(c) < min_area:
            break
        x, y, bw, bh = cv2.boundingRect(c)
        # pad a little so lesions near the edge are included
        pad = int(0.04 * max(bw, bh))
        x, y = max(0, x - pad), max(0, y - pad)
        bw, bh = min(w - x, bw + 2 * pad), min(h - y, bh + 2 * pad)
        # skip if this box is mostly contained in a larger one already kept
        if any(_contained((x, y, bw, bh), kb) for kb in boxes):
            continue
        boxes.append((x, y, bw, bh))
        if len(boxes) >= max_boxes:
            break
    return boxes


def _contained(inner, outer, frac=0.7):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    ax0, ay0 = max(ix, ox), max(iy, oy)
    ax1, ay1 = min(ix + iw, ox + ow), min(iy + ih, oy + oh)
    inter = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    return inter >= frac * (iw * ih)


def center_roi(frame, frac=0.7):
    h, w = frame.shape[:2]
    bw, bh = int(w * frac), int(h * frac)
    return [((w - bw) // 2, (h - bh) // 2, bw, bh)]


# ------------------------------------------------------------
# Simple centroid tracker with EMA-smoothed class probabilities
# ------------------------------------------------------------
class Tracker:
    def __init__(self, n_classes, ema=0.6, max_dist=0.15, ttl=8):
        self.tracks = {}          # id -> dict
        self.next_id = 0
        self.n = n_classes
        self.ema = ema
        self.max_dist = max_dist  # as fraction of frame diagonal
        self.ttl = ttl

    def _centroid(self, b):
        x, y, w, h = b
        return np.array([x + w / 2, y + h / 2], float)

    def update(self, dets, diag):
        """dets: list of (box, is_leaf, leaf_p, probs|None). Returns annotated tracks."""
        for t in self.tracks.values():
            t["age"] += 1
        used = set()
        for box, is_leaf, leaf_p, probs in dets:
            c = self._centroid(box)
            best, bestd = None, 1e9
            for tid, t in self.tracks.items():
                if tid in used:
                    continue
                d = np.linalg.norm(c - t["centroid"]) / diag
                if d < bestd:
                    best, bestd = tid, d
            if best is not None and bestd <= self.max_dist:
                t = self.tracks[best]; used.add(best)
                t["centroid"], t["box"], t["age"] = c, box, 0
                t["is_leaf"], t["leaf_p"] = is_leaf, leaf_p
                if probs is not None:
                    t["probs"] = self.ema * t.get("probs", probs) + (1 - self.ema) * probs
            else:
                tid = self.next_id; self.next_id += 1
                self.tracks[tid] = {"centroid": c, "box": box, "age": 0,
                                    "is_leaf": is_leaf, "leaf_p": leaf_p,
                                    "probs": probs}
                used.add(tid)
        self.tracks = {k: v for k, v in self.tracks.items() if v["age"] <= self.ttl}
        return list(self.tracks.values())


# ------------------------------------------------------------
# Drawing
# ------------------------------------------------------------
def draw_label(frame, box, text, color):
    H, W = frame.shape[:2]
    x, y, w, h = box
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
    scale, thick = 0.6, 2
    (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    bw, bh = tw + 10, th + bl + 8
    # prefer the strip just above the box; if it would clip off the top, put it
    # just inside the top edge of the box instead. Clamp x to stay on-screen.
    lx = min(max(0, x), W - bw)
    ly = y - bh
    if ly < 0:
        ly = y + 2
    ly = min(ly, H - bh)
    cv2.rectangle(frame, (lx, ly), (lx + bw, ly + bh), color, -1)
    cv2.putText(frame, text, (lx + 5, ly + th + 4), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (255, 255, 255), thick, cv2.LINE_AA)


def classify_box(frame, box, ens, gate, gate_thr, conf):
    x, y, w, h = box
    crop = frame[y:y + h, x:x + w]
    if crop.size == 0 or w < 24 or h < 24:
        return None
    pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    is_leaf, leaf_p = gate.is_leaf(pil, threshold=gate_thr)
    if not is_leaf:
        return (box, False, leaf_p, None)
    probs = P._predict_tensor_batch(ens, pil, tta=False)  # fast, no TTA
    return (box, True, leaf_p, probs)


def track_to_drawing(t, class_names, conf):
    box = t["box"]
    if not t["is_leaf"]:
        return box, f"Not a leaf {t['leaf_p']:.2f}", C_NOTLEAF
    probs = t.get("probs")
    if probs is None:
        return box, f"Leaf {t['leaf_p']:.2f}", C_UNCERT
    k = int(np.argmax(probs)); p = float(probs[k]); name = class_names[k]
    if p < conf:
        return box, f"Uncertain ({name} {p*100:.0f}%)", C_UNCERT
    color = C_HEALTHY if name.lower().startswith("healthy") else C_DISEASE
    return box, f"{name.replace('_', ' ')} {p*100:.0f}%", color


# ------------------------------------------------------------
# Runners
# ------------------------------------------------------------
def get_dets(frame, args, ens, gate):
    boxes = center_roi(frame) if args.roi else detect_leaf_boxes(frame, args.max_boxes)
    if not boxes:
        boxes = center_roi(frame)
    dets = []
    for b in boxes:
        d = classify_box(frame, b, ens, gate, args.gate_thr, args.conf)
        if d is not None:
            dets.append(d)
    return dets


def run_image_mode(paths, args, ens, gate, class_names, save):
    os.makedirs(save, exist_ok=True) if save else None
    for path in paths:
        frame = cv2.imread(path)
        if frame is None:
            print("  skip (unreadable):", path); continue
        dets = get_dets(frame, args, ens, gate)
        for box, is_leaf, leaf_p, probs in dets:
            t = {"box": box, "is_leaf": is_leaf, "leaf_p": leaf_p, "probs": probs}
            b, text, color = track_to_drawing(t, class_names, args.conf)
            draw_label(frame, b, text, color)
        if save:
            out = os.path.join(save, "annot_" + os.path.basename(path))
            cv2.imwrite(out, frame); print("  wrote", out)
        # console summary
        summ = ", ".join(track_to_drawing({"box": d[0], "is_leaf": d[1], "leaf_p": d[2],
                                            "probs": d[3]}, class_names, args.conf)[1] for d in dets)
        print(f"  {os.path.basename(path)} -> {summ or '(no region)'}")


def run_video_mode(source, args, ens, gate, class_names):
    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 20
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    diag = float(np.hypot(W, H))
    writer = None
    if args.save:
        writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    can_display = (not args.no_display) and bool(os.environ.get("DISPLAY")) and hasattr(cv2, "imshow")
    tracker = Tracker(len(class_names))
    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % args.every == 0:
            dets = get_dets(frame, args, ens, gate)
            tracks = tracker.update(dets, diag)
        else:
            tracks = list(tracker.tracks.values())
        for t in tracks:
            b, text, color = track_to_drawing(t, class_names, args.conf)
            draw_label(frame, b, text, color)
        cv2.putText(frame, "FarmEasy live", (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2, cv2.LINE_AA)
        if writer:
            writer.write(frame)
        if can_display:
            try:
                cv2.imshow("FarmEasy", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            except cv2.error:
                # headless OpenCV build / no GUI -> stop trying to display
                print("(no GUI available; install opencv-python for a live window. "
                      "Continuing to write output only.)")
                can_display = False
        fi += 1
    cap.release()
    if writer:
        writer.release(); print("saved annotated video ->", args.save)
    if can_display:
        cv2.destroyAllWindows()
    print(f"processed {fi} frames")


def main():
    args = parse_args()
    keys = None if args.models == "all" else [k.strip() for k in args.models.split(",")]
    ens = P.load_ensemble(args.out_dir, keys=keys)
    gate = load_leaf_gate(args.gate_dir)
    class_names = ens.class_names
    print("Disease classes:", class_names)
    print("Using models:", "all" if keys is None else keys)

    src = args.source
    is_dir = os.path.isdir(src)
    is_img = os.path.isfile(src) and src.lower().endswith(IMG_EXT)
    if is_dir or is_img:
        if is_dir:
            paths = sorted(os.path.join(src, f) for f in os.listdir(src)
                           if f.lower().endswith(IMG_EXT))
        else:
            paths = [src]
        save = args.save or os.path.join(BASE_DIR, "live_out")
        print(f"image mode: {len(paths)} image(s) -> {save}")
        run_image_mode(paths, args, ens, gate, class_names, save)
    else:
        run_video_mode(src, args, ens, gate, class_names)


if __name__ == "__main__":
    main()
