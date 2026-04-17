# 亚马逊包装主图生成器

当用户请求设计亚马逊产品包装、生成产品效果图、创建包装主图时，使用此 Skill。

## 启动

```bash
cd /root/.openclaw/workspace/skills/ita-amazon-packaging-skill
bash start.sh
```

服务运行在 `http://localhost:5012`。

## 工具

### 批量生成效果图（推荐）

一次生成多张不同风格的亚马逊包装效果图。

```http
POST http://localhost:5012/api/batch-generate
Content-Type: application/json

{
  "product_name": "产品名称（必填）",
  "package_type": "包装类型，如：彩盒、礼盒、袋装",
  "target_market": "目标市场，如：美国、欧洲",
  "style_keywords": ["风格关键词数组，如：卡通、可爱、简约"],
  "core_features": ["核心卖点数组，如：500+配件、无毒材料"],
  "brand_name": "品牌名称",
  "count": 6,
  "image_backend": "apiyi"
}
```

返回值包含 `images` 数组，每张图有 `image_key`（可直接在飞书消息中展示）和 `filepath`。

### 生成单张效果图

```http
POST http://localhost:5012/api/generate
Content-Type: application/json

{
  "product_name": "产品名称（必填）",
  "package_type": "彩盒",
  "style_keywords": ["卡通", "糖果色"],
  "core_features": ["500+配件", "无毒材料"],
  "brand_name": "CraftJoy",
  "generate_image": true,
  "image_backend": "apiyi"
}
```

### 分析参考图片

分析用户上传的参考图片，提取设计要素。

```http
POST http://localhost:5012/api/analyze-image
Content-Type: application/json

{
  "image_url": "图片URL",
  "extra_instruction": "额外分析要求（可选）"
}
```

### 健康检查

```http
GET http://localhost:5012/health
```

## 使用流程

1. 用户提供产品信息（名称、卖点、风格偏好等）
2. 调用 `/api/batch-generate` 批量生成 6 张不同风格的效果图
3. 将生成的图片通过 `image_key` 展示给用户
4. 如果用户提供了参考图片，先调用 `/api/analyze-image` 分析，再将分析结果传入生成接口

## 支持的设计风格

- 信息优先型：大字体卖点突出，适合移动端缩略图
- 高端礼盒型：哑光/UV 工艺感，适合送礼类产品
- 透明橱窗型：透明展示窗，展示实物增加信任感
- 缩略图冲击型：高饱和度配色，在搜索结果中脱颖而出
- 场景插画型：使用场景插画，传达产品使用方式
- 极简品牌型：简约品牌风，适合 A+ 内容页面
