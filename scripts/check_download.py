# scripts/check_download.py
import os

model_path = "/workspace/models/llama4-scout-4bit"
expected_files = [
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "model.safetensors",  # または複数の分割ファイル
]

print(f"Checking model at: {model_path}")
print("-" * 50)

# ディレクトリサイズ
total_size = 0
for root, dirs, files in os.walk(model_path):
    for file in files:
        filepath = os.path.join(root, file)
        total_size += os.path.getsize(filepath)

print(f"Total size: {total_size / (1024**3):.2f} GB")

# ファイルリスト
print("\nFiles found:")
for root, dirs, files in os.walk(model_path):
    for file in sorted(files):
        filepath = os.path.join(root, file)
        size = os.path.getsize(filepath) / (1024**3)
        print(f"  {file}: {size:.2f} GB")

# 必要なファイルの確認
print("\nRequired files check:")
for file in expected_files:
    exists = any(file in f for f in os.listdir(model_path))
    print(f"  {file}: {'✓' if exists else '✗'}")
