"""Extend auth_users with email, role, and last_login_at_utc.

Adds fields needed for user management and future SSO/RBAC extensibility.
"""

from __future__ import annotations

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        'ALTER TABLE "auth_users" ADD COLUMN IF NOT EXISTS "email" '
        "VARCHAR(256)"
    )
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "ix_auth_users_email" '
        'ON "auth_users" ("email") WHERE "email" IS NOT NULL'
    )
    op.execute(
        'ALTER TABLE "auth_users" ADD COLUMN IF NOT EXISTS "role" '
        "VARCHAR(32) NOT NULL DEFAULT 'member'"
    )
    op.execute(
        'ALTER TABLE "auth_users" ADD COLUMN IF NOT EXISTS "last_login_at_utc" '
        "TIMESTAMP"
    )
    # Backfill existing users as admin (the seed admin user)
    op.execute(
        "UPDATE \"auth_users\" SET \"role\" = 'admin' WHERE \"role\" = 'member'"
    )


def downgrade() -> None:
    op.execute('ALTER TABLE "auth_users" DROP COLUMN IF EXISTS "last_login_at_utc"')
    op.execute('ALTER TABLE "auth_users" DROP COLUMN IF EXISTS "role"')
    op.execute('DROP INDEX IF EXISTS "ix_auth_users_email"')
    op.execute('ALTER TABLE "auth_users" DROP COLUMN IF EXISTS "email"')
