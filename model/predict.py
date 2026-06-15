# ============================================================
#  CORN LEAF DISEASE — ENSEMBLE PREDICTOR
# ============================================================
#  Loads the models described in ensemble_out/manifest.json and
#  soft-votes their probabilities. Because it reads each model's
#  architecture + normalization straight from the manifest written
#  at train time, it can NEVER drift out of sync with training
#  (the bug in the old predict_bagging.py, which built a different
#  architecture than it was trained with).
#
#  Optional hflip test-time augmentation (TTA) for a small free boost.
#
#  Usage:
#    from predict import load_ensemble, predict_pil, predict_path
#    ens = load_ensemble()                       # load once
#    label, probs = predict_path("leaf.jpg", ens)
#
#    python predict.py leaf.jpg                   # CLI
# ============================================================

import os
import json
import argparse

import torch
import torch.nn as nn
from torchvision import transforms as T
from PIL import Image

import timm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(BASE_DIR, "ensemble_out")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Ensemble:
    def __init__(self, models, transforms, idx_to_class, weights=None):
        self.models = models            # list[nn.Module]
        self.transforms = transforms    # list[Compose] (parallel to models)
        self.idx_to_class = idx_to_class
        self.class_names = [idx_to_class[i] for i in range(len(idx_to_class))]
        # Per-model soft-vote weights (parallel to models). Default: equal.
        if weights is None:
            weights = [1.0] * len(models)
        s = float(sum(weights)) or 1.0
        self.weights = [w / s for w in weights]


def load_ensemble(out_dir=DEFAULT_OUT, keys=None):
    """Load the soft-vote ensemble. Pass `keys` (e.g. ["effb3"]) to load only a
    subset of models — useful for fast live-video inference."""
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path) as f:
        man = json.load(f)

    img_size = man["img_size"]
    vflip_tta = bool(man.get("vflip_tta", False))
    idx_to_class = {int(k): v for k, v in man["idx_to_class"].items()}
    num_classes = len(idx_to_class)
    weight_map = man.get("ensemble_weights", {})

    model_entries = man["models"]
    if keys:
        model_entries = [m for m in model_entries if m["key"] in keys]
        if not model_entries:
            raise ValueError(f"none of {keys} found in manifest")

    models, transforms, weights = [], [], []
    for m in model_entries:
        model = timm.create_model(m["timm"], pretrained=False, num_classes=num_classes)
        state = torch.load(os.path.join(out_dir, m["ckpt"]), map_location=DEVICE)
        model.load_state_dict(state)
        model.eval().to(DEVICE)
        models.append(model)

        # Mirror training's eval transform exactly: aspect-preserving resize to
        # size/crop_pct, then center-crop. Both crop_pct and the per-model input
        # size are stored in the manifest (swin trains at 224, EffNets at 288).
        m_size = int(m.get("img_size") or img_size)
        crop_pct = float(m.get("crop_pct") or 0.95)
        resize_to = int(round(m_size / crop_pct))
        transforms.append(T.Compose([
            T.Resize(resize_to),
            T.CenterCrop(m_size),
            T.ToTensor(),
            T.Normalize(m["mean"], m["std"]),
        ]))
        weights.append(weight_map.get(m["key"], 1.0))

    print(f"Loaded {len(models)} models from {out_dir}")
    ens = Ensemble(models, transforms, idx_to_class, weights)
    ens.vflip_tta = vflip_tta
    return ens


@torch.no_grad()
def _predict_tensor_batch(ens, pil_img, tta=True):
    """Weighted average of softmax probabilities across all models (each with
    its own preprocessing + soft-vote weight), optionally with flip TTA."""
    rgb = pil_img.convert("RGB")
    vflip = tta and getattr(ens, "vflip_tta", False)
    prob_sum = None
    for model, tf, wt in zip(ens.models, ens.transforms, ens.weights):
        x = tf(rgb).unsqueeze(0).to(DEVICE)
        views = [x]
        if tta:
            views.append(torch.flip(x, dims=[3]))        # horizontal
            if vflip:
                views.append(torch.flip(x, dims=[2]))    # vertical
        model_probs = None
        for v in views:
            p = torch.softmax(model(v).float(), dim=1)
            model_probs = p if model_probs is None else model_probs + p
        model_probs = model_probs / len(views)          # avg over TTA views
        weighted = model_probs * wt
        prob_sum = weighted if prob_sum is None else prob_sum + weighted
    return prob_sum.cpu().numpy()[0]                     # weights already sum to 1


def predict_pil(pil_img, ens=None, tta=True):
    if ens is None:
        ens = load_ensemble()
    probs = _predict_tensor_batch(ens, pil_img, tta=tta)
    pred_idx = int(probs.argmax())
    label = ens.idx_to_class[pred_idx]
    prob_dict = {ens.idx_to_class[i]: float(probs[i]) for i in range(len(probs))}
    return label, prob_dict


def predict_path(img_path, ens=None, tta=True):
    return predict_pil(Image.open(img_path), ens=ens, tta=tta)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="path to a leaf image")
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--no-tta", action="store_true")
    args = ap.parse_args()

    ens = load_ensemble(args.out_dir)
    label, probs = predict_path(args.image, ens, tta=not args.no_tta)
    print("\nPrediction:", label)
    for cls, p in sorted(probs.items(), key=lambda kv: -kv[1]):
        print(f"  {cls:16s} {p:.4f}")
