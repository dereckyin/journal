from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from .. import audit
from ..extensions import db
from ..models import TitlePreset, User
from ..permissions import current_user, role_required

bp = Blueprint("title_presets", __name__)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def list_presets():
    kind = request.args.get("kind")
    q = TitlePreset.query
    if kind:
        if kind not in TitlePreset.KINDS:
            return jsonify(error="invalid kind"), 400
        q = q.filter(TitlePreset.kind == kind)
    rows = q.order_by(
        TitlePreset.kind.asc(),
        TitlePreset.sort_order.asc(),
        TitlePreset.id.asc(),
    ).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("")
@role_required(User.ROLE_ADMIN)
def create_preset():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    kind = (data.get("kind") or "").strip()
    name = (data.get("name") or "").strip()
    if kind not in TitlePreset.KINDS:
        return jsonify(error="invalid kind"), 400
    if not name:
        return jsonify(error="name required"), 400
    if len(name) > 120:
        return jsonify(error="name too long"), 400

    try:
        sort_order = int(data.get("sort_order") or 0)
    except (TypeError, ValueError):
        return jsonify(error="invalid sort_order"), 400

    row = TitlePreset(kind=kind, name=name, sort_order=sort_order)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="duplicate name for this kind"), 409

    audit.log(
        "title_presets.create",
        actor=actor,
        target_type="title_preset",
        target_id=row.id,
        meta={"kind": kind, "name": name},
    )
    return jsonify(row.to_dict()), 201


@bp.patch("/<int:preset_id>")
@role_required(User.ROLE_ADMIN)
def update_preset(preset_id: int):
    actor = current_user()
    row = TitlePreset.query.get_or_404(preset_id)
    data = request.get_json(silent=True) or {}
    changes: dict = {}

    if "name" in data:
        new_name = (data["name"] or "").strip()
        if not new_name:
            return jsonify(error="name required"), 400
        if len(new_name) > 120:
            return jsonify(error="name too long"), 400
        if new_name != row.name:
            changes["name"] = {"from": row.name, "to": new_name}
            row.name = new_name

    if "sort_order" in data:
        try:
            new_order = int(data["sort_order"] or 0)
        except (TypeError, ValueError):
            return jsonify(error="invalid sort_order"), 400
        if new_order != row.sort_order:
            changes["sort_order"] = {"from": row.sort_order, "to": new_order}
            row.sort_order = new_order

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="duplicate name for this kind"), 409

    if changes:
        audit.log(
            "title_presets.update",
            actor=actor,
            target_type="title_preset",
            target_id=row.id,
            meta={"kind": row.kind, "changes": changes},
        )
    return jsonify(row.to_dict())


@bp.delete("/<int:preset_id>")
@role_required(User.ROLE_ADMIN)
def delete_preset(preset_id: int):
    actor = current_user()
    row = TitlePreset.query.get_or_404(preset_id)
    kind, name = row.kind, row.name
    db.session.delete(row)
    db.session.commit()
    audit.log(
        "title_presets.delete",
        actor=actor,
        target_type="title_preset",
        target_id=preset_id,
        meta={"kind": kind, "name": name},
    )
    return jsonify(ok=True)
