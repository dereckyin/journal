from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from .. import audit
from ..extensions import db
from ..models import ChangeRequest, Department, Project, ProjectMember, User
from ..permissions import current_user

bp = Blueprint("change_requests", __name__)


def _norm_id(val):
    if val is None or val == "":
        return None
    try:
        i = int(val)
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def effective_approver_id(cr: ChangeRequest) -> int | None:
    return cr.effective_approver_id()


def can_approve(user: User, cr: ChangeRequest) -> bool:
    if cr.status != ChangeRequest.STATUS_SUBMITTED:
        return False
    if user.role == User.ROLE_ADMIN:
        return True
    aid = effective_approver_id(cr)
    return aid is not None and user.id == aid


def can_view_change_request(user: User, cr: ChangeRequest) -> bool:
    if user.role == User.ROLE_ADMIN:
        return True
    if cr.requester_id == user.id:
        return True
    if user.role == User.ROLE_MANAGER:
        if user.department_id is None:
            return cr.requester_id == user.id
        req = cr.requester
        if req and req.department_id == user.department_id:
            return True
    if cr.project_id:
        if ProjectMember.query.filter_by(
            project_id=cr.project_id, user_id=user.id
        ).first():
            return True
    return can_approve(user, cr)


def can_log_time_on_change_request(user: User, cr: ChangeRequest) -> bool:
    if cr.status != ChangeRequest.STATUS_APPROVED:
        return False
    return can_view_change_request(user, cr)


def _pending_approver_filter(q, user: User):
    """待簽：已送審且目前使用者為有效簽核人（含部門主管預設）。"""
    q = q.filter(ChangeRequest.status == ChangeRequest.STATUS_SUBMITTED)
    if user.role == User.ROLE_ADMIN:
        return q
    q = (
        q.join(User, ChangeRequest.requester_id == User.id)
        .outerjoin(
            Department,
            User.department_id == Department.id,
        )
        .filter(
            or_(
                ChangeRequest.approver_id == user.id,
                (ChangeRequest.approver_id.is_(None))
                & (Department.manager_id == user.id),
            )
        )
    )
    return q


@bp.get("")
@jwt_required()
def list_change_requests():
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401

    scope = (request.args.get("scope") or "mine").strip()
    status_filter = request.args.get("status")

    q = ChangeRequest.query

    if scope == "loggable":
        q = q.filter(ChangeRequest.status == ChangeRequest.STATUS_APPROVED)
        rows = q.order_by(ChangeRequest.updated_at.desc()).all()
        rows = [cr for cr in rows if can_log_time_on_change_request(user, cr)]
        return jsonify([cr.to_dict() for cr in rows])

    if scope == "pending":
        q = _pending_approver_filter(q, user)
    elif scope == "department":
        if user.role == User.ROLE_ADMIN:
            pass
        elif user.role == User.ROLE_MANAGER:
            if user.department_id is None:
                q = q.filter(ChangeRequest.requester_id == user.id)
            else:
                q = q.join(User, ChangeRequest.requester_id == User.id).filter(
                    User.department_id == user.department_id
                )
        else:
            q = q.filter(ChangeRequest.requester_id == user.id)
    elif scope == "all":
        if user.role != User.ROLE_ADMIN:
            q = q.filter(ChangeRequest.requester_id == user.id)
    else:
        # mine
        q = q.filter(ChangeRequest.requester_id == user.id)

    if status_filter:
        q = q.filter(ChangeRequest.status == status_filter)

    rows = q.order_by(ChangeRequest.updated_at.desc()).distinct().all()
    visible = [cr for cr in rows if can_view_change_request(user, cr)]
    return jsonify([cr.to_dict() for cr in visible])


@bp.post("")
@jwt_required()
def create_change_request():
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title required"), 400

    project_id = _norm_id(data.get("project_id"))
    approver_id = _norm_id(data.get("approver_id"))

    if project_id and not Project.query.get(project_id):
        return jsonify(error="project not found"), 404
    if approver_id:
        au = User.query.filter_by(id=approver_id, is_active=True).first()
        if not au:
            return jsonify(error="approver not found"), 404

    cr = ChangeRequest(
        title=title,
        description=data.get("description"),
        project_id=project_id,
        requester_id=user.id,
        approver_id=approver_id,
        status=ChangeRequest.STATUS_DRAFT,
    )
    db.session.add(cr)
    db.session.commit()
    audit.log(
        "change_requests.create",
        actor=user,
        target_type="change_request",
        target_id=cr.id,
        meta={"title": title},
    )
    return jsonify(cr.to_dict()), 201


@bp.get("/<int:cr_id>")
@jwt_required()
def get_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if not can_view_change_request(user, cr):
        return jsonify(error="forbidden"), 403
    return jsonify(cr.to_dict())


@bp.patch("/<int:cr_id>")
@jwt_required()
def update_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if cr.requester_id != user.id and user.role != User.ROLE_ADMIN:
        return jsonify(error="forbidden"), 403
    if cr.status not in (ChangeRequest.STATUS_DRAFT, ChangeRequest.STATUS_REJECTED):
        return jsonify(error="only draft or rejected can be edited"), 400

    data = request.get_json(silent=True) or {}
    if "title" in data:
        t = (data.get("title") or "").strip()
        if not t:
            return jsonify(error="title required"), 400
        cr.title = t
    if "description" in data:
        cr.description = data.get("description")
    if "project_id" in data:
        pid = _norm_id(data.get("project_id"))
        if pid and not Project.query.get(pid):
            return jsonify(error="project not found"), 404
        cr.project_id = pid
    if "approver_id" in data:
        aid = _norm_id(data.get("approver_id"))
        if aid:
            au = User.query.filter_by(id=aid, is_active=True).first()
            if not au:
                return jsonify(error="approver not found"), 404
        cr.approver_id = aid

    db.session.commit()
    audit.log(
        "change_requests.update",
        actor=user,
        target_type="change_request",
        target_id=cr.id,
    )
    return jsonify(cr.to_dict())


@bp.post("/<int:cr_id>/submit")
@jwt_required()
def submit_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if cr.requester_id != user.id:
        return jsonify(error="forbidden"), 403
    if cr.status not in (
        ChangeRequest.STATUS_DRAFT,
        ChangeRequest.STATUS_REJECTED,
    ):
        return jsonify(error="invalid status for submit"), 400
    if effective_approver_id(cr) is None:
        return jsonify(
            error="無法送審：請指定簽核人，或將申請人加入具部門主管的部門"
        ), 400

    cr.status = ChangeRequest.STATUS_SUBMITTED
    cr.submitted_at = datetime.utcnow()
    cr.decided_at = None
    cr.decided_by_id = None
    cr.decision_note = None
    db.session.commit()
    audit.log(
        "change_requests.submit",
        actor=user,
        target_type="change_request",
        target_id=cr.id,
    )
    return jsonify(cr.to_dict())


@bp.post("/<int:cr_id>/approve")
@jwt_required()
def approve_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if not can_approve(user, cr):
        return jsonify(error="forbidden"), 403

    data = request.get_json(silent=True) or {}
    note = data.get("decision_note")

    cr.status = ChangeRequest.STATUS_APPROVED
    cr.decided_at = datetime.utcnow()
    cr.decided_by_id = user.id
    cr.decision_note = note
    db.session.commit()
    audit.log(
        "change_requests.approve",
        actor=user,
        target_type="change_request",
        target_id=cr.id,
    )
    return jsonify(cr.to_dict())


@bp.post("/<int:cr_id>/reject")
@jwt_required()
def reject_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if not can_approve(user, cr):
        return jsonify(error="forbidden"), 403

    data = request.get_json(silent=True) or {}
    note = (data.get("decision_note") or "").strip()
    if not note:
        return jsonify(error="decision_note required for reject"), 400

    cr.status = ChangeRequest.STATUS_REJECTED
    cr.decided_at = datetime.utcnow()
    cr.decided_by_id = user.id
    cr.decision_note = note
    db.session.commit()
    audit.log(
        "change_requests.reject",
        actor=user,
        target_type="change_request",
        target_id=cr.id,
    )
    return jsonify(cr.to_dict())


@bp.delete("/<int:cr_id>")
@jwt_required()
def delete_change_request(cr_id: int):
    user = current_user()
    if user is None:
        return jsonify(error="account inactive or revoked"), 401
    cr = ChangeRequest.query.get_or_404(cr_id)
    if cr.status != ChangeRequest.STATUS_DRAFT:
        return jsonify(error="only draft can be deleted"), 400
    if cr.requester_id != user.id and user.role != User.ROLE_ADMIN:
        return jsonify(error="forbidden"), 403
    db.session.delete(cr)
    db.session.commit()
    audit.log(
        "change_requests.delete",
        actor=user,
        target_type="change_request",
        target_id=cr_id,
    )
    return jsonify(ok=True)
