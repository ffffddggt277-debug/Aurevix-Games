"""Versioned metadata, published only after approval."""
from alembic import op
import sqlalchemy as sa
revision='002'
down_revision='001'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('versions',sa.Column('metadata_json',sa.Text(),nullable=False,server_default='{}'))
def downgrade():
    op.drop_column('versions','metadata_json')
