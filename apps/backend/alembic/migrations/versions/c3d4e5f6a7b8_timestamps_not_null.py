"""created_date / updated_date NOT NULL with a UTC server default

Revision ID: c3d4e5f6a7b8
Revises: b2d3e4f5a6c7
Create Date: 2026-09-23 10:00:00.000000

The timestamps were nullable with a default only in the ORM (TilthwaveBaseModel.utc_now). Every
"latest reading" is `ORDER BY created_date DESC LIMIT 1`, and Postgres sorts NULL first under
DESC, so any row written outside the ORM (a bulk load, psql, a fixture) became the flow runner's
current reading. Now the database fills the column itself, in naive UTC like the ORM does, and
refuses NULL. Cheap while the tables are small (SET NOT NULL scans the table under an exclusive
lock); it only gets more expensive.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2d3e4f5a6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every table built on TilthwaveBaseModel.
TABLES = (
    'farm', 'sensor', 'sensor_records', 'users', 'water_source', 'zone', 'irrigation_task', 'tree',
    'water_switcher', 'zone_sensors',
)
# Naive UTC, the same clock the ORM writes (common.dates.utc_now); plain now() would be the
# session's time zone, which the compose stack sets to the farm's.
UTC_NOW = "(now() at time zone 'utc')"


def upgrade() -> None:
    for table in TABLES:
        op.execute(sa.text(
            f"UPDATE {table} SET created_date = COALESCE(updated_date, {UTC_NOW}) WHERE created_date IS NULL"
        ))
        op.execute(sa.text(f"UPDATE {table} SET updated_date = created_date WHERE updated_date IS NULL"))
        for column in ('created_date', 'updated_date'):
            op.alter_column(table, column, server_default=sa.text(UTC_NOW), nullable=False)


def downgrade() -> None:
    for table in TABLES:
        for column in ('created_date', 'updated_date'):
            op.alter_column(table, column, server_default=None, nullable=True)
