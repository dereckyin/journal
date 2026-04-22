from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required

from .models import User


def role_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = claims.get("role")
            if role not in roles:
                return jsonify(error="forbidden: role not allowed"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user() -> User | None:
    from flask_jwt_extended import get_jwt_identity

    uid = get_jwt_identity()
    if uid is None:
        return None
    return db_get_user(int(uid))


def db_get_user(user_id: int) -> User | None:
    return User.query.filter_by(id=user_id, is_active=True).first()
