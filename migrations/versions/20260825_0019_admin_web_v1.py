"""Record the Phase 18 admin API baseline.

Revision ID: 20260825_0019
Revises: 20260825_0018
"""

from collections.abc import Sequence

revision: str = "20260825_0019"
down_revision: str | None = "20260825_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
