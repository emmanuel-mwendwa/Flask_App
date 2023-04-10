"""handling rich text

Revision ID: 5685699405bd
Revises: 1427973555d9
Create Date: 2023-04-10 12:08:43.889832

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5685699405bd'
down_revision = '1427973555d9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('body_html', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_column('body_html')

    # ### end Alembic commands ###
