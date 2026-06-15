# FarmEasy Backend Deployment

This backend is a FastAPI service that loads the model files from `model/`.
Use Docker for hosting so the Python, PyTorch, OpenCV, and model files travel
together.

## 1. Test the container locally

From the project root:

```bash
docker build -f server/Dockerfile -t farmeasy-backend .
docker run --rm -p 8000:8000 farmeasy-backend
```

Check it:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata
```

The public API docs will be available at:

```text
http://localhost:8000/docs
```

## 2. Deploy with Docker

Use these settings on a Docker-based host such as a VPS, Render, Railway, Fly.io,
or a cloud VM:

- Build context: project root
- Dockerfile path: `server/Dockerfile`
- Exposed port: `8000`
- Start command: leave blank, or use the Dockerfile default
- Health check path: `/health`

Recommended environment variables:

```bash
FARMEASY_HOST=0.0.0.0
FARMEASY_PORT=8000
FARMEASY_BUNDLE_DIR=/app/model
FARMEASY_MODELS=effb3
FARMEASY_TTA=0
FARMEASY_LOAD_ON_STARTUP=1
FARMEASY_SERIALIZE_INFERENCE=1
FARMEASY_CORS_ORIGINS=*
```

Most hosts inject a `PORT` variable. The Dockerfile already honors `PORT` when
the host provides it.

## 3. VPS quick start

On a Linux server with Docker installed:

```bash
git clone <your-repo-url> farmeasy
cd farmeasy
docker build -f server/Dockerfile -t farmeasy-backend .
docker run -d \
  --name farmeasy-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  farmeasy-backend
```

For HTTPS, put Nginx or Caddy in front of the container and proxy to
`http://127.0.0.1:8000`.

## 4. Connect the Flutter app

Build or run Flutter with the deployed backend URL:

```bash
flutter run --dart-define=FARMEASY_API_BASE_URL=https://your-backend-domain.com
```

For Android release:

```bash
flutter build apk --release \
  --dart-define=FARMEASY_API_BASE_URL=https://your-backend-domain.com
```

The app uses this value in `farm_easy_app/lib/core/app_constants.dart`.

## Notes

- The default model setting is `FARMEASY_MODELS=effb3` because this repository
  only includes `effb3_best.pth` from the disease ensemble.
- Do not set `FARMEASY_MODELS=all` unless the other checkpoint files listed in
  `model/ensemble_out_v2/manifest.json` are present.
- CPU hosting works, but PyTorch model startup can be slow. Use at least 1-2 GB
  RAM for a small demo, and more if you expect concurrent video predictions.
