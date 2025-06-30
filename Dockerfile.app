# Dockerfile.app
FROM python:3.12-slim

WORKDIR /workspace/Aruism-AI-Local

# 必要なPythonライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 以降、このコンテナに入って作業する
CMD ["/bin/bash"]