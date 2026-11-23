"""entry documents: KYC, income proof, property documents and certificates

Revision ID: e5f7b1d3a9c8
Revises: d4e6a9c2f1b7
Create Date: 2026-11-20 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5f7b1d3a9c8'
down_revision: Union[str, None] = 'd4e6a9c2f1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entry_documents',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('company_id', sa.UUID(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('entry_id', sa.UUID(), sa.ForeignKey('sankalp_entries.id'), nullable=False),
        sa.Column('uploaded_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('sub_type', sa.String(100), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_entry_documents_company_id', 'entry_documents', ['company_id'])
    op.create_index('ix_entry_documents_entry_id', 'entry_documents', ['entry_id'])


def downgrade() -> None:
    op.drop_index('ix_entry_documents_entry_id', table_name='entry_documents')
    op.drop_index('ix_entry_documents_company_id', table_name='entry_documents')
    op.drop_table('entry_documents')
