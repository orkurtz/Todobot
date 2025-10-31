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
    # Remove existing duplicates, keeping the lowest id per (parent_recurring_id, due_date)
    op.execute(
        """
        WITH dups AS (
          SELECT
            id,
            ROW_NUMBER() OVER (
              PARTITION BY parent_recurring_id, due_date
              ORDER BY id
            ) AS rn
          FROM task
          WHERE parent_recurring_id IS NOT NULL
            AND due_date IS NOT NULL
        )
        DELETE FROM task t
        USING dups
        WHERE t.id = dups.id
          AND dups.rn > 1;
        """
    )

    # Create a unique index to prevent duplicate instances for same parent and due date
    op.create_index('uq_task_parent_due', 'task', ['parent_recurring_id', 'due_date'], unique=True)


def downgrade():
    op.drop_index('uq_task_parent_due', table_name='task')
