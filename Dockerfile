FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Use direct, pinned CPU wheel URLs. The index currently redirects pip to a
# host that Docker Desktop cannot resolve reliably on this machine.
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt \
    && pip install \
        'https://download.pytorch.org/whl/cpu/torch-2.1.0%2Bcpu-cp310-cp310-linux_x86_64.whl' \
        'https://download.pytorch.org/whl/cpu/torchvision-0.16.0%2Bcpu-cp310-cp310-linux_x86_64.whl' \
    && pip install --no-deps 'mmengine==0.10.7' \
    && pip install --no-deps 'mmcv==2.1.0' -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.1/index.html \
    && pip install 'addict==2.4.0' 'yapf==0.43.0' 'termcolor==3.3.0' 'matplotlib<3.9' \
    && pip install 'mmdet==3.3.0'

# MMEngine imports its logging/config helpers at runtime; keep this explicit instead
# of relying on an unrelated CLI package to bring it in transitively.
RUN pip install 'rich>=13,<14'

COPY . /app
RUN mkdir -p /data/uploads /data/results /models /dataset /work_dirs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
