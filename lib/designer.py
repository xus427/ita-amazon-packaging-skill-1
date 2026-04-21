"""
亚马逊包装主图生成器
核心逻辑：根据产品信息生成设计方案和 AI 提示词
"""

from typing import Dict, List, Optional
import random
import re
from lib.style_keywords import get_keyword_prompt_fragments, get_keyword_negative_fragments


class PackagingDesigner:
    """包装设计师 - 生成设计方案和提示词"""
    CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
    NON_EN_TEXT_RE = re.compile(r"[^A-Za-z0-9&+\-/:,.'() ]+")
    
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
    
    @staticmethod
    def _clamp(v: float, vmin: float, vmax: float) -> float:
        return max(vmin, min(vmax, float(v)))

    @classmethod
    def _force_english_text(cls, text: str, fallback: str) -> str:
        """
        强制转为英文可用文本：
        - 包含中文时，尽量提取英文/数字字符
        - 若提取后为空，回退到 fallback
        """
        raw = str(text or "").strip()
        if not raw:
            return fallback
        if not cls.CJK_RE.search(raw):
            return raw
        cleaned = cls.NON_EN_TEXT_RE.sub(" ", raw)
        cleaned = " ".join(cleaned.split())
        return cleaned if cleaned else fallback

    @classmethod
    def _sanitize_prompt_part(cls, text: str) -> str:
        """
        最终 prompt 级别清洗：
        - 去除中文字符
        - 保留常见英文符号
        """
        raw = str(text or "").strip()
        if not raw:
            return ""
        raw = cls.CJK_RE.sub(" ", raw)
        raw = cls.NON_EN_TEXT_RE.sub(" ", raw)
        return " ".join(raw.split())

    def _map_style_atoms_to_prompt_controls(self, style_atoms: Dict) -> Dict:
        """Instance 入口，委托给模块级 map_style_atoms_to_prompt。"""
        return map_style_atoms_to_prompt(style_atoms)
    
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
        
        # 3. 设计内容展示区
        content_display = self._design_content_area(params)
        
        # 4. 应用合规布局
        compliance = self._apply_compliance(params)
        
        # 5. 生成 AI 提示词
        prompt = self._generate_prompt(params, color_scheme, hierarchy)
        
        return {
            "product_name": params.get("product_name", ""),
            "package_type": params.get("package_type", "彩盒"),
            "color_scheme": color_scheme,
            "information_hierarchy": hierarchy,
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
        features = []
        
        # 一级：最重要的卖点（通常是数量/核心功能）
        primary = features[0] if features else "PREMIUM QUALITY"
        
        # 二级：产品名称
        secondary = params.get("product_name", "Product Name")
        
        # 三级：其他卖点
        tertiary = features[1:4] if len(features) > 1 else ["High Quality", "Great Gift"]

        primary = self._force_english_text(primary, "PREMIUM QUALITY")
        secondary = self._force_english_text(secondary, "Product Name")
        tertiary = [
            self._force_english_text(item, fallback)
            for item, fallback in zip(
                tertiary,
                ["High Quality", "Great Gift", "Easy To Use"],
            )
        ]

        return {
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary
        }
    
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
    
    def _generate_prompt(self, params: Dict, color_scheme: Dict, hierarchy: Dict) -> str:
        """生成 AI 绘图提示词"""
        product_name = self._force_english_text(params.get("product_name", "Product"), "Product")
        package_type = self._force_english_text(params.get("package_type", "packaging box"), "packaging box")
        style_keywords = params.get("style_keywords", [])
        image_ratio = params.get("image_ratio", "3:4")
        
        # 转换风格关键词（工业级结构化映射）
        style_parts = get_keyword_prompt_fragments(style_keywords)
        neg_parts = get_keyword_negative_fragments(style_keywords)
        
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
            "all visible text must be English only, no Chinese characters, no Hanzi",
            ("avoid: " + ", ".join(neg_parts)) if neg_parts else "",
            f"--ar {image_ratio}"
        ]
        
        # 如果有展示窗需求
        if params.get("need_content_display", True):
            prompt_parts.insert(3, "transparent window showing product inside")
        
        prompt_parts = [self._sanitize_prompt_part(p) for p in prompt_parts]
        prompt_parts = [p for p in prompt_parts if p]
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
        product_name = self._force_english_text(params.get("product_name", "Product"), "Product")
        package_type = self._force_english_text(params.get("package_type", "packaging box"), "packaging box")
        hierarchy = self._build_hierarchy(params)
        ref = params.get("_ref_analysis", {})
        ref_parts = self._build_reference_prompt(ref)
        controls = self._map_style_atoms_to_prompt_controls(params.get("_style_atoms", {}))
        primary_color = self._force_english_text((params.get("primary_color") or "").strip(), "")
        image_ratio = params.get("image_ratio", "3:4")
        keyword_prompts = get_keyword_prompt_fragments(params.get("style_keywords", []))
        keyword_negs = get_keyword_negative_fragments(params.get("style_keywords", []))
        spec_prompt = str(params.get("_design_spec_prompt", "") or "").strip()

        variations = []
        designs_pool = self.DESIGN_VARIATIONS[:count]

        for i, dv in enumerate(designs_pool):
            color_scheme = self.COLOR_SCHEMES.get(dv["color_key"],
                                                   random.choice(list(self.COLOR_SCHEMES.values())))

            prompt_parts = [
                f"Amazon product packaging {package_type} for {product_name}",
            ]

            if ref_parts:
                prompt_parts.append(f"reference style: {self._sanitize_prompt_part(ref_parts)}")
            if spec_prompt:
                prompt_parts.append(f"design brief: {self._sanitize_prompt_part(spec_prompt)}")

            design_phrases = controls.get("phrases", []) or [
                controls.get("contrast_phrase", ""),
                controls.get("layout_phrase", ""),
                controls.get("headline_phrase", ""),
            ]
            prompt_parts += design_phrases
            prompt_parts += keyword_prompts
            prompt_parts += [
                f"color scheme: {color_scheme['desc']}",
                (f"primary color focus: {primary_color}" if primary_color else ""),
                dv["style"],
                dv["layout"],
                f'headline text "{hierarchy["primary"]}" on front',
                dv.get("extra", ""),
                "pure white background RGB(255,255,255)",
                controls.get("frame_fill_phrase", "product fills 85 percent of frame"),
                "professional commercial product photography, even studio lighting, soft shadow",
                "high detail, 8k, sharp focus",
                "isolated on pure white, no props, no scene",
                "Amazon listing main image ready",
                "all visible text must be English only, no Chinese characters, no Hanzi",
                ("avoid: " + ", ".join(keyword_negs)) if keyword_negs else "",
                f"--ar {image_ratio}",
            ]

            prompt_parts = [self._sanitize_prompt_part(p) for p in prompt_parts]
            prompt_parts = [p for p in prompt_parts if p]
            prompt = ", ".join(prompt_parts)

            design_info = {
                "product_name": product_name,
                "package_type": params.get("package_type", "彩盒"),
                "color_scheme": color_scheme,
                "information_hierarchy": hierarchy,
                "style_label": dv["label"],
                "amazon_note": dv.get("extra", ""),
                "reference_analysis": ref if ref else None,
                "style_atoms": controls["debug_atoms"],
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


# ==================== design_controls → prompt 映射 ====================
# 模块级函数，供 app.py / 其它模块直接调用，等价于旧 _map_style_atoms_to_prompt_controls，
# 但覆盖完整 design_controls（色彩 / 构图 / 文本 / 风格 四组 11 个 atom）。
# 返回结构：
#   {
#     "phrases": [...],                # 拼接到 prompt 的短语列表（已过滤空）
#     "debug_atoms": {...},            # 被 clamp 后的实际生效值
#     # --- 向后兼容字段 ---
#     "contrast_phrase": ...,
#     "headline_phrase": ...,
#     "layout_phrase": ...,
#     "frame_fill_phrase": ...,
#   }
_ATOM_PROMPT_BOUNDS = {
    "color_contrast":    (0.0, 1.0, 0.50),
    "palette_warmth":    (0.0, 1.0, 0.50),
    "color_saturation":  (0.0, 1.0, 0.50),
    "layout_density":    (0.0, 1.0, 0.50),
    "whitespace_ratio":  (0.0, 1.0, 0.35),
    "frame_fill":        (0.40, 1.0, 0.85),
    "headline_scale":    (0.0, 1.0, 0.50),
    "typography_weight": (0.0, 1.0, 0.60),
    "mood_premium":      (0.0, 1.0, 0.40),
    "mood_playful":      (0.0, 1.0, 0.40),
    "minimalism_level":  (0.0, 1.0, 0.30),
    "texture_realism":   (0.0, 1.0, 0.55),
}


def _clamp_atom(atoms: Dict, name: str) -> float:
    lo, hi, default = _ATOM_PROMPT_BOUNDS[name]
    try:
        v = float(atoms.get(name, default))
    except Exception:
        v = default
    return max(lo, min(hi, v))


def map_style_atoms_to_prompt(style_atoms: Dict) -> Dict:
    """把 design_controls / style_atoms 映射为可拼接的 prompt 短语（向后兼容旧字段）。"""
    atoms = style_atoms or {}
    cc  = _clamp_atom(atoms, "color_contrast")
    pw  = _clamp_atom(atoms, "palette_warmth")
    cs  = _clamp_atom(atoms, "color_saturation")
    ld  = _clamp_atom(atoms, "layout_density")
    ws  = _clamp_atom(atoms, "whitespace_ratio")
    ff  = _clamp_atom(atoms, "frame_fill")
    hs  = _clamp_atom(atoms, "headline_scale")
    tw  = _clamp_atom(atoms, "typography_weight")
    mp  = _clamp_atom(atoms, "mood_premium")
    mpl = _clamp_atom(atoms, "mood_playful")
    ml  = _clamp_atom(atoms, "minimalism_level")
    tr  = _clamp_atom(atoms, "texture_realism")

    # ---------- 色彩 ----------
    if cc >= 0.75:
        contrast_phrase = "maximum contrast color blocks, very high visual separation"
    elif cc >= 0.55:
        contrast_phrase = "balanced high contrast color system"
    elif cc >= 0.30:
        contrast_phrase = "soft and moderate contrast color system"
    else:
        contrast_phrase = "low-contrast tonal color harmony"

    if cs >= 0.70:
        saturation_phrase = "vivid highly saturated color palette"
    elif cs <= 0.30:
        saturation_phrase = "muted desaturated color palette"
    else:
        saturation_phrase = ""

    if pw >= 0.70:
        warmth_phrase = "warm-toned palette with orange, red and amber accents"
    elif pw <= 0.30:
        warmth_phrase = "cool-toned palette with blue and teal accents"
    else:
        warmth_phrase = ""

    # ---------- 构图 ----------
    if ld >= 0.70:
        layout_phrase = "dense information layout with compact visual modules"
    elif ld >= 0.45:
        layout_phrase = "balanced modular layout with clear spacing"
    else:
        layout_phrase = "spacious layout with generous whitespace"

    if ws >= 0.65:
        whitespace_phrase = "high whitespace ratio, premium breathing room"
    elif ws <= 0.20:
        whitespace_phrase = "edge-to-edge composition with minimal whitespace"
    else:
        whitespace_phrase = ""

    ff_percent = int(round(60 + ff * 35))  # 0.4→74, 1.0→95
    frame_fill_phrase = f"product fills {ff_percent} percent of frame"

    # ---------- 文本 ----------
    if hs >= 0.75:
        headline_phrase = "oversized dominant headline text for instant readability"
    elif hs >= 0.55:
        headline_phrase = "prominent headline text with clear hierarchy"
    else:
        headline_phrase = "moderate headline emphasis with balanced text hierarchy"

    if tw >= 0.70:
        typography_phrase = "heavy bold typography, strong weight"
    elif tw <= 0.35:
        typography_phrase = "light refined typography, airy weight"
    else:
        typography_phrase = ""

    # ---------- 情绪 / 风格 ----------
    mood_bits = []
    if mp >= 0.65:
        mood_bits.append("premium refined aesthetic, luxury finish")
    if mpl >= 0.65:
        mood_bits.append("playful friendly tone, fun vibe")
    if ml >= 0.70:
        mood_bits.append("minimalist clean design, reductive composition")
    elif ml <= 0.25:
        mood_bits.append("rich decorative visual density")
    if tr >= 0.70:
        mood_bits.append("photorealistic material texture, real-world studio look")
    elif tr <= 0.30:
        mood_bits.append("stylized graphic texture, less photographic realism")
    mood_phrase = ", ".join(mood_bits) if mood_bits else ""

    phrases = [
        contrast_phrase,
        saturation_phrase,
        warmth_phrase,
        layout_phrase,
        whitespace_phrase,
        headline_phrase,
        typography_phrase,
        mood_phrase,
    ]
    phrases = [p for p in phrases if p]

    debug_atoms = {
        "color_contrast":    round(cc, 4),
        "palette_warmth":    round(pw, 4),
        "color_saturation":  round(cs, 4),
        "layout_density":    round(ld, 4),
        "whitespace_ratio":  round(ws, 4),
        "frame_fill":        round(ff, 4),
        "headline_scale":    round(hs, 4),
        "typography_weight": round(tw, 4),
        "mood_premium":      round(mp, 4),
        "mood_playful":      round(mpl, 4),
        "minimalism_level":  round(ml, 4),
        "texture_realism":   round(tr, 4),
    }

    return {
        "phrases": phrases,
        "debug_atoms": debug_atoms,
        "contrast_phrase": contrast_phrase,
        "headline_phrase": headline_phrase,
        "layout_phrase": layout_phrase,
        "frame_fill_phrase": frame_fill_phrase,
    }
