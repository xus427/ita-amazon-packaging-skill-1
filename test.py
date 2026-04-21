#!/usr/bin/env python3
"""测试亚马逊包装主图生成器"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5012"

def test_health():
    """测试健康检查"""
    print("=" * 50)
    print("测试 1: 健康检查")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"状态码: {r.status_code}")
        data = r.json()
        print(f"服务: {data.get('service')}")
        print(f"默认后端: {data.get('default_backend')}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_backends():
    """测试后端列表"""
    print("=" * 50)
    print("测试 2: 可用后端列表")
    try:
        r = requests.get(f"{BASE_URL}/api/backends", timeout=5)
        data = r.json()
        print(f"可用后端:")
        for b in data.get('backends', []):
            print(f"  - {b['name']}: {b['display_name']}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_design_only():
    """测试仅生成设计方案"""
    print("=" * 50)
    print("测试 3: 仅生成设计方案")
    try:
        payload = {
            "product_name": "儿童DIY手链套装",
            "package_type": "礼盒",
            "style_keywords": ["童趣", "真实感"],
            "brand_name": "CraftJoy",
            "age_mark": "6+"
        }
        r = requests.post(f"{BASE_URL}/api/design-only", json=payload, timeout=10)
        data = r.json()
        print(f"状态: {data.get('msg')}")
        
        if 'design' in data:
            design = data['design']
            print(f"\n设计方案:")
            print(f"  产品: {design.get('product_name')}")
            print(f"  配色: {design.get('color_scheme', {}).get('name')}")
            tertiary = design.get('information_hierarchy', {}).get('tertiary', [])
            print(f"  文本层级: {', '.join(tertiary[:3])}")
            print(f"\nAI提示词预览:")
            print(f"  {design.get('prompt', '')[:100]}...")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_generate_with_image():
    """测试生成图片（使用 Pollinations）"""
    print("=" * 50)
    print("测试 4: 生成设计方案 + 图片 (Pollinations)")
    print("注意: 图片生成可能需要 30-60 秒...")
    try:
        payload = {
            "product_name": "儿童DIY手链套装",
            "package_type": "礼盒",
            "style_keywords": ["童趣", "真实感"],
            "brand_name": "CraftJoy",
            "age_mark": "6+",
            "generate_image": True,
            "image_backend": "pollinations"
        }
        r = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=120)
        data = r.json()
        
        print(f"状态: {data.get('msg')}")
        print(f"图片生成: {'成功' if data.get('image_generated') else '失败'}")
        
        if data.get('image'):
            img = data['image']
            if img.get('success'):
                print(f"图片路径: {img.get('filepath')}")
                print(f"图片URL: {img.get('url', 'N/A')[:80]}...")
            else:
                print(f"图片生成错误: {img.get('error')}")
        
        return data.get('image_generated', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    print("亚马逊包装主图生成器测试")
    print("=" * 50)
    
    results = []
    results.append(("健康检查", test_health()))
    results.append(("后端列表", test_backends()))
    results.append(("设计方案", test_design_only()))
    results.append(("图片生成", test_generate_with_image()))
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)
