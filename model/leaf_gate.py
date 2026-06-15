# ============================================================
#  LEAF-GATE  —  inference loader
# ============================================================
#  Loads the MobileNetV3 leaf/not-leaf classifier trained by train_leaf_gate.py
#  and exposes a simple is_leaf() check used by the live pipeline.
# ============================================================
import os
import json

import torch
from torchvision import transforms as T
from PIL import Image
import timm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(BASE_DIR, "leaf_gate_out")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class LeafGate:
    def __init__(self, model, transform, leaf_index, threshold):
        self.model = model
        self.transform = transform
        self.leaf_index = leaf_index
        self.threshold = threshold

    @torch.no_grad()
    def leaf_prob(self, pil_img):
        x = self.transform(pil_img.convert("RGB")).unsqueeze(0).to(DEVICE)
        p = torch.softmax(self.model(x).float(), dim=1)[0, self.leaf_index].item()
        return p

    def is_leaf(self, pil_img, threshold=None):
        p = self.leaf_prob(pil_img)
        thr = self.threshold if threshold is None else threshold
        return p >= thr, p


def load_leaf_gate(out_dir=DEFAULT_OUT):
    man = json.load(open(os.path.join(out_dir, "leaf_gate_manifest.json")))
    model = timm.create_model(man["timm"], pretrained=False, num_classes=2)
    state = torch.load(os.path.join(out_dir, man["ckpt"]), map_location=DEVICE)
    model.load_state_dict(state)
    model.eval().to(DEVICE)
    sz = man["img_size"]
    tf = T.Compose([
        T.Resize(int(sz / 0.9)), T.CenterCrop(sz),
        T.ToTensor(), T.Normalize(man["mean"], man["std"]),
    ])
    print(f"Loaded leaf-gate from {out_dir} (val_f1={man.get('val_f1', '?')})")
    return LeafGate(model, tf, int(man["leaf_index"]), float(man["threshold"]))


if __name__ == "__main__":
    import sys
    gate = load_leaf_gate()
    for path in sys.argv[1:]:
        ok, p = gate.is_leaf(Image.open(path))
        print(f"{'LEAF    ' if ok else 'NOT-LEAF'}  p(leaf)={p:.3f}  {path}")
