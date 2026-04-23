from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from .models import User


def _load_current_user() -> User | None:
    """Load the authenticated user fresh from DB each request.

    We do NOT trust the role cached in the JWT because an admin may have
    demoted or deactivated the account after the token was issued.
    The result is cached on flask.g for the rest of the request.
    """
    cached = getattr(g, "_current_user", None)
    if cached is not None:
        return cached
    uid = get_jwt_identity()
    if uid is None:
        return None
    user = User.query.filter_by(id=int(uid), is_active=True).first()
    g._current_user = user
    return user


def role_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            # 1) 帳號已不存在或被停用 → 401，讓前端攔截器自動清 token 並導回登入
            if user is None:
                return jsonify(error="account inactive or revoked"), 401
            # 2) 以 DB 當前 role 判斷，不信任 token 內舊的 claims（防止降級後仍保有舊權限）
            if user.role not in roles:
                return jsonify(error="forbidden: role not allowed"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user() -> User | None:
    return _load_current_user()


def db_get_user(user_id: int) -> User | None:
    return User.query.filter_by(id=user_id, is_active=True).first()
