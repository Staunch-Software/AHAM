"""callers: languages (branches and callers), a branch's usual caller, callers marked absent for a day

Revision ID: d4e6a9c2f1b7
Revises: c3d5f8a1e6b2
Create Date: 2026-11-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e6a9c2f1b7'
down_revision: Union[str, None] = 'c3d5f8a1e6b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# the language of a branch, from its region's name (editable on the Callers page)
REGION_LANGUAGE = [("AP & TG", "Telugu"), ("Andhra%", "Telugu"), ("Karnataka%", "Kannada"), ("Chennai%", "Tamil"),
                   ("RoTN%", "Tamil")]


def upgrade() -> None:
    op.add_column('branches', sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), server_default='[]',
                                        nullable=False))
    op.add_column('branches', sa.Column('usual_caller_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_branches_usual_caller', 'branches', 'users', ['usual_caller_id'], ['id'])
    op.add_column('users', sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), server_default='[]',
                                     nullable=False))
    op.create_table(
        'caller_absences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('caller_id', sa.UUID(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('marked_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['caller_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('caller_id', 'day', name='uq_caller_absences_caller_day'),
    )
    op.create_index('ix_caller_absences_company_day', 'caller_absences', ['company_id', 'day'])
    for pattern, language in REGION_LANGUAGE:
        op.execute(sa.text(
            "UPDATE branches SET languages = CAST(:langs AS jsonb) FROM regions "
            "WHERE regions.id = branches.region_id AND regions.name LIKE :pattern AND branches.languages = '[]'::jsonb"
        ).bindparams(langs=f'["{language}"]', pattern=pattern))


def downgrade() -> None:
    op.drop_index('ix_caller_absences_company_day', table_name='caller_absences')
    op.drop_table('caller_absences')
    op.drop_column('users', 'languages')
    op.drop_constraint('fk_branches_usual_caller', 'branches', type_='foreignkey')
    op.drop_column('branches', 'usual_caller_id')
    op.drop_column('branches', 'languages')
