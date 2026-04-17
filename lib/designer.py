"""
亚马逊包装主图生成器
核心逻辑：根据产品信息生成设计方案和 AI 提示词
"""

from typing import Dict, List, Optional
import random


class PackagingDesigner:
    """包装设计师 - 生成设计方案和提示词"""
    
    # 预设配色方案
    COLOR_SCHEMES = {
        "candy": {
            "name": "糖果色",
            "colors": ["#FF6B9D", "#FFE66D", "#4ECDC4", "#95E1D3"],
            "desc": "高饱和糖果粉、柠檬黄、薄荷绿"
        },
        "ocean": {
            "name": "海洋风",
            "colors": ["#0077B6", "#00B4D8", "#90E0EF", "#CAF0F8"],
            "desc": "深海蓝、天空蓝、浅蓝渐变"
        },
        "forest": {
            "name": "森林系",
            "colors": ["#2D6A4F", "#40916C", "#52B788", "#74C69D"],
            "desc": "深绿、草绿、薄荷绿"
        },
        "sunset": {
            "name": "日落橙",
            "colors": ["#F72585", "#7209B7", "#3A0CA3", "#4361EE"],
            "desc": "玫红、紫罗兰、深蓝渐变"
        },
        "warm": {
            "name": "暖色调",
            "colors": ["#FF6B35", "#F7931E", "#FFD23F", "#FFF3B0"],
            "desc": "活力橙、金黄、奶油色"
        }
    }
    
    # 风格关键词映射
    STYLE_MAP = {
        "卡通": "cartoon illustration style, cute characters",
        "可爱": "kawaii style, adorable design",
        "趣味": "fun and playful design, vibrant colors",
        "DIY": "DIY craft style, handmade aesthetic",
        "手绘": "hand-drawn style, sketch illustration",
        "3D": "3D rendered packaging, realistic shadows",
        "简约": "minimalist design, clean lines",
        "复古": "vintage retro style, classic typography",
        "科技": "futuristic tech style, neon accents",
        "自然": "organic natural style, earth tones"
    }
    
    def __init__(self):
        self.design = {}
    
    def generate_design(self, params: Dict) -> Dict:
        """
        生成完整的设计方案
        
        Args:
            params: 产品参数
        
        Returns:
            设计方案字典
        """
        # 1. 确定视觉风格
        color_scheme = self._select_color_scheme(params.get("style_keywords", []))
        
        # 2. 构建信息层级
        hierarchy = self._build_hierarchy(params)
        
        # 3. 提取卖点
        selling_points = self._extract_selling_points(params.get("core_features", []))
        
        # 4. 设计内容展示区
        content_display = self._design_content_area(params)
        
        # 5. 应用合规布局
        compliance = self._apply_compliance(params)
        
        # 6. 生成 AI 提示词
        prompt = self._generate_prompt(params, color_scheme, hierarchy, selling_points)
        
        return {
            "product_name": params.get("product_name", ""),
            "package_type": params.get("package_type", "彩盒"),
            "color_scheme": color_scheme,
            "information_hierarchy": hierarchy,
            "selling_points": selling_points,
            "content_display": content_display,
            "compliance": compliance,
            "prompt": prompt,
            "layout_description": self._generate_layout_description(params, color_scheme, hierarchy)
        }
    
    def _select_color_scheme(self, style_keywords: List[str]) -> Dict:
        """根据风格关键词选择配色"""
        # 根据关键词匹配配色
        keyword_colors = {
            "糖果": "candy", "粉色": "candy", "可爱": "candy",
            "海洋": "ocean", "蓝色": "ocean", "清凉": "ocean",
            "森林": "forest", "绿色": "forest", "自然": "forest",
            "日落": "sunset", "紫色": "sunset", "梦幻": "sunset",
            "温暖": "warm", "橙色": "warm", "活力": "warm"
        }
        
        for keyword in style_keywords:
            if keyword in keyword_colors:
                scheme_key = keyword_colors[keyword]
                return self.COLOR_SCHEMES[scheme_key]
        
        # 默认随机选择
        return random.choice(list(self.COLOR_SCHEMES.values()))
    
    def _build_hierarchy(self, params: Dict) -> Dict:
        """构建信息层级"""
        features = params.get("core_features", [])
        
        # 一级：最重要的卖点（通常是数量/核心功能）
        primary = features[0] if features else "PREMIUM QUALITY"
        
        # 二级：产品名称
        secondary = params.get("product_name", "Product Name")
        
        # 三级：其他卖点
        tertiary = features[1:4] if len(features) > 1 else ["High Quality", "Great Gift"]
        
        return {
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary
        }
    
    def _extract_selling_points(self, features: List[str]) -> List[str]:
        """提取并优化卖点（每条≤5词）"""
        selling_points = []
        
        for feature in features[:5]:  # 最多5个卖点
            # 简化为≤5词
            words = feature.split()
            if len(words) > 5:
                feature = " ".join(words[:5])
            selling_points.append(feature)
        
        # 如果卖点不足，补充默认
        defaults = ["Perfect Gift Choice", "Premium Materials", "Easy to Use", "Creative Fun", "Educational Toy"]
        while len(selling_points) < 3:
            selling_points.append(defaults[len(selling_points)])
        
        return selling_points
    
    def _design_content_area(self, params: Dict) -> Dict:
        """设计内容展示区"""
        if not params.get("need_content_display", True):
            return {"enabled": False}
        
        display_elements = params.get("display_elements", [])
        
        return {
            "enabled": True,
            "window_type": "透明展示窗" if params.get("package_type") == "礼盒" else "产品图示",
            "elements": display_elements or ["产品实物图", "配件展示"],
            "layout": "居中或右侧展示"
        }
    
    def _apply_compliance(self, params: Dict) -> Dict:
        """应用合规布局"""
        compliance = params.get("compliance", {})
        
        return {
            "brand_position": "左上角",
            "brand": params.get("brand_name", "Your Brand"),
            "age_mark_position": "右上角",
            "age_mark": compliance.get("age_mark", "3+"),
            "warning_position": "底部",
            "warning": compliance.get("warning", "WARNING: CHOKING HAZARD - SMALL PARTS. NOT FOR CHILDREN UNDER 3 YEARS.")
        }
    
    def _generate_prompt(self, params: Dict, color_scheme: Dict, hierarchy: Dict, selling_points: List[str]) -> str:
        """生成 AI 绘图提示词"""
        product_name = params.get("product_name", "Product")
        package_type = params.get("package_type", "packaging box")
        style_keywords = params.get("style_keywords", [])
        
        # 转换风格关键词
        style_parts = []
        for keyword in style_keywords:
            if keyword in self.STYLE_MAP:
                style_parts.append(self.STYLE_MAP[keyword])
        
        if not style_parts:
            style_parts = ["professional packaging design", "commercial product photography"]
        
        # 构建提示词
        prompt_parts = [
            f"Product packaging {package_type} for {product_name}",
            f"color scheme: {color_scheme['desc']}",
            ", ".join(style_parts),
            f'large bold text "{hierarchy["primary"]}" on front',
            "clean white background",
            "professional product photography",
            "studio lighting",
            "high detail, 8k",
            "no scene, isolated on white",
            "e-commerce ready",
            "--ar 3:4"
        ]
        
        # 如果有展示窗需求
        if params.get("need_content_display", True):
            prompt_parts.insert(3, "transparent window showing product inside")
        
        return ", ".join(prompt_parts)
    
    def _generate_layout_description(self, params: Dict, color_scheme: Dict, hierarchy: Dict) -> str:
        """生成布局描述"""
        lines = [
            f"包装设计方案：{params.get('product_name', 'Product')}",
            f"",
            f"【配色方案】{color_scheme['name']}",
            f"主色：{', '.join(color_scheme['colors'][:2])}",
            f"",
            f"【信息层级】",
            f"一级（最大字体）：{hierarchy['primary']}",
            f"二级（产品名）：{hierarchy['secondary']}",
            f"三级（卖点）：{', '.join(hierarchy['tertiary'][:3])}",
            f"",
            f"【布局说明】",
            f"- 左上角：品牌 Logo",
            f"- 右上角：年龄标识 {params.get('compliance', {}).get('age_mark', '3+')}",
            f"- 中央：核心卖点 + 产品名称",
            f"- 底部：安全警告语"
        ]
        
        return "\n".join(lines)


    DESIGN_VARIATIONS = [
        {
            "label": "信息优先型",
            "style": "clean commercial packaging, high contrast bold typography, sharp edges, Amazon hero image ready",
            "color_key": "candy",
            "layout": "oversized core selling point text at top, product name centered, feature icons at bottom, 85% frame fill",
            "extra": "designed for maximum thumbnail readability on mobile, high color contrast against white",
        },
        {
            "label": "高端礼盒型",
            "style": "premium gift box packaging, matte finish with spot UV gloss, embossed logo, luxury unboxing feel",
            "color_key": "ocean",
            "layout": "magnetic closure lid, ribbon pull, gold foil brand name, elegant thin serif typography",
            "extra": "conveys high perceived value, ideal for gift-oriented keywords on Amazon",
        },
        {
            "label": "透明橱窗型",
            "style": "clear window packaging, see-through front panel showing real product inside, trust-building design",
            "color_key": "warm",
            "layout": "large die-cut window in center, colorful frame border, feature callouts on sides, product visible",
            "extra": "builds buyer confidence by showing actual contents, reduces return rate",
        },
        {
            "label": "缩略图冲击型",
            "style": "bold high-saturation colors, maximum contrast packaging, eye-catching shelf presence, vibrant gradients",
            "color_key": "sunset",
            "layout": "large product name in thick sans-serif font, contrasting color blocks, starburst badge for key feature",
            "extra": "optimized for Amazon search results thumbnail, stands out among competitors at small sizes",
        },
        {
            "label": "场景插画型",
            "style": "illustrated lifestyle packaging, usage scenario artwork printed on box, storytelling design",
            "color_key": "forest",
            "layout": "wrap-around illustration showing product in use, brand logo top-left, age badge top-right, features as small icons",
            "extra": "communicates product usage without text, appeals to emotional purchase decisions",
        },
        {
            "label": "极简品牌型",
            "style": "minimalist brand-focused packaging, single accent color on white, clean sans-serif, Apple-inspired simplicity",
            "color_key": "ocean",
            "layout": "centered product silhouette, brand name prominent, one-line tagline, maximum whitespace, subtle shadow",
            "extra": "premium brand perception, works well for A+ content and brand story pages",
        },
        {
            "label": "全配件展示型",
            "style": "exploded view packaging, all components displayed around open box, what-you-get clarity",
            "color_key": "candy",
            "layout": "open box in center with all accessories arranged around it, numbered callouts, clean grid arrangement",
            "extra": "ideal for multi-component products, reduces 'what is included' customer questions",
        },
        {
            "label": "对比差异型",
            "style": "comparison highlight packaging, before-after or upgrade visual, competitive advantage showcase",
            "color_key": "warm",
            "layout": "split design with product advantage on one side, competitor pain point implied on other, bold checkmark icons",
            "extra": "drives conversion by visually communicating why this product is better, strong for competitive niches",
        },
    ]

    def generate_prompt_variations(self, params: Dict, count: int = 6) -> list:
        """
        为同一产品生成多套有差异的设计方案。
        每套方案使用不同的配色 + 风格 + 排版思路，生成独立的 prompt。
        如果 params 中包含 _ref_analysis（参考图分析结果），会融入每条 prompt。
        """
        product_name = params.get("product_name", "Product")
        package_type = params.get("package_type", "packaging box")
        hierarchy = self._build_hierarchy(params)
        selling_points = self._extract_selling_points(params.get("core_features", []))

        ref = params.get("_ref_analysis", {})
        ref_parts = self._build_reference_prompt(ref)

        variations = []
        designs_pool = self.DESIGN_VARIATIONS[:count]

        for i, dv in enumerate(designs_pool):
            color_scheme = self.COLOR_SCHEMES.get(dv["color_key"],
                                                   random.choice(list(self.COLOR_SCHEMES.values())))

            prompt_parts = [
                f"Amazon product packaging {package_type} for {product_name}",
            ]

            if ref_parts:
                prompt_parts.append(f"reference style: {ref_parts}")

            prompt_parts += [
                f"color scheme: {color_scheme['desc']}",
                dv["style"],
                dv["layout"],
                f'large bold text "{hierarchy["primary"]}" on front',
                dv.get("extra", ""),
                "pure white background RGB(255,255,255)",
                "product fills 85 percent of frame",
                "professional commercial product photography, even studio lighting, soft shadow",
                "high detail, 8k, sharp focus",
                "isolated on pure white, no props, no scene",
                "Amazon listing main image ready",
                "--ar 3:4",
            ]

            prompt_parts = [p for p in prompt_parts if p]
            prompt = ", ".join(prompt_parts)

            design_info = {
                "product_name": product_name,
                "package_type": params.get("package_type", "彩盒"),
                "color_scheme": color_scheme,
                "information_hierarchy": hierarchy,
                "selling_points": selling_points,
                "style_label": dv["label"],
                "amazon_note": dv.get("extra", ""),
                "reference_analysis": ref if ref else None,
                "prompt": prompt,
            }

            variations.append({
                "index": i,
                "prompt": prompt,
                "variation": dv["label"],
                "design": design_info,
            })

        return variations

    @staticmethod
    def _build_reference_prompt(ref: Dict) -> str:
        """将参考图分析结果拼成一段 prompt 片段"""
        if not ref:
            return ""

        parts = []
        if ref.get("style"):
            parts.append(ref["style"])
        if ref.get("color_scheme"):
            parts.append(ref["color_scheme"])
        if ref.get("typography"):
            parts.append(ref["typography"])
        if ref.get("layout"):
            parts.append(ref["layout"])
        if ref.get("key_elements"):
            parts.append(ref["key_elements"])
        if ref.get("overall_mood"):
            parts.append(ref["overall_mood"])
        return ", ".join(parts)


# 单例模式
designer = PackagingDesigner()


def generate_packaging_design(params: Dict) -> Dict:
    """便捷的生成函数"""
    return designer.generate_design(params)


def generate_prompt_variations(params: Dict, count: int = 6) -> list:
    """生成多套不同设计风格的 prompt"""
    return designer.generate_prompt_variations(params, count)
