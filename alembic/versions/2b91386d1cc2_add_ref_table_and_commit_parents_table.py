"""Add ref table and commit parents table

Revision ID: 2b91386d1cc2
Revises: 0011c7158340
Create Date: 2016-06-19 20:48:17.205986

"""

# revision identifiers, used by Alembic.
revision = '2b91386d1cc2'
down_revision = '0011c7158340'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('commit_parent',
    sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['commits.id'], name=op.f('fk_commit_parent_child_id_commits')),
    sa.ForeignKeyConstraint(['parent_id'], ['commits.id'], name=op.f('fk_commit_parent_parent_id_commits')),
    sa.PrimaryKeyConstraint('child_id', 'parent_id', name=op.f('pk_commit_parent'))
    )
    op.create_table('refs',
    sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('added_at', sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
    sa.Column('head_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.ForeignKeyConstraint(['head_id'], ['commits.id'], name=op.f('fk_refs_head_id_commits')),
    sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], name=op.f('fk_refs_repo_id_repos')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refs'))
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('refs')
    op.drop_table('commit_parent')
    ### end Alembic commands ###