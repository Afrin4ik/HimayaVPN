"""require credentials for active vpn keys

Revision ID: 3127e10846a1
Revises: 44cf0bfc76c1
Create Date: 2026-07-13 03:27:38.426660

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3127e10846a1"
down_revision: Union[str, Sequence[str], None] = "44cf0bfc76c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint(
    "ck_vpn_keys_active_has_credentials",
    "vpn_keys",
    type_="check",
)
