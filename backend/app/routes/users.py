from flask import Blueprint, jsonify, request

from .. import audit
from ..extensions import db
from ..models import User
from ..permissions import current_user, role_required

bp = Blueprint("users", __name__)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def list_users():
    user = current_user()
    q = User.query
    if user.role == User.ROLE_MANAGER:
        q = q.filter(User.department_id == user.department_id)
    users = q.order_by(User.id).all()
    include = user.role == User.ROLE_ADMIN
    return jsonify([u.to_dict(include_sensitive=include) for u in users])


@bp.post("")
@role_required(User.ROLE_ADMIN)
def create_user():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    required = ("username", "password", "full_name", "role")
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify(error=f"missing: {', '.join(missing)}"), 400
    if data["role"] not in User.ROLES:
        return jsonify(error="invalid role"), 400
    if User.query.filter_by(username=data["username"]).first():
        return jsonify(error="username already exists"), 409

    user = User(
        username=data["username"].strip(),
        full_name=data["full_name"].strip(),
        email=data.get("email"),
        role=data["role"],
        department_id=data.get("department_id"),
        hourly_rate=data.get("hourly_rate") or 0,
        is_active=bool(data.get("is_active", True)),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    audit.log(
        "users.create",
        actor=actor,
        target_type="user",
        target_id=user.id,
        meta={
            "username": user.username,
            "role": user.role,
            "department_id": user.department_id,
            "hourly_rate_set": "hourly_rate" in data,
        },
    )
    return jsonify(user.to_dict(include_sensitive=True)), 201


@bp.patch("/<int:user_id>")
@role_required(User.ROLE_ADMIN)
def update_user(user_id: int):
    actor = current_user()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    changes: dict = {}
    old_role = user.role
    old_active = user.is_active
    old_rate = float(user.hourly_rate or 0)

    for field in ("full_name", "email", "department_id", "is_active"):
        if field in data:
            if getattr(user, field) != data[field]:
                changes[field] = {"from": getattr(user, field), "to": data[field]}
            setattr(user, field, data[field])
    if "role" in data:
        if data["role"] not in User.ROLES:
            return jsonify(error="invalid role"), 400
        if user.role != data["role"]:
            changes["role"] = {"from": old_role, "to": data["role"]}
        user.role = data["role"]
    if "hourly_rate" in data:
        new_rate = float(data["hourly_rate"] or 0)
        if old_rate != new_rate:
            changes["hourly_rate"] = {"from": old_rate, "to": new_rate}
        user.hourly_rate = new_rate
    if data.get("password"):
        changes["password"] = "changed"
        user.set_password(data["password"])

    db.session.commit()

    # 專屬事件：角色變更、時薪變更、停用
    if "role" in changes:
        audit.log(
            "users.role_changed",
            actor=actor,
            target_type="user",
            target_id=user.id,
            meta={"username": user.username, **changes["role"]},
        )
    if "hourly_rate" in changes:
        audit.log(
            "users.rate_changed",
            actor=actor,
            target_type="user",
            target_id=user.id,
            meta={"username": user.username, **changes["hourly_rate"]},
        )
    if old_active and user.is_active is False:
        audit.log(
            "users.deactivated",
            actor=actor,
            target_type="user",
            target_id=user.id,
            meta={"username": user.username},
        )
    # 總體更新事件
    audit.log(
        "users.update",
        actor=actor,
        target_type="user",
        target_id=user.id,
        meta={"username": user.username, "changes": list(changes.keys())},
    )
    return jsonify(user.to_dict(include_sensitive=True))


@bp.delete("/<int:user_id>")
@role_required(User.ROLE_ADMIN)
def delete_user(user_id: int):
    actor = current_user()
    user = User.query.get_or_404(user_id)
    if user.is_active:
        user.is_active = False
        db.session.commit()
        audit.log(
            "users.deactivated",
            actor=actor,
            target_type="user",
            target_id=user.id,
            meta={"username": user.username, "via": "delete"},
        )
    return jsonify(ok=True)
