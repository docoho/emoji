"""drop unused collectionemoji.position column

Revision ID: 20260513_0001
Revises: 20260429_0001
Create Date: 2026-05-13 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260513_0001"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Introspect before dropping: the position column/index may already be
    # absent if the legacy prod DB was built before they existed, or if the
    # schema was created from the current SQLModel metadata (e.g. in tests).
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("collectionemoji")}
    if "idx_collection_emoji_collection_position" in existing_indexes:
        op.drop_index("idx_collection_emoji_collection_position", table_name="collectionemoji")

    existing_columns = {col["name"] for col in inspector.get_columns("collectionemoji")}
    if "position" in existing_columns:
        # SQLite can't ALTER ... DROP COLUMN directly; batch mode rewrites the table.
        with op.batch_alter_table("collectionemoji") as batch_op:
            batch_op.drop_column("position")


def downgrade() -> None:
    with op.batch_alter_table("collectionemoji") as batch_op:
        batch_op.add_column(sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(
        "idx_collection_emoji_collection_position",
        "collectionemoji",
        ["collection_id", "position"],
    )
