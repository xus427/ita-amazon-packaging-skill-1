"""
数据库模型 - SQLite + SQLAlchemy
"""

import os
import json
import uuid
import hashlib
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(120), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship("Project", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = _hash_password(password)

    def check_password(self, password: str) -> bool:
        return self.password_hash == _hash_password(password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat(),
        }


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = db.relationship("GenerateTask", backref="project", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "task_count": len(self.tasks),
        }


class GenerateTask(db.Model):
    __tablename__ = "generate_tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    product_name = db.Column(db.String(200), nullable=False)
    package_type = db.Column(db.String(50), default="彩盒")
    brand_name = db.Column(db.String(100), default="")
    style_keywords = db.Column(db.Text, default="[]")
    core_features = db.Column(db.Text, default="[]")
    count = db.Column(db.Integer, default=6)
    backend = db.Column(db.String(30), default="apiyi")
    image_ratio = db.Column(db.String(10), default="3:4")

    status = db.Column(db.String(20), default="pending")  # pending / running / done / failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    images = db.relationship("GeneratedImage", backref="task", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "project_id": self.project_id,
            "product_name": self.product_name,
            "package_type": self.package_type,
            "brand_name": self.brand_name,
            "style_keywords": json.loads(self.style_keywords) if self.style_keywords else [],
            "core_features": json.loads(self.core_features) if self.core_features else [],
            "count": self.count,
            "backend": self.backend,
            "image_ratio": self.image_ratio or "3:4",
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "images": [img.to_dict() for img in self.images],
        }


class GeneratedImage(db.Model):
    __tablename__ = "generated_images"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = db.Column(db.String(36), db.ForeignKey("generate_tasks.id"), nullable=False)
    index = db.Column(db.Integer, default=0)
    variation = db.Column(db.String(100), default="")
    filename = db.Column(db.String(255), default="")
    filepath = db.Column(db.String(500), default="")
    url = db.Column(db.String(1000), default="")
    success = db.Column(db.Boolean, default=False)
    error = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "index": self.index,
            "variation": self.variation,
            "filename": self.filename,
            "url": self.url,
            "filepath": self.filepath,
            "success": self.success,
            "error": self.error,
        }


class UserStyleAtom(db.Model):
    """用户 + 项目级 style atom 强度偏好（可手动调节）"""
    __tablename__ = "user_style_atoms"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.String(36), nullable=False, default="default_project", index=True)
    atom = db.Column(db.String(64), nullable=False, index=True)
    value = db.Column(db.Float, default=0.5)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "project_id", "atom", name="uq_user_project_atom"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "atom": self.atom,
            "value": self.value,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StyleTraceLog(db.Model):
    """风格学习轨迹日志（用于回放与分析）"""
    __tablename__ = "style_trace_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=True, index=True)
    task_id = db.Column(db.String(36), db.ForeignKey("generate_tasks.id"), nullable=True, index=True)
    event = db.Column(db.String(30), default="generate")
    payload = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        try:
            payload = json.loads(self.payload) if self.payload else {}
        except Exception:
            payload = {}
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "event": self.event,
            "payload": payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db(app):
    """初始化数据库，创建表和默认管理员"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _migrate_user_style_atoms_schema()
        _migrate_generate_tasks_image_ratio()
        if not User.query.first():
            admin = User(username="admin", display_name="管理员")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()


def _migrate_user_style_atoms_schema():
    """
    将旧版 user_style_atoms（user_id + atom）升级为
    新版（user_id + project_id + atom）。
    - 旧数据 project_id 自动回填 default_project
    - 重建唯一约束为 (user_id, project_id, atom)
    """
    conn = db.session.connection()
    table_exists = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_style_atoms'")
    ).fetchone()
    if not table_exists:
        return

    cols = conn.execute(text("PRAGMA table_info(user_style_atoms)")).fetchall()
    col_names = {c[1] for c in cols}
    has_project_col = "project_id" in col_names

    unique_ok = False
    idx_rows = conn.execute(text("PRAGMA index_list(user_style_atoms)")).fetchall()
    for idx in idx_rows:
        idx_name = idx[1]
        is_unique = int(idx[2]) == 1
        if not is_unique:
            continue
        idx_cols = conn.execute(text(f"PRAGMA index_info({idx_name})")).fetchall()
        names = [r[2] for r in idx_cols]
        if names == ["user_id", "project_id", "atom"]:
            unique_ok = True
            break

    if has_project_col and unique_ok:
        # 仅兜底补空值
        conn.execute(text("UPDATE user_style_atoms SET project_id='default_project' WHERE project_id IS NULL OR project_id=''"))
        db.session.commit()
        return

    # 重建表（SQLite 对旧 UNIQUE 约束不可直接修改）
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_style_atoms_new (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            project_id VARCHAR(36) NOT NULL DEFAULT 'default_project',
            atom VARCHAR(64) NOT NULL,
            value FLOAT DEFAULT 0.5,
            likes INTEGER DEFAULT 0,
            dislikes INTEGER DEFAULT 0,
            updated_at DATETIME,
            created_at DATETIME,
            CONSTRAINT uq_user_project_atom UNIQUE (user_id, project_id, atom)
        )
    """))

    if has_project_col:
        conn.execute(text("""
            INSERT OR REPLACE INTO user_style_atoms_new
            (id, user_id, project_id, atom, value, likes, dislikes, updated_at, created_at)
            SELECT id, user_id,
                   COALESCE(NULLIF(project_id, ''), 'default_project') AS project_id,
                   atom, value, likes, dislikes, updated_at, created_at
            FROM user_style_atoms
        """))
    else:
        conn.execute(text("""
            INSERT OR REPLACE INTO user_style_atoms_new
            (id, user_id, project_id, atom, value, likes, dislikes, updated_at, created_at)
            SELECT id, user_id,
                   'default_project' AS project_id,
                   atom, value, likes, dislikes, updated_at, created_at
            FROM user_style_atoms
        """))

    conn.execute(text("DROP TABLE user_style_atoms"))
    conn.execute(text("ALTER TABLE user_style_atoms_new RENAME TO user_style_atoms"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_style_atoms_user_id ON user_style_atoms(user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_style_atoms_project_id ON user_style_atoms(project_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_style_atoms_atom ON user_style_atoms(atom)"))
    db.session.commit()


def _migrate_generate_tasks_image_ratio():
    """为 generate_tasks 增加 image_ratio 字段（兼容已有 SQLite）。"""
    conn = db.session.connection()
    table_exists = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='generate_tasks'")
    ).fetchone()
    if not table_exists:
        return

    cols = conn.execute(text("PRAGMA table_info(generate_tasks)")).fetchall()
    col_names = {c[1] for c in cols}
    if "image_ratio" not in col_names:
        conn.execute(text("ALTER TABLE generate_tasks ADD COLUMN image_ratio VARCHAR(10) DEFAULT '3:4'"))
    conn.execute(text("UPDATE generate_tasks SET image_ratio='3:4' WHERE image_ratio IS NULL OR image_ratio=''"))
    db.session.commit()
