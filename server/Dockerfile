FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FARMEASY_HOST=0.0.0.0
ENV FARMEASY_PORT=8000
ENV FARMEASY_BUNDLE_DIR=/app/model
ENV FARMEASY_MODELS=effb3
ENV FARMEASY_TTA=0
ENV FARMEASY_LOAD_ON_STARTUP=1
ENV FARMEASY_MCP_ENABLED=0
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV TORCH_NUM_THREADS=1
ENV TORCH_NUM_INTEROP_THREADS=1
ENV OMP_WAIT_POLICY=PASSIVE
ENV MALLOC_ARENA_MAX=2

WORKDIR /app

COPY server/requirements.txt /app/server/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.12.0 torchvision==0.27.0
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY model /app/model
COPY server /app/server

EXPOSE 8000

CMD ["sh", "-c", "python -m server --host 0.0.0.0 --port ${PORT:-${FARMEASY_PORT:-8000}}"]
