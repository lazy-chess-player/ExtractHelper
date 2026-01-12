from huggingface_hub import snapshot_download
from pathlib import Path

repo_id = "Qwen/Qwen2.5-3B-Instruct-GGUF"
target_dir = Path("data/models")
target_dir.mkdir(parents=True, exist_ok=True)

# 下载 GGUF 文件
snapshot_download(
    repo_id=repo_id,
    allow_patterns=["qwen2.5-3b-instruct-q4_k_m.gguf"],
    local_dir=str(target_dir),
    local_dir_use_symlinks=False,
)

print("DONE. Check data/models/")

