"""review fixes: handling branch, expired actions, audit details, settings history, unique names

Revision ID: 7b3e9c41d2a8
Revises: 332ff8183856
Create Date: 2026-11-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7b3e9c41d2a8'
down_revision: Union[str, None] = '332ff8183856'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sankalp_entries', sa.Column('work_branch_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_entry_work_branch', 'sankalp_entries', 'branches', ['work_branch_id'], ['id'])
    op.create_index('ix_entry_company_work_branch', 'sankalp_entries', ['company_id', 'work_branch_id'],
                    postgresql_where=sa.text('work_branch_id IS NOT NULL'))
    op.add_column('sankalp_entries', sa.Column('expired_action', sa.String(length=40), nullable=True))
    op.add_column('sankalp_entries', sa.Column('expired_on', sa.Date(), nullable=True))
    op.add_column('audit_logs', sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_table(
        'settings_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('saved_by', sa.UUID(), nullable=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'effective_from', name='uq_settings_history_day'),
    )
    op.create_index('ix_settings_history_company_id', 'settings_history', ['company_id'])
    op.create_unique_constraint('uq_branch_name', 'branches', ['company_id', 'name'])
    op.create_unique_constraint('uq_region_name', 'regions', ['company_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_region_name', 'regions', type_='unique')
    op.drop_constraint('uq_branch_name', 'branches', type_='unique')
    op.drop_index('ix_settings_history_company_id', table_name='settings_history')
    op.drop_table('settings_history')
    op.drop_column('audit_logs', 'details')
    op.drop_column('sankalp_entries', 'expired_on')
    op.drop_column('sankalp_entries', 'expired_action')
    op.drop_index('ix_entry_company_work_branch', table_name='sankalp_entries')
    op.drop_constraint('fk_entry_work_branch', 'sankalp_entries', type_='foreignkey')
    op.drop_column('sankalp_entries', 'work_branch_id')
