"""make ec2_region helper_image optional

Images are written directly to an EBS snapshot, the helper image is no
longer used for image creation.

Revision ID: 3f1c9d7a2b64
Revises: 89a2cf1d3255
Create Date: 2026-10-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f1c9d7a2b64'
down_revision = '89a2cf1d3255'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ec2_region') as batch_op:
        batch_op.alter_column(
            'helper_image',
            existing_type=sa.String(length=32),
            nullable=True
        )


def downgrade():
    # Regions added without a helper image cannot satisfy the constraint
    op.execute(
        "UPDATE ec2_region SET helper_image = '' WHERE helper_image IS NULL"
    )
    with op.batch_alter_table('ec2_region') as batch_op:
        batch_op.alter_column(
            'helper_image',
            existing_type=sa.String(length=32),
            nullable=False
        )
