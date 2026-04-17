"""
亚马逊包装主图生成器 - Flask API 服务
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# 导入本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.designer import generate_packaging_design, generate_prompt_variations
from lib.image_generator import get_generator
from lib.config import get_env, get_env_bool, get_env_int
from lib.feishu_uploader import get_feishu_uploader
from lib.image_analyzer import get_image_analyzer

app = Flask(__name__)

# 配置
OUTPUT_DIR = get_env("OUTPUT_DIR", "./output")
UPLOAD_DIR = get_env("UPLOAD_DIR", "./uploads")
DEFAULT_BACKEND = get_env("DEFAULT_IMAGE_BACKEND", "pollinations")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _upload_to_feishu(filepath: str) -> dict:
    """尝试将图片上传到飞书，返回上传结果（未配置则跳过）"""
    uploader = get_feishu_uploader()
    if uploader is None:
        return {"success": False, "error": "飞书未配置 (FEISHU_APP_ID / FEISHU_APP_SECRET)"}
    return uploader.upload_image(filepath)


@app.route("/output/<path:filename>", methods=["GET"])
def serve_output(filename):
    """通过 HTTP 访问生成的图片"""
    abs_output = os.path.abspath(OUTPUT_DIR)
    return send_from_directory(abs_output, filename)


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    feishu_configured = get_feishu_uploader() is not None
    return jsonify({
        "service": "amazon-packaging-skill",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "default_backend": DEFAULT_BACKEND,
        "output_dir": OUTPUT_DIR,
        "feishu_upload": "ready" if feishu_configured else "not_configured"
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    生成包装设计方案和图片
    
    请求体示例:
    {
        "product_name": "儿童 DIY 手链套装",
        "package_type": "礼盒",
        "target_market": "美国",
        "style_keywords": ["卡通", "糖果色", "可爱"],
        "core_features": ["500+配件", "无毒材料", "教程 included"],
        "display_elements": ["彩色珠子", "卡通吊坠"],
        "brand_name": "CraftJoy",
        "age_mark": "6+",
        "need_content_display": true,
        "generate_image": true,
        "image_backend": "pollinations"
    }
    """
    try:
        data = request.get_json() or {}
        
        # 验证必填字段
        if not data.get("product_name"):
            return jsonify({
                "code": 400,
                "error": "product_name is required"
            }), 400
        
        # 1. 生成设计方案
        design = generate_packaging_design(data)
        
        result = {
            "code": 200,
            "design": design,
            "image_generated": False
        }
        
        # 2. 是否生成图片
        if data.get("generate_image", True):
            backend = data.get("image_backend", DEFAULT_BACKEND)
            
            try:
                generator = get_generator(
                    backend=backend,
                    output_dir=OUTPUT_DIR,
                    api_key=get_env("API_KEY"),
                    sd_api_url=get_env("SD_API_URL"),
                    mj_api_key=get_env("MJ_API_KEY")
                )

                image_result = generator.generate(design["prompt"])
                
                result["image"] = image_result
                result["image_generated"] = image_result.get("success", False)
                
                if image_result.get("success"):
                    feishu_result = _upload_to_feishu(image_result["filepath"])
                    if feishu_result["success"]:
                        result["image"]["image_key"] = feishu_result["image_key"]
                        result["msg"] = "设计方案和图片生成成功（已上传飞书）"
                    else:
                        result["msg"] = "设计方案和图片生成成功"
                        result["feishu_warning"] = feishu_result.get("error")
                else:
                    result["msg"] = "设计方案生成成功，但图片生成失败"
                    result["warning"] = image_result.get("error", "Unknown error")
                    
            except Exception as e:
                result["image_generated"] = False
                result["warning"] = f"图片生成失败: {str(e)}"
                result["msg"] = "设计方案生成成功，但图片生成失败"
        else:
            result["msg"] = "设计方案生成成功（未生成图片）"
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "error": str(e)
        }), 500


def _save_upload(file) -> str:
    """保存上传的文件，返回本地路径"""
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename) or "ref.png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_DIR, saved_name)
    file.save(filepath)
    return filepath


def _analyze_reference(image_source: str, extra: str = "") -> dict:
    """分析参考图片，返回分析结果或空字典"""
    analyzer = get_image_analyzer()
    if analyzer is None:
        return {}
    result = analyzer.analyze(image_source, extra)
    if result.get("success"):
        return result["analysis"]
    return {}


@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    """
    分析参考图片，提取设计要素

    支持两种方式:
    1. 上传文件: form-data 中 image 字段
    2. 图片URL: JSON body {"image_url": "https://..."}
    可选: extra_instruction 额外分析要求
    """
    try:
        analyzer = get_image_analyzer()
        if analyzer is None:
            return jsonify({"code": 500, "error": "API_KEY 未配置，无法分析图片"}), 500

        extra = ""

        if request.content_type and "multipart/form-data" in request.content_type:
            file = request.files.get("image")
            if not file:
                return jsonify({"code": 400, "error": "请上传 image 文件"}), 400
            filepath = _save_upload(file)
            image_source = filepath
            extra = request.form.get("extra_instruction", "")
        else:
            data = request.get_json() or {}
            image_source = data.get("image_url", "")
            if not image_source:
                return jsonify({"code": 400, "error": "请提供 image_url 或上传文件"}), 400
            extra = data.get("extra_instruction", "")

        result = analyzer.analyze(image_source, extra)

        if result.get("success"):
            return jsonify({
                "code": 200,
                "analysis": result["analysis"],
                "msg": "图片分析完成",
            })
        else:
            return jsonify({"code": 500, "error": result.get("error")}), 500

    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/batch-generate", methods=["POST"])
def batch_generate():
    """
    批量并发生成多张效果图（支持参考图）

    方式1 - JSON（图片URL参考）:
    {
        "product_name": "儿童 DIY 手链套装",
        "package_type": "礼盒",
        "core_features": ["500+配件", "无毒材料"],
        "brand_name": "CraftJoy",
        "count": 6,
        "reference_image_url": "https://example.com/ref.jpg"
    }

    方式2 - form-data（文件上传参考）:
      reference_image: 文件
      data: JSON字符串（同上，不含 reference_image_url）
    """
    try:
        ref_analysis = {}

        if request.content_type and "multipart/form-data" in request.content_type:
            import json as _json
            data = _json.loads(request.form.get("data", "{}"))
            ref_file = request.files.get("reference_image")
            if ref_file:
                filepath = _save_upload(ref_file)
                ref_analysis = _analyze_reference(filepath)
        else:
            data = request.get_json() or {}
            ref_url = data.get("reference_image_url", "")
            if ref_url:
                ref_analysis = _analyze_reference(ref_url)

        if not data.get("product_name"):
            return jsonify({"code": 400, "error": "product_name is required"}), 400

        if ref_analysis:
            data["_ref_analysis"] = ref_analysis

        count = min(int(data.get("count", 6)), 8)
        backend = data.get("image_backend", DEFAULT_BACKEND)

        variations = generate_prompt_variations(data, count)

        generator = get_generator(
            backend=backend,
            output_dir=OUTPUT_DIR,
            api_key=get_env("API_KEY"),
            sd_api_url=get_env("SD_API_URL"),
            mj_api_key=get_env("MJ_API_KEY"),
        )

        def _generate_one(var):
            img = generator.generate(var["prompt"])
            if img.get("success"):
                feishu = _upload_to_feishu(img["filepath"])
                if feishu["success"]:
                    img["image_key"] = feishu["image_key"]
            return {
                "index": var["index"],
                "variation": var["variation"],
                "image": img,
            }

        images = []
        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = {pool.submit(_generate_one, v): v for v in variations}
            for future in as_completed(futures):
                images.append(future.result())

        images.sort(key=lambda x: x["index"])

        success_count = sum(1 for img in images if img["image"].get("success"))

        return jsonify({
            "code": 200,
            "design": variations[0]["design"],
            "images": images,
            "total": count,
            "success_count": success_count,
            "msg": f"批量生成完成：{success_count}/{count} 张成功",
        })

    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/design-only", methods=["POST"])
def design_only():
    """
    仅生成设计方案（不生成图片）
    
    请求体示例:
    {
        "product_name": "儿童 DIY 手链套装",
        "style_keywords": ["卡通", "糖果色"],
        "core_features": ["500+配件", "无毒材料"]
    }
    """
    try:
        data = request.get_json() or {}
        
        if not data.get("product_name"):
            return jsonify({
                "code": 400,
                "error": "product_name is required"
            }), 400
        
        design = generate_packaging_design(data)
        
        return jsonify({
            "code": 200,
            "design": design,
            "msg": "设计方案生成成功"
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "error": str(e)
        }), 500


@app.route("/api/image", methods=["POST"])
def generate_image_only():
    """
    仅生成图片（需要已有提示词）
    
    请求体示例:
    {
        "prompt": "product packaging box...",
        "backend": "pollinations",
        "filename": "custom_name.png"
    }
    """
    try:
        data = request.get_json() or {}
        
        if not data.get("prompt"):
            return jsonify({
                "code": 400,
                "error": "prompt is required"
            }), 400
        
        backend = data.get("backend", DEFAULT_BACKEND)
        
        generator = get_generator(
            backend=backend,
            output_dir=OUTPUT_DIR,
            api_key=get_env("API_KEY"),
            sd_api_url=get_env("SD_API_URL"),
            mj_api_key=get_env("MJ_API_KEY")
        )
        
        result = generator.generate(
            prompt=data["prompt"],
            filename=data.get("filename")
        )
        
        if result.get("success"):
            feishu_result = _upload_to_feishu(result["filepath"])
            if feishu_result["success"]:
                result["image_key"] = feishu_result["image_key"]

            return jsonify({
                "code": 200,
                "data": result,
                "msg": "图片生成成功"
            })
        else:
            return jsonify({
                "code": 500,
                "error": result.get("error", "Image generation failed"),
                "data": result
            }), 500
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "error": str(e)
        }), 500


@app.route("/api/backends", methods=["GET"])
def list_backends():
    """列出可用的图片生成后端"""
    backends = [
        {
            "name": "apiyi",
            "display_name": "API易 (DALL-E / GPT-Image)",
            "description": "付费 API，速度快质量高，需要配置 API_KEY",
            "requires_config": True,
            "config_key": "API_KEY"
        },
        {
            "name": "pollinations",
            "display_name": "Pollinations AI",
            "description": "免费、无需 API Key，适合快速测试",
            "requires_config": False
        },
        {
            "name": "sd",
            "display_name": "Stable Diffusion",
            "description": "本地或远程 SD 服务，需要配置 SD_API_URL",
            "requires_config": True,
            "config_key": "SD_API_URL"
        },
        {
            "name": "mj",
            "display_name": "Midjourney",
            "description": "通过第三方 API，需要配置 MJ_API_KEY",
            "requires_config": True,
            "config_key": "MJ_API_KEY"
        }
    ]
    
    return jsonify({
        "code": 200,
        "backends": backends,
        "default": DEFAULT_BACKEND
    })


if __name__ == "__main__":
    host = get_env("FLASK_HOST", "0.0.0.0")
    port = get_env_int("FLASK_PORT", 5012)
    debug = get_env_bool("FLASK_DEBUG", False)
    
    print(f"=" * 60)
    print(f"亚马逊包装主图生成器服务启动中...")
    print(f"  地址: http://{host}:{port}")
    print(f"  默认绘图后端: {DEFAULT_BACKEND}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"=" * 60)
    
    app.run(host=host, port=port, debug=debug)
