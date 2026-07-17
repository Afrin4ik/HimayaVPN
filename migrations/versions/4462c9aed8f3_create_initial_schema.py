"""create initial schema

Revision ID: 4462c9aed8f3
Revises:
Create Date: 2026-07-18 02:02:49.957065

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4462c9aed8f3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "price_rub",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "duration_days",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "limit_ip",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "total_gb",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(code) <> ''",
            name="ck_tariffs_code_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name="ck_tariffs_title_not_blank",
        ),
        sa.CheckConstraint(
            "price_rub >= 0",
            name="ck_tariffs_price_rub_non_negative",
        ),
        sa.CheckConstraint(
            "duration_days > 0",
            name="ck_tariffs_duration_days_positive",
        ),
        sa.CheckConstraint(
            "limit_ip > 0",
            name="ck_tariffs_limit_ip_positive",
        ),
        sa.CheckConstraint(
            "total_gb > 0",
            name="ck_tariffs_total_gb_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "username",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "first_name",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "last_name",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "language_code",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "is_bot",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "trial_available",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_users_telegram_id",
        "users",
        ["telegram_id"],
        unique=True,
    )

    op.create_table(
        "vpn_keys",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "xui_email",
            sa.String(length=320),
            nullable=True,
        ),
        sa.Column(
            "xui_uuid",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "xui_sub_id",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "subscription_url",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "inbound_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="creating",
            nullable=False,
        ),
        sa.Column(
            "tariff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "pending_tariff_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "pending_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "status in "
                "('creating', 'active', 'failed', "
                "'disabled', 'renewing')"
            ),
            name="ck_vpn_keys_status",
        ),
        sa.CheckConstraint(
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
            name="ck_vpn_keys_active_has_credentials",
        ),
        sa.CheckConstraint(
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
            name="ck_vpn_keys_renewing_has_pending_data",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tariff_id"],
            ["tariffs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pending_tariff_id"],
            ["tariffs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_vpn_keys_user_id",
        ),
        sa.UniqueConstraint("xui_email"),
        sa.UniqueConstraint("xui_uuid"),
        sa.UniqueConstraint("xui_sub_id"),
        sa.UniqueConstraint("subscription_url"),
    )

    op.create_index(
        "ix_vpn_keys_status_updated_at",
        "vpn_keys",
        ["status", "updated_at"],
        unique=False,
    )

    op.create_index(
        "ix_vpn_keys_status_expires_at",
        "vpn_keys",
        ["status", "expires_at"],
        unique=False,
    )

    op.create_table(
        "orders",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "tariff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "amount_rub",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="created",
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "provider_payment_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('created', 'paid', 'cancelled', 'failed')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint(
            "amount_rub >= 0",
            name="ck_orders_amount_rub_non_negative",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_orders_payload_is_object",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tariff_id"],
            ["tariffs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_payment_id"),
    )

    op.create_index(
        "ix_orders_user_id_created_at",
        "orders",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orders_user_id_created_at",
        table_name="orders",
    )
    op.drop_table("orders")

    op.drop_index(
        "ix_vpn_keys_status_expires_at",
        table_name="vpn_keys",
    )
    op.drop_index(
        "ix_vpn_keys_status_updated_at",
        table_name="vpn_keys",
    )
    op.drop_table("vpn_keys")

    op.drop_index(
        "ix_users_telegram_id",
        table_name="users",
    )
    op.drop_table("users")

    op.drop_table("tariffs")
