"""Create the Phase 0 migration baseline.

Revision ID: 20260821_0001
Revises: None
"""

from collections.abc import Sequence

revision: str = "20260821_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the migration chain without premature domain tables."""


def downgrade() -> None:
    """Remove the baseline revision marker."""

