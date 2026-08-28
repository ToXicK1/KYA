"""Initial Agent Registry Schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-03 13:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'agents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_organization', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING_VERIFICATION', 'ACTIVE', 'SUSPENDED', 'REVOKED', name='agent_status_enum', native_enum=False), nullable=False),
        sa.Column('manifest', sa.JSON(), nullable=False),
        sa.Column('manifest_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_owner_organization'), 'agents', ['owner_organization'], unique=False)
    op.create_index(op.f('ix_agents_status'), 'agents', ['status'], unique=False)

    op.create_table(
        'public_keys',
        sa.Column('key_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('algorithm', sa.Enum('ED25519', 'ECDSA_P256', 'RSA_4096', 'SECP256K1', name='key_algorithm_enum', native_enum=False), nullable=False),
        sa.Column('pem_content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("pem_content NOT LIKE '%PRIVATE KEY%' AND pem_content NOT LIKE '%RSA PRIVATE KEY%'", name='chk_no_private_key'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key_id')
    )
    op.create_index(op.f('ix_public_keys_agent_id'), 'public_keys', ['agent_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_public_keys_agent_id'), table_name='public_keys')
    op.drop_table('public_keys')
    op.drop_index(op.f('ix_agents_status'), table_name='agents')
    op.drop_index(op.f('ix_agents_owner_organization'), table_name='agents')
    op.drop_table('agents')
