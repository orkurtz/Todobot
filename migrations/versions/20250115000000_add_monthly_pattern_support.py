"""add monthly pattern support

Revision ID: 20250115000000
Revises: 20251031004134
Create Date: 2025-01-15 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250115000000'
down_revision = '20251031004134'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recurrence_day_of_month', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('recurrence_day_of_month')

