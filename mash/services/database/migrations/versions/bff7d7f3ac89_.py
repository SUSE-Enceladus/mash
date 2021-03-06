"""empty message

Revision ID: bff7d7f3ac89
Revises: 
Create Date: 2019-09-26 14:55:04.601841

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bff7d7f3ac89'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.create_table('azure_account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('region', sa.String(length=32), nullable=False),
    sa.Column('source_container', sa.String(length=64), nullable=False),
    sa.Column('source_resource_group', sa.String(length=90), nullable=False),
    sa.Column('source_storage_account', sa.String(length=24), nullable=False),
    sa.Column('destination_container', sa.String(length=64), nullable=False),
    sa.Column('destination_resource_group', sa.String(length=90), nullable=False),
    sa.Column('destination_storage_account', sa.String(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'user_id', name='_azure_account_user_uc')
    )
    op.create_table('ec2_group',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'user_id', name='_ec2_group_user_uc')
    )
    op.create_table('gce_account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('bucket', sa.String(length=222), nullable=False),
    sa.Column('region', sa.String(length=32), nullable=False),
    sa.Column('testing_account', sa.String(length=64), nullable=True),
    sa.Column('is_publishing_account', sa.Boolean(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'user_id', name='_gce_account_user_uc')
    )
    op.create_table('job',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.String(length=40), nullable=False),
    sa.Column('last_service', sa.String(length=16), nullable=False),
    sa.Column('utctime', sa.String(length=32), nullable=False),
    sa.Column('image', sa.String(length=128), nullable=False),
    sa.Column('download_url', sa.String(length=128), nullable=False),
    sa.Column('cloud_architecture', sa.String(length=8), nullable=True),
    sa.Column('profile', sa.String(length=32), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.Column('token_type', sa.String(length=10), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expires', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_jti'), 'token', ['jti'], unique=False)
    op.create_table('ec2_account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('partition', sa.String(length=10), nullable=False),
    sa.Column('region', sa.String(length=32), nullable=False),
    sa.Column('subnet', sa.String(length=32), nullable=True),
    sa.Column('group_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['ec2_group.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'user_id', name='_ec2_account_user_uc')
    )
    op.create_table('ec2_region',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.Column('helper_image', sa.String(length=32), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['ec2_account.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ec2_region')
    op.drop_table('ec2_account')
    op.drop_index(op.f('ix_token_jti'), table_name='token')
    op.drop_table('token')
    op.drop_table('job')
    op.drop_table('gce_account')
    op.drop_table('ec2_group')
    op.drop_table('azure_account')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    # ### end Alembic commands ###
