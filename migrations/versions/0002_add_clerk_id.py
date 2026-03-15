"""Add clerk_id to users table for Clerk authentication integration.

Revision ID: 0002_add_clerk_id
Revises: 0001_init_schema
Create Date: 2026-03-15
"""

from __future__ import annotations

from alembic import op

revision = "0002_add_clerk_id"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS clerk_id TEXT UNIQUE;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_users_clerk_id ON users(clerk_id)
        WHERE clerk_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_clerk_id;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS clerk_id;")
