"""Add mtc_verified column to stock_lots and seed starter grade references.

Revision ID: 0006_mtc_verified_and_grades
Revises: 0005_subvectors_and_erp
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_mtc_verified_and_grades"
down_revision: str | None = "0005_subvectors_and_erp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STARTER_GRADES = [
    # ASTM A105
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.35, "unit": "%"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "MN", "kind": "CHEM", "min_value": 0.60, "max_value": 1.05, "unit": "%"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.040, "unit": "%"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "SI", "kind": "CHEM", "min_value": 0.10, "max_value": 0.35, "unit": "%"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "TENSILE", "kind": "MECH", "min_value": 485, "max_value": None, "unit": "MPA"},
    {"grade": "ASTM A105", "product_form": "FORGING", "property": "YIELD", "kind": "MECH", "min_value": 250, "max_value": None, "unit": "MPA"},
    # ASTM A216 WCB
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.30, "unit": "%"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "MN", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "SI", "kind": "CHEM", "min_value": None, "max_value": 0.60, "unit": "%"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "TENSILE", "kind": "MECH", "min_value": 485, "max_value": None, "unit": "MPA"},
    {"grade": "ASTM A216 WCB", "product_form": "CASTING", "property": "YIELD", "kind": "MECH", "min_value": 250, "max_value": None, "unit": "MPA"},
    # ASTM A350 LF2
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.30, "unit": "%"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "MN", "kind": "CHEM", "min_value": 0.60, "max_value": 1.35, "unit": "%"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.040, "unit": "%"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "SI", "kind": "CHEM", "min_value": 0.15, "max_value": 0.30, "unit": "%"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "TENSILE", "kind": "MECH", "min_value": 485, "max_value": None, "unit": "MPA"},
    {"grade": "ASTM A350 LF2", "product_form": "FORGING", "property": "YIELD", "kind": "MECH", "min_value": 250, "max_value": None, "unit": "MPA"},
    # ASTM A182 F316
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.08, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "MN", "kind": "CHEM", "min_value": None, "max_value": 2.00, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.045, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "SI", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "CR", "kind": "CHEM", "min_value": 16.0, "max_value": 18.0, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "NI", "kind": "CHEM", "min_value": 10.0, "max_value": 14.0, "unit": "%"},
    {"grade": "ASTM A182 F316", "product_form": "FORGING", "property": "MO", "kind": "CHEM", "min_value": 2.0, "max_value": 3.0, "unit": "%"},
    # ASTM A182 F51 (Duplex)
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.03, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "MN", "kind": "CHEM", "min_value": None, "max_value": 2.00, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.020, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "SI", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "CR", "kind": "CHEM", "min_value": 21.0, "max_value": 23.0, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "NI", "kind": "CHEM", "min_value": 4.5, "max_value": 6.5, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "MO", "kind": "CHEM", "min_value": 2.5, "max_value": 3.5, "unit": "%"},
    {"grade": "ASTM A182 F51", "product_form": "FORGING", "property": "N", "kind": "CHEM", "min_value": 0.08, "max_value": 0.20, "unit": "%"},
    # ASTM A335 P11
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "C", "kind": "CHEM", "min_value": 0.05, "max_value": 0.15, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "MN", "kind": "CHEM", "min_value": 0.30, "max_value": 0.60, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "SI", "kind": "CHEM", "min_value": 0.50, "max_value": 1.00, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "CR", "kind": "CHEM", "min_value": 1.00, "max_value": 1.50, "unit": "%"},
    {"grade": "ASTM A335 P11", "product_form": "PIPE", "property": "MO", "kind": "CHEM", "min_value": 0.44, "max_value": 0.65, "unit": "%"},
    # ASTM A335 P22
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "C", "kind": "CHEM", "min_value": 0.05, "max_value": 0.15, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "MN", "kind": "CHEM", "min_value": 0.30, "max_value": 0.60, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "SI", "kind": "CHEM", "min_value": None, "max_value": 0.50, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "CR", "kind": "CHEM", "min_value": 1.90, "max_value": 2.60, "unit": "%"},
    {"grade": "ASTM A335 P22", "product_form": "PIPE", "property": "MO", "kind": "CHEM", "min_value": 0.87, "max_value": 1.13, "unit": "%"},
    # API 5L X52
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.22, "unit": "%"},
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "MN", "kind": "CHEM", "min_value": None, "max_value": 1.40, "unit": "%"},
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.015, "unit": "%"},
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "YIELD", "kind": "MECH", "min_value": 360, "max_value": None, "unit": "MPA"},
    {"grade": "API 5L X52", "product_form": "PIPE", "property": "TENSILE", "kind": "MECH", "min_value": 460, "max_value": None, "unit": "MPA"},
    # API 5L X65
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.22, "unit": "%"},
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "MN", "kind": "CHEM", "min_value": None, "max_value": 1.45, "unit": "%"},
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.025, "unit": "%"},
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.015, "unit": "%"},
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "YIELD", "kind": "MECH", "min_value": 450, "max_value": None, "unit": "MPA"},
    {"grade": "API 5L X65", "product_form": "PIPE", "property": "TENSILE", "kind": "MECH", "min_value": 535, "max_value": None, "unit": "MPA"},
    # ASTM A213 T22 (Boiler Tube)
    {"grade": "ASTM A213 T22", "product_form": "TUBE", "property": "C", "kind": "CHEM", "min_value": 0.05, "max_value": 0.15, "unit": "%"},
    {"grade": "ASTM A213 T22", "product_form": "TUBE", "property": "MN", "kind": "CHEM", "min_value": 0.30, "max_value": 0.60, "unit": "%"},
    {"grade": "ASTM A213 T22", "product_form": "TUBE", "property": "CR", "kind": "CHEM", "min_value": 1.90, "max_value": 2.60, "unit": "%"},
    {"grade": "ASTM A213 T22", "product_form": "TUBE", "property": "MO", "kind": "CHEM", "min_value": 0.87, "max_value": 1.13, "unit": "%"},
    # ASTM A213 T91 (Boiler Tube)
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "C", "kind": "CHEM", "min_value": 0.08, "max_value": 0.12, "unit": "%"},
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "MN", "kind": "CHEM", "min_value": 0.30, "max_value": 0.60, "unit": "%"},
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "CR", "kind": "CHEM", "min_value": 8.00, "max_value": 9.50, "unit": "%"},
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "MO", "kind": "CHEM", "min_value": 0.85, "max_value": 1.05, "unit": "%"},
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "V", "kind": "CHEM", "min_value": 0.18, "max_value": 0.25, "unit": "%"},
    {"grade": "ASTM A213 T91", "product_form": "TUBE", "property": "N", "kind": "CHEM", "min_value": 0.03, "max_value": 0.07, "unit": "%"},
]


def upgrade() -> None:
    # 1. Add mtc_verified column to stock_lots
    op.add_column(
        "stock_lots",
        sa.Column("mtc_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 2. Seed starter grades into grade_reference (all verified=False per S15)
    grade_ref_table = sa.table(
        "grade_reference",
        sa.column("grade", sa.Text),
        sa.column("product_form", sa.Text),
        sa.column("property", sa.Text),
        sa.column("kind", sa.Text),
        sa.column("min_value", sa.Numeric),
        sa.column("max_value", sa.Numeric),
        sa.column("unit", sa.Text),
        sa.column("condition", sa.Text),
        sa.column("source", sa.Text),
        sa.column("verified", sa.Boolean),
    )

    insert_rows = []
    for g in STARTER_GRADES:
        insert_rows.append(
            {
                "grade": g["grade"],
                "product_form": g["product_form"],
                "property": g["property"],
                "kind": g["kind"],
                "min_value": g["min_value"],
                "max_value": g["max_value"],
                "unit": g["unit"],
                "condition": None,
                "source": "ASTM / API starter seed [VERIFY]",
                "verified": False,
            }
        )

    op.bulk_insert(grade_ref_table, insert_rows)


def downgrade() -> None:
    # 1. Remove seeded starter grades
    op.execute("DELETE FROM grade_reference WHERE source = 'ASTM / API starter seed [VERIFY]';")

    # 2. Drop mtc_verified column
    op.drop_column("stock_lots", "mtc_verified")
