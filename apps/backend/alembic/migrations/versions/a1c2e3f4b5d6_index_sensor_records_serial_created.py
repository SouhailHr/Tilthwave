"""index sensor_records (sensor_serial_number, created_date desc) for latest-reading lookups

Revision ID: a1c2e3f4b5d6
Revises: 5b56f11845d5
Create Date: 2026-09-15 20:00:00.000000

The flow runner asks, per sensor and every tick, for the newest record; the dashboard lists
records per sensor. Both were sequential scans over a table that grows by ~40k rows/day.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c2e3f4b5d6'
down_revision: Union[str, None] = '5b56f11845d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = 'ix_sensor_records_sensor_serial_number_created_date'


def upgrade() -> None:
    op.create_index(INDEX_NAME, 'sensor_records', ['sensor_serial_number', sa.text('created_date DESC')])


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name='sensor_records')
