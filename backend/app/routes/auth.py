from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from ..models import User
from ..permissions import current_user

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="username and password required"), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify(error="invalid credentials"), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    return jsonify(
        access_token=token,
        user=user.to_dict(include_sensitive=(user.role == User.ROLE_ADMIN)),
    )


@bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify(error="user not found"), 404
    return jsonify(user=user.to_dict(include_sensitive=(user.role == User.ROLE_ADMIN)))


@bp.post("/logout")
@jwt_required()
def logout():
    # Stateless JWT: client drops the token. Endpoint kept for symmetry.
    return jsonify(ok=True)
