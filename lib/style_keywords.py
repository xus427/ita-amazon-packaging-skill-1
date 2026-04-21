"""
Structured style keyword control layer.
"""

from typing import Dict, List

ATOM_FIELDS = [
    "color_contrast",
    "color_saturation",
    "palette_warmth",
    "layout_density",
    "whitespace_ratio",
    "frame_fill",
    "headline_scale",
    "typography_weight",
    "mood_premium",
    "mood_playful",
    "minimalism_level",
    "texture_realism",
]

STYLE_KEYWORDS: Dict[str, Dict] = {
    "nordic": {
        "label": "北欧极简",
        "prompt_fragments": ["soft gray-beige palette", "matte paper texture", "large blank margins", "thin sans-serif title", "centered symmetric layout"],
        "negative_fragments": ["no neon accent", "no crowded icons", "no heavy drop shadows"],
        "atom_effects": {"color_saturation": -0.35, "layout_density": -0.35, "whitespace_ratio": 0.45, "minimalism_level": 0.55, "typography_weight": -0.2},
    },
    "minimal": {
        "label": "极简",
        "prompt_fragments": ["single focal product block", "monochrome background", "one-line headline", "strict grid alignment", "clean negative space"],
        "negative_fragments": ["no decorative pattern", "no sticker clutter", "no multi-color gradients"],
        "atom_effects": {"minimalism_level": 0.7, "layout_density": -0.5, "whitespace_ratio": 0.5, "color_saturation": -0.25, "frame_fill": -0.2},
    },
    "luxury": {
        "label": "高端奢华",
        "prompt_fragments": ["deep black base", "foil stamped logo", "embossed emblem", "spot UV highlights", "fine serif typography"],
        "negative_fragments": ["no cartoon graphics", "no flat icon style", "no cheap plastic look"],
        "atom_effects": {"mood_premium": 0.75, "texture_realism": 0.5, "typography_weight": 0.2, "color_contrast": 0.25, "mood_playful": -0.4},
    },
    "premium_packaging": {
        "label": "电商高端包装",
        "prompt_fragments": ["front-facing packshot", "clear hierarchy headline", "material finish close-up", "conversion-focused badge area", "retail-ready clean framing"],
        "negative_fragments": ["no chaotic collage", "no illegible text blocks", "no low-detail rendering"],
        "atom_effects": {"mood_premium": 0.55, "headline_scale": 0.25, "color_contrast": 0.2, "layout_density": 0.1, "texture_realism": 0.45},
    },
    "tech_futuristic": {
        "label": "未来科技",
        "prompt_fragments": ["cool blue cyan glow", "hard-edge geometric panels", "circuit-like line accents", "precision sans typography", "metallic gradient stripes"],
        "negative_fragments": ["no hand-drawn brush", "no vintage ornaments", "no earthy wood grain"],
        "atom_effects": {"color_contrast": 0.35, "color_saturation": 0.2, "palette_warmth": -0.35, "typography_weight": 0.2, "texture_realism": 0.25},
    },
    "cyberpunk": {
        "label": "赛博朋克",
        "prompt_fragments": ["magenta-cyan neon rim", "dark urban backdrop cues", "high-energy diagonal composition", "glitch stripe overlays", "bold condensed headline"],
        "negative_fragments": ["no pastel palette", "no soft minimal layout", "no matte kraft texture"],
        "atom_effects": {"color_contrast": 0.7, "color_saturation": 0.65, "palette_warmth": -0.2, "layout_density": 0.35, "mood_playful": 0.1},
    },
    "playful_kids": {
        "label": "童趣卡通",
        "prompt_fragments": ["rounded shape blocks", "bubble headline style", "bright candy palette", "friendly mascot zone", "large playful icons"],
        "negative_fragments": ["no dark moody tones", "no sharp metallic edges", "no formal serif body"],
        "atom_effects": {"mood_playful": 0.8, "color_saturation": 0.55, "headline_scale": 0.35, "mood_premium": -0.35, "minimalism_level": -0.25},
    },
    "bold_commercial": {
        "label": "强营销冲击",
        "prompt_fragments": ["oversized benefit headline", "red-yellow contrast bursts", "high-visibility callout badges", "tight benefit stacking", "shelf-impact composition"],
        "negative_fragments": ["no subtle low-contrast look", "no tiny headline", "no oversized whitespace"],
        "atom_effects": {"color_contrast": 0.75, "headline_scale": 0.55, "layout_density": 0.45, "frame_fill": 0.3, "whitespace_ratio": -0.35},
    },
    "vintage_retro": {
        "label": "复古",
        "prompt_fragments": ["aged paper tones", "classic frame border", "engraving-style illustration", "retro serif headline", "ink print grain texture"],
        "negative_fragments": ["no futuristic glow", "no glossy plastic finish", "no flat modern icon pack"],
        "atom_effects": {"palette_warmth": 0.35, "color_saturation": -0.15, "typography_weight": 0.2, "mood_premium": 0.15, "texture_realism": 0.3},
    },
    "flat_design": {
        "label": "扁平",
        "prompt_fragments": ["solid color blocks", "2D vector iconography", "uniform stroke width", "shadow-free elements", "simple geometric composition"],
        "negative_fragments": ["no photoreal texture", "no volumetric lighting", "no metallic reflections"],
        "atom_effects": {"minimalism_level": 0.35, "texture_realism": -0.7, "typography_weight": -0.1, "layout_density": -0.05, "color_saturation": 0.15},
    },
    "organic_natural": {
        "label": "自然有机",
        "prompt_fragments": ["kraft paper surface", "leaf silhouette accents", "earthy green-brown palette", "soft daylight rendering", "organic asymmetry layout"],
        "negative_fragments": ["no neon magenta", "no chrome metallic finish", "no hard sci-fi lines"],
        "atom_effects": {"palette_warmth": 0.3, "color_saturation": -0.15, "texture_realism": 0.45, "mood_premium": 0.1, "mood_playful": -0.1},
    },
    "kawaii_japanese": {
        "label": "日系可爱",
        "prompt_fragments": ["pastel pink-mint palette", "chibi mascot placement", "rounded badge stickers", "soft gradient clouds", "cute handwritten accent text"],
        "negative_fragments": ["no harsh dark contrast", "no industrial metal texture", "no strict corporate layout"],
        "atom_effects": {"mood_playful": 0.7, "color_saturation": 0.35, "palette_warmth": 0.2, "headline_scale": 0.2, "mood_premium": -0.2},
    },
    "dark_dramatic": {
        "label": "暗黑戏剧",
        "prompt_fragments": ["black-charcoal dominant field", "single hard spotlight", "deep shadow gradients", "high-contrast typography", "dramatic vignette framing"],
        "negative_fragments": ["no cheerful pastel", "no lightweight playful icons", "no overexposed white background"],
        "atom_effects": {"color_contrast": 0.6, "color_saturation": -0.2, "mood_premium": 0.3, "mood_playful": -0.5, "texture_realism": 0.35},
    },
    "editorial_magazine": {
        "label": "杂志风",
        "prompt_fragments": ["grid-driven columns", "large masthead-like title", "subheading hierarchy blocks", "photo-text balance", "clean editorial margins"],
        "negative_fragments": ["no toy-like stickers", "no random badge explosion", "no chaotic alignment"],
        "atom_effects": {"layout_density": 0.25, "headline_scale": 0.35, "typography_weight": 0.1, "whitespace_ratio": 0.15, "minimalism_level": 0.15},
    },
    "toy_packaging": {
        "label": "玩具包装",
        "prompt_fragments": ["window box product reveal", "age badge corner mark", "feature icon strip", "character-led visual block", "high-energy shelf visibility"],
        "negative_fragments": ["no muted grayscale palette", "no luxury-only restraint", "no sterile medical layout"],
        "atom_effects": {"mood_playful": 0.65, "headline_scale": 0.4, "layout_density": 0.35, "color_saturation": 0.45, "frame_fill": 0.25},
    },
    "clean_medical": {
        "label": "医疗洁净",
        "prompt_fragments": ["white-blue sterile palette", "clinical icon line set", "precision spacing", "clean dosage-style labeling", "hygienic minimal composition"],
        "negative_fragments": ["no grunge texture", "no saturated rainbow palette", "no decorative script fonts"],
        "atom_effects": {"minimalism_level": 0.45, "whitespace_ratio": 0.35, "palette_warmth": -0.25, "texture_realism": 0.2, "mood_playful": -0.35},
    },
    "sporty_energy": {
        "label": "运动活力",
        "prompt_fragments": ["dynamic diagonal streaks", "bold action typography", "high-speed motion cues", "energetic red-orange accents", "performance badge blocks"],
        "negative_fragments": ["no static calm layout", "no ultra-thin fragile type", "no pastel low-energy palette"],
        "atom_effects": {"color_contrast": 0.45, "color_saturation": 0.4, "headline_scale": 0.35, "layout_density": 0.3, "mood_playful": 0.25},
    },
    "feminine_soft": {
        "label": "女性柔和",
        "prompt_fragments": ["powder pink-lilac tones", "soft rounded frames", "silk-like gentle gradients", "elegant light typography", "delicate floral micro motifs"],
        "negative_fragments": ["no harsh blocky geometry", "no heavy black dominance", "no aggressive burst graphics"],
        "atom_effects": {"palette_warmth": 0.2, "color_saturation": 0.1, "typography_weight": -0.2, "mood_premium": 0.2, "mood_playful": 0.15},
    },
    "masculine_strong": {
        "label": "男性硬朗",
        "prompt_fragments": ["charcoal-steel palette", "thick block typography", "angular framing", "rugged material texture", "high-force compact composition"],
        "negative_fragments": ["no pastel candy tones", "no decorative curls", "no soft toy styling"],
        "atom_effects": {"typography_weight": 0.45, "color_contrast": 0.4, "layout_density": 0.2, "mood_playful": -0.25, "texture_realism": 0.3},
    },
    "luxury_minimal": {
        "label": "极简奢华",
        "prompt_fragments": ["black-white-gold triad", "ample calm whitespace", "single centered emblem", "ultra-clean composition", "precise foil detail"],
        "negative_fragments": ["no busy sticker overlays", "no cartoon mascot blocks", "no loud multi-color bursts"],
        "atom_effects": {"mood_premium": 0.8, "minimalism_level": 0.55, "whitespace_ratio": 0.45, "layout_density": -0.25, "texture_realism": 0.4},
    },
    "colorful_maximal": {
        "label": "高饱和丰富",
        "prompt_fragments": ["multi-hue gradient panels", "layered sticker callouts", "dense decorative pattern field", "loud color transitions", "visually packed composition"],
        "negative_fragments": ["no minimalist empty layout", "no muted grayscale palette", "no thin understated headline"],
        "atom_effects": {"color_saturation": 0.85, "layout_density": 0.55, "whitespace_ratio": -0.45, "mood_playful": 0.35, "minimalism_level": -0.45},
    },
    "industrial_mechanical": {
        "label": "工业机械风",
        "prompt_fragments": ["brushed metal panel texture", "rivet-like structural details", "technical label blocks", "hazard stripe accents", "precision blueprint geometry"],
        "negative_fragments": ["no soft pastel ornaments", "no organic floral textures", "no playful mascot style"],
        "atom_effects": {"texture_realism": 0.65, "typography_weight": 0.25, "color_contrast": 0.35, "mood_playful": -0.35, "palette_warmth": -0.15},
    },
    "photorealistic": {
        "label": "真实感",
        "prompt_fragments": [
            "ultra realistic product rendering",
            "studio photography lighting",
            "soft shadow grounding",
            "high detail material texture",
            "real world surface imperfections",
            "accurate reflections and highlights",
            "physically based rendering look",
            "natural light falloff",
        ],
        "negative_fragments": [
            "no cartoon style",
            "no flat illustration",
            "no exaggerated colors",
            "no unrealistic proportions",
            "no plastic toy-like texture",
        ],
        "atom_effects": {
            "texture_realism": 0.8,
            "color_saturation": -0.2,
            "color_contrast": 0.2,
            "mood_premium": 0.3,
            "minimalism_level": 0.1,
        },
    },
}

KEYWORD_ALIASES = {
    "北欧": "nordic",
    "极简": "minimal",
    "高端奢华": "luxury",
    "电商高端包装": "premium_packaging",
    "未来科技": "tech_futuristic",
    "科技": "tech_futuristic",
    "赛博朋克": "cyberpunk",
    "童趣卡通": "playful_kids",
    "童趣": "playful_kids",
    "强营销冲击": "bold_commercial",
    "复古": "vintage_retro",
    "扁平": "flat_design",
    "自然有机": "organic_natural",
    "原木": "organic_natural",
    "日系可爱": "kawaii_japanese",
    "暗黑戏剧": "dark_dramatic",
    "暗黑": "dark_dramatic",
    "杂志风": "editorial_magazine",
    "玩具包装": "toy_packaging",
    "医疗洁净": "clean_medical",
    "运动活力": "sporty_energy",
    "女性柔和": "feminine_soft",
    "男性硬朗": "masculine_strong",
    "极简奢华": "luxury_minimal",
    "高饱和丰富": "colorful_maximal",
    "工业机械风": "industrial_mechanical",
    "真实感": "photorealistic",
    "欧美": "premium_packaging",
    "ins": "editorial_magazine",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _normalize_keywords(keywords: List[str]) -> List[str]:
    keys = []
    seen = set()
    for raw in keywords or []:
        name = str(raw or "").strip()
        if not name:
            continue
        key = name if name in STYLE_KEYWORDS else KEYWORD_ALIASES.get(name, "")
        if not key or key not in STYLE_KEYWORDS or key in seen:
            continue
        keys.append(key)
        seen.add(key)
    return keys


def get_keyword_prompt_fragments(keywords: List[str]) -> List[str]:
    items = []
    seen = set()
    for key in _normalize_keywords(keywords):
        for frag in STYLE_KEYWORDS[key]["prompt_fragments"]:
            if frag not in seen:
                items.append(frag)
                seen.add(frag)
    return items


def get_keyword_negative_fragments(keywords: List[str]) -> List[str]:
    items = []
    seen = set()
    for key in _normalize_keywords(keywords):
        for frag in STYLE_KEYWORDS[key]["negative_fragments"]:
            if frag not in seen:
                items.append(frag)
                seen.add(frag)
    return items


def get_keyword_atom_effects(keywords: List[str]) -> Dict[str, float]:
    effects = {atom: 0.0 for atom in ATOM_FIELDS}
    for key in _normalize_keywords(keywords):
        atom_effects = STYLE_KEYWORDS[key].get("atom_effects", {})
        for atom, delta in atom_effects.items():
            if atom not in effects:
                continue
            effects[atom] = _clamp(effects[atom] + float(delta), -1.0, 1.0)
    return effects


def build_example_style_payload(keywords: List[str]) -> Dict:
    """
    Example:
      build_example_style_payload(["nordic", "luxury_minimal"])
    """
    return {
        "keywords": _normalize_keywords(keywords),
        "prompt_fragments": get_keyword_prompt_fragments(keywords),
        "negative_fragments": get_keyword_negative_fragments(keywords),
        "atom_effects": get_keyword_atom_effects(keywords),
    }
