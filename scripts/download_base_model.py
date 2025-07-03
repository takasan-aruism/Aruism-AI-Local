# Dockerfile.tensorrt
FROM nvcr.io/nvidia/pytorch:24.10-py3

WORKDIR /workspace/Aruism-AI-Local

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    wget \
    curl \
    build-essential \
    python3-dev \
    vim \
    htop \
    nvtop \
    libopenmpi-dev \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# 既存のrequirements.txtをコピー
COPY requirements.txt .

# Pythonパッケージのインストール
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# torch-tensorrtを削除（競合回避）
RUN pip uninstall torch-tensorrt -y || true

# TensorRT-LLMと関連パッケージのインストール
RUN pip install tensorrt==10.11.0.33 && \
    pip install tensorrt_llm -U --pre --extra-index-url https://pypi.nvidia.com && \
    pip install transformers==4.51.1 accelerate scipy sentencepiece protobuf && \
    pip install huggingface-hub datasets pynvml

# ディレクトリ作成
RUN mkdir -p models engines scripts cache

CMD ["tail", "-f", "/dev/null"]