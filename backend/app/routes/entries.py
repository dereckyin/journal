from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from .. import audit
from ..extensions import db
from ..models import ChangeRequest, PersonalCategory, Project, TimeEntry, User
from ..permissions import current_user, role_required
from .change_requests import can_log_time_on_change_request

bp = Blueprint("entries", __name__)

EDIT_PAST_DAYS = 7  # employees can edit entries up to N days old


def _norm_entry_id(val):
    if val is None or val == "":
        return None
    try:
        i = int(val)
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


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
    category_id = request.args.get("category_id", type=int)
    change_request_id = request.args.get("change_request_id", type=int)
    scope = request.args.get("scope")

    q = TimeEntry.query

    if from_str:
        q = q.filter(TimeEntry.end_time > _parse_dt(from_str))
    if to_str:
        q = q.filter(TimeEntry.start_time < _parse_dt(to_str))
    if project_id:
        q = q.filter(TimeEntry.project_id == project_id)
    if category_id:
        q = q.filter(TimeEntry.category_id == category_id)
    if change_request_id:
        q = q.filter(TimeEntry.change_request_id == change_request_id)

    if user.role == User.ROLE_EMPLOYEE:
        # 防禦性：employee 若試圖傳 user_id 而且不是自己，明確 403（不 silently 回傳自己的）
        if user_id_param and user_id_param != user.id:
            return jsonify(error="forbidden: cannot read other users"), 403
        q = q.filter(TimeEntry.user_id == user.id)
    elif user.role == User.ROLE_MANAGER:
        # manager 沒部門 → 只能看自己，禁止跨部門窺視
        if user.department_id is None:
            if user_id_param and user_id_param != user.id:
                return jsonify(error="forbidden: manager without department"), 403
            q = q.filter(TimeEntry.user_id == user.id)
        elif user_id_param:
            target = User.query.get(user_id_param)
            if (
                not target
                or target.department_id is None
                or target.department_id != user.department_id
            ):
                return jsonify(error="forbidden: different department"), 403
            q = q.filter(TimeEntry.user_id == user_id_param)
        else:
            if scope == "team":
                member_ids = [u.id for u in user.department.members] if user.department else [user.id]
                q = q.filter(TimeEntry.user_id.in_(member_ids))
            else:
                q = q.filter(TimeEntry.user_id == user.id)
    else:  # admin
        if user_id_param:
            q = q.filter(TimeEntry.user_id == user_id_param)
        elif scope != "team":
            # 與 manager 一致：admin 預設只看自己，須帶 ?scope=team 才回傳全公司
            q = q.filter(TimeEntry.user_id == user.id)

    entries = q.order_by(TimeEntry.start_time.asc()).all()

    # 稽核：admin / manager 明確指定他人 user_id 或用 team scope → 記錄一筆檢視
    if user.role != User.ROLE_EMPLOYEE:
        is_viewing_others = (
            (user_id_param and user_id_param != user.id)
            or scope == "team"
        )
        if is_viewing_others:
            audit.log(
                "entries.view_others",
                actor=user,
                target_type="user" if user_id_param else "scope",
                target_id=user_id_param,
                meta={
                    "scope": scope,
                    "from": from_str,
                    "to": to_str,
                    "project_id": project_id,
                    "category_id": category_id,
                    "change_request_id": change_request_id,
                    "count": len(entries),
                },
            )

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

    project_id = _norm_entry_id(data.get("project_id"))
    category_id = _norm_entry_id(data.get("category_id"))
    change_request_id = _norm_entry_id(data.get("change_request_id"))
    n_targets = sum(x is not None for x in (project_id, category_id, change_request_id))
    if n_targets != 1:
        return jsonify(
            error="exactly one of project_id, category_id, change_request_id required"
        ), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title required"), 400

    raw_uid = data.get("user_id")
    try:
        target_user_id = int(raw_uid) if raw_uid not in (None, "", 0) else user.id
    except (TypeError, ValueError):
        return jsonify(error="invalid user_id"), 400
    if target_user_id != user.id and user.role != User.ROLE_ADMIN:
        return jsonify(error="forbidden: cannot log for another user"), 403
    if target_user_id != user.id:
        # admin 代填時，確認目標使用者存在且有效
        target = User.query.filter_by(id=target_user_id, is_active=True).first()
        if not target:
            return jsonify(error="target user not found or inactive"), 404

    if project_id:
        if not Project.query.get(project_id):
            return jsonify(error="project not found"), 404
    if category_id:
        if not PersonalCategory.query.get(category_id):
            return jsonify(error="category not found"), 404
    if change_request_id:
        cr = ChangeRequest.query.get(change_request_id)
        if not cr:
            return jsonify(error="change request not found"), 404
        target_u = User.query.get(target_user_id)
        if not target_u or not can_log_time_on_change_request(target_u, cr):
            return jsonify(error="forbidden: cannot log time on this change request"), 403

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
        change_request_id=change_request_id,
        title=title,
        description=data.get("description"),
        start_time=start,
        end_time=end,
    )
    db.session.add(entry)
    db.session.commit()
    if target_user_id != user.id:
        audit.log(
            "entries.create_for_other",
            actor=user,
            target_type="entry",
            target_id=entry.id,
            meta={
                "for_user_id": target_user_id,
                "project_id": project_id,
                "category_id": category_id,
                "change_request_id": change_request_id,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
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

    project_id = entry.project_id
    category_id = entry.category_id
    change_request_id = entry.change_request_id

    if "project_id" in data:
        project_id = _norm_entry_id(data["project_id"])
        if project_id:
            category_id = None
            change_request_id = None
    if "category_id" in data:
        category_id = _norm_entry_id(data["category_id"])
        if category_id:
            project_id = None
            change_request_id = None
    if "change_request_id" in data:
        change_request_id = _norm_entry_id(data["change_request_id"])
        if change_request_id:
            project_id = None
            category_id = None

    n_targets = sum(x is not None for x in (project_id, category_id, change_request_id))
    if n_targets != 1:
        return jsonify(
            error="exactly one of project_id, category_id, change_request_id required"
        ), 400

    if project_id and not Project.query.get(project_id):
        return jsonify(error="project not found"), 404
    if category_id and not PersonalCategory.query.get(category_id):
        return jsonify(error="category not found"), 404
    if change_request_id:
        cr = ChangeRequest.query.get(change_request_id)
        if not cr:
            return jsonify(error="change request not found"), 404
        owner = User.query.get(entry.user_id)
        if not owner or not can_log_time_on_change_request(owner, cr):
            return jsonify(error="forbidden: cannot log time on this change request"), 403

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
    entry.change_request_id = change_request_id
    if "title" in data:
        entry.title = (data["title"] or "").strip() or entry.title
    if "description" in data:
        entry.description = data["description"]

    db.session.commit()
    if entry.user_id != user.id:
        audit.log(
            "entries.update_other",
            actor=user,
            target_type="entry",
            target_id=entry.id,
            meta={"for_user_id": entry.user_id},
        )
    return jsonify(entry.to_dict())


@bp.delete("/<int:entry_id>")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def delete_entry(entry_id: int):
    user = current_user()
    entry = TimeEntry.query.get_or_404(entry_id)
    if not _can_edit(user, entry):
        return jsonify(error="forbidden: cannot delete this entry"), 403
    owner_id = entry.user_id
    db.session.delete(entry)
    db.session.commit()
    if owner_id != user.id:
        audit.log(
            "entries.delete_other",
            actor=user,
            target_type="entry",
            target_id=entry_id,
            meta={"for_user_id": owner_id},
        )
    return jsonify(ok=True)
