# ============================================================
#  Export FarmEasy models to ONNX  (for mobile / on-device / cross-runtime)
# ============================================================
#  Produces:
#     onnx_out/leaf_gate.onnx        (MobileNetV3 leaf/not-leaf, 2 logits)
#     onnx_out/<key>.onnx            (each chosen disease model, 5 logits)
#     onnx_out/preprocess.json       (resize/crop/mean/std/classes per model)
#
#  On mobile, run leaf_gate.onnx first; if leaf, run the disease model(s) and
#  softmax-average their logits (soft-vote). Preprocessing MUST match
#  preprocess.json exactly (per-model resize -> center-crop -> normalize).
#
#  Install:  pip install onnx onnxruntime
#  Run:      python export_onnx.py --models effb3            # smallest mobile bundle
#            python export_onnx.py --models effb3,effb4      # stronger
# ============================================================
import os
import json
import argparse

import torch
import timm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def export_one(timm_name, ckpt, num_classes, size, onnx_path):
    model = timm.create_model(timm_name, pretrained=False, num_classes=num_classes)
    model.load_state_dict(torch.load(ckpt, map_location="cpu"))
    model.eval()
    dummy = torch.randn(1, 3, size, size)
    torch.onnx.export(
        model, dummy, onnx_path,
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )
    print("  wrote", onnx_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble-dir", default=os.path.join(BASE_DIR, "ensemble_out_v2"))
    ap.add_argument("--gate-dir", default=os.path.join(BASE_DIR, "leaf_gate_out"))
    ap.add_argument("--out-dir", default=os.path.join(BASE_DIR, "onnx_out"))
    ap.add_argument("--models", default="effb3", help="'all' or comma list of keys")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    man = json.load(open(os.path.join(args.ensemble_dir, "manifest.json")))
    idx2 = {int(k): v for k, v in man["idx_to_class"].items()}
    classes = [idx2[i] for i in range(len(idx2))]
    keys = None if args.models == "all" else [k.strip() for k in args.models.split(",")]
    pre = {"classes": classes, "leaf_gate": None, "disease_models": []}

    # leaf gate
    gman = json.load(open(os.path.join(args.gate_dir, "leaf_gate_manifest.json")))
    export_one(gman["timm"], os.path.join(args.gate_dir, gman["ckpt"]), 2,
               gman["img_size"], os.path.join(args.out_dir, "leaf_gate.onnx"))
    sz = gman["img_size"]
    pre["leaf_gate"] = {"file": "leaf_gate.onnx", "img_size": sz,
                        "resize": int(sz / 0.9), "crop": sz,
                        "mean": gman["mean"], "std": gman["std"],
                        "leaf_index": gman["leaf_index"], "threshold": gman["threshold"]}

    # disease models
    for m in man["models"]:
        if keys and m["key"] not in keys:
            continue
        size = int(m.get("img_size") or man["img_size"])
        crop_pct = float(m.get("crop_pct") or 0.95)
        out = os.path.join(args.out_dir, f"{m['key']}.onnx")
        export_one(m["timm"], os.path.join(args.ensemble_dir, m["ckpt"]),
                   len(classes), size, out)
        pre["disease_models"].append({
            "key": m["key"], "file": f"{m['key']}.onnx", "img_size": size,
            "resize": int(round(size / crop_pct)), "crop": size,
            "mean": m["mean"], "std": m["std"],
            "weight": man.get("ensemble_weights", {}).get(m["key"], 1.0)})

    json.dump(pre, open(os.path.join(args.out_dir, "preprocess.json"), "w"), indent=2)
    print("wrote", os.path.join(args.out_dir, "preprocess.json"))
    print("\nMobile flow: preprocess -> leaf_gate.onnx (softmax, index",
          pre["leaf_gate"]["leaf_index"], ">= threshold) -> disease model(s) -> "
          "softmax & weight-average logits -> argmax over classes.")


if __name__ == "__main__":
    main()
