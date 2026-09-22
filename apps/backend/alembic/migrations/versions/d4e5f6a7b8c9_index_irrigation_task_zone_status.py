"""index irrigation_task (zone_name, status)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-23 12:00:00.000000

The flow runner reads the in-progress tasks every tick and the dashboard counts tasks by status;
both were sequential scans over a table that grows with every irrigation. Built CONCURRENTLY, in
its own autocommit block, so the streamer and the API keep writing while it builds.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = 'ix_irrigation_task_zone_name_status'


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(INDEX_NAME, 'irrigation_task', ['zone_name', 'status'], postgresql_concurrently=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(INDEX_NAME, table_name='irrigation_task', postgresql_concurrently=True)
