"""account authentication

Revision ID: 678fe5628061
Revises: b9862ec5d3f7
Create Date: 2023-02-06 10:08:10.974063

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '678fe5628061'
down_revision = 'b9862ec5d3f7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confirmed', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('confirmed')

    # ### end Alembic commands ###
