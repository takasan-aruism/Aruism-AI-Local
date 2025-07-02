# Dockerfile.app
FROM python:3.10-slim
WORKDIR /workspace/Aruism-AI-Local
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["tail", "-f", "/dev/null"]
