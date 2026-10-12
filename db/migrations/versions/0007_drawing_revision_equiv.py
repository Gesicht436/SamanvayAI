"""Add drawing_revision_equivalence table per Section 9.2 and Invariant S13.

Revision ID: 0007_drawing_revision_equiv
Revises: 0006_mtc_verified_and_grades
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_drawing_revision_equiv"
down_revision: str | None = "0006_mtc_verified_and_grades"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drawing_revision_equivalence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("drawing_owner", sa.Text(), nullable=False),
        sa.Column("drawing_norm", sa.Text(), nullable=False),
        sa.Column("rev_a", sa.Text(), nullable=False),
        sa.Column("rev_b", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("proposed_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "approved_by IS NULL OR proposed_by <> approved_by",
            name="rev_maker_ne_checker",
        ),
    )
    op.create_index(
        "ix_drawing_rev_equiv_owner_norm",
        "drawing_revision_equivalence",
        ["drawing_owner", "drawing_norm"],
    )


def downgrade() -> None:
    op.drop_index("ix_drawing_rev_equiv_owner_norm", table_name="drawing_revision_equivalence")
    op.drop_table("drawing_revision_equivalence")
