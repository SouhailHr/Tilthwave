"""sensor.farm_name: tenant linkage so /sensors and /sensor-records are scoped per farm

Revision ID: b2d3e4f5a6c7
Revises: a1c2e3f4b5d6
Create Date: 2026-09-20 16:00:00.000000

Sensors had no farm column, so the per-farm filter every other resource gets could not apply:
any authenticated user could read, edit or delete another farm's sensors and readings. The
column is backfilled from the links a sensor already has (zone via zone_sensors, switcher via
its zone, water source directly); a sensor with no link stays NULL and is invisible through the
API until an admin re-assigns it.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2d3e4f5a6c7'
down_revision: Union[str, None] = 'a1c2e3f4b5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = 'sensor_farm_name_fkey'
INDEX_NAME = 'ix_sensor_farm_name'

# The downgrade keeps what it drops: a sensor assigned by an admin has no link row, so the
# backfill below cannot re-derive its farm after a downgrade/upgrade round trip. The upgrade
# restores from that snapshot first (only farms that still exist), then removes it.
SNAPSHOT_TABLE = 'sensor_farm_name_snapshot'
SNAPSHOT = f"""
    CREATE TABLE IF NOT EXISTS {SNAPSHOT_TABLE} AS
    SELECT serial_number, farm_name FROM sensor WHERE farm_name IS NOT NULL
"""
RESTORE = f"""
    DO $$
    BEGIN
        IF to_regclass('{SNAPSHOT_TABLE}') IS NOT NULL THEN
            UPDATE sensor AS s SET farm_name = b.farm_name
            FROM {SNAPSHOT_TABLE} AS b
            WHERE b.serial_number = s.serial_number AND s.farm_name IS NULL
              AND EXISTS (SELECT 1 FROM farm AS f WHERE f.farm_name = b.farm_name);
            DROP TABLE {SNAPSHOT_TABLE};
        END IF;
    END
    $$
"""

BACKFILL = (
    # zone sensors -> zone.farm_name
    """
    UPDATE sensor AS s SET farm_name = z.farm_name
    FROM zone_sensors AS zs JOIN zone AS z ON z.zone_name = zs.zone_name
    WHERE zs.sensor_serial_number = s.serial_number AND s.farm_name IS NULL
    """,
    # switcher sensors -> water_switcher.zone_name -> zone.farm_name
    """
    UPDATE sensor AS s SET farm_name = z.farm_name
    FROM water_switcher AS w JOIN zone AS z ON z.zone_name = w.zone_name
    WHERE w.sensor_serial_number = s.serial_number AND s.farm_name IS NULL
    """,
    # source sensors -> water_source.farm_name
    """
    UPDATE sensor AS s SET farm_name = w.farm_name
    FROM water_source AS w
    WHERE w.sensor_serial_number = s.serial_number AND s.farm_name IS NULL
    """,
)


def upgrade() -> None:
    op.add_column(
        'sensor',
        sa.Column(
            'farm_name', sa.String(length=100), nullable=True,
            comment='Foreign key referencing the farm that owns the sensor.',
        ),
    )
    op.create_foreign_key(
        FK_NAME, 'sensor', 'farm', ['farm_name'], ['farm_name'], onupdate='CASCADE', ondelete='SET NULL'
    )
    op.create_index(INDEX_NAME, 'sensor', ['farm_name'])
    op.execute(sa.text(RESTORE))
    for statement in BACKFILL:
        op.execute(sa.text(statement))


def downgrade() -> None:
    op.execute(sa.text(SNAPSHOT))
    op.drop_index(INDEX_NAME, table_name='sensor')
    op.drop_constraint(FK_NAME, 'sensor', type_='foreignkey')
    op.drop_column('sensor', 'farm_name')
