"""Create Phase 19 immutable configuration versions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0020"
down_revision = "20260825_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "configuration_versions",
        sa.Column("namespace", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("increases_risk", sa.Boolean(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("namespace", "version", name="uq_configuration_namespace_version"),
    )


def downgrade() -> None:
    op.drop_table("configuration_versions")
