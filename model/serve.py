# ============================================================
#  FarmEasy — REST inference server  (FastAPI)
# ============================================================
#  A thin HTTP wrapper around farmeasy.FarmEasy so any app (web / mobile /
#  desktop) can get predictions over the network without bundling PyTorch.
#
#  Install:  pip install fastapi "uvicorn[standard]" python-multipart pillow
#  Run:      uvicorn serve:app --host 0.0.0.0 --port 8000
#            (or:  python serve.py)
#
#  Endpoints:
#    GET  /health                      -> {"status":"ok","classes":[...]}
#    POST /predict   (multipart file)  -> analysis JSON (see farmeasy.py)
#
#  Example:
#    curl -F "file=@leaf.jpg" http://localhost:8000/predict
# ============================================================
import io
import os

from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image

from farmeasy import FarmEasy

# Configure via env vars so deployment doesn't need code edits.
MODELS = os.environ.get("FARMEASY_MODELS", "effb3")      # "effb3" | "all" | "effb3,effb4"
TTA = os.environ.get("FARMEASY_TTA", "0") == "1"

app = FastAPI(title="FarmEasy Corn Disease API", version="1.0")
fe = FarmEasy(models=MODELS, tta=TTA)   # loads models once at import/startup


@app.get("/health")
def health():
    return {"status": "ok", "classes": fe.class_names, "models": MODELS, "tta": TTA}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        data = await file.read()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(status_code=400, detail="could not read image")
    return fe.analyze(img)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
