from __future__ import annotations

from app.schemas import Emoji


EMOJI_CATALOG: list[Emoji] = [
    Emoji(
        id=1,
        symbol="😀",
        title="Grinning Face",
        description="A classic smile conveying general happiness.",
        category="Smileys",
        keywords=["happy", "smile", "joy"],
    ),
    Emoji(
        id=2,
        symbol="🚀",
        title="Rocket",
        description="Symbolizes fast progress or launching new ideas.",
        category="Travel",
        keywords=["launch", "startup", "space"],
    ),
    Emoji(
        id=3,
        symbol="🎉",
        title="Party Popper",
        description="Used to celebrate special occasions and wins.",
        category="Activities",
        keywords=["celebration", "party", "congrats"],
    ),
    Emoji(
        id=4,
        symbol="🤖",
        title="Robot",
        description="Represents technology, automation, or playful robotics.",
        category="Objects",
        keywords=["bot", "automation", "ai"],
    ),
    Emoji(
        id=5,
        symbol="🌈",
        title="Rainbow",
        description="Often used for joy, hope, and inclusivity.",
        category="Nature",
        keywords=["hope", "color", "pride"],
    ),
]


def next_catalog_id() -> int:
    return max((emoji.id for emoji in EMOJI_CATALOG), default=0) + 1


__all__ = ["EMOJI_CATALOG", "next_catalog_id"]
