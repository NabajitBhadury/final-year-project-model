# ============================================================
#  FarmEasy — high-level inference API  (single integration point)
# ============================================================
#  This is the ONE class an application needs. It wraps the leaf-gate and the
#  disease ensemble behind a single analyze() call with a stable JSON-friendly
#  output contract.
#
#      from farmeasy import FarmEasy
#      from PIL import Image
#      fe = FarmEasy()                       # loads models once (do this at startup)
#      result = fe.analyze(Image.open("leaf.jpg"))
#
#  result (dict):
#      {
#        "is_leaf":      true/false,        # leaf-gate decision
#        "leaf_prob":    0.0-1.0,           # gate confidence it is a corn leaf
#        "label":        "Gray_Leaf_Spot",  # None if not a leaf or uncertain
#        "confidence":   0.0-1.0,           # top-class probability
#        "status":       "ok" | "not_leaf" | "uncertain",
#        "probabilities": {class: prob, ...}
#      }
# ============================================================
import os

from PIL import Image

import predict as P
from leaf_gate import load_leaf_gate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class FarmEasy:
    def __init__(self,
                 ensemble_dir=os.path.join(BASE_DIR, "ensemble_out_v2"),
                 gate_dir=os.path.join(BASE_DIR, "leaf_gate_out"),
                 models="effb3",          # "effb3" (fast) | "all" | "effb3,effb4"
                 tta=False,               # flip test-time augmentation (slower, +accuracy)
                 gate_threshold=0.5,      # min p(leaf) to accept
                 conf_threshold=0.45):    # min top-class prob to commit to a label
        keys = None if models == "all" else [k.strip() for k in models.split(",")]
        self.ens = P.load_ensemble(ensemble_dir, keys=keys)
        self.gate = load_leaf_gate(gate_dir)
        self.tta = tta
        self.gate_threshold = gate_threshold
        self.conf_threshold = conf_threshold
        self.class_names = self.ens.class_names

    def analyze(self, pil_img):
        img = pil_img.convert("RGB")
        is_leaf, leaf_p = self.gate.is_leaf(img, threshold=self.gate_threshold)
        if not is_leaf:
            return {"is_leaf": False, "leaf_prob": round(leaf_p, 4),
                    "label": None, "confidence": None, "status": "not_leaf",
                    "probabilities": {}}
        label, probs = P.predict_pil(img, self.ens, tta=self.tta)
        top = max(probs.values())
        status = "ok" if top >= self.conf_threshold else "uncertain"
        return {"is_leaf": True, "leaf_prob": round(leaf_p, 4),
                "label": label if status == "ok" else None,
                "confidence": round(float(top), 4), "status": status,
                "probabilities": {k: round(float(v), 4) for k, v in probs.items()}}

    def analyze_path(self, path):
        return self.analyze(Image.open(path))


if __name__ == "__main__":
    import sys, json
    fe = FarmEasy()
    for p in sys.argv[1:]:
        print(p)
        print(json.dumps(fe.analyze_path(p), indent=2))
