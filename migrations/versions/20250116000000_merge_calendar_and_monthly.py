"""merge calendar and monthly pattern branches

Revision ID: 20250116000000
Revises: ('20250101000000', '20250115000000')
Create Date: 2025-01-16 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250116000000'
down_revision = ('20250101000000', '20250115000000')  # Both heads
branch_labels = None
depends_on = None


def upgrade():
    # Merge migration - no changes needed, just merges the branches
    pass


def downgrade():
    # Merge migration - no changes needed
    pass

