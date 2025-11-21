"""add calendar sync tracking

Revision ID: 20250102000000
Revises: 20250116000000
Create Date: 2025-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250102000000'
down_revision = '20250116000000'
branch_labels = None
depends_on = None


def upgrade():
    # Add sync tracking fields to User table
    op.add_column('user', sa.Column('calendar_sync_color', sa.String(50), nullable=True))
    op.add_column('user', sa.Column('calendar_sync_hashtag', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user', sa.Column('last_calendar_sync', sa.DateTime(), nullable=True))
    
    # Add sync tracking fields to Task table
    op.add_column('task', sa.Column('last_modified_at', sa.DateTime(), nullable=True))
    op.add_column('task', sa.Column('calendar_last_modified', sa.DateTime(), nullable=True))
    op.add_column('task', sa.Column('created_from_calendar', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    # Remove Task table columns
    op.drop_column('task', 'created_from_calendar')
    op.drop_column('task', 'calendar_last_modified')
    op.drop_column('task', 'last_modified_at')
    
    # Remove User table columns
    op.drop_column('user', 'last_calendar_sync')
    op.drop_column('user', 'calendar_sync_hashtag')
    op.drop_column('user', 'calendar_sync_color')

