FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && pip install 'torch>=2.1,<2.6' 'torchvision>=0.16,<0.21' \
    && mim install 'mmengine>=0.10,<1' \
    && mim install 'mmcv>=2.0.0,<2.2.0' \
    && pip install 'mmdet==3.3.0'

COPY . /app
RUN mkdir -p /data/uploads /data/results /models /dataset /work_dirs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
