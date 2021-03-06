"""Add email fields in commits table

Revision ID: 2fb094745389
Revises: 2b91386d1cc2
Create Date: 2016-06-19 21:39:04.808088

"""

# revision identifiers, used by Alembic.
revision = '2fb094745389'
down_revision = '2b91386d1cc2'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('commits', sa.Column('author_email_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('commits', sa.Column('committer_email_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(op.f('fk_commits_committer_email_id_emails'), 'commits', 'emails', ['committer_email_id'], ['id'])
    op.create_foreign_key(op.f('fk_commits_author_email_id_emails'), 'commits', 'emails', ['author_email_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('fk_commits_author_email_id_emails'), 'commits', type_='foreignkey')
    op.drop_constraint(op.f('fk_commits_committer_email_id_emails'), 'commits', type_='foreignkey')
    op.drop_column('commits', 'committer_email_id')
    op.drop_column('commits', 'author_email_id')
    ### end Alembic commands ###
