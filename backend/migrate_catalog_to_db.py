#!/usr/bin/env python3
"""
Migration script to move static emoji catalog to database.
Adds catalog emojis as submissions owned by tigerdumas@gmail.com
"""

from sqlmodel import Session, select

from app.core.security import hash_password
from app.db import engine, init_db
from app.models import EmojiSubmission, User

CATALOG_EMOJIS = [
    {
        "symbol": "😀",
        "title": "Grinning Face",
        "description": "A classic smile conveying general happiness.",
        "category": "Smileys",
        "keywords": ["happy", "smile", "joy"],
    },
    {
        "symbol": "🚀",
        "title": "Rocket",
        "description": "Symbolizes fast progress or launching new ideas.",
        "category": "Travel",
        "keywords": ["launch", "startup", "space"],
    },
    {
        "symbol": "🎉",
        "title": "Party Popper",
        "description": "Used to celebrate special occasions and wins.",
        "category": "Activities",
        "keywords": ["celebration", "party", "congrats"],
    },
    {
        "symbol": "🤖",
        "title": "Robot",
        "description": "Represents technology, automation, or playful robotics.",
        "category": "Objects",
        "keywords": ["bot", "automation", "ai"],
    },
    {
        "symbol": "🌈",
        "title": "Rainbow",
        "description": "Often used for joy, hope, and inclusivity.",
        "category": "Nature",
        "keywords": ["hope", "color", "pride"],
    },
]

OWNER_EMAIL = "tigerdumas@gmail.com"


def migrate_catalog():
    """Migrate static catalog emojis to database."""
    init_db()

    with Session(engine) as session:
        # Check if user exists, create if not
        user = session.exec(select(User).where(User.email == OWNER_EMAIL)).first()

        if not user:
            print(f"Creating user: {OWNER_EMAIL}")
            user = User(
                email=OWNER_EMAIL,
                hashed_password=hash_password("ChangeMe123!"),
                display_name="Tiger Dumas",
                is_active=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✓ User created with ID: {user.id}")
        else:
            print(f"✓ User already exists with ID: {user.id}")

        # Add catalog emojis
        added_count = 0
        skipped_count = 0

        for emoji_data in CATALOG_EMOJIS:
            # Check if emoji already exists
            existing = session.exec(
                select(EmojiSubmission).where(
                    EmojiSubmission.symbol == emoji_data["symbol"],
                    EmojiSubmission.title == emoji_data["title"],
                )
            ).first()

            if existing:
                print(f"⊘ Skipping '{emoji_data['title']}' - already exists")
                skipped_count += 1
                continue

            # Create emoji submission
            submission = EmojiSubmission(
                symbol=emoji_data["symbol"],
                title=emoji_data["title"],
                description=emoji_data["description"],
                category=emoji_data["category"],
                submitter_email=OWNER_EMAIL,
                submitter_id=user.id,
            )
            submission.keyword_list = emoji_data["keywords"]

            session.add(submission)
            print(f"✓ Added '{emoji_data['title']}' ({emoji_data['symbol']})")
            added_count += 1

        session.commit()

        print(f"\n{'='*50}")
        print(f"Migration complete!")
        print(f"  Added: {added_count} emojis")
        print(f"  Skipped: {skipped_count} emojis")
        print(f"  Owner: {OWNER_EMAIL} (ID: {user.id})")
        print(f"{'='*50}")


if __name__ == "__main__":
    migrate_catalog()
