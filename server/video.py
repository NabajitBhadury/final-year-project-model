"""Video frame sampling and FarmEasy inference."""

from __future__ import annotations

import contextlib
import os
import tempfile
import time
import uuid
from typing import Optional

from PIL import Image

from .inference import get_service


def analyze_video_bytes(
    data: bytes,
    *,
    filename: Optional[str],
    content_type: Optional[str],
    sample_every_n_frames: int,
    max_frames: int,
    gate_threshold: Optional[float],
    conf_threshold: Optional[float],
    tta: Optional[bool],
) -> dict:
    if sample_every_n_frames < 1:
        raise ValueError("sample_every_n_frames must be at least 1")
    if max_frames < 1:
        raise ValueError("max_frames must be at least 1")

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "video analysis requires opencv-python-headless; install server/requirements.txt"
        ) from exc

    request_id = uuid.uuid4().hex
    start = time.perf_counter()
    suffix = ""
    if filename and "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1]

    temp_path = None
    capture = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            temp_path = tmp.name

        capture = cv2.VideoCapture(temp_path)
        if not capture.isOpened():
            raise ValueError("could not read video")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or None
        total_raw = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        total_frames = total_raw if total_raw > 0 else None
        duration_sec = round(total_raw / fps, 3) if total_raw and fps else None

        frames = []
        status_counts: dict[str, int] = {}
        label_counts: dict[str, int] = {}
        frame_index = 0

        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % sample_every_n_frames != 0:
                frame_index += 1
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            timestamp_ms = (frame_index / fps * 1000.0) if fps else 0.0
            image_info = {
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": None,
                "filename": filename,
                "content_type": content_type,
            }
            prediction = get_service().analyze_image(
                image,
                gate_threshold=gate_threshold,
                conf_threshold=conf_threshold,
                tta=tta,
                image_info=image_info,
            )
            status = prediction["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            if prediction.get("label"):
                label = prediction["label"]
                label_counts[label] = label_counts.get(label, 0) + 1

            frames.append(
                {
                    "frame_index": frame_index,
                    "timestamp_ms": round(timestamp_ms, 2),
                    "prediction": prediction,
                }
            )
            frame_index += 1

        if not frames:
            raise ValueError("no readable frames found in video")

        return {
            "request_id": request_id,
            "filename": filename,
            "content_type": content_type,
            "total_frames": total_frames,
            "fps": round(fps, 3) if fps else None,
            "duration_sec": duration_sec,
            "sample_every_n_frames": sample_every_n_frames,
            "max_frames": max_frames,
            "sampled_frames": len(frames),
            "status_counts": status_counts,
            "label_counts": label_counts,
            "frames": frames,
            "processing_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    finally:
        if capture is not None:
            capture.release()
        if temp_path:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
