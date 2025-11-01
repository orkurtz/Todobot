"""add calendar integration

Revision ID: 20250101000000
Revises: 20251031004134
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250101000000'
down_revision = '20251031004134'
branch_labels = None
depends_on = None


def upgrade():
    # Add calendar fields to User table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_calendar_enabled', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('google_access_token_encrypted', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('google_refresh_token_encrypted', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('google_token_expiry', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('google_calendar_id', sa.String(length=255), nullable=True))
    
    # Add calendar sync fields to Task table
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calendar_event_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('calendar_synced', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('calendar_sync_error', sa.Text(), nullable=True))
    
    # Create index for calendar event lookups
    op.create_index('idx_task_calendar_event', 'task', ['calendar_event_id'], unique=False)


def downgrade():
    # Drop index
    op.drop_index('idx_task_calendar_event', table_name='task')
    
    # Remove calendar fields from Task table
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('calendar_sync_error')
        batch_op.drop_column('calendar_synced')
        batch_op.drop_column('calendar_event_id')
    
    # Remove calendar fields from User table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('google_calendar_id')
        batch_op.drop_column('google_token_expiry')
        batch_op.drop_column('google_refresh_token_encrypted')
        batch_op.drop_column('google_access_token_encrypted')
        batch_op.drop_column('google_calendar_enabled')

