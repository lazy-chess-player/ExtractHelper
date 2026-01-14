from __future__ import annotations
import os
from pathlib import Path

"""
Bootstrap 模块
用于在项目启动时加载环境变量（如 .env 文件），并配置 Hugging Face 镜像等。
"""

def _repo_root() -> Path:
    """获取代码仓库根目录"""
    return Path(__file__).resolve().parents[1]

def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    """
    解析 .env 文件内容
    :param dotenv_path: .env 文件路径
    :return: 键值对字典
    """
    env: dict[str, str] = {}
    if not dotenv_path.exists():
        return env
    for line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def bootstrap() -> None:
    """
    初始化环境
    1. 加载 .env 到 os.environ
    2. 设置 HF_ENDPOINT 镜像
    3. 设置 HF_HOME 缓存目录
    """
    root = _repo_root()
    dot = _load_dotenv(root / ".env")

    for k, v in dot.items():
        os.environ.setdefault(k, v)

    # 默认使用 hf-mirror 镜像加速下载
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    # 禁用符号链接警告
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    # 设置 Hugging Face 缓存目录到 data/kb/hf_home，避免占用 C 盘
    os.environ.setdefault("HF_HOME", str(root / "data" / "kb" / "hf_home"))
