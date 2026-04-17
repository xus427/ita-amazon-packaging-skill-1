# 亚马逊包装主图生成器 Skill

直接生成亚马逊产品包装主图，支持 AI 绘图 API 调用。

## 功能

1. 根据产品信息生成包装设计方案
2. 自动生成优化的 AI 绘图提示词
3. 调用绘图 API 直接生成图片
4. 支持多种绘图后端：Pollinations、Stable Diffusion、Midjourney

## 快速开始

```bash
cd /root/.openclaw/workspace/skills/amazon-packaging-skill
python3 app.py
```

## API 接口

### 生成包装图

```bash
POST /api/generate

{
  "product_name": "儿童 DIY 手链套装",
  "package_type": "礼盒",
  "target_market": "美国",
  "style_keywords": ["卡通", "糖果色", "可爱"],
  "core_features": ["500+配件", "无毒材料", "教程 included"],
  "brand_name": "CraftJoy",
  "age_mark": "6+",
  "generate_image": true,
  "image_backend": "pollinations"  // 可选: pollinations, sd, mj
}
```

### 仅生成提示词

```bash
POST /api/generate

{
  "product_name": "儿童 DIY 手链套装",
  "generate_image": false
}
```

## 配置

复制 `.env.example` 为 `.env` 并配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_HOST` | 服务监听地址 | `0.0.0.0` |
| `FLASK_PORT` | 服务端口 | `5010` |
| `DEFAULT_IMAGE_BACKEND` | 默认绘图后端 | `pollinations` |
| `SD_API_URL` | Stable Diffusion API 地址 | — |
| `MJ_API_KEY` | Midjourney API Key | — |
| `OUTPUT_DIR` | 图片输出目录 | `./output` |

## 绘图后端

### Pollinations (默认，免费)
- 无需 API Key
- 直接通过 URL 生成图片
- 适合快速测试

### Stable Diffusion
- 需要本地或远程 SD 服务
- 配置 `SD_API_URL`

### Midjourney
- 需要 API Key
- 配置 `MJ_API_KEY`
