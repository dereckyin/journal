from flask import Blueprint, jsonify, request

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
    return jsonify(user.to_dict(include_sensitive=True)), 201


@bp.patch("/<int:user_id>")
@role_required(User.ROLE_ADMIN)
def update_user(user_id: int):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    for field in ("full_name", "email", "department_id", "is_active"):
        if field in data:
            setattr(user, field, data[field])
    if "role" in data:
        if data["role"] not in User.ROLES:
            return jsonify(error="invalid role"), 400
        user.role = data["role"]
    if "hourly_rate" in data:
        user.hourly_rate = data["hourly_rate"] or 0
    if data.get("password"):
        user.set_password(data["password"])

    db.session.commit()
    return jsonify(user.to_dict(include_sensitive=True))


@bp.delete("/<int:user_id>")
@role_required(User.ROLE_ADMIN)
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify(ok=True)
