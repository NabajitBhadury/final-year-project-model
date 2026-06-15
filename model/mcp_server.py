# ============================================================
#  FarmEasy — MCP server  (Model Context Protocol)
# ============================================================
#  Exposes the trained corn-leaf disease pipeline (leaf-gate + ensemble) as
#  MCP tools, so an LLM / agent client (e.g. Claude Desktop, or any MCP host)
#  can analyze leaf images by calling a tool.
#
#  Everything runs LOCALLY on this machine — no training, no GPU required.
#  On Apple Silicon (M-series) it runs on CPU automatically; effb3 is small and
#  fast there. The trained weights ship in the bundle (ensemble_out_v2/,
#  leaf_gate_out/), so there is nothing to train.
#
#  Install:
#      pip install "mcp[cli]" torch torchvision timm pillow numpy
#  Run (stdio transport, the usual way an MCP client launches it):
#      python mcp_server.py
#
#  Register it with an MCP client. Example Claude Desktop config
#  (claude_desktop_config.json):
#      {
#        "mcpServers": {
#          "farmeasy": {
#            "command": "python",
#            "args": ["/absolute/path/to/mcp_server.py"]
#          }
#        }
#      }
#
#  Optional env var:  FARMEASY_MODELS=effb3   (default; or "all", "effb3,effb4")
# ============================================================
import base64
import io
import os

from PIL import Image
from mcp.server.fastmcp import FastMCP

from farmeasy import FarmEasy

MODELS = os.environ.get("FARMEASY_MODELS", "effb3")

# Load the models ONCE at startup (slow); the instance is reused for every call.
fe = FarmEasy(models=MODELS)

mcp = FastMCP("farmeasy")


@mcp.tool()
def analyze_corn_leaf(image_path: str = "", image_base64: str = "") -> dict:
    """Analyze a photo of a corn leaf for disease.

    Provide exactly one of:
      - image_path:   a path to an image file on this machine, or
      - image_base64: base64-encoded image bytes (e.g. an uploaded photo).

    Returns a dict:
      is_leaf       (bool)  did the leaf-gate accept this as a corn leaf
      leaf_prob     (float) gate confidence it is a leaf, 0-1
      label         (str|None) predicted disease class (None if not a leaf / uncertain)
      confidence    (float|None) top-class probability
      status        (str)  "ok" | "not_leaf" | "uncertain"
      probabilities (dict) per-class probabilities
    Classes: Blight, Common_Rust, Gray_Leaf_Spot, Healthy, Insects_damage.
    """
    if image_path:
        img = Image.open(image_path)
    elif image_base64:
        img = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    else:
        raise ValueError("Provide either image_path or image_base64.")
    return fe.analyze(img)


@mcp.tool()
def list_disease_classes() -> list:
    """Return the list of disease classes the model can predict."""
    return list(fe.class_names)


if __name__ == "__main__":
    mcp.run()
