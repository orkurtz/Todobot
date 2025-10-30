"""add recurring tasks support

Revision ID: 20251030230756
Revises: ba8784afef48
Create Date: 2025-10-30 23:07:56

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251030230756'
down_revision = 'ba8784afef48'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        # Recurring pattern fields
        batch_op.add_column(sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('recurrence_pattern', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('recurrence_interval', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recurrence_days_of_week', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('recurrence_end_date', sa.DateTime(), nullable=True))
        
        # Instance tracking
        batch_op.add_column(sa.Column('parent_recurring_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recurring_instance_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recurring_max_instances', sa.Integer(), server_default='100', nullable=True))
        
        # Foreign key and indexes
        batch_op.create_foreign_key('fk_task_parent_recurring', 'task', ['parent_recurring_id'], ['id'])
        batch_op.create_index('idx_task_is_recurring', ['is_recurring'], unique=False)
        batch_op.create_index('idx_task_parent_recurring', ['parent_recurring_id'], unique=False)


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_index('idx_task_parent_recurring')
        batch_op.drop_index('idx_task_is_recurring')
        batch_op.drop_constraint('fk_task_parent_recurring', type_='foreignkey')
        batch_op.drop_column('recurring_max_instances')
        batch_op.drop_column('recurring_instance_count')
        batch_op.drop_column('parent_recurring_id')
        batch_op.drop_column('recurrence_end_date')
        batch_op.drop_column('recurrence_days_of_week')
        batch_op.drop_column('recurrence_interval')
        batch_op.drop_column('recurrence_pattern')
        batch_op.drop_column('is_recurring')

