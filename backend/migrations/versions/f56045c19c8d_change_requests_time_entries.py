"""change_requests_time_entries

Revision ID: f56045c19c8d
Revises:
Create Date: 2026-04-24 10:14:32.183756

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "f56045c19c8d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    tables = insp.get_table_names()

    if "change_requests" not in tables:
        op.create_table(
            "change_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("requester_id", sa.Integer(), nullable=False),
            sa.Column("approver_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("decided_by_id", sa.Integer(), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "status in ('draft','submitted','approved','rejected')",
                name="ck_change_request_status",
            ),
            sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    insp = inspect(conn)
    te_cols = {c["name"] for c in insp.get_columns("time_entries")}
    if "change_request_id" not in te_cols:
        with op.batch_alter_table("time_entries", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("change_request_id", sa.Integer(), nullable=True)
            )
            batch_op.drop_constraint("ck_entry_project_xor_category", type_="check")
            batch_op.create_check_constraint(
                "ck_entry_project_category_cr_xor",
                "("
                "(project_id IS NOT NULL AND category_id IS NULL AND change_request_id IS NULL) OR "
                "(project_id IS NULL AND category_id IS NOT NULL AND change_request_id IS NULL) OR "
                "(project_id IS NULL AND category_id IS NULL AND change_request_id IS NOT NULL)"
                ")",
            )
            batch_op.create_foreign_key(
                "fk_time_entries_change_request_id_change_requests",
                "change_requests",
                ["change_request_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    if "title_presets" in insp.get_table_names():
        with op.batch_alter_table("title_presets", schema=None) as batch_op:
            batch_op.drop_constraint("ck_title_preset_kind", type_="check")
            batch_op.create_check_constraint(
                "ck_title_preset_kind",
                "kind in ('project','category','change_request')",
            )


def downgrade():
    with op.batch_alter_table("title_presets", schema=None) as batch_op:
        batch_op.drop_constraint("ck_title_preset_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_title_preset_kind",
            "kind in ('project','category')",
        )

    conn = op.get_bind()
    insp = inspect(conn)
    te_cols = {c["name"] for c in insp.get_columns("time_entries")}
    if "change_request_id" in te_cols:
        with op.batch_alter_table("time_entries", schema=None) as batch_op:
            batch_op.drop_constraint(
                "fk_time_entries_change_request_id_change_requests",
                type_="foreignkey",
            )
            batch_op.drop_constraint(
                "ck_entry_project_category_cr_xor", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_entry_project_xor_category",
                "("
                "(project_id IS NOT NULL AND category_id IS NULL) OR "
                "(project_id IS NULL AND category_id IS NOT NULL)"
                ")",
            )
            batch_op.drop_column("change_request_id")

    insp = inspect(conn)
    if "change_requests" in insp.get_table_names():
        op.drop_table("change_requests")
