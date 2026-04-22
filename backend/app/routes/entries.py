from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_

from ..extensions import db
from ..models import PersonalCategory, Project, TimeEntry, User
from ..permissions import current_user, role_required

bp = Blueprint("entries", __name__)

EDIT_PAST_DAYS = 7  # employees can edit entries up to N days old


def _parse_dt(value: str) -> datetime:
    if not value:
        raise ValueError("datetime required")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _check_overlap(user_id: int, start: datetime, end: datetime, exclude_id=None):
    q = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.start_time < end,
        TimeEntry.end_time > start,
    )
    if exclude_id is not None:
        q = q.filter(TimeEntry.id != exclude_id)
    return q.first()


def _can_edit(user: User, entry: TimeEntry) -> bool:
    if user.role == User.ROLE_ADMIN:
        return True
    if entry.user_id != user.id:
        return False
    # employee / manager can edit their own within grace window
    age = datetime.utcnow() - entry.start_time
    return age <= timedelta(days=EDIT_PAST_DAYS)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def list_entries():
    user = current_user()
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    user_id_param = request.args.get("user_id", type=int)
    project_id = request.args.get("project_id", type=int)

    q = TimeEntry.query

    if from_str:
        q = q.filter(TimeEntry.end_time > _parse_dt(from_str))
    if to_str:
        q = q.filter(TimeEntry.start_time < _parse_dt(to_str))
    if project_id:
        q = q.filter(TimeEntry.project_id == project_id)

    target_user_id = user_id_param or user.id

    if user.role == User.ROLE_EMPLOYEE:
        q = q.filter(TimeEntry.user_id == user.id)
    elif user.role == User.ROLE_MANAGER:
        if user_id_param:
            target = User.query.get(user_id_param)
            if not target or target.department_id != user.department_id:
                return jsonify(error="forbidden: different department"), 403
            q = q.filter(TimeEntry.user_id == user_id_param)
        else:
            # default: manager sees own entries; use ?scope=team for whole department
            scope = request.args.get("scope")
            if scope == "team":
                member_ids = [u.id for u in user.department.members] if user.department else [user.id]
                q = q.filter(TimeEntry.user_id.in_(member_ids))
            else:
                q = q.filter(TimeEntry.user_id == user.id)
    else:  # admin
        if user_id_param:
            q = q.filter(TimeEntry.user_id == user_id_param)

    entries = q.order_by(TimeEntry.start_time.asc()).all()
    return jsonify([e.to_dict() for e in entries])


@bp.post("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def create_entry():
    user = current_user()
    data = request.get_json(silent=True) or {}

    try:
        start = _parse_dt(data.get("start_time"))
        end = _parse_dt(data.get("end_time"))
    except (ValueError, TypeError) as e:
        return jsonify(error=f"invalid datetime: {e}"), 400

    if end <= start:
        return jsonify(error="end_time must be after start_time"), 400

    project_id = data.get("project_id")
    category_id = data.get("category_id")
    if bool(project_id) == bool(category_id):
        return jsonify(error="exactly one of project_id or category_id required"), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title required"), 400

    target_user_id = data.get("user_id") or user.id
    if target_user_id != user.id and user.role != User.ROLE_ADMIN:
        return jsonify(error="forbidden: cannot log for another user"), 403

    if project_id:
        if not Project.query.get(project_id):
            return jsonify(error="project not found"), 404
    if category_id:
        if not PersonalCategory.query.get(category_id):
            return jsonify(error="category not found"), 404

    overlap = _check_overlap(target_user_id, start, end)
    if overlap:
        return jsonify(
            error="time range overlaps existing entry",
            conflict=overlap.to_dict(),
        ), 409

    entry = TimeEntry(
        user_id=target_user_id,
        project_id=project_id,
        category_id=category_id,
        title=title,
        description=data.get("description"),
        start_time=start,
        end_time=end,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@bp.patch("/<int:entry_id>")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def update_entry(entry_id: int):
    user = current_user()
    entry = TimeEntry.query.get_or_404(entry_id)

    if not _can_edit(user, entry):
        return jsonify(error="forbidden: cannot edit this entry"), 403

    data = request.get_json(silent=True) or {}

    new_start = entry.start_time
    new_end = entry.end_time
    if "start_time" in data:
        try:
            new_start = _parse_dt(data["start_time"])
        except (ValueError, TypeError):
            return jsonify(error="invalid start_time"), 400
    if "end_time" in data:
        try:
            new_end = _parse_dt(data["end_time"])
        except (ValueError, TypeError):
            return jsonify(error="invalid end_time"), 400
    if new_end <= new_start:
        return jsonify(error="end_time must be after start_time"), 400

    project_id = data.get("project_id", entry.project_id)
    category_id = data.get("category_id", entry.category_id)
    # if caller explicitly sets one side, clear the other
    if "project_id" in data and data["project_id"]:
        category_id = None
    if "category_id" in data and data["category_id"]:
        project_id = None
    if bool(project_id) == bool(category_id):
        return jsonify(error="exactly one of project_id or category_id required"), 400

    overlap = _check_overlap(entry.user_id, new_start, new_end, exclude_id=entry.id)
    if overlap:
        return jsonify(
            error="time range overlaps existing entry",
            conflict=overlap.to_dict(),
        ), 409

    entry.start_time = new_start
    entry.end_time = new_end
    entry.project_id = project_id
    entry.category_id = category_id
    if "title" in data:
        entry.title = (data["title"] or "").strip() or entry.title
    if "description" in data:
        entry.description = data["description"]

    db.session.commit()
    return jsonify(entry.to_dict())


@bp.delete("/<int:entry_id>")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def delete_entry(entry_id: int):
    user = current_user()
    entry = TimeEntry.query.get_or_404(entry_id)
    if not _can_edit(user, entry):
        return jsonify(error="forbidden: cannot delete this entry"), 403
    db.session.delete(entry)
    db.session.commit()
    return jsonify(ok=True)
