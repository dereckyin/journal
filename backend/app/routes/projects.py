from datetime import date

from flask import Blueprint, jsonify, request

from .. import audit
from ..extensions import db
from ..models import Project, ProjectMember, User
from ..permissions import current_user, role_required

bp = Blueprint("projects", __name__)


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def list_projects():
    user = current_user()
    only_mine = request.args.get("mine") in ("1", "true", "yes")
    q = Project.query

    if only_mine and user.role == User.ROLE_EMPLOYEE:
        q = q.join(ProjectMember, ProjectMember.project_id == Project.id).filter(
            ProjectMember.user_id == user.id
        )

    projects = q.order_by(Project.status.asc(), Project.code.asc()).all()
    # 預算為財務敏感資訊，僅 admin 可見
    include_budget = user.role == User.ROLE_ADMIN
    return jsonify([p.to_dict(include_budget=include_budget) for p in projects])


@bp.post("")
@role_required(User.ROLE_ADMIN)
def create_project():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code or not name:
        return jsonify(error="code and name required"), 400
    if Project.query.filter_by(code=code).first():
        return jsonify(error="project code already exists"), 409

    user = current_user()
    project = Project(
        code=code,
        name=name,
        description=data.get("description"),
        budget=data.get("budget") or 0,
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        status=data.get("status") or Project.STATUS_ACTIVE,
        color=data.get("color") or "#409EFF",
        created_by=user.id if user else None,
    )
    db.session.add(project)
    db.session.flush()

    for uid in data.get("member_ids") or []:
        db.session.add(ProjectMember(project_id=project.id, user_id=int(uid)))

    db.session.commit()
    audit.log(
        "projects.create",
        actor=user,
        target_type="project",
        target_id=project.id,
        meta={"code": project.code, "name": project.name, "budget": float(project.budget or 0)},
    )
    return jsonify(project.to_dict()), 201


@bp.patch("/<int:project_id>")
@role_required(User.ROLE_ADMIN)
def update_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    data = request.get_json(silent=True) or {}

    for field in ("name", "description", "status", "color"):
        if field in data:
            setattr(project, field, data[field])
    if "budget" in data:
        project.budget = data["budget"] or 0
    if "start_date" in data:
        project.start_date = _parse_date(data["start_date"])
    if "end_date" in data:
        project.end_date = _parse_date(data["end_date"])
    if "code" in data:
        new_code = (data["code"] or "").strip()
        if new_code and new_code != project.code:
            if Project.query.filter_by(code=new_code).first():
                return jsonify(error="project code already exists"), 409
            project.code = new_code

    if "member_ids" in data:
        ProjectMember.query.filter_by(project_id=project.id).delete()
        for uid in data["member_ids"] or []:
            db.session.add(ProjectMember(project_id=project.id, user_id=int(uid)))

    db.session.commit()
    audit.log(
        "projects.update",
        actor=current_user(),
        target_type="project",
        target_id=project.id,
        meta={"fields": list(data.keys())},
    )
    return jsonify(project.to_dict())


@bp.delete("/<int:project_id>")
@role_required(User.ROLE_ADMIN)
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    project.status = Project.STATUS_CLOSED
    db.session.commit()
    audit.log(
        "projects.close",
        actor=current_user(),
        target_type="project",
        target_id=project.id,
        meta={"code": project.code, "name": project.name},
    )
    return jsonify(ok=True)
