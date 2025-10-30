"""add unique parent+due index

Revision ID: 20251031004134
Revises: 20251030230756
Create Date: 2025-10-31 00:41:34

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251031004134'
down_revision = '20251030230756'
branch_labels = None
depends_on = None


def upgrade():
    # Create a unique index to prevent duplicate instances for same parent and due date
    op.create_index('uq_task_parent_due', 'task', ['parent_recurring_id', 'due_date'], unique=True)


def downgrade():
    op.drop_index('uq_task_parent_due', table_name='task')
