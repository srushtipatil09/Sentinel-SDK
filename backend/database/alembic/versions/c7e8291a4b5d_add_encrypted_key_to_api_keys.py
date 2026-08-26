"""Add encrypted_key column to api_keys

Revision ID: c7e8291a4b5d
Revises: 5b3f622e0a1d
Create Date: 2026-08-26 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c7e8291a4b5d'
down_revision: Union[str, None] = '5b3f622e0a1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("encrypted_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "encrypted_key")
