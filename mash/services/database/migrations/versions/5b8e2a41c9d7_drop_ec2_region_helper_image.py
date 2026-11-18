"""drop ec2_region helper_image

The helper image of additional regions was deprecated and ignored,
images are written directly to an EBS snapshot.

Revision ID: 5b8e2a41c9d7
Revises: 3f1c9d7a2b64
Create Date: 2026-11-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b8e2a41c9d7'
down_revision = '3f1c9d7a2b64'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ec2_region') as batch_op:
        batch_op.drop_column('helper_image')


def downgrade():
    with op.batch_alter_table('ec2_region') as batch_op:
        batch_op.add_column(
            sa.Column('helper_image', sa.String(length=32), nullable=True)
        )
