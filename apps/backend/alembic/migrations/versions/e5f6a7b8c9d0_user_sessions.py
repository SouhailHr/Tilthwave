"""user_sessions: the server-side half of a session token

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-23 14:00:00.000000

Every login opens a row here and the JWT names it in `jti`. The auth middleware refuses a token
whose row is missing, revoked, idle past API_SESSION_IDLE_MINUTES or past expires_at, so logout,
"sign out everywhere", a password change and deactivation end a session at once instead of when
the token expires. Tokens issued before this revision carry no `jti` and are refused: everyone
signs in again once, which is the point.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_NOW = "(now() at time zone 'utc')"


def upgrade() -> None:
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Unique identifier for the record.'),
        sa.Column('created_date', sa.DateTime(), server_default=sa.text(UTC_NOW), nullable=False,
                  comment='Date and time when the record was created.'),
        sa.Column('updated_date', sa.DateTime(), server_default=sa.text(UTC_NOW), nullable=False,
                  comment='Date and time when the record was last updated.'),
        sa.Column('performed_by', sa.String(), nullable=True,
                  comment='A field states who is the user that did the action'),
        sa.Column('token_id', sa.String(length=64), nullable=False, comment="The jti claim of the session's JWT."),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='The signed-in user.'),
        sa.Column('channel', sa.String(length=10), nullable=False,
                  comment='How the credential travels: header (bearer) or cookie.'),
        sa.Column('last_seen', sa.DateTime(), nullable=False, comment='Last request on this session (UTC).'),
        sa.Column('expires_at', sa.DateTime(), nullable=False,
                  comment='Absolute end of the session (UTC), whatever the activity.'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True,
                  comment='Set by logout, a password change or an admin; ends it.'),
        sa.Column('user_agent', sa.String(length=200), nullable=True,
                  comment='User-Agent at login, for the sessions list.'),
        sa.Column('client_ip', sa.String(length=45), nullable=True,
                  comment='Client address at login, for the sessions list.'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id'),
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
