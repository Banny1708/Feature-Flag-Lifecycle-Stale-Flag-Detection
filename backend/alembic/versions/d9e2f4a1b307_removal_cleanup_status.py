"""removal cleanup_status (Phase 3: real Piranha adapter outcome)

Revision ID: d9e2f4a1b307
Revises: 86cfdea61941
Create Date: 2026-10-25

Adds a nullable `cleanup_status` column to `removal_operations` recording the
verified Piranha adapter outcome: DRY_RUN, APPLIED, NO_CHANGES, UNSUPPORTED.
NULL for rows created before Phase 3. Additive + nullable: safe on
PostgreSQL and SQLite (batch mode), existing history untouched.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd9e2f4a1b307'
down_revision: Union[str, None] = '86cfdea61941'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('removal_operations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cleanup_status', sa.String(length=32),
                                      nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('removal_operations', schema=None) as batch_op:
        batch_op.drop_column('cleanup_status')
