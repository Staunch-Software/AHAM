"""client feedback: where an entry came from (the phone or a bulk upload)

Revision ID: a1c4e7f2b9d0
Revises: 7b3e9c41d2a8
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7f2b9d0'
down_revision: Union[str, None] = '7b3e9c41d2a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sankalp_entries', sa.Column('source', sa.String(length=10), server_default='app', nullable=False))
    op.add_column('sankalp_entries', sa.Column('import_batch_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_entry_import_batch', 'sankalp_entries', 'import_batches', ['import_batch_id'], ['id'])
    # the call outcome "RNR" is now written out in full
    op.execute("UPDATE call_attempts SET outcome = 'Rang, no answer' WHERE outcome = 'RNR'")
    op.execute("UPDATE entry_events SET detail = jsonb_set(detail, '{outcome}', '\"Rang, no answer\"') "
               "WHERE kind = 'call' AND detail->>'outcome' = 'RNR'")


def downgrade() -> None:
    op.execute("UPDATE call_attempts SET outcome = 'RNR' WHERE outcome = 'Rang, no answer'")
    op.drop_constraint('fk_entry_import_batch', 'sankalp_entries', type_='foreignkey')
    op.drop_column('sankalp_entries', 'import_batch_id')
    op.drop_column('sankalp_entries', 'source')
