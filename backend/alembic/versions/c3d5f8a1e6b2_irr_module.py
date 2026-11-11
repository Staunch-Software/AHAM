"""weighted average IRR: disbursement register and IRR settings

Revision ID: c3d5f8a1e6b2
Revises: a1c4e7f2b9d0
Create Date: 2026-11-09 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d5f8a1e6b2'
down_revision: Union[str, None] = 'a1c4e7f2b9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'irr_disbursements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('dedup_key', sa.String(length=200), nullable=False),
        sa.Column('loan_account', sa.String(length=50), nullable=False),
        sa.Column('disbursement_ref', sa.String(length=50), nullable=True),
        sa.Column('disbursement_date', sa.Date(), nullable=False),
        sa.Column('product', sa.String(length=100), nullable=False),
        sa.Column('product_key', sa.String(length=100), nullable=False),
        sa.Column('product_class', sa.String(length=3), nullable=False),
        sa.Column('branch_id', sa.UUID(), nullable=False),
        sa.Column('region_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(16, 2), nullable=False),
        sa.Column('tenure_months', sa.Numeric(8, 2), nullable=True),
        sa.Column('roi', sa.Numeric(7, 4), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('excluded', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('exception', sa.String(length=200), nullable=True),
        sa.Column('corrected_by', sa.UUID(), nullable=True),
        sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('import_batch_id', sa.UUID(), nullable=True),
        sa.Column('source_row', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id']),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'dedup_key', name='uq_irr_disbursement_key'),
    )
    op.create_index('ix_irr_disbursements_company_day', 'irr_disbursements', ['company_id', 'disbursement_date'])
    op.create_index('ix_irr_disbursements_branch_id', 'irr_disbursements', ['branch_id'])
    op.create_table(
        'irr_settings',
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('company_id'),
    )


def downgrade() -> None:
    op.drop_table('irr_settings')
    op.drop_index('ix_irr_disbursements_branch_id', table_name='irr_disbursements')
    op.drop_index('ix_irr_disbursements_company_day', table_name='irr_disbursements')
    op.drop_table('irr_disbursements')
