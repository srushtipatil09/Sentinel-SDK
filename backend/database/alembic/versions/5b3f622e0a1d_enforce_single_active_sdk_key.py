"""Enforce single active SDK key per project

Revision ID: 5b3f622e0a1d
Revises: 4a2e511f9b3c
Create Date: 2026-08-26 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '5b3f622e0a1d'
down_revision: Union[str, None] = '4a2e511f9b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clean up duplicate active keys per project (keeping the newest active key)
    op.execute("""
        UPDATE api_keys
        SET is_active = false, is_deleted = true, deleted_at = NOW()
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at DESC) as rnum
                FROM api_keys
                WHERE is_active = true AND is_deleted = false
            ) sub
            WHERE rnum > 1
        );
    """)

    # 2. Create partial unique index enforcing only 1 active key per project
    op.create_index(
        "idx_unique_active_project_api_key",
        "api_keys",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND is_deleted = false")
    )


def downgrade() -> None:
    op.drop_index("idx_unique_active_project_api_key", table_name="api_keys")
