"""
Design Requirement Engine
Parse free-form requirement text into structured design spec,
then build prompt guidance from the spec.
"""

from typing import Dict, List

from lib.style_keywords import get_keyword_prompt_fragments


def _empty_spec() -> Dict:
    return {
        "product": {},
        "visual_focus": {},
        "layout": {},
        "text": {},
        "style_hint": {"keywords": []},
        "constraints": {},
    }


def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def parse_design_requirement(text: str) -> Dict:
    """
    Rule-based parsing from natural language requirement text to DesignSpec.
    """
    raw = str(text or "").strip().lower()
    spec = _empty_spec()
    if not raw:
        return spec

    # ----- product -----
    if _contains_any(raw, ["鼠标", "mouse"]):
        spec["product"]["name"] = "wireless mouse"
        spec["product"]["category"] = "electronics"
    elif _contains_any(raw, ["玩具", "toy"]):
        spec["product"]["name"] = "toy product"
        spec["product"]["category"] = "toy"
    elif _contains_any(raw, ["护肤", "化妆", "skincare", "cosmetic"]):
        spec["product"]["name"] = "beauty product"
        spec["product"]["category"] = "beauty"

    # ----- visual focus / layout -----
    if _contains_any(raw, ["主图", "amazon", "亚马逊"]):
        spec["visual_focus"]["primary"] = "product"
        spec["visual_focus"]["secondary"] = "feature_badges"
        spec["visual_focus"]["focus_strategy"] = "centered"
        spec["layout"]["type"] = "product_centered"
        spec["constraints"]["platform"] = "amazon_main_image"

    if _contains_any(raw, ["信息很多", "信息密集", "信息量大"]):
        spec["layout"]["density"] = "high"
    elif _contains_any(raw, ["简洁", "简约", "留白"]):
        spec["layout"]["density"] = "low"
        spec["layout"]["whitespace"] = "high"
    else:
        spec["layout"]["density"] = spec["layout"].get("density", "medium")

    # ----- text requirements -----
    if _contains_any(raw, ["大标题", "标题要大", "标题很大"]):
        spec["text"]["headline"] = "large"
        spec["text"]["headline_scale_boost"] = 0.35
    if _contains_any(raw, ["参数突出", "参数醒目", "卖点突出", "突出卖点"]):
        spec["text"]["feature_style"] = "badge"
        spec["text"]["readability"] = "high"
        spec["layout"]["density"] = "medium"

    # ----- style keywords / atoms hints -----
    keywords = []
    style_hint = spec["style_hint"]
    if _contains_any(raw, ["高对比", "强对比", "对比强"]):
        style_hint["color"] = "high_contrast"
        style_hint["contrast_boost"] = 0.5
        keywords.append("bold_commercial")
    if _contains_any(raw, ["科技感", "科技风", "futuristic", "tech"]):
        keywords.append("tech_futuristic")
    if _contains_any(raw, ["童趣", "卡通", "可爱"]):
        keywords.append("playful_kids")
    if _contains_any(raw, ["极简", "简洁"]):
        keywords.append("minimal")
    if _contains_any(raw, ["真实感", "写实", "摄影感", "realistic", "photoreal"]):
        keywords.append("photorealistic")

    # de-duplicate while keeping order
    dedup = []
    seen = set()
    for k in keywords:
        if k not in seen:
            seen.add(k)
            dedup.append(k)
    style_hint["keywords"] = dedup

    # ----- constraints -----
    if _contains_any(raw, ["白底", "白色背景", "white background", "pure white"]):
        spec["constraints"]["background"] = "white"

    return spec


def build_prompt_from_spec(spec: Dict) -> str:
    """
    Build prompt fragments from parsed DesignSpec.
    """
    prompt_parts: List[str] = []

    product = spec.get("product", {})
    product_name = product.get("name")
    if product_name:
        prompt_parts.append(f"{product_name} packaging")

    layout = spec.get("layout", {})
    if layout.get("type") == "product_centered":
        prompt_parts.append("centered product composition")
    if layout.get("density") == "high":
        prompt_parts.append("dense information layout")
    elif layout.get("density") == "low":
        prompt_parts.append("clean sparse layout with ample spacing")
    if layout.get("whitespace") == "high":
        prompt_parts.append("generous whitespace")

    text = spec.get("text", {})
    if text.get("headline") == "large":
        prompt_parts.append("large bold headline")
    if text.get("feature_style") == "badge":
        prompt_parts.append("feature parameters in badge style")
    if text.get("readability") == "high":
        prompt_parts.append("high readability at thumbnail size")

    style_hint = spec.get("style_hint", {})
    keywords = style_hint.get("keywords", []) or []
    prompt_parts.extend(get_keyword_prompt_fragments(keywords))

    constraints = spec.get("constraints", {})
    if constraints.get("background") == "white":
        prompt_parts.append("pure white background")
    if constraints.get("platform") == "amazon_main_image":
        prompt_parts.append("amazon main image compliant framing")

    return ", ".join([p for p in prompt_parts if p])
