import itertools
import random
import sqlite3
from pathlib import Path

DB_PATH = "generations.db"

# Prompt components - mix and match for variety
CATS = [
    "cat", "kitten", "fluffy cat", "sleek cat", "fat cat", "elegant cat",
    "mysterious cat", "majestic cat", "playful kitten", "wise old cat",
]

ACCESSORIES = [
    "wearing golden blockchain necklace",
    "with bitcoin earrings",
    "wearing ethereum pendant",
    "with VR headset",
    "wearing hacker hoodie",
    "with laser eyes",
    "wearing crown made of circuit boards",
    "with glowing crypto wallet",
    "wearing NFT collar",
    "with holographic glasses",
    "wearing LED collar",
    "with mechanical wings",
    "wearing space helmet",
    "with diamond claws",
    "wearing ninja mask",
    "",  # no accessory
]

STYLES = [
    "cyberpunk style",
    "anime style",
    "realistic photography",
    "neon art style",
    "vaporwave aesthetic",
    "pixel art style",
    "oil painting style",
    "watercolor style",
    "3D render",
    "comic book style",
    "synthwave style",
    "steampunk style",
    "minimalist style",
    "psychedelic art",
    "low poly art",
    "ukiyo-e japanese art",
]

COLORS = [
    "golden and purple colors",
    "neon pink and blue",
    "green matrix colors",
    "orange and black",
    "silver and cyan",
    "red and gold",
    "black and neon green",
    "white and holographic",
    "rainbow iridescent",
    "dark purple and gold",
    "electric blue",
    "sunset orange and pink",
]

BACKGROUNDS = [
    "blockchain network background",
    "crypto trading charts background",
    "neon city skyline",
    "digital matrix rain",
    "space with galaxies",
    "abstract geometric shapes",
    "futuristic server room",
    "glowing circuit board",
    "tokyo street at night",
    "floating in cyberspace",
    "ancient temple with tech",
    "underwater tech city",
    "",  # no specific background
]

QUALITY = [
    "4k, highly detailed",
    "8k, ultra detailed",
    "masterpiece, best quality",
    "photorealistic, sharp focus",
    "cinematic lighting, detailed",
    "studio lighting, professional",
]


def init_db():
    """Initialize SQLite database for tracking generations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def generate_all_prompts():
    """Generate all possible prompt combinations."""
    prompts = []
    for cat, accessory, style, color, bg, quality in itertools.product(
        CATS, ACCESSORIES, STYLES, COLORS, BACKGROUNDS, QUALITY
    ):
        parts = [f"a {cat}"]
        if accessory:
            parts.append(accessory)
        parts.extend([style, color])
        if bg:
            parts.append(bg)
        parts.append(quality)

        prompt = ", ".join(parts)
        prompts.append(prompt)

    return prompts


def seed_database(shuffle: bool = True):
    """Populate database with all prompt combinations."""
    init_db()
    prompts = generate_all_prompts()

    if shuffle:
        random.shuffle(prompts)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert prompts, ignore if already exists
    for prompt in prompts:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO generations (prompt) VALUES (?)",
                (prompt,)
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()

    # Get stats
    cursor.execute("SELECT COUNT(*) FROM generations")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'completed'")
    completed = cursor.fetchone()[0]

    conn.close()

    print(f"Database seeded: {total} total prompts, {pending} pending, {completed} completed")
    return total


def get_next_prompt():
    """Get next pending prompt from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, prompt FROM generations
        WHERE status = 'pending'
        ORDER BY id
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"id": result[0], "prompt": result[1]}
    return None


def mark_in_progress(prompt_id: int):
    """Mark a prompt as in progress."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'in_progress' WHERE id = ?",
        (prompt_id,)
    )
    conn.commit()
    conn.close()


def mark_completed(prompt_id: int, filename: str):
    """Mark a prompt as completed with the output filename."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE generations
           SET status = 'completed', filename = ?, completed_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (filename, prompt_id)
    )
    conn.commit()
    conn.close()


def mark_failed(prompt_id: int):
    """Mark a prompt as failed (will be retried)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'pending' WHERE id = ?",
        (prompt_id,)
    )
    conn.commit()
    conn.close()


def get_stats():
    """Get generation statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM generations")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'in_progress'")
    in_progress = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "in_progress": in_progress,
        "progress_percent": (completed / total * 100) if total > 0 else 0
    }


def reset_in_progress():
    """Reset any 'in_progress' items back to 'pending' (for crash recovery)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'pending' WHERE status = 'in_progress'"
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        print(f"Reset {affected} interrupted generations back to pending")
    return affected


if __name__ == "__main__":
    # Show what we can generate
    total = len(CATS) * len(ACCESSORIES) * len(STYLES) * len(COLORS) * len(BACKGROUNDS) * len(QUALITY)
    print(f"Possible combinations: {total:,}")
    print(f"\nComponents:")
    print(f"  - Cats: {len(CATS)}")
    print(f"  - Accessories: {len(ACCESSORIES)}")
    print(f"  - Styles: {len(STYLES)}")
    print(f"  - Colors: {len(COLORS)}")
    print(f"  - Backgrounds: {len(BACKGROUNDS)}")
    print(f"  - Quality tags: {len(QUALITY)}")

    print(f"\nExample prompts:")
    prompts = generate_all_prompts()
    for p in random.sample(prompts, min(5, len(prompts))):
        print(f"  - {p[:100]}...")
