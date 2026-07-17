"""add tariff constraints

Revision ID: e5d3812e05d1
Revises: 60971341c73e
Create Date: 2026-07-17 21:12:24.485157

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e5d3812e05d1"
down_revision: Union[str, Sequence[str], None] = "60971341c73e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_tariffs_code_not_blank",
        "tariffs",
        "btrim(code) <> ''",
    )

    op.create_check_constraint(
        "ck_tariffs_title_not_blank",
        "tariffs",
        "btrim(title) <> ''",
    )

    op.create_check_constraint(
        "ck_tariffs_price_rub_non_negative",
        "tariffs",
        "price_rub >= 0",
    )

    op.create_check_constraint(
        "ck_tariffs_duration_days_positive",
        "tariffs",
        "duration_days > 0",
    )

    op.create_check_constraint(
        "ck_tariffs_limit_ip_positive",
        "tariffs",
        "limit_ip > 0",
    )

    op.create_check_constraint(
        "ck_tariffs_total_gb_positive",
        "tariffs",
        "total_gb > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tariffs_total_gb_positive",
        "tariffs",
        type_="check",
    )

    op.drop_constraint(
        "ck_tariffs_limit_ip_positive",
        "tariffs",
        type_="check",
    )

    op.drop_constraint(
        "ck_tariffs_duration_days_positive",
        "tariffs",
        type_="check",
    )

    op.drop_constraint(
        "ck_tariffs_price_rub_non_negative",
        "tariffs",
        type_="check",
    )

    op.drop_constraint(
        "ck_tariffs_title_not_blank",
        "tariffs",
        type_="check",
    )

    op.drop_constraint(
        "ck_tariffs_code_not_blank",
        "tariffs",
        type_="check",
    )
