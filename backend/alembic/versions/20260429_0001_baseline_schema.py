"""baseline schema

Revision ID: 20260429_0001
Revises:
Create Date: 2026-04-29 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("google_id", sa.String(), nullable=True),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("bio", sa.String(length=280), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index("ix_user_google_id", "user", ["google_id"], unique=True)
    op.create_index("idx_user_google_id", "user", ["google_id"], unique=True)

    op.create_table(
        "collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "slug"),
    )
    op.create_index("ix_collection_owner_id", "collection", ["owner_id"])
    op.create_index("ix_collection_slug", "collection", ["slug"])
    op.create_index("idx_collection_owner_created_at", "collection", ["owner_id", "created_at"])
    op.create_index("idx_collection_owner_kind", "collection", ["owner_id", "kind"])

    op.create_table(
        "emojisubmission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("keywords", sa.String(length=512), nullable=False),
        sa.Column("submitter_email", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("submitter_id", sa.Integer(), nullable=True),
        sa.Column("moderation_status", sa.String(length=32), nullable=False),
        sa.Column("moderation_reason", sa.String(length=512), nullable=True),
        sa.Column("moderated_at", sa.DateTime(), nullable=True),
        sa.Column("moderated_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["moderated_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["submitter_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_emojisubmission_status_created",
        "emojisubmission",
        ["moderation_status", "created_at"],
    )
    op.create_index(
        "idx_emojisubmission_submitter_created",
        "emojisubmission",
        ["submitter_id", "created_at"],
    )
    op.create_index("idx_emojisubmission_category", "emojisubmission", ["category"])

    op.create_table(
        "collectionemoji",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("emoji_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.id"]),
        sa.ForeignKeyConstraint(["emoji_id"], ["emojisubmission.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "emoji_id"),
    )
    op.create_index("ix_collectionemoji_collection_id", "collectionemoji", ["collection_id"])
    op.create_index("ix_collectionemoji_emoji_id", "collectionemoji", ["emoji_id"])
    op.create_index(
        "idx_collection_emoji_collection_position",
        "collectionemoji",
        ["collection_id", "position"],
    )
    op.create_index("idx_collection_emoji_emoji_id", "collectionemoji", ["emoji_id"])

    op.create_table(
        "emojicomment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emoji_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["emoji_id"], ["emojisubmission.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emojicomment_author_id", "emojicomment", ["author_id"])
    op.create_index("ix_emojicomment_emoji_id", "emojicomment", ["emoji_id"])
    op.create_index(
        "idx_emoji_comment_author_deleted",
        "emojicomment",
        ["author_id", "deleted_at"],
    )
    op.create_index(
        "idx_emoji_comment_emoji_deleted",
        "emojicomment",
        ["emoji_id", "deleted_at"],
    )

    op.create_table(
        "emojilike",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("emoji_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["emoji_id"], ["emojisubmission.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "emoji_id"),
    )
    op.create_index("idx_emojilike_emoji_created", "emojilike", ["emoji_id", "created_at"])

    op.create_table(
        "emojireport",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emoji_id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("admin_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["emoji_id"], ["emojisubmission.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emojireport_emoji_id", "emojireport", ["emoji_id"])
    op.create_index("ix_emojireport_reporter_id", "emojireport", ["reporter_id"])
    op.create_index("idx_emoji_report_emoji_status", "emojireport", ["emoji_id", "status"])
    op.create_index(
        "idx_emoji_report_reporter_status",
        "emojireport",
        ["reporter_id", "status"],
    )
    op.create_index("idx_emoji_report_status_created", "emojireport", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("emojireport")
    op.drop_table("emojilike")
    op.drop_table("emojicomment")
    op.drop_table("collectionemoji")
    op.drop_table("emojisubmission")
    op.drop_table("collection")
    op.drop_table("user")
