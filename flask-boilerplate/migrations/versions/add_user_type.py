# migrations/versions/add_user_type.py
"""Add user type and companion access

Revision ID: 2bd94bd3e0e8  # This should be a unique ID
Revises: 1bd94bd3e0e8    # This should match your previous migration ID
Create Date: 2024-03-23 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2bd94bd3e0e8'  # This should be different from your existing migrations
down_revision = '1bd94bd3e0e8'  # This should match your previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Create enum type for UserType
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('user_type', sa.String(20), nullable=True))
    
    # Set default value for existing users
    op.execute("UPDATE users SET user_type = 'PATIENT' WHERE user_type IS NULL")
    
    # Make column not nullable
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('user_type', nullable=False)

    # Create companion_access table
    op.create_table('companion_access',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('companion_id', sa.Integer(), nullable=False),
        sa.Column('medication_access', sa.String(20), nullable=False, server_default='NONE'),
        sa.Column('glucose_access', sa.String(20), nullable=False, server_default='NONE'),
        sa.Column('blood_pressure_access', sa.String(20), nullable=False, server_default='NONE'),
        sa.Column('export_access', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['companion_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('unique_patient_companion', 'companion_access', ['patient_id', 'companion_id'])

def downgrade():
    op.drop_table('companion_access')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('user_type')