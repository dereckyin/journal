from flask import Blueprint, jsonify, request

from .. import audit
from ..extensions import db
from ..models import Department, User
from ..permissions import current_user, role_required

bp = Blueprint("departments", __name__)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def list_departments():
    depts = Department.query.order_by(Department.name).all()
    return jsonify([d.to_dict() for d in depts])


@bp.post("")
@role_required(User.ROLE_ADMIN)
def create_department():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name required"), 400
    if Department.query.filter_by(name=name).first():
        return jsonify(error="department already exists"), 409
    dept = Department(name=name, manager_id=data.get("manager_id"))
    db.session.add(dept)
    db.session.commit()
    audit.log(
        "departments.create",
        actor=current_user(),
        target_type="department",
        target_id=dept.id,
        meta={"name": dept.name},
    )
    return jsonify(dept.to_dict()), 201


@bp.patch("/<int:dept_id>")
@role_required(User.ROLE_ADMIN)
def update_department(dept_id: int):
    dept = Department.query.get_or_404(dept_id)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        dept.name = (data["name"] or "").strip() or dept.name
    if "manager_id" in data:
        dept.manager_id = data["manager_id"]
    db.session.commit()
    audit.log(
        "departments.update",
        actor=current_user(),
        target_type="department",
        target_id=dept.id,
        meta={"fields": list(data.keys())},
    )
    return jsonify(dept.to_dict())


@bp.delete("/<int:dept_id>")
@role_required(User.ROLE_ADMIN)
def delete_department(dept_id: int):
    dept = Department.query.get_or_404(dept_id)
    if dept.members:
        return jsonify(error="department has members, reassign first"), 400
    dept_name = dept.name
    db.session.delete(dept)
    db.session.commit()
    audit.log(
        "departments.delete",
        actor=current_user(),
        target_type="department",
        target_id=dept_id,
        meta={"name": dept_name},
    )
    return jsonify(ok=True)
