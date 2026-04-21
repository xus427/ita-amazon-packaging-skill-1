"""
图片生成器 - 调用各种 AI 绘图 API
"""

import requests
import os
import base64
import urllib.parse
import tempfile
from typing import Dict, Optional, Tuple
from datetime import datetime

_MAX_INIT_IMAGE_BYTES = 20 * 1024 * 1024


def _load_init_image_bytes(init_image_path: Optional[str], init_image_url: Optional[str]) -> Tuple[Optional[bytes], str]:
    """Load raw image bytes from local path or http(s) URL or data:image/*;base64,..."""
    path = (init_image_path or "").strip()
    url = (init_image_url or "").strip()
    if path and os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read(), ""
    if url.startswith("data:image"):
        try:
            header, b64part = url.split(",", 1)
            raw = base64.b64decode(b64part)
            if len(raw) > _MAX_INIT_IMAGE_BYTES:
                return None, "init image too large"
            return raw, ""
        except Exception as e:
            return None, f"invalid data:image: {e}"
    if url.startswith("http://") or url.startswith("https://"):
        try:
            r = requests.get(url, timeout=90, stream=True)
            r.raise_for_status()
            cl = r.headers.get("Content-Length")
            if cl and int(cl) > _MAX_INIT_IMAGE_BYTES:
                return None, "init image too large"
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > _MAX_INIT_IMAGE_BYTES:
                    return None, "init image too large"
                chunks.append(chunk)
            return b"".join(chunks), ""
        except Exception as e:
            return None, f"download init image failed: {e}"
    if path or url:
        return None, "init image path not found or invalid URL"
    return None, "init_image_path or init_image_url is required"


class ImageGenerator:
    """图片生成器基类"""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate(self, prompt: str, filename: Optional[str] = None, image_ratio: str = "3:4") -> Dict:
        """
        生成图片
        
        Args:
            prompt: AI 绘图提示词
            filename: 输出文件名（不含扩展名）
        
        Returns:
            包含图片路径或 URL 的字典
        """
        raise NotImplementedError

    def edit_image(
        self,
        prompt: str,
        *,
        init_image_path: Optional[str] = None,
        init_image_url: Optional[str] = None,
        filename: Optional[str] = None,
        image_ratio: str = "3:4",
        denoise_strength: float = 0.25,
        **kwargs,
    ) -> Dict:
        """
        Image-conditioned edit (img2img / image edits). Not all backends support this.
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
    
    def generate(self, prompt: str, filename: Optional[str] = None, image_ratio: str = "3:4") -> Dict:
        """使用 Pollinations 生成图片"""
        try:
            # URL 编码提示词
            encoded_prompt = urllib.parse.quote(prompt)
            
            # 构建 URL（添加参数优化质量）
            ratio_to_size = {
                "1:1": (1024, 1024),
                "4:5": (1024, 1280),
                "3:4": (1024, 1366),
                "2:3": (1024, 1536),
                "16:9": (1366, 768),
                "9:16": (768, 1366),
            }
            width, height = ratio_to_size.get((image_ratio or "3:4"), (1024, 1366))
            url = f"{self.BASE_URL}/{encoded_prompt}?width={width}&height={height}&nologo=true&seed=42&enhance=true"
            
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

    def edit_image(
        self,
        prompt: str,
        *,
        init_image_path: Optional[str] = None,
        init_image_url: Optional[str] = None,
        filename: Optional[str] = None,
        image_ratio: str = "3:4",
        denoise_strength: float = 0.25,
        **kwargs,
    ) -> Dict:
        return {
            "success": False,
            "backend": "pollinations",
            "error": "Pollinations backend does not support true image edit/img2img in this app",
            "prompt": prompt,
        }


class StableDiffusionGenerator(ImageGenerator):
    """
    Stable Diffusion API 生成器
    需要配置 SD_API_URL
    """
    
    def __init__(self, api_url: str, output_dir: str = "./output"):
        super().__init__(output_dir)
        self.api_url = api_url.rstrip("/")
    
    def generate(self, prompt: str, filename: Optional[str] = None, image_ratio: str = "3:4") -> Dict:
        """使用 Stable Diffusion 生成图片"""
        try:
            ratio_to_size = {
                "1:1": (1024, 1024),
                "4:5": (1024, 1280),
                "3:4": (768, 1024),
                "2:3": (768, 1152),
                "16:9": (1280, 720),
                "9:16": (720, 1280),
            }
            width, height = ratio_to_size.get((image_ratio or "3:4"), (768, 1024))
            payload = {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted, ugly, deformed",
                "width": width,
                "height": height,
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

    def edit_image(
        self,
        prompt: str,
        *,
        init_image_path: Optional[str] = None,
        init_image_url: Optional[str] = None,
        filename: Optional[str] = None,
        image_ratio: str = "3:4",
        denoise_strength: float = 0.25,
        **kwargs,
    ) -> Dict:
        """Automatic1111 img2img."""
        try:
            raw, err = _load_init_image_bytes(init_image_path, init_image_url)
            if err or not raw:
                return {
                    "success": False,
                    "backend": "stable_diffusion",
                    "error": err or "missing init image",
                    "prompt": prompt,
                }
            b64 = base64.b64encode(raw).decode("utf-8")

            ratio_to_size = {
                "1:1": (1024, 1024),
                "4:5": (1024, 1280),
                "3:4": (768, 1024),
                "2:3": (768, 1152),
                "16:9": (1280, 720),
                "9:16": (720, 1280),
            }
            width, height = ratio_to_size.get((image_ratio or "3:4"), (768, 1024))

            strength = max(0.05, min(0.95, float(denoise_strength)))
            cfg_scale = float(kwargs.get("cfg_scale", 7.0))

            payload = {
                "init_images": [b64],
                "prompt": prompt,
                "negative_prompt": str(kwargs.get("negative_prompt", "blurry, low quality, distorted, ugly, deformed")),
                "width": width,
                "height": height,
                "steps": int(kwargs.get("steps", 28)),
                "cfg_scale": cfg_scale,
                "sampler_name": str(kwargs.get("sampler_name", "DPM++ 2M Karras")),
                "denoising_strength": strength,
            }

            response = requests.post(
                f"{self.api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            result = response.json()

            if "images" in result and len(result["images"]) > 0:
                image_data = base64.b64decode(result["images"][0])
                if not filename:
                    filename = self._generate_filename(prefix="packaging_edit")
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                return {
                    "success": True,
                    "backend": "stable_diffusion",
                    "filepath": filepath,
                    "filename": filename,
                    "prompt": prompt,
                    "edit": {"kind": "img2img", "denoise_strength": strength},
                }

            return {
                "success": False,
                "backend": "stable_diffusion",
                "error": "No image generated (img2img)",
                "prompt": prompt,
            }
        except Exception as e:
            return {
                "success": False,
                "backend": "stable_diffusion",
                "error": str(e),
                "prompt": prompt,
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

    def generate(self, prompt: str, filename: Optional[str] = None, image_ratio: str = "3:4") -> Dict:
        """使用 API易 生成图片"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            ratio_to_size = {
                "1:1": "1024x1024",
                "4:5": "1024x1280",
                "3:4": "1024x1366",
                "2:3": "1024x1536",
                "16:9": "1536x864",
                "9:16": "864x1536",
            }
            payload = {
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": ratio_to_size.get((image_ratio or "3:4"), self.size),
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

    def edit_image(
        self,
        prompt: str,
        *,
        init_image_path: Optional[str] = None,
        init_image_url: Optional[str] = None,
        filename: Optional[str] = None,
        image_ratio: str = "3:4",
        denoise_strength: float = 0.25,
        **kwargs,
    ) -> Dict:
        """
        OpenAI-compatible image edit endpoint (multipart).
        `denoise_strength` is mapped to provider-specific fields when possible.
        """
        tmp_path = None
        try:
            path = (init_image_path or "").strip()
            if path and os.path.isfile(path):
                open_path = path
            else:
                raw, err = _load_init_image_bytes(None, init_image_url)
                if err or not raw:
                    return {
                        "success": False,
                        "backend": "apiyi",
                        "error": err or "init_image_path or init_image_url required",
                        "prompt": prompt,
                    }
                fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="edit_init_")
                os.close(fd)
                with open(tmp_path, "wb") as wf:
                    wf.write(raw)
                open_path = tmp_path

            ratio_to_size = {
                "1:1": "1024x1024",
                "4:5": "1024x1280",
                "3:4": "1024x1366",
                "2:3": "1024x1536",
                "16:9": "1536x864",
                "9:16": "864x1536",
            }
            size = ratio_to_size.get((image_ratio or "3:4"), self.size)

            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Map strength loosely: many providers ignore it for edits; still send common aliases.
            strength = max(0.05, min(0.95, float(denoise_strength)))

            with open(open_path, "rb") as f:
                files = {
                    "image": ("image.png", f, "image/png"),
                }
                data = {
                    "model": self.model,
                    "prompt": prompt,
                    "size": size,
                    "n": "1",
                    # common optional fields (ignored safely by many gateways)
                    "strength": str(strength),
                    "image_strength": str(strength),
                }

                response = requests.post(
                    f"{self.base_url}/images/edits",
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()

            item = (result.get("data") or [{}])[0]
            image_url = item.get("url", "")
            b64 = item.get("b64_json", "")

            if not filename:
                filename = self._generate_filename(prefix="packaging_edit")

            filepath = os.path.join(self.output_dir, filename)

            if image_url:
                img_resp = requests.get(image_url, timeout=60)
                img_resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)
            elif b64:
                raw = base64.b64decode(b64)
                with open(filepath, "wb") as f:
                    f.write(raw)
            else:
                return {
                    "success": False,
                    "backend": "apiyi",
                    "error": "API 未返回图片数据（url/b64_json）",
                    "prompt": prompt,
                }

            return {
                "success": True,
                "backend": "apiyi",
                "model": self.model,
                "filepath": filepath,
                "filename": filename,
                "url": image_url,
                "revised_prompt": item.get("revised_prompt", ""),
                "prompt": prompt,
                "edit": {"kind": "images/edits", "denoise_strength": strength, "size": size},
            }
        except Exception as e:
            return {
                "success": False,
                "backend": "apiyi",
                "error": str(e),
                "prompt": prompt,
            }
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


class MidjourneyGenerator(ImageGenerator):
    """
    Midjourney API 生成器（通过第三方 API）
    需要配置 MJ_API_KEY
    """
    
    def __init__(self, api_key: str, output_dir: str = "./output"):
        super().__init__(output_dir)
        self.api_key = api_key
        self.api_url = "https://api.midjourneyapi.io/v2/imagine"  # 示例 API
    
    def generate(self, prompt: str, filename: Optional[str] = None, image_ratio: str = "3:4") -> Dict:
        """使用 Midjourney 生成图片"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "aspect_ratio": image_ratio or "3:4"
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

    def edit_image(
        self,
        prompt: str,
        *,
        init_image_path: Optional[str] = None,
        init_image_url: Optional[str] = None,
        filename: Optional[str] = None,
        image_ratio: str = "3:4",
        denoise_strength: float = 0.25,
        **kwargs,
    ) -> Dict:
        return {
            "success": False,
            "backend": "midjourney",
            "error": "Midjourney backend does not support direct image edit in this app",
            "prompt": prompt,
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
