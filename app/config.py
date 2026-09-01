"""应用配置：支持环境变量和网页导入的本地 API Key。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_KEY_FILE = PROJECT_ROOT / "runtime" / "api_key.txt"
_runtime_api_key: str | None = None


def get_api_key() -> str:
    """返回当前 Key；网页导入值优先，其次是环境变量。"""
    if _runtime_api_key is not None:
        return _runtime_api_key
    if API_KEY_FILE.is_file():
        return API_KEY_FILE.read_text(encoding="utf-8").strip()
    return DEEPSEEK_API_KEY.strip()


def api_key_source() -> str | None:
    """返回 Key 来源，不暴露 Key 内容。"""
    if _runtime_api_key is not None or API_KEY_FILE.is_file():
        return "runtime_file"
    if DEEPSEEK_API_KEY.strip():
        return "environment"
    return None


def save_api_key(api_key: str) -> Path:
    """将 Key 原子写入本地 txt，并立即供当前进程使用。"""
    normalized = api_key.strip()
    if not normalized:
        raise ValueError("API Key 不能为空")
    if any(char.isspace() for char in normalized):
        raise ValueError("API Key 不能包含空白字符")

    API_KEY_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp_file = API_KEY_FILE.with_suffix(".tmp")
    temp_file.write_text(normalized, encoding="utf-8")
    temp_file.chmod(0o600)
    temp_file.replace(API_KEY_FILE)
    API_KEY_FILE.chmod(0o600)

    global _runtime_api_key
    _runtime_api_key = normalized
    return API_KEY_FILE
