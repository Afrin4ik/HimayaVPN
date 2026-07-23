"""add yookassa payment lifecycle

Revision ID: 8afaa917f312
Revises: 4462c9aed8f3
Create Date: 2026-07-23 20:28:09.105324

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8afaa917f312"
down_revision: Union[str, Sequence[str], None] = "4462c9aed8f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
    )

    op.execute(
        "UPDATE orders "
        "SET idempotency_key = 'legacy-' || id::text "
        "WHERE idempotency_key IS NULL"
    )

    op.alter_column(
        "orders",
        "idempotency_key",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_orders_idempotency_key",
        "orders",
        ["idempotency_key"],
    )

    op.add_column(
        "orders",
        sa.Column("confirmation_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "fulfillment_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "fulfilled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "fulfillment_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("fulfillment_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "notified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("notification_error", sa.Text(), nullable=True),
    )

    op.drop_constraint(
        "ck_orders_status",
        "orders",
        type_="check",
    )
    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        (
            "status in ("
            "'created', 'paid', 'fulfilling', "
            "'fulfilled', 'cancelled', 'failed'"
            ")"
        ),
    )

    op.add_column(
        "vpn_keys",
        sa.Column("pending_order_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vpn_keys",
        sa.Column("last_fulfilled_order_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_vpn_keys_pending_order_id_orders",
        "vpn_keys",
        "orders",
        ["pending_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_vpn_keys_last_fulfilled_order_id_orders",
        "vpn_keys",
        "orders",
        ["last_fulfilled_order_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_unique_constraint(
        "uq_vpn_keys_pending_order_id",
        "vpn_keys",
        ["pending_order_id"],
    )
    op.create_unique_constraint(
        "uq_vpn_keys_last_fulfilled_order_id",
        "vpn_keys",
        ["last_fulfilled_order_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_vpn_keys_last_fulfilled_order_id",
        "vpn_keys",
        type_="unique",
    )
    op.drop_constraint(
        "uq_vpn_keys_pending_order_id",
        "vpn_keys",
        type_="unique",
    )
    op.drop_constraint(
        "fk_vpn_keys_last_fulfilled_order_id_orders",
        "vpn_keys",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_vpn_keys_pending_order_id_orders",
        "vpn_keys",
        type_="foreignkey",
    )

    op.drop_column("vpn_keys", "last_fulfilled_order_id")
    op.drop_column("vpn_keys", "pending_order_id")

    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status in ('created', 'paid', 'cancelled', 'failed')",
    )

    op.drop_column("orders", "notification_error")
    op.drop_column("orders", "notified_at")
    op.drop_column("orders", "fulfillment_error")
    op.drop_column("orders", "fulfillment_attempts")
    op.drop_column("orders", "fulfilled_at")
    op.drop_column("orders", "fulfillment_started_at")
    op.drop_column("orders", "confirmation_url")

    op.drop_constraint(
        "uq_orders_idempotency_key",
        "orders",
        type_="unique",
    )
    op.drop_column("orders", "idempotency_key")
