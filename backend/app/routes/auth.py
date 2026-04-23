from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from .. import audit
from ..extensions import limiter
from ..models import User
from ..permissions import current_user

bp = Blueprint("auth", __name__)


def _token_pair(user: User) -> dict:
    claims = {"role": user.role, "username": user.username}
    access = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user.id), additional_claims=claims)
    return {"access_token": access, "refresh_token": refresh}


@bp.post("/login")
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="username and password required"), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        audit.log(
            "auth.login_failed",
            actor_username=username,
            meta={"reason": "invalid_credentials_or_inactive"},
        )
        return jsonify(error="invalid credentials"), 401

    tokens = _token_pair(user)
    audit.log("auth.login_success", actor=user)
    return jsonify(
        **tokens,
        user=user.to_dict(include_sensitive=(user.role == User.ROLE_ADMIN)),
    )


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    user = User.query.filter_by(id=int(uid), is_active=True).first() if uid else None
    if not user:
        # 帳號被停用 → refresh 一律失敗，前端會自動登出
        return jsonify(error="account inactive or revoked"), 401
    access = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    audit.log("auth.refresh", actor=user)
    return jsonify(access_token=access)


@bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify(error="account inactive or not found"), 401
    return jsonify(user=user.to_dict(include_sensitive=(user.role == User.ROLE_ADMIN)))


@bp.post("/logout")
@jwt_required()
def logout():
    user = current_user()
    if user:
        audit.log("auth.logout", actor=user)
    # 無狀態 JWT：實際登出由客戶端丟棄 token
    return jsonify(ok=True)
