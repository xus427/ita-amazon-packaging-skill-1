"""
飞书图片上传工具。
将本地图片上传到飞书服务器，获取 image_key 以便在消息卡片中展示。
"""

import os
import time
import requests
from typing import Dict, Optional


class FeishuUploader:
    """飞书图片上传器"""

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/images"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token（带缓存，过期前 60s 自动刷新）"""
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        resp = requests.post(self.TOKEN_URL, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书 token 失败: {data.get('msg')}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = now + data.get("expire", 7200) - 60
        return self._token

    def upload_image(self, filepath: str) -> Dict:
        """
        上传图片到飞书。

        Args:
            filepath: 本地图片文件路径

        Returns:
            {"success": True, "image_key": "img_xxx"} 或 {"success": False, "error": "..."}
        """
        if not os.path.isfile(filepath):
            return {"success": False, "error": f"文件不存在: {filepath}"}

        try:
            token = self._get_tenant_access_token()

            with open(filepath, "rb") as f:
                resp = requests.post(
                    self.UPLOAD_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    data={"image_type": "message"},
                    files={"image": f},
                    timeout=30,
                )

            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                return {"success": False, "error": f"飞书上传失败: {data.get('msg')}"}

            image_key = data.get("data", {}).get("image_key", "")
            if not image_key:
                return {"success": False, "error": "飞书未返回 image_key"}

            return {"success": True, "image_key": image_key}

        except Exception as e:
            return {"success": False, "error": f"上传飞书异常: {str(e)}"}


_uploader: Optional[FeishuUploader] = None


def get_feishu_uploader() -> Optional[FeishuUploader]:
    """获取飞书上传器单例（未配置时返回 None）"""
    global _uploader
    if _uploader is not None:
        return _uploader

    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        return None

    _uploader = FeishuUploader(app_id, app_secret)
    return _uploader
