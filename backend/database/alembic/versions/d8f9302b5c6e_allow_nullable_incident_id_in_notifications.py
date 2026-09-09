"""Allow nullable incident_id in notification_histories for test and standalone alerts

Revision ID: d8f9302b5c6e
Revises: c7e8291a4b5d
Create Date: 2026-09-09 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd8f9302b5c6e'
down_revision: Union[str, None] = 'c7e8291a4b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'notification_histories',
        'incident_id',
        existing_type=sa.UUID(),
        nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        'notification_histories',
        'incident_id',
        existing_type=sa.UUID(),
        nullable=False
    )
