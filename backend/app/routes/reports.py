from calendar import monthrange
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import Department, PersonalCategory, Project, TimeEntry, User
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
    project_id = request.args.get("project_id", type=int)
    q = (
        db.session.query(
            Project.id,
            Project.code,
            Project.name,
            Project.budget,
            Project.color,
            func.coalesce(
                func.sum(
                    (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                    * 24.0
                ),
                0.0,
            ).label("hours"),
            func.coalesce(
                func.sum(
                    (func.julianday(TimeEntry.end_time) - func.julianday(TimeEntry.start_time))
                    * 24.0
                    * User.hourly_rate
                ),
                0.0,
            ).label("cost"),
        )
        .outerjoin(TimeEntry, TimeEntry.project_id == Project.id)
        .outerjoin(User, User.id == TimeEntry.user_id)
        .group_by(Project.id)
    )
    if project_id:
        q = q.filter(Project.id == project_id)

    rows = q.all()
    result = []
    for r in rows:
        budget = float(r.budget or 0)
        cost = float(r.cost or 0)
        result.append(
            {
                "project_id": r.id,
                "code": r.code,
                "name": r.name,
                "color": r.color,
                "budget": budget,
                "hours": round(float(r.hours or 0), 2),
                "cost": round(cost, 2),
                "remaining": round(budget - cost, 2),
                "utilization": round(cost / budget * 100, 2) if budget else None,
            }
        )
    return jsonify(result)


@bp.get("/user-hours")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def user_hours():
    user = current_user()
    target_id = request.args.get("user_id", type=int) or user.id

    if user.role == User.ROLE_EMPLOYEE and target_id != user.id:
        return jsonify(error="forbidden"), 403
    if user.role == User.ROLE_MANAGER and target_id != user.id:
        target = User.query.get(target_id)
        if not target or target.department_id != user.department_id:
            return jsonify(error="forbidden: different department"), 403

    year, month = _parse_month(request.args.get("month"))
    start, end = _month_range(year, month)

    target = User.query.get_or_404(target_id)
    rate = float(target.hourly_rate or 0)

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
    projects = [
        {
            "project_id": r.id,
            "name": r.name,
            "color": r.color,
            "hours": round(float(r.hours or 0), 2),
            "cost": round(float(r.hours or 0) * rate, 2),
        }
        for r in rows
    ]

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

    total_hours = sum(p["hours"] for p in projects) + sum(c["hours"] for c in categories)
    return jsonify(
        user={
            "id": target.id,
            "full_name": target.full_name,
            "hourly_rate": rate,
        },
        month=f"{year:04d}-{month:02d}",
        total_hours=round(total_hours, 2),
        total_cost=round(sum(p["cost"] for p in projects), 2),
        projects=projects,
        categories=categories,
    )


@bp.get("/department-summary")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def department_summary():
    user = current_user()
    dept_id = request.args.get("dept_id", type=int)
    if user.role == User.ROLE_MANAGER:
        dept_id = user.department_id

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

    rows = q.all()
    result = []
    for r in rows:
        hours = float(r.hours or 0)
        rate = float(r.hourly_rate or 0)
        result.append(
            {
                "user_id": r.id,
                "full_name": r.full_name,
                "department_id": r.department_id,
                "department_name": r.department_name,
                "hours": round(hours, 2),
                "cost": round(hours * rate, 2),
            }
        )
    return jsonify(
        month=f"{year:04d}-{month:02d}",
        department_id=dept_id,
        rows=result,
        total_hours=round(sum(r["hours"] for r in result), 2),
        total_cost=round(sum(r["cost"] for r in result), 2),
    )
