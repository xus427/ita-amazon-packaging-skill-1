"""
环境变量配置加载与读取工具。
"""

import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / ".env"

# 显式加载项目根目录的 .env，避免在不同工作目录启动时读取失败。
load_dotenv(dotenv_path=DOTENV_PATH)


def get_env(key: str, default: str = "") -> str:
    """读取字符串环境变量（未设置时返回 default）。"""
    return os.getenv(key, default)


def get_env_int(key: str, default: int) -> int:
    """读取整数环境变量，格式错误时回退到默认值。"""
    value = os.getenv(key)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """读取布尔环境变量，支持 true/1/yes/on。"""
    value = os.getenv(key)
    if value is None:
        return default

    return value.strip().lower() in {"true", "1", "yes", "on"}
