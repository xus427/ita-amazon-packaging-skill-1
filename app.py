"""
亚马逊包装主图生成器 - Flask API 服务 + Web 界面
"""

import json
import os
import sys
import random
import hashlib
import uuid
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, render_template, make_response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.designer import generate_packaging_design, generate_prompt_variations
from lib.image_generator import get_generator
from lib.config import get_env, get_env_bool, get_env_int
from lib.feishu_uploader import get_feishu_uploader
from lib.image_analyzer import get_image_analyzer
from lib.models import (
    db, init_db, User, Project, GenerateTask, GeneratedImage,
    UserStyleAtom, StyleTraceLog,
)

app = Flask(__name__)

# ---------- 配置 ----------
OUTPUT_DIR = get_env("OUTPUT_DIR", "./output")
UPLOAD_DIR = get_env("UPLOAD_DIR", "./uploads")
DEFAULT_BACKEND = get_env("DEFAULT_IMAGE_BACKEND", "pollinations")
SECRET_KEY = get_env("SECRET_KEY", "pack-design-local-secret-key-2024")

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///packdesign.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# 非 debug 时 Jinja 默认不监视模板变更，改 HTML 后易一直看到旧页
app.config["TEMPLATES_AUTO_RELOAD"] = True

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db(app)

ATOM_CONFIG = {
    # ---- color 色彩 ----
    "color_contrast":    {"default": 0.50, "min": 0.00, "max": 1.00, "step_up": 0.03, "step_down": 0.03},
    "palette_warmth":    {"default": 0.50, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
    "color_saturation":  {"default": 0.50, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
    # ---- composition 构图 ----
    "layout_density":    {"default": 0.50, "min": 0.00, "max": 1.00, "step_up": 0.02, "step_down": 0.02},
    "whitespace_ratio":  {"default": 0.35, "min": 0.00, "max": 1.00, "step_up": 0.03, "step_down": 0.03},
    "frame_fill":        {"default": 0.85, "min": 0.40, "max": 1.00, "step_up": 0.02, "step_down": 0.02},
    # ---- text 文本 ----
    "headline_scale":    {"default": 0.50, "min": 0.00, "max": 1.00, "step_up": 0.03, "step_down": 0.03},
    "typography_weight": {"default": 0.60, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
    # ---- mood 风格 ----
    "mood_premium":      {"default": 0.40, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
    "mood_playful":      {"default": 0.40, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
    "minimalism_level":  {"default": 0.30, "min": 0.00, "max": 1.00, "step_up": 0.05, "step_down": 0.05},
}

DESIGN_CONTROLS_SCHEMA = [
    {
        "group_id": "color",
        "group_label": "色彩",
        "atoms": [
            {"id": "color_contrast",   "label": "对比度"},
            {"id": "palette_warmth",   "label": "冷暖倾向"},
            {"id": "color_saturation", "label": "饱和度"},
        ],
    },
    {
        "group_id": "composition",
        "group_label": "构图",
        "atoms": [
            {"id": "layout_density",   "label": "版面密度"},
            {"id": "whitespace_ratio", "label": "留白比例"},
            {"id": "frame_fill",       "label": "主体占比"},
        ],
    },
    {
        "group_id": "text",
        "group_label": "文本",
        "atoms": [
            {"id": "headline_scale",    "label": "标题大小"},
            {"id": "typography_weight", "label": "字重"},
        ],
    },
    {
        "group_id": "mood",
        "group_label": "风格",
        "atoms": [
            {"id": "mood_premium",     "label": "高级感"},
            {"id": "mood_playful",     "label": "趣味感"},
            {"id": "minimalism_level", "label": "极简程度"},
        ],
    },
]

# ---------- Captcha 存储 (内存) ----------
_captcha_store: dict = {}


def _generate_captcha_svg(text: str) -> str:
    """生成一个简单的数学验证码 SVG"""
    svg_w, svg_h = 120, 40
    chars = list(text)
    elements = []
    elements.append(
        f'<rect width="{svg_w}" height="{svg_h}" fill="#eef2ff" rx="6"/>'
    )
    for i, ch in enumerate(chars):
        x = 12 + i * 18
        y = 28 + random.randint(-3, 3)
        rot = random.randint(-15, 15)
        color = random.choice(["#4f46e5", "#7c3aed", "#6366f1", "#4338ca"])
        elements.append(
            f'<text x="{x}" y="{y}" font-size="22" font-family="monospace" '
            f'fill="{color}" transform="rotate({rot},{x},{y})">'
            f"{html.escape(ch)}</text>"
        )
    for _ in range(3):
        x1, y1 = random.randint(0, svg_w), random.randint(0, svg_h)
        x2, y2 = random.randint(0, svg_w), random.randint(0, svg_h)
        elements.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#c7d2fe" stroke-width="1"/>'
        )
    inner = "".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}">{inner}</svg>'
    )


# ---------- Token 工具 ----------
def _make_token(user_id: str) -> str:
    raw = f"{user_id}:{SECRET_KEY}:{datetime.utcnow().date().isoformat()}"
    sig = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{user_id}.{sig}"


def _parse_token(token: str):
    """解析 token，返回 user_id 或 None"""
    if not token or "." not in token:
        return None
    parts = token.split(".", 1)
    return parts[0]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
        user_id = _parse_token(token)
        if not user_id:
            return jsonify({"code": 401, "error": "请先登录"}), 401
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"code": 401, "error": "用户不存在"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def _get_request_context(data: dict = None) -> dict:
    """
    统一注入上下文：
    - user_id：优先使用已登录用户，兼容前端显式传入 user_id
    - project_id：优先使用 payload / query 中的 project_id
    """
    data = data or {}
    current_user = getattr(request, "current_user", None)
    payload_user_id = str(data.get("user_id") or request.args.get("user_id") or "").strip()
    payload_project_id = str(data.get("project_id") or request.args.get("project_id") or "").strip()
    user_id = current_user.id if current_user else (payload_user_id or "default_user")
    project_id = payload_project_id or "default_project"
    return {
        "user_id": user_id,
        "project_id": project_id,
        "context": {
            "user_id": user_id,
            "project_id": project_id,
        }
    }


# ---------- 页面路由 ----------
@app.route("/")
def index():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/output/<path:filename>", methods=["GET"])
def serve_output(filename):
    abs_output = os.path.abspath(OUTPUT_DIR)
    return send_from_directory(abs_output, filename)


# ---------- 健康检查 ----------
@app.route("/health", methods=["GET"])
def health():
    feishu_configured = get_feishu_uploader() is not None
    base = os.path.dirname(os.path.abspath(__file__))
    index_template = os.path.join(base, "templates", "index.html")
    has_ref_paste_ui = False
    if os.path.isfile(index_template):
        with open(index_template, "r", encoding="utf-8", errors="replace") as f:
            has_ref_paste_ui = "refPasteZone" in f.read(400000)
    return jsonify({
        "service": "amazon-packaging-skill",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "default_backend": DEFAULT_BACKEND,
        "output_dir": OUTPUT_DIR,
        "feishu_upload": "ready" if feishu_configured else "not_configured",
        "index_template": index_template,
        "index_has_ref_paste_ui": has_ref_paste_ui,
    })


# ---------- 验证码 ----------
@app.route("/api/captcha", methods=["GET"])
def captcha():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    answer = a + b
    captcha_id = str(uuid.uuid4())
    _captcha_store[captcha_id] = str(answer)
    if len(_captcha_store) > 500:
        keys = list(_captcha_store.keys())[:200]
        for k in keys:
            _captcha_store.pop(k, None)
    text = f"{a} + {b} = ?"
    svg = _generate_captcha_svg(text)
    return jsonify({"code": 200, "captcha_id": captcha_id, "svg": svg})


def _verify_captcha(captcha_id: str, answer: str) -> bool:
    expected = _captcha_store.pop(captcha_id, None)
    if expected is None:
        return False
    return str(answer).strip() == expected


# ---------- 认证 ----------
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    captcha_id = data.get("captcha_id", "")
    captcha_answer = data.get("captcha_answer", "")

    if not _verify_captcha(captcha_id, captcha_answer):
        return jsonify({"code": 400, "error": "验证码错误"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"code": 400, "error": "用户名或密码错误"}), 400

    token = _make_token(user.id)
    return jsonify({"code": 200, "user": user.to_dict(), "token": token})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "").strip() or username
    captcha_id = data.get("captcha_id", "")
    captcha_answer = data.get("captcha_answer", "")

    if not username or len(password) < 4:
        return jsonify({"code": 400, "error": "用户名不能为空，密码至少4位"}), 400

    if not _verify_captcha(captcha_id, captcha_answer):
        return jsonify({"code": 400, "error": "验证码错误"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"code": 400, "error": "用户名已存在"}), 400

    user = User(username=username, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = _make_token(user.id)
    return jsonify({"code": 200, "user": user.to_dict(), "token": token})


# ---------- 项目管理 ----------
@app.route("/api/projects", methods=["GET"])
@login_required
def list_projects():
    projects = Project.query.filter_by(user_id=request.current_user.id)\
        .order_by(Project.updated_at.desc()).all()
    return jsonify({"code": 200, "projects": [p.to_dict() for p in projects]})


@app.route("/api/projects", methods=["POST"])
@login_required
def create_project():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"code": 400, "error": "项目名称不能为空"}), 400

    project = Project(
        name=name,
        description=data.get("description", ""),
        user_id=request.current_user.id,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"code": 200, "project": project.to_dict()})


@app.route("/api/projects/<project_id>/tasks", methods=["GET"])
@login_required
def list_tasks(project_id):
    project = db.session.get(Project, project_id)
    if not project or project.user_id != request.current_user.id:
        return jsonify({"code": 404, "error": "项目不存在"}), 404
    tasks = GenerateTask.query.filter_by(project_id=project_id)\
        .order_by(GenerateTask.created_at.desc()).all()
    return jsonify({"code": 200, "tasks": [t.to_dict() for t in tasks]})


@app.route("/api/tasks/<task_id>", methods=["GET"])
@login_required
def get_task(task_id):
    task = db.session.get(GenerateTask, task_id)
    if not task or task.user_id != request.current_user.id:
        return jsonify({"code": 404, "error": "任务不存在"}), 404
    return jsonify({"code": 200, "task": task.to_dict()})


@app.route("/api/style-traces", methods=["GET"])
@login_required
def list_style_traces():
    ctx = _get_request_context()
    user_id = ctx["user_id"]
    project_id = ctx["project_id"]

    order = (request.args.get("order") or "desc").lower()
    if order not in {"asc", "desc"}:
        order = "desc"
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 200)
    except Exception:
        limit = 20
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except Exception:
        offset = 0

    q = StyleTraceLog.query.filter_by(user_id=user_id)
    if project_id and project_id != "default_project":
        q = q.filter_by(project_id=project_id)
    total = q.count()
    if order == "asc":
        rows = q.order_by(StyleTraceLog.created_at.asc()).offset(offset).limit(limit).all()
    else:
        rows = q.order_by(StyleTraceLog.created_at.desc()).offset(offset).limit(limit).all()

    traces = []
    for r in rows:
        item = r.to_dict()
        payload = item.pop("payload", {}) or {}
        payload.setdefault("trace_id", item["id"])
        payload.setdefault("timestamp", item["created_at"])
        payload.setdefault("event", item.get("event"))
        payload.setdefault("project_id", item.get("project_id"))
        payload.setdefault("task_id", item.get("task_id"))
        traces.append(payload)

    return jsonify({
        "code": 200,
        "data": {
            "user_id": user_id,
            "project_id": project_id,
            "order": order,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(traces),
                "total": total,
                "has_more": offset + len(traces) < total,
            },
            "traces": traces,
        },
        "msg": "ok",
    })


@app.route("/api/design-controls", methods=["GET"])
@login_required
def get_design_controls():
    """返回完整的 design_controls schema + 当前用户各 atom 值（用于专业控制面板）。"""
    ctx = _get_request_context()
    user_id = ctx["user_id"]
    project_id = ctx["project_id"]
    current = get_style_atoms(user_id, project_id)
    return jsonify({
        "code": 200,
        "data": {
            "user_id": user_id,
            "project_id": project_id,
            "schema_version": 1,
            "groups": DESIGN_CONTROLS_SCHEMA,
            "bounds": {atom: {"min": cfg["min"], "max": cfg["max"], "step_up": cfg["step_up"], "step_down": cfg["step_down"]}
                       for atom, cfg in ATOM_CONFIG.items()},
            "defaults": {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()},
            "values": current,
        },
    })


@app.route("/api/style-adjust", methods=["POST"])
@login_required
def style_adjust():
    """
    两种用法：
      1) direction 模式（+1 / -1 / 0）：按 step_up/step_down 累加，记 like/dislike
      2) value 模式（直接给 0~1 滑块值）：直接落库，不动 like/dislike
    """
    data = request.get_json() or {}
    ctx = _get_request_context(data)
    atom = (data.get("atom") or "").strip()
    if atom not in ATOM_CONFIG:
        return jsonify({"code": 400, "error": f"invalid atom: {atom}"}), 400

    cfg = ATOM_CONFIG[atom]
    current_atoms = get_style_atoms(ctx["user_id"], ctx["project_id"])
    before = float(current_atoms.get(atom, cfg["default"]))

    raw_value = data.get("value", None)
    has_value = raw_value is not None and raw_value != ""

    if has_value:
        try:
            value = float(raw_value)
        except Exception:
            return jsonify({"code": 400, "error": "value must be a number in [0,1]"}), 400
        attempted = value
        direction = 0
        rule_hit = ["manual_adjust_slider"]
        feedback_event = "neutral"
        reason_text = "用户通过滑块直接设置风格强度"
    else:
        try:
            direction = int(data.get("direction"))
        except Exception:
            return jsonify({"code": 400, "error": "direction must be -1, 0, or 1, or provide 'value'"}), 400
        if direction not in (-1, 0, 1):
            return jsonify({"code": 400, "error": "direction must be -1, 0, or 1"}), 400
        if direction == 1:
            attempted = before + cfg["step_up"]
        elif direction == -1:
            attempted = before - cfg["step_down"]
        else:
            attempted = before
        rule_hit = ["manual_adjust_step"]
        feedback_event = "like" if direction == 1 else ("dislike" if direction == -1 else "neutral")
        reason_text = "用户手动调节风格强度"

    after = _clamp(attempted, cfg["min"], cfg["max"])
    save_style_atoms(ctx["user_id"], ctx["project_id"], {atom: after})
    if not has_value:
        row = _get_or_create_user_atom(ctx["user_id"], ctx["project_id"], atom)
        if direction == 1:
            row.likes += 1
        elif direction == -1:
            row.dislikes += 1
        db.session.commit()
    current_atoms = get_style_atoms(ctx["user_id"], ctx["project_id"])

    clamp_hit = []
    if after != attempted:
        clamp_hit.append({
            "atom": atom,
            "min": cfg["min"],
            "max": cfg["max"],
            "attempted_value": round(attempted, 6),
            "clamped_value": round(after, 6),
            "reason": "manual_adjust_bound",
        })

    payload = _build_style_trace(
        user_id=ctx["user_id"],
        project_id=ctx["project_id"],
        current_keywords=[],
        current_atoms=current_atoms,
        trigger="manual_adjust",
    )
    payload.update({
        "before": {atom: before},
        "after": {atom: after},
        "delta": {atom: round(after - before, 6)},
        "rule_hit": rule_hit,
        "clamp_hit": clamp_hit,
        "event": "manual_adjust",
        "feedback_event": feedback_event,
        "explanation": {
            "top2_changes": [{
                "rank": 1,
                "atom": atom,
                "old_value": before,
                "new_value": after,
                "delta": round(after - before, 6),
                "reason_text": reason_text,
            }],
            "one_line_summary": (
                f"你将 {atom} 设置为 {round(after, 2)}。" if has_value
                else f"你手动将 {atom} {'增强' if direction == 1 else ('减弱' if direction == -1 else '保持')}。"
            ),
        },
    })
    _save_style_trace(
        user_id=ctx["user_id"],
        project_id=None if ctx["project_id"] == "default_project" else ctx["project_id"],
        task_id=None,
        event="manual_adjust",
        payload=payload,
    )

    return jsonify({
        "code": 200,
        "msg": "style adjusted",
        "data": {
            "user_id": ctx["user_id"],
            "project_id": ctx["project_id"],
            "atom": atom,
            "mode": "value" if has_value else "direction",
            "direction": 0 if has_value else direction,
            "before": before,
            "after": after,
            "delta": round(after - before, 6),
            "clamp_hit": bool(clamp_hit),
            "rule_hit": rule_hit,
            "atoms": current_atoms,
            "trace": payload,
            "updated_at": datetime.utcnow().isoformat(),
        },
    })


@app.route("/api/style-adjust/reset", methods=["POST"])
@login_required
def style_adjust_reset():
    """重置当前用户核心 atom 到默认值。"""
    data = request.get_json() or {}
    ctx = _get_request_context(data)
    before = {}
    after = {}
    delta = {}
    clamp_hit = []
    for atom, cfg in ATOM_CONFIG.items():
        row = _get_or_create_user_atom(ctx["user_id"], ctx["project_id"], atom)
        old_v = float(row.value)
        new_v = float(cfg["default"])
        row.value = new_v
        before[atom] = old_v
        after[atom] = new_v
        delta[atom] = round(new_v - old_v, 6)
    db.session.commit()

    current_atoms = get_style_atoms(ctx["user_id"], ctx["project_id"])
    payload = _build_style_trace(
        user_id=ctx["user_id"],
        project_id=ctx["project_id"],
        current_keywords=[],
        current_atoms=current_atoms,
        trigger="manual_adjust_reset",
    )
    payload.update({
        "before": before,
        "after": after,
        "delta": delta,
        "rule_hit": ["manual_adjust_reset_default"],
        "clamp_hit": clamp_hit,
        "event": "manual_adjust_reset",
        "feedback_event": "neutral",
        "explanation": {
            "top2_changes": [],
            "one_line_summary": "已将风格强度恢复为默认值。",
        },
    })
    _save_style_trace(
        user_id=ctx["user_id"],
        project_id=None if ctx["project_id"] == "default_project" else ctx["project_id"],
        task_id=None,
        event="manual_adjust_reset",
        payload=payload,
    )
    return jsonify({
        "code": 200,
        "msg": "style reset to defaults",
        "data": {
            "user_id": ctx["user_id"],
            "project_id": ctx["project_id"],
            "atoms": after,
            "rule_hit": ["manual_adjust_reset_default"],
            "trace": payload,
            "updated_at": datetime.utcnow().isoformat(),
        },
    })


@app.route("/api/style-feedback", methods=["POST"])
@login_required
def style_feedback():
    """记录用户对某张生成图的偏好，并回写 atom。"""
    data = request.get_json() or {}
    ctx = _get_request_context(data)
    task_id = (data.get("task_id") or "").strip()
    feedback = (data.get("feedback") or "like").strip().lower()
    try:
        image_index = int(data.get("image_index"))
    except Exception:
        return jsonify({"code": 400, "error": "image_index is required"}), 400

    if feedback not in {"like", "dislike"}:
        return jsonify({"code": 400, "error": "feedback must be like/dislike"}), 400

    task = db.session.get(GenerateTask, task_id)
    if not task or task.user_id != ctx["user_id"]:
        return jsonify({"code": 404, "error": "任务不存在"}), 404

    selected = GeneratedImage.query.filter_by(task_id=task_id, index=image_index).first()
    if not selected:
        return jsonify({"code": 404, "error": "图片不存在"}), 404

    adj = _style_adjust_by_image_feedback(
        user_id=ctx["user_id"],
        project_id=task.project_id or ctx["project_id"],
        variation=selected.variation or "",
        feedback=feedback,
    )
    current_atoms = get_style_atoms(ctx["user_id"], task.project_id or ctx["project_id"])
    payload = _build_style_trace(
        user_id=ctx["user_id"],
        project_id=task.project_id or ctx["project_id"],
        current_keywords=_safe_json_list(task.style_keywords),
        current_atoms=current_atoms,
        trigger="image_feedback",
    )
    payload.update({
        **adj,
        "event": "image_feedback",
        "feedback_event": feedback,
        "selected_image": {
            "task_id": task_id,
            "image_index": image_index,
            "variation": selected.variation,
            "image_id": selected.id,
        },
        "explanation": {
            "top2_changes": [
                {
                    "rank": i + 1,
                    "atom": atom,
                    "old_value": adj["before"][atom],
                    "new_value": adj["after"][atom],
                    "delta": adj["delta"][atom],
                    "reason_text": f"你选择了「{selected.variation or '该风格'}」",
                }
                for i, atom in enumerate(list(adj["delta"].keys())[:2])
            ],
            "one_line_summary": f"系统已记录你对「{selected.variation or '该方案'}」的偏好，并同步微调风格强度。",
        },
    })
    default_atoms = {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()}
    payload["design_controls_snapshot"] = {
        "schema_version": 1,
        "groups": DESIGN_CONTROLS_SCHEMA,
        "values": current_atoms,
        "defaults": default_atoms,
        "bounds": {atom: {"min": cfg["min"], "max": cfg["max"]} for atom, cfg in ATOM_CONFIG.items()},
        "diff_vs_default": {
            atom: round(current_atoms.get(atom, default_atoms[atom]) - default_atoms[atom], 4)
            for atom in default_atoms.keys()
        },
    }
    _save_style_trace(
        user_id=ctx["user_id"],
        project_id=task.project_id,
        task_id=task_id,
        event="image_feedback",
        payload=payload,
    )
    return jsonify({
        "code": 200,
        "msg": "feedback recorded",
        "data": {
            "user_id": ctx["user_id"],
            "project_id": task.project_id or ctx["project_id"],
            "task_id": task_id,
            "image_index": image_index,
            "variation": selected.variation,
            "feedback": feedback,
            "atom_delta": adj["delta"],
            "current_atoms": current_atoms,
            "style_trace": payload,
        },
    })


# ---------- Web 端生成 ----------
def _upload_to_feishu(filepath: str) -> dict:
    uploader = get_feishu_uploader()
    if uploader is None:
        return {"success": False, "error": "飞书未配置"}
    return uploader.upload_image(filepath)


def _save_upload(file) -> str:
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename) or "ref.png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_DIR, saved_name)
    file.save(filepath)
    return filepath


def _analyze_reference(image_source: str, extra: str = "") -> dict:
    analyzer = get_image_analyzer()
    if analyzer is None:
        return {}
    result = analyzer.analyze(image_source, extra)
    if result.get("success"):
        return result["analysis"]
    return {}


def _safe_json_list(raw) -> list:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _clamp(v: float, vmin: float, vmax: float) -> float:
    return max(vmin, min(vmax, v))


def _normalize_project_id(project_id: str) -> str:
    pid = str(project_id or "").strip()
    return pid or "default_project"


def _get_persisted_atom_values(user_id: str, project_id: str) -> dict:
    pid = _normalize_project_id(project_id)
    rows = UserStyleAtom.query.filter_by(user_id=user_id, project_id=pid).all()
    return {r.atom: float(r.value) for r in rows if r.atom in ATOM_CONFIG}


def get_style_atoms(user_id: str, project_id: str = None) -> dict:
    """
    读取用户+项目级 style_atoms。
    """
    atoms = {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()}
    atoms.update(_get_persisted_atom_values(user_id, project_id))
    return atoms


def save_style_atoms(user_id: str, project_id: str, atoms: dict) -> dict:
    """
    保存用户+项目级 style_atoms。
    """
    current = get_style_atoms(user_id, project_id)
    for atom, value in (atoms or {}).items():
        if atom not in ATOM_CONFIG:
            continue
        cfg = ATOM_CONFIG[atom]
        row = _get_or_create_user_atom(user_id, project_id, atom)
        current[atom] = _clamp(float(value), cfg["min"], cfg["max"])
        row.value = current[atom]
    db.session.commit()
    return current


def _normalize_style_overrides(overrides: dict) -> dict:
    normalized = {}
    for atom, value in (overrides or {}).items():
        if atom not in ATOM_CONFIG:
            continue
        cfg = ATOM_CONFIG[atom]
        try:
            normalized[atom] = _clamp(float(value), cfg["min"], cfg["max"])
        except Exception:
            continue
    return normalized


def _get_or_create_user_atom(user_id: str, project_id: str, atom: str) -> UserStyleAtom:
    cfg = ATOM_CONFIG[atom]
    pid = _normalize_project_id(project_id)
    row = UserStyleAtom.query.filter_by(user_id=user_id, project_id=pid, atom=atom).first()
    if row:
        return row
    row = UserStyleAtom(user_id=user_id, project_id=pid, atom=atom, value=cfg["default"])
    db.session.add(row)
    db.session.flush()
    return row


def _apply_user_atom_overrides(user_id: str, project_id: str, atoms: dict) -> dict:
    """应用用户手动调节后的 atom 值（若有）"""
    merged = dict(atoms)
    merged.update(_get_persisted_atom_values(user_id, project_id))
    return merged


def resolve_style_atoms(user_id: str, project_id: str, style_keywords: list = None, overrides: dict = None) -> dict:
    """
    用户级风格状态解析：
    1. 关键词投影 baseline
    2. 用户持久化 style_atoms 覆盖
    3. 本次请求 overrides 覆盖
    """
    keyword_base = _compute_style_atoms_from_keywords(style_keywords or [])
    persisted = _get_persisted_atom_values(user_id, project_id)
    defaults = {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()}
    normalized_overrides = _normalize_style_overrides(overrides)
    is_new_project = len(persisted) == 0

    if is_new_project:
        # 新项目首次生成：以“关键词注入的初始风格”为起点（而不是纯默认值）
        # 并避免前端初始滑块默认值把关键词注入结果覆盖回默认。
        merged = dict(keyword_base)
        filtered_overrides = {}
        for atom, value in normalized_overrides.items():
            if abs(float(value) - float(defaults.get(atom, 0.5))) > 1e-9:
                filtered_overrides[atom] = value
        merged.update(filtered_overrides)
    else:
        merged = dict(keyword_base)
        merged.update(persisted)
        merged.update(normalized_overrides)
    return merged


def _resolve_style_atoms(user_id: str, style_keywords: list, project_id: str = None, overrides: dict = None) -> dict:
    return resolve_style_atoms(user_id, project_id or "default_project", style_keywords, overrides)


def _compute_style_atoms_from_keywords(keywords: list) -> dict:
    """将风格关键词映射为完整 design_controls baseline（0~1）。"""
    atoms = {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()}

    boosts = {
        "color_contrast": {
            "卡通": 0.03, "可爱": 0.02, "趣味": 0.08, "科技": 0.06, "3D": 0.04, "复古": 0.03,
        },
        "palette_warmth": {
            "可爱": 0.05, "趣味": 0.06, "复古": 0.04, "自然": 0.03,
            "科技": -0.06, "简约": -0.03, "高端": -0.02,
        },
        "color_saturation": {
            "卡通": 0.05, "可爱": 0.04, "趣味": 0.08, "3D": 0.03,
            "简约": -0.08, "高端": -0.05, "自然": -0.03,
        },
        "layout_density": {
            "简约": -0.08, "高端": -0.04, "复古": 0.02, "科技": 0.02, "DIY": 0.04, "趣味": 0.05,
        },
        "whitespace_ratio": {
            "简约": 0.12, "高端": 0.08, "自然": 0.03,
            "趣味": -0.05, "DIY": -0.05,
        },
        "frame_fill": {
            "简约": -0.04, "高端": -0.02, "趣味": 0.03,
        },
        "headline_scale": {
            "简约": 0.04, "科技": 0.03, "复古": 0.03, "趣味": 0.04, "DIY": 0.02,
        },
        "typography_weight": {
            "科技": 0.05, "复古": 0.04, "趣味": 0.03, "DIY": 0.02,
            "简约": -0.05, "高端": -0.03,
        },
        "mood_premium": {
            "高端": 0.20, "简约": 0.08, "科技": 0.04,
            "卡通": -0.08, "可爱": -0.06, "趣味": -0.08, "DIY": -0.05,
        },
        "mood_playful": {
            "卡通": 0.15, "可爱": 0.12, "趣味": 0.18, "DIY": 0.05,
            "高端": -0.10, "简约": -0.05, "科技": -0.04,
        },
        "minimalism_level": {
            "简约": 0.25, "高端": 0.10,
            "卡通": -0.08, "可爱": -0.05, "趣味": -0.08, "DIY": -0.05, "复古": -0.04,
        },
    }
    for atom, cfg in boosts.items():
        if atom not in atoms:
            continue
        for kw in keywords or []:
            atoms[atom] += cfg.get(kw, 0.0)
        bounds = ATOM_CONFIG.get(atom, {"min": 0.0, "max": 1.0})
        atoms[atom] = _clamp(atoms[atom], bounds["min"], bounds["max"])
    return atoms


def _build_style_trace(
    user_id: str,
    project_id: str,
    current_keywords: list,
    window_size: int = 5,
    current_atoms: dict = None,
    trigger: str = "generate",
) -> dict:
    """
    生成 style_trace（向后兼容）并新增：
    - trend
    - current_style_summary
    - evolution_window
    """
    tasks = (
        GenerateTask.query
        .filter_by(user_id=user_id, project_id=project_id)
        .order_by(GenerateTask.created_at.desc())
        .limit(max(window_size, 1))
        .all()
    )
    # 反转后按时间升序，便于做 last-first 趋势计算
    tasks = list(reversed(tasks))

    keyword_count = {}
    per_gen = []
    for t in tasks:
        kws = _safe_json_list(t.style_keywords)
        for kw in kws:
            keyword_count[kw] = keyword_count.get(kw, 0) + 1
        atoms = _compute_style_atoms_from_keywords(kws)
        per_gen.append({
            "task_id": t.id,
            "created_at": t.created_at.isoformat(),
            "style_keywords": kws,
            "atoms": atoms,
        })

    current_atoms = dict(current_atoms or _resolve_style_atoms(user_id, current_keywords, project_id=project_id))
    default_atoms = {atom: cfg["default"] for atom, cfg in ATOM_CONFIG.items()}
    before_atoms = per_gen[-2]["atoms"] if len(per_gen) >= 2 else dict(default_atoms)
    # 兜底：确保两边键集合一致
    for k, v in default_atoms.items():
        before_atoms.setdefault(k, v)
        current_atoms.setdefault(k, v)

    delta = {k: round(current_atoms[k] - before_atoms.get(k, default_atoms[k]), 4)
             for k in current_atoms.keys()}

    def _trend_for(atom: str) -> str:
        if len(per_gen) < 2:
            return "stable"
        first_v = per_gen[0]["atoms"].get(atom, default_atoms.get(atom, 0.5))
        last_v = per_gen[-1]["atoms"].get(atom, default_atoms.get(atom, 0.5))
        diff = last_v - first_v
        if diff > 0.03:
            return "up"
        if diff < -0.03:
            return "down"
        return "stable"

    top_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:3]
    top_keyword_labels = [k for k, _ in top_keywords]

    trend = {
        "window_size": window_size,
        "direction": {k: _trend_for(k) for k in current_atoms.keys()},
        "delta": delta,
    }

    summary_bits = []
    if current_atoms["color_contrast"] >= 0.6:
        summary_bits.append("高对比")
    if current_atoms["headline_scale"] >= 0.58:
        summary_bits.append("大标题")
    if not summary_bits:
        summary_bits.append("均衡风格")

    if top_keyword_labels:
        summary_text = f"当前更偏向{' + '.join(summary_bits)}，近期常用关键词：{', '.join(top_keyword_labels)}"
    else:
        summary_text = f"当前更偏向{' + '.join(summary_bits)}"

    style_trace = {
        "user_id": user_id,
        "project_id": project_id,
        "trigger": {"type": trigger},
        "context": {
            "user_id": user_id,
            "project_id": project_id,
        },
        # ------- 旧字段（向后兼容）-------
        "explanation": {
            "top2_changes": [
                {
                    "rank": 1,
                    "atom": "color_contrast",
                    "old_value": before_atoms["color_contrast"],
                    "new_value": current_atoms["color_contrast"],
                    "delta": delta["color_contrast"],
                    "reason_text": "根据最近显式风格偏好调整",
                },
                {
                    "rank": 2,
                    "atom": "headline_scale",
                    "old_value": before_atoms["headline_scale"],
                    "new_value": current_atoms["headline_scale"],
                    "delta": delta["headline_scale"],
                    "reason_text": "根据最近显式风格偏好调整",
                },
            ],
            "one_line_summary": "你最近偏好更吸睛的视觉表达，系统本次同步调整了对比度与标题强度。",
        },
        "before": before_atoms,
        "after": current_atoms,
        "delta": delta,
        "rule_hit": ["keyword_to_atom_projection"],
        "clamp_hit": [],
        # ------- 新字段 -------
        "trend": trend,
        "current_style_summary": {
            "label": " + ".join(summary_bits),
            "text": summary_text,
            "top_keywords": top_keyword_labels,
            "atoms": current_atoms,
        },
        "evolution_window": {
            "size": window_size,
            "start_at": per_gen[0]["created_at"] if per_gen else None,
            "end_at": per_gen[-1]["created_at"] if per_gen else None,
            "generations": per_gen,
        },
        "generation_debug": {
            "atom_source": "keyword_base_plus_manual_overrides",
            "effective_atoms": current_atoms,
        },
        # ------- design_controls_snapshot -------
        # 本次生成时，11 个设计控件（色彩 / 构图 / 文本 / 风格）的完整值 + 来源，
        # 用于前端控制面板回显 / 回放。
        "design_controls_snapshot": {
            "schema_version": 1,
            "groups": DESIGN_CONTROLS_SCHEMA,
            "values": current_atoms,
            "defaults": default_atoms,
            "bounds": {atom: {"min": cfg["min"], "max": cfg["max"]} for atom, cfg in ATOM_CONFIG.items()},
            "diff_vs_default": {
                k: round(current_atoms[k] - default_atoms.get(k, 0.5), 4)
                for k in current_atoms.keys()
            },
        },
    }
    return style_trace


def _save_style_trace(user_id: str, project_id: str, task_id: str, event: str, payload: dict):
    payload = dict(payload or {})
    payload.setdefault("user_id", user_id)
    payload.setdefault("project_id", project_id)
    payload.setdefault("event", event)
    row = StyleTraceLog(
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        event=event,
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.session.add(row)
    db.session.commit()


def _style_adjust_by_image_feedback(user_id: str, project_id: str, variation: str, feedback: str = "like") -> dict:
    """
    根据用户选中图片的 variation 做轻量 atom 调整（显式反馈，无 EMA）。
    返回 before/after/delta/rule_hit/clamp_hit，便于直接写 trace。
    """
    direction = 1 if feedback == "like" else (-1 if feedback == "dislike" else 0)
    if direction == 0:
        return {"before": {}, "after": {}, "delta": {}, "rule_hit": ["image_feedback_noop"], "clamp_hit": []}

    # variation -> atom 方向（可继续扩展）
    mapping = {
        "信息优先型": {"color_contrast": 1, "headline_scale": 1},
        "缩略图冲击型": {"color_contrast": 1, "headline_scale": 1},
        "高端礼盒型": {"layout_density": -1},
        "极简品牌型": {"layout_density": -1},
        "全配件展示型": {"layout_density": 1},
        "对比差异型": {"color_contrast": 1},
    }
    atom_steps = mapping.get(variation, {"color_contrast": 1})

    before, after, delta = {}, {}, {}
    clamp_hit = []
    for atom, atom_dir in atom_steps.items():
        if atom not in ATOM_CONFIG:
            continue
        cfg = ATOM_CONFIG[atom]
        row = _get_or_create_user_atom(user_id, project_id, atom)
        old_v = float(row.value)
        step = cfg["step_up"] if atom_dir * direction > 0 else cfg["step_down"]
        attempted = old_v + step if atom_dir * direction > 0 else old_v - step
        new_v = _clamp(attempted, cfg["min"], cfg["max"])
        row.value = new_v
        if direction > 0:
            row.likes += 1
        else:
            row.dislikes += 1
        before[atom] = old_v
        after[atom] = new_v
        delta[atom] = round(new_v - old_v, 6)
        if new_v != attempted:
            clamp_hit.append({
                "atom": atom,
                "min": cfg["min"],
                "max": cfg["max"],
                "attempted_value": round(attempted, 6),
                "clamped_value": round(new_v, 6),
                "reason": "image_feedback_bound",
            })
    db.session.commit()
    return {
        "before": before,
        "after": after,
        "delta": delta,
        "rule_hit": ["image_feedback_variation_map"],
        "clamp_hit": clamp_hit,
    }


@app.route("/api/web/generate", methods=["POST"])
@login_required
def web_generate():
    """Web 界面批量生成（带数据库持久化）"""
    try:
        data = request.get_json() or {}
        ctx = _get_request_context(data)
        product_name = data.get("product_name", "").strip()
        if not product_name:
            return jsonify({"code": 400, "error": "请输入产品名称"}), 400

        project_id = ctx["project_id"]
        project = db.session.get(Project, project_id) if project_id else None
        if not project or project.user_id != ctx["user_id"]:
            return jsonify({"code": 400, "error": "请选择有效的项目"}), 400

        count = min(int(data.get("count", 6)), 8)
        backend = data.get("image_backend", DEFAULT_BACKEND)

        task = GenerateTask(
            project_id=project.id,
            user_id=ctx["user_id"],
            product_name=product_name,
            package_type=data.get("package_type", "彩盒"),
            brand_name=data.get("brand_name", ""),
            style_keywords=json.dumps(data.get("style_keywords", []), ensure_ascii=False),
            core_features=json.dumps(data.get("core_features", []), ensure_ascii=False),
            count=count,
            backend=backend,
            status="running",
        )
        db.session.add(task)
        db.session.commit()

        ref_analysis = {}
        ref_url = data.get("reference_image_url", "")
        if ref_url:
            ref_analysis = _analyze_reference(ref_url)

        resolved_atoms = resolve_style_atoms(
            user_id=ctx["user_id"],
            project_id=project.id,
            style_keywords=data.get("style_keywords", []),
            overrides=data.get("style_overrides") or data.get("_style_atoms") or {},
        )
        gen_params = {
            "product_name": product_name,
            "package_type": data.get("package_type", "彩盒"),
            "brand_name": data.get("brand_name", ""),
            "core_features": data.get("core_features", []),
            "style_keywords": data.get("style_keywords", []),
            "_style_atoms": resolved_atoms,
            "__style_atoms": resolved_atoms,
            "context": ctx["context"],
        }
        if ref_analysis:
            gen_params["_ref_analysis"] = ref_analysis

        variations = generate_prompt_variations(gen_params, count)

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
                if feishu.get("success"):
                    img["image_key"] = feishu["image_key"]
            return {"index": var["index"], "variation": var["variation"], "image": img}

        images = []
        with ThreadPoolExecutor(max_workers=min(count, 4)) as pool:
            futures = {pool.submit(_generate_one, v): v for v in variations}
            for future in as_completed(futures):
                try:
                    images.append(future.result())
                except Exception as e:
                    v = futures[future]
                    images.append({
                        "index": v["index"],
                        "variation": v["variation"],
                        "image": {"success": False, "error": str(e)},
                    })

        images.sort(key=lambda x: x["index"])

        for img_data in images:
            img_info = img_data["image"]
            gen_img = GeneratedImage(
                task_id=task.id,
                index=img_data["index"],
                variation=img_data.get("variation", ""),
                filename=img_info.get("filename", ""),
                filepath=img_info.get("filepath", ""),
                url=img_info.get("url", ""),
                success=img_info.get("success", False),
                error=img_info.get("error", ""),
            )
            db.session.add(gen_img)

        success_count = sum(1 for img in images if img["image"].get("success"))
        task.status = "done" if success_count > 0 else "failed"
        task.finished_at = datetime.utcnow()
        db.session.commit()

        project.updated_at = datetime.utcnow()
        db.session.commit()

        style_trace = _build_style_trace(
            user_id=ctx["user_id"],
            project_id=project.id,
            current_keywords=data.get("style_keywords", []),
            window_size=min(int(data.get("evolution_window_size", 5) or 5), 20),
            current_atoms=resolved_atoms,
            trigger="generate",
        )
        _save_style_trace(
            user_id=ctx["user_id"],
            project_id=project.id,
            task_id=task.id,
            event="generate",
            payload=style_trace,
        )

        return jsonify({
            "code": 200,
            "task_id": task.id,
            "images": images,
            "total": count,
            "success_count": success_count,
            "msg": f"批量生成完成：{success_count}/{count} 张成功",
            "context": ctx["context"],
            "style_trace": style_trace,
        })

    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


# ---------- 原有 API 接口（保留不变） ----------
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json() or {}
        if not data.get("product_name"):
            return jsonify({"code": 400, "error": "product_name is required"}), 400

        design = generate_packaging_design(data)
        result = {"code": 200, "design": design, "image_generated": False}

        if data.get("generate_image", True):
            backend = data.get("image_backend", DEFAULT_BACKEND)
            try:
                generator = get_generator(
                    backend=backend, output_dir=OUTPUT_DIR,
                    api_key=get_env("API_KEY"),
                    sd_api_url=get_env("SD_API_URL"),
                    mj_api_key=get_env("MJ_API_KEY"),
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
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
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
            return jsonify({"code": 200, "analysis": result["analysis"], "msg": "图片分析完成"})
        else:
            return jsonify({"code": 500, "error": result.get("error")}), 500
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/batch-generate", methods=["POST"])
def batch_generate():
    try:
        ref_analysis = {}
        if request.content_type and "multipart/form-data" in request.content_type:
            data = json.loads(request.form.get("data", "{}"))
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
            backend=backend, output_dir=OUTPUT_DIR,
            api_key=get_env("API_KEY"),
            sd_api_url=get_env("SD_API_URL"),
            mj_api_key=get_env("MJ_API_KEY"),
        )

        def _gen_one(var):
            img = generator.generate(var["prompt"])
            if img.get("success"):
                feishu = _upload_to_feishu(img["filepath"])
                if feishu["success"]:
                    img["image_key"] = feishu["image_key"]
            return {"index": var["index"], "variation": var["variation"], "image": img}

        images = []
        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = {pool.submit(_gen_one, v): v for v in variations}
            for future in as_completed(futures):
                images.append(future.result())
        images.sort(key=lambda x: x["index"])

        success_count = sum(1 for img in images if img["image"].get("success"))
        return jsonify({
            "code": 200, "design": variations[0]["design"],
            "images": images, "total": count,
            "success_count": success_count,
            "msg": f"批量生成完成：{success_count}/{count} 张成功",
        })
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/design-only", methods=["POST"])
def design_only():
    try:
        data = request.get_json() or {}
        if not data.get("product_name"):
            return jsonify({"code": 400, "error": "product_name is required"}), 400
        design = generate_packaging_design(data)
        return jsonify({"code": 200, "design": design, "msg": "设计方案生成成功"})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/image", methods=["POST"])
def generate_image_only():
    try:
        data = request.get_json() or {}
        if not data.get("prompt"):
            return jsonify({"code": 400, "error": "prompt is required"}), 400
        backend = data.get("backend", DEFAULT_BACKEND)
        generator = get_generator(
            backend=backend, output_dir=OUTPUT_DIR,
            api_key=get_env("API_KEY"),
            sd_api_url=get_env("SD_API_URL"),
            mj_api_key=get_env("MJ_API_KEY"),
        )
        result = generator.generate(prompt=data["prompt"], filename=data.get("filename"))
        if result.get("success"):
            feishu_result = _upload_to_feishu(result["filepath"])
            if feishu_result["success"]:
                result["image_key"] = feishu_result["image_key"]
            return jsonify({"code": 200, "data": result, "msg": "图片生成成功"})
        else:
            return jsonify({"code": 500, "error": result.get("error", "Image generation failed"), "data": result}), 500
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/api/backends", methods=["GET"])
def list_backends():
    backends = [
        {"name": "apiyi", "display_name": "API易 (DALL-E / GPT-Image)",
         "description": "付费 API，速度快质量高，需要配置 API_KEY",
         "requires_config": True, "config_key": "API_KEY"},
        {"name": "pollinations", "display_name": "Pollinations AI",
         "description": "免费、无需 API Key，适合快速测试",
         "requires_config": False},
        {"name": "sd", "display_name": "Stable Diffusion",
         "description": "本地或远程 SD 服务，需要配置 SD_API_URL",
         "requires_config": True, "config_key": "SD_API_URL"},
        {"name": "mj", "display_name": "Midjourney",
         "description": "通过第三方 API，需要配置 MJ_API_KEY",
         "requires_config": True, "config_key": "MJ_API_KEY"},
    ]
    return jsonify({"code": 200, "backends": backends, "default": DEFAULT_BACKEND})


if __name__ == "__main__":
    host = get_env("FLASK_HOST", "0.0.0.0")
    port = get_env_int("FLASK_PORT", 5012)
    debug = get_env_bool("FLASK_DEBUG", False)

    _base = os.path.dirname(os.path.abspath(__file__))
    _idx = os.path.join(_base, "templates", "index.html")
    print("=" * 60)
    print("亚马逊包装主图生成器服务启动中...")
    print(f"  工作目录 app.py: {_base}")
    print(f"  首页模板文件: {_idx}")
    if os.path.isfile(_idx):
        print(f"  模板更新时间: {datetime.fromtimestamp(os.path.getmtime(_idx)).isoformat()}")
    print(f"  Web 界面: http://127.0.0.1:{port}")
    print(f"  默认绘图后端: {DEFAULT_BACKEND}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  数据库: SQLite (packdesign.db)")
    print(f"  默认账号: admin / admin123")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)
