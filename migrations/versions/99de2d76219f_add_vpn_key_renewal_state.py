"""add vpn key renewal state

Revision ID: 99de2d76219f
Revises: 3127e10846a1
Create Date: 2026-07-13 18:39:39.235909

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "99de2d76219f"
down_revision: Union[str, Sequence[str], None] = "3127e10846a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vpn_keys",
        sa.Column(
            "pending_tariff_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "vpn_keys",
        sa.Column(
            "pending_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_vpn_keys_pending_tariff_id_tariffs",
        "vpn_keys",
        "tariffs",
        ["pending_tariff_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "ck_vpn_keys_status",
        "vpn_keys",
        type_="check",
    )

    op.create_check_constraint(
        "ck_vpn_keys_status",
        "vpn_keys",
        (
            "status in "
            "('creating', 'active', 'renewing', "
            "'failed', 'disabled')"
        ),
    )

    op.drop_constraint(
        "ck_vpn_keys_active_has_credentials",
        "vpn_keys",
        type_="check",
    )

    op.create_check_constraint(
        "ck_vpn_keys_active_has_credentials",
        "vpn_keys",
        (
            "status NOT IN ('active', 'renewing') OR ("
            "xui_email IS NOT NULL AND "
            "btrim(xui_email) <> '' AND "
            "xui_uuid IS NOT NULL AND "
            "btrim(xui_uuid) <> '' AND "
            "xui_sub_id IS NOT NULL AND "
            "btrim(xui_sub_id) <> '' AND "
            "subscription_url IS NOT NULL AND "
            "btrim(subscription_url) <> '' AND "
            "expires_at IS NOT NULL"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_vpn_keys_renewing_has_pending_data",
        "vpn_keys",
        (
            "("
            "status = 'renewing' AND "
            "pending_tariff_id IS NOT NULL AND "
            "pending_expires_at IS NOT NULL"
            ") OR ("
            "status <> 'renewing' AND "
            "pending_tariff_id IS NULL AND "
            "pending_expires_at IS NULL"
            ")"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_vpn_keys_renewing_has_pending_data",
        "vpn_keys",
        type_="check",
    )

    op.drop_constraint(
        "ck_vpn_keys_active_has_credentials",
        "vpn_keys",
        type_="check",
    )

    op.create_check_constraint(
        "ck_vpn_keys_active_has_credentials",
        "vpn_keys",
        (
            "status <> 'active' OR ("
            "xui_email IS NOT NULL AND "
            "btrim(xui_email) <> '' AND "
            "xui_uuid IS NOT NULL AND "
            "btrim(xui_uuid) <> '' AND "
            "xui_sub_id IS NOT NULL AND "
            "btrim(xui_sub_id) <> '' AND "
            "subscription_url IS NOT NULL AND "
            "btrim(subscription_url) <> '' AND "
            "expires_at IS NOT NULL"
            ")"
        ),
    )

    op.drop_constraint(
        "ck_vpn_keys_status",
        "vpn_keys",
        type_="check",
    )

    op.create_check_constraint(
        "ck_vpn_keys_status",
        "vpn_keys",
        (
            "status in "
            "('creating', 'active', 'failed', 'disabled')"
        ),
    )

    op.drop_constraint(
        "fk_vpn_keys_pending_tariff_id_tariffs",
        "vpn_keys",
        type_="foreignkey",
    )

    op.drop_column("vpn_keys", "pending_expires_at")
    op.drop_column("vpn_keys", "pending_tariff_id")
