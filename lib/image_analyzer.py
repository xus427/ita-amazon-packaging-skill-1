"""
参考图片分析器。
通过 GPT-4o 视觉能力分析用户上传的参考图，提取设计要素用于指导包装生成。
"""

import base64
import os
from typing import Dict, Optional

import requests

ANALYSIS_PROMPT = """你是一名资深的亚马逊产品包装设计专家。请分析这张参考图片，提取以下设计要素，用 JSON 格式返回：

{
  "color_scheme": "主色调和配色描述（英文，用于 AI 绘图 prompt）",
  "style": "设计风格描述（英文，如 minimalist / cartoon / premium / bold typography 等）",
  "layout": "排版布局特点（英文，如 centered composition / asymmetric / grid layout 等）",
  "typography": "字体风格（英文，如 bold sans-serif / elegant serif / rounded playful 等）",
  "key_elements": "画面中的关键视觉元素（英文，逗号分隔）",
  "overall_mood": "整体氛围和调性（英文，如 playful and vibrant / clean and professional 等）",
  "amazon_suitability": "这个设计是否适合亚马逊平台，以及改进建议（中文，1-2句话）"
}

只返回 JSON，不要其他文字。"""


class ImageAnalyzer:
    """基于 GPT-4o 视觉能力的图片分析器"""

    def __init__(self, api_key: str,
                 base_url: str = "https://api.apiyi.com/v1",
                 model: str = "gpt-4o"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @staticmethod
    def _encode_image(filepath: str) -> str:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze(self, image_source: str,
                extra_instruction: str = "") -> Dict:
        """
        分析参考图片。

        Args:
            image_source: 本地文件路径、http(s) 图片 URL、或 data:image/...;base64,... 格式
            extra_instruction: 用户额外的分析要求

        Returns:
            {"success": True, "analysis": {...}} 或 {"success": False, "error": "..."}
        """
        try:
            if image_source.startswith(("http://", "https://")):
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image_source, "detail": "high"},
                }
            elif image_source.startswith("data:image/"):
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image_source, "detail": "high"},
                }
            elif os.path.isfile(image_source):
                b64 = self._encode_image(image_source)
                ext = os.path.splitext(image_source)[1].lstrip(".").lower()
                mime = {"png": "image/png", "jpg": "image/jpeg",
                        "jpeg": "image/jpeg", "webp": "image/webp",
                        "gif": "image/gif"}.get(ext, "image/png")
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                }
            else:
                return {"success": False, "error": f"无法识别的图片来源: {image_source}"}

            prompt = ANALYSIS_PROMPT
            if extra_instruction:
                prompt += f"\n\n用户额外要求：{extra_instruction}"

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_content,
                        ],
                    }
                ],
                "max_tokens": 800,
                "temperature": 0.3,
            }

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            import json
            analysis = json.loads(content)
            return {"success": True, "analysis": analysis}

        except Exception as e:
            return {"success": False, "error": str(e)}


_analyzer: Optional[ImageAnalyzer] = None


def get_image_analyzer() -> Optional[ImageAnalyzer]:
    """获取图片分析器单例（未配置 API_KEY 时返回 None）"""
    global _analyzer
    if _analyzer is not None:
        return _analyzer

    api_key = os.getenv("API_KEY", "")
    if not api_key:
        return None

    base_url = os.getenv("APIYI_BASE_URL", "https://api.apiyi.com/v1")
    model = os.getenv("VISION_MODEL", "gpt-4o")
    _analyzer = ImageAnalyzer(api_key, base_url, model)
    return _analyzer
