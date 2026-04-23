from datetime import datetime

from flask import Blueprint, jsonify, request

from ..models import AuditLog, User
from ..permissions import role_required

bp = Blueprint("audit", __name__)


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


@bp.get("")
@role_required(User.ROLE_ADMIN)
def list_audit():
    page = max(request.args.get("page", type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", type=int) or 50, 1), 200)
    action = request.args.get("action")
    actor_id = request.args.get("actor_id", type=int)
    target_type = request.args.get("target_type")
    target_id = request.args.get("target_id", type=int)
    date_from = _parse_dt(request.args.get("from"))
    date_to = _parse_dt(request.args.get("to"))

    q = AuditLog.query
    if action:
        if "," in action:
            q = q.filter(AuditLog.action.in_([a.strip() for a in action.split(",") if a.strip()]))
        elif action.endswith("*"):
            q = q.filter(AuditLog.action.like(action[:-1] + "%"))
        else:
            q = q.filter(AuditLog.action == action)
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if target_id:
        q = q.filter(AuditLog.target_id == target_id)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)

    total = q.count()
    rows = (
        q.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return jsonify(
        page=page,
        per_page=per_page,
        total=total,
        rows=[r.to_dict() for r in rows],
    )
