"""自检 .env 中的 SD_API_URL 是否与可用的 AUTOMATIC1111 API 一致。"""
import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _root)

from lib.config import get_env  # noqa: E402
import requests  # noqa: E402


def main() -> int:
    base = (get_env("SD_API_URL", "") or "").strip().rstrip("/")
    if not base:
        print("[FAIL] .env 中未设置 SD_API_URL")
        return 1
    url = base + "/sdapi/v1/sd-models"
    print("[INFO] SD_API_URL =", base)
    print("[INFO] GET", url)
    try:
        r = requests.get(url, timeout=5)
        print("[INFO] HTTP", r.status_code)
        if r.status_code != 200:
            print("[FAIL] 未返回 200，请确认 WebUI 已用 --api 启动")
            return 1
        data = r.json()
        if not isinstance(data, list):
            print("[FAIL] 响应不是模型列表 JSON")
            return 1
        print("[OK] AUTOMATIC1111 API 可用，模型数量:", len(data))
        return 0
    except Exception as e:
        print("[FAIL]", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
