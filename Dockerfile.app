# Dockerfile.app
FROM python:3.12-slim

WORKDIR /workspace/Aruism-AI-Local

# プロジェクトに必要なPythonライブラリをインストール
# プロジェクトルートにあるrequirements.txtをコピーする
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# コンテナを起動したままにするためのコマンド
CMD ["tail", "-f", "/dev/null"]