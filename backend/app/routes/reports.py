from calendar import monthrange
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from .. import audit
from ..extensions import db
from ..models import (
    ChangeRequest,
    Department,
    PersonalCategory,
    Project,
    TimeEntry,
    User,
)
from ..permissions import current_user, role_required

bp = Blueprint("reports", __name__)


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    last_day = monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, last_day, 23, 59, 59)
    return start, end


def _parse_month(param: str | None) -> tuple[int, int]:
    if not param:
        today = date.today()
        return today.year, today.month
    y, m = param.split("-")
    return int(y), int(m)


@bp.get("/project-cost")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def project_cost():
    user = current_user()
    is_admin = user.role == User.ROLE_ADMIN
    project_id = request.args.get("project_id", type=int)
    audit.log(
        "reports.view_project_cost",
        actor=user,
        target_type="project" if project_id else None,
        target_id=project_id,
        meta={"admin": is_admin},
    )

    h_expr = (
        (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
        * 24.0
    )

    direct = (
        db.session.query(
            TimeEntry.project_id.label("pid"),
            func.coalesce(func.sum(h_expr), 0.0).label("hours"),
            func.coalesce(func.sum(h_expr * User.hourly_rate), 0.0).label("cost"),
        )
        .select_from(TimeEntry)
        .join(User, User.id == TimeEntry.user_id)
        .filter(TimeEntry.project_id.isnot(None))
        .group_by(TimeEntry.project_id)
        .all()
    )
    via_cr = (
        db.session.query(
            ChangeRequest.project_id.label("pid"),
            func.coalesce(func.sum(h_expr), 0.0).label("hours"),
            func.coalesce(func.sum(h_expr * User.hourly_rate), 0.0).label("cost"),
        )
        .select_from(TimeEntry)
        .join(ChangeRequest, TimeEntry.change_request_id == ChangeRequest.id)
        .join(User, User.id == TimeEntry.user_id)
        .filter(ChangeRequest.project_id.isnot(None))
        .group_by(ChangeRequest.project_id)
        .all()
    )

    merged: dict[int, dict] = {}
    for row in direct:
        if row.pid is None:
            continue
        merged[row.pid] = {
            "hours": float(row.hours or 0),
            "cost": float(row.cost or 0),
        }
    for row in via_cr:
        if row.pid is None:
            continue
        m = merged.setdefault(row.pid, {"hours": 0.0, "cost": 0.0})
        m["hours"] += float(row.hours or 0)
        m["cost"] += float(row.cost or 0)

    pq = Project.query
    if project_id:
        pq = pq.filter(Project.id == project_id)
    projects = pq.order_by(Project.code.asc()).all()

    result = []
    for p in projects:
        m = merged.get(p.id, {"hours": 0.0, "cost": 0.0})
        budget = float(p.budget or 0)
        cost = float(m["cost"])
        hours = float(m["hours"])
        item = {
            "project_id": p.id,
            "code": p.code,
            "name": p.name,
            "color": p.color,
            "budget": budget,
            "hours": round(hours, 2),
        }
        if is_admin:
            item["cost"] = round(cost, 2)
            item["remaining"] = round(budget - cost, 2)
            item["utilization"] = (
                round(cost / budget * 100, 2) if budget else None
            )
        result.append(item)
    return jsonify(result)


@bp.get("/user-hours")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def user_hours():
    user = current_user()
    target_id = request.args.get("user_id", type=int) or user.id

    if user.role == User.ROLE_EMPLOYEE and target_id != user.id:
        return jsonify(error="forbidden"), 403
    if user.role == User.ROLE_MANAGER and target_id != user.id:
        if user.department_id is None:
            return jsonify(error="forbidden: manager without department"), 403
        target = User.query.get(target_id)
        if (
            not target
            or target.department_id is None
            or target.department_id != user.department_id
        ):
            return jsonify(error="forbidden: different department"), 403

    year, month = _parse_month(request.args.get("month"))
    start, end = _month_range(year, month)

    target = User.query.get_or_404(target_id)
    is_admin = user.role == User.ROLE_ADMIN
    rate = float(target.hourly_rate or 0) if is_admin else 0.0

    if target_id != user.id:
        audit.log(
            "reports.view_user_hours_other",
            actor=user,
            target_type="user",
            target_id=target_id,
            meta={
                "month": request.args.get("month"),
                "include_cost": is_admin,
            },
        )

    # per project hours
    rows = (
        db.session.query(
            Project.id,
            Project.name,
            Project.color,
            func.sum(
                (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                * 24.0
            ).label("hours"),
        )
        .join(TimeEntry, TimeEntry.project_id == Project.id)
        .filter(
            TimeEntry.user_id == target_id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time <= end,
        )
        .group_by(Project.id)
        .all()
    )
    projects = []
    for r in rows:
        hours = round(float(r.hours or 0), 2)
        item = {
            "project_id": r.id,
            "name": r.name,
            "color": r.color,
            "hours": hours,
        }
        if is_admin:
            item["cost"] = round(hours * rate, 2)
        projects.append(item)

    # per personal category hours
    cat_rows = (
        db.session.query(
            PersonalCategory.id,
            PersonalCategory.name,
            PersonalCategory.color,
            func.sum(
                (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                * 24.0
            ).label("hours"),
        )
        .join(TimeEntry, TimeEntry.category_id == PersonalCategory.id)
        .filter(
            TimeEntry.user_id == target_id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time <= end,
        )
        .group_by(PersonalCategory.id)
        .all()
    )
    categories = [
        {
            "category_id": r.id,
            "name": r.name,
            "color": r.color,
            "hours": round(float(r.hours or 0), 2),
        }
        for r in cat_rows
    ]

    cr_rows = (
        db.session.query(
            ChangeRequest.id,
            ChangeRequest.title,
            ChangeRequest.project_id,
            Project.name.label("project_name"),
            Project.color.label("project_color"),
            func.sum(
                (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                * 24.0
            ).label("hours"),
        )
        .join(TimeEntry, TimeEntry.change_request_id == ChangeRequest.id)
        .outerjoin(Project, ChangeRequest.project_id == Project.id)
        .filter(
            TimeEntry.user_id == target_id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time <= end,
        )
        .group_by(
            ChangeRequest.id,
            ChangeRequest.title,
            ChangeRequest.project_id,
            Project.name,
            Project.color,
        )
        .all()
    )
    change_requests = []
    for r in cr_rows:
        hours = round(float(r.hours or 0), 2)
        color = r.project_color or "#E6A23C"
        item = {
            "change_request_id": r.id,
            "title": r.title,
            "project_id": r.project_id,
            "project_name": r.project_name,
            "color": color,
            "hours": hours,
        }
        if is_admin:
            item["cost"] = round(hours * rate, 2)
        change_requests.append(item)

    total_hours = (
        sum(p["hours"] for p in projects)
        + sum(c["hours"] for c in categories)
        + sum(cr["hours"] for cr in change_requests)
    )
    user_payload = {
        "id": target.id,
        "full_name": target.full_name,
    }
    payload = {
        "user": user_payload,
        "month": f"{year:04d}-{month:02d}",
        "total_hours": round(total_hours, 2),
        "projects": projects,
        "categories": categories,
        "change_requests": change_requests,
    }
    # 薪資保密：僅 admin 可看到時薪與月人力成本；員工 / 主管（含查詢自己）一律不回傳
    if is_admin:
        user_payload["hourly_rate"] = rate
        payload["total_cost"] = round(float(total_hours) * rate, 2)
    return jsonify(payload)


@bp.get("/department-summary")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def department_summary():
    user = current_user()
    dept_id = request.args.get("dept_id", type=int)
    if user.role == User.ROLE_MANAGER:
        if user.department_id is None:
            return jsonify(error="forbidden: manager without department"), 403
        # 強制覆寫為自己部門，忽略 query 傳入
        dept_id = user.department_id

    audit.log(
        "reports.view_department_summary",
        actor=user,
        target_type="department" if dept_id else None,
        target_id=dept_id,
        meta={
            "month": request.args.get("month"),
            "include_cost": user.role == User.ROLE_ADMIN,
        },
    )

    year, month = _parse_month(request.args.get("month"))
    start, end = _month_range(year, month)

    q = (
        db.session.query(
            User.id,
            User.full_name,
            User.hourly_rate,
            User.department_id,
            Department.name.label("department_name"),
            func.coalesce(
                func.sum(
                    (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                    * 24.0
                ),
                0.0,
            ).label("hours"),
        )
        .outerjoin(
            TimeEntry,
            (TimeEntry.user_id == User.id)
            & (TimeEntry.start_time >= start)
            & (TimeEntry.start_time <= end),
        )
        .outerjoin(Department, Department.id == User.department_id)
        .filter(User.is_active == True)  # noqa: E712
        .group_by(User.id)
    )
    if dept_id:
        q = q.filter(User.department_id == dept_id)

    is_admin = user.role == User.ROLE_ADMIN
    rows = q.all()
    result = []
    for r in rows:
        hours = float(r.hours or 0)
        rate = float(r.hourly_rate or 0)
        item = {
            "user_id": r.id,
            "full_name": r.full_name,
            "department_id": r.department_id,
            "department_name": r.department_name,
            "hours": round(hours, 2),
        }
        # 薪資保密：僅 admin 可看到人力成本
        if is_admin:
            item["cost"] = round(hours * rate, 2)
        result.append(item)

    payload = {
        "month": f"{year:04d}-{month:02d}",
        "department_id": dept_id,
        "rows": result,
        "total_hours": round(sum(r["hours"] for r in result), 2),
    }
    if is_admin:
        payload["total_cost"] = round(
            sum(r.get("cost", 0) for r in result), 2
        )
    return jsonify(payload)
