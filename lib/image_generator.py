"""
图片生成器 - 调用各种 AI 绘图 API
"""

import requests
import os
import base64
import urllib.parse
from typing import Dict, Optional, Tuple
from datetime import datetime


class ImageGenerator:
    """图片生成器基类"""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate(self, prompt: str, filename: Optional[str] = None) -> Dict:
        """
        生成图片
        
        Args:
            prompt: AI 绘图提示词
            filename: 输出文件名（不含扩展名）
        
        Returns:
            包含图片路径或 URL 的字典
        """
        raise NotImplementedError
    
    def _generate_filename(self, prefix: str = "packaging") -> str:
        """生成文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.png"


class PollinationsGenerator(ImageGenerator):
    """
    Pollinations AI 图片生成器
    免费、无需 API Key，直接通过 URL 生成
    """
    
    BASE_URL = "https://image.pollinations.ai/prompt"
    
    def generate(self, prompt: str, filename: Optional[str] = None) -> Dict:
        """使用 Pollinations 生成图片"""
        try:
            # URL 编码提示词
            encoded_prompt = urllib.parse.quote(prompt)
            
            # 构建 URL（添加参数优化质量）
            url = f"{self.BASE_URL}/{encoded_prompt}?width=1024&height=1366&nologo=true&seed=42&enhance=true"
            
            # 下载图片
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            
            # 保存图片
            if not filename:
                filename = self._generate_filename()
            
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            return {
                "success": True,
                "backend": "pollinations",
                "filepath": filepath,
                "filename": filename,
                "url": url,
                "prompt": prompt
            }
            
        except Exception as e:
            return {
                "success": False,
                "backend": "pollinations",
                "error": str(e),
                "prompt": prompt
            }


class StableDiffusionGenerator(ImageGenerator):
    """
    Stable Diffusion API 生成器
    需要配置 SD_API_URL
    """
    
    def __init__(self, api_url: str, output_dir: str = "./output"):
        super().__init__(output_dir)
        self.api_url = api_url.rstrip("/")
    
    def generate(self, prompt: str, filename: Optional[str] = None) -> Dict:
        """使用 Stable Diffusion 生成图片"""
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted, ugly, deformed",
                "width": 768,
                "height": 1024,
                "steps": 30,
                "cfg_scale": 7.5,
                "sampler_name": "DPM++ 2M Karras"
            }
            
            response = requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "images" in result and len(result["images"]) > 0:
                # 解码 base64 图片
                image_data = base64.b64decode(result["images"][0])
                
                if not filename:
                    filename = self._generate_filename()
                
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                return {
                    "success": True,
                    "backend": "stable_diffusion",
                    "filepath": filepath,
                    "filename": filename,
                    "prompt": prompt
                }
            else:
                return {
                    "success": False,
                    "backend": "stable_diffusion",
                    "error": "No image generated",
                    "prompt": prompt
                }
                
        except Exception as e:
            return {
                "success": False,
                "backend": "stable_diffusion",
                "error": str(e),
                "prompt": prompt
            }


class ApiYiGenerator(ImageGenerator):
    """
    API易图片生成器（OpenAI 兼容接口）
    支持 dall-e-3、dall-e-2、gpt-image-1、sora-image 等模型
    """

    def __init__(self, api_key: str, output_dir: str = "./output",
                 base_url: str = "https://api.apiyi.com/v1",
                 model: str = "dall-e-3",
                 size: str = "1024x1792",
                 quality: str = "standard"):
        super().__init__(output_dir)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.size = size
        self.quality = quality

    def generate(self, prompt: str, filename: Optional[str] = None) -> Dict:
        """使用 API易 生成图片"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": self.size,
                "quality": self.quality,
                "response_format": "url",
            }

            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            image_url = result["data"][0].get("url", "")
            if not image_url:
                return {
                    "success": False,
                    "backend": "apiyi",
                    "error": "API 未返回图片 URL",
                    "prompt": prompt,
                }

            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()

            if not filename:
                filename = self._generate_filename()

            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            return {
                "success": True,
                "backend": "apiyi",
                "model": self.model,
                "filepath": filepath,
                "filename": filename,
                "url": image_url,
                "revised_prompt": result["data"][0].get("revised_prompt", ""),
                "prompt": prompt,
            }

        except Exception as e:
            return {
                "success": False,
                "backend": "apiyi",
                "error": str(e),
                "prompt": prompt,
            }


class MidjourneyGenerator(ImageGenerator):
    """
    Midjourney API 生成器（通过第三方 API）
    需要配置 MJ_API_KEY
    """
    
    def __init__(self, api_key: str, output_dir: str = "./output"):
        super().__init__(output_dir)
        self.api_key = api_key
        self.api_url = "https://api.midjourneyapi.io/v2/imagine"  # 示例 API
    
    def generate(self, prompt: str, filename: Optional[str] = None) -> Dict:
        """使用 Midjourney 生成图片"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "aspect_ratio": "3:4"
            }
            
            # 提交任务
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Midjourney 通常是异步的，返回任务 ID
            return {
                "success": True,
                "backend": "midjourney",
                "task_id": result.get("task_id"),
                "status": "pending",
                "prompt": prompt,
                "note": "Midjourney generation is async, check status with task_id"
            }
            
        except Exception as e:
            return {
                "success": False,
                "backend": "midjourney",
                "error": str(e),
                "prompt": prompt
            }


def get_generator(backend: str = "pollinations", **kwargs) -> ImageGenerator:
    """
    获取图片生成器实例
    
    Args:
        backend: 后端类型 (pollinations, sd, midjourney)
        **kwargs: 额外配置参数
    
    Returns:
        ImageGenerator 实例
    """
    backend = backend.lower()
    
    if backend == "apiyi":
        api_key = kwargs.get("api_key") or os.getenv("API_KEY", "")
        if not api_key:
            raise ValueError("API_KEY is required for API易 backend")
        return ApiYiGenerator(
            api_key=api_key,
            output_dir=kwargs.get("output_dir", "./output"),
            base_url=kwargs.get("apiyi_base_url") or os.getenv("APIYI_BASE_URL", "https://api.apiyi.com/v1"),
            model=kwargs.get("apiyi_model") or os.getenv("APIYI_MODEL", "dall-e-3"),
            size=kwargs.get("apiyi_size") or os.getenv("APIYI_SIZE", "1024x1792"),
            quality=kwargs.get("apiyi_quality") or os.getenv("APIYI_QUALITY", "standard"),
        )

    elif backend == "pollinations":
        return PollinationsGenerator(output_dir=kwargs.get("output_dir", "./output"))

    elif backend == "sd" or backend == "stable_diffusion":
        api_url = kwargs.get("sd_api_url") or os.getenv("SD_API_URL", "")
        if not api_url:
            raise ValueError("SD_API_URL is required for Stable Diffusion backend")
        return StableDiffusionGenerator(api_url, output_dir=kwargs.get("output_dir", "./output"))

    elif backend == "mj" or backend == "midjourney":
        api_key = kwargs.get("mj_api_key") or os.getenv("MJ_API_KEY", "")
        if not api_key:
            raise ValueError("MJ_API_KEY is required for Midjourney backend")
        return MidjourneyGenerator(api_key, output_dir=kwargs.get("output_dir", "./output"))

    else:
        raise ValueError(f"Unknown backend: {backend}")
