from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import bcrypt
from sqlalchemy import CheckConstraint, UniqueConstraint

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Department(db.Model, TimestampMixin):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    manager = db.relationship(
        "User",
        foreign_keys=[manager_id],
        post_update=True,
        uselist=False,
    )
    members = db.relationship(
        "User",
        back_populates="department",
        foreign_keys="User.department_id",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "manager_id": self.manager_id,
            "manager_name": self.manager.full_name if self.manager else None,
            "member_count": len(self.members),
        }


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    ROLE_EMPLOYEE = "employee"
    ROLE_MANAGER = "manager"
    ROLE_ADMIN = "admin"
    ROLES = (ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(20), nullable=False, default=ROLE_EMPLOYEE)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    hourly_rate = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    department = db.relationship(
        "Department",
        back_populates="members",
        foreign_keys=[department_id],
    )
    entries = db.relationship(
        "TimeEntry", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("role in ('employee','manager','admin')", name="ck_user_role"),
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = bcrypt.hashpw(
            raw.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.checkpw(
                raw.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except ValueError:
            return False

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "is_active": self.is_active,
        }
        if include_sensitive:
            data["hourly_rate"] = float(self.hourly_rate or 0)
        return data


class Project(db.Model, TimestampMixin):
    __tablename__ = "projects"

    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    budget = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)
    color = db.Column(db.String(20), nullable=False, default="#409EFF")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    members = db.relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    entries = db.relationship("TimeEntry", back_populates="project")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "budget": float(self.budget or 0),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "color": self.color,
            "member_ids": [m.user_id for m in self.members],
        }


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User")


class PersonalCategory(db.Model, TimestampMixin):
    __tablename__ = "personal_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(20), nullable=False, default="#909399")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}


class TimeEntry(db.Model, TimestampMixin):
    __tablename__ = "time_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("personal_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)

    user = db.relationship("User", back_populates="entries")
    project = db.relationship("Project", back_populates="entries")
    category = db.relationship("PersonalCategory")

    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL AND category_id IS NULL) OR "
            "(project_id IS NULL AND category_id IS NOT NULL)",
            name="ck_entry_project_xor_category",
        ),
        CheckConstraint("end_time > start_time", name="ck_entry_time_range"),
    )

    @property
    def hours(self) -> float:
        delta = self.end_time - self.start_time
        return round(delta.total_seconds() / 3600.0, 4)

    def cost(self, hourly_rate: Decimal | float | None = None) -> float:
        rate = hourly_rate if hourly_rate is not None else (self.user.hourly_rate or 0)
        return round(self.hours * float(rate), 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "project_color": self.project.color if self.project else None,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_color": self.category.color if self.category else None,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "hours": self.hours,
        }
