from flask import Blueprint, jsonify, request

from .. import audit
from ..extensions import db
from ..models import PersonalCategory, User
from ..permissions import current_user, role_required

bp = Blueprint("categories", __name__)


@bp.get("")
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER, User.ROLE_EMPLOYEE)
def list_categories():
    cats = PersonalCategory.query.order_by(PersonalCategory.name).all()
    return jsonify([c.to_dict() for c in cats])


@bp.post("")
@role_required(User.ROLE_ADMIN)
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name required"), 400
    if PersonalCategory.query.filter_by(name=name).first():
        return jsonify(error="category already exists"), 409
    cat = PersonalCategory(name=name, color=data.get("color") or "#909399")
    db.session.add(cat)
    db.session.commit()
    audit.log(
        "categories.create",
        actor=current_user(),
        target_type="category",
        target_id=cat.id,
        meta={"name": cat.name},
    )
    return jsonify(cat.to_dict()), 201


@bp.patch("/<int:cat_id>")
@role_required(User.ROLE_ADMIN)
def update_category(cat_id: int):
    cat = PersonalCategory.query.get_or_404(cat_id)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        cat.name = (data["name"] or "").strip() or cat.name
    if "color" in data:
        cat.color = data["color"] or cat.color
    db.session.commit()
    audit.log(
        "categories.update",
        actor=current_user(),
        target_type="category",
        target_id=cat.id,
        meta={"fields": list(data.keys())},
    )
    return jsonify(cat.to_dict())


@bp.delete("/<int:cat_id>")
@role_required(User.ROLE_ADMIN)
def delete_category(cat_id: int):
    cat = PersonalCategory.query.get_or_404(cat_id)
    cat_name = cat.name
    db.session.delete(cat)
    db.session.commit()
    audit.log(
        "categories.delete",
        actor=current_user(),
        target_type="category",
        target_id=cat_id,
        meta={"name": cat_name},
    )
    return jsonify(ok=True)
