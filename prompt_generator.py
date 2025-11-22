import itertools
import random
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION - Choose which generator to use (from .env)
# =============================================================================
ACTIVE_THEME = os.getenv("ACTIVE_THEME", "cats")  # Options: "cats", "dogs"

# =============================================================================
# THEME DEFINITIONS
# =============================================================================

THEMES = {
    "cats": {
        "name": "CCats",
        "app_name": "CCats",
        "db_path": "generations_cats.db",
        "output_prefix": "cat",
        "subjects": [
            "cat", "kitten", "fluffy cat", "sleek cat", "fat cat", "elegant cat",
            "mysterious cat", "majestic cat", "playful kitten", "wise old cat",
        ],
        "accessories": [
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
        ],
    },
    "dogs": {
        "name": "CDogs",
        "app_name": "CDogs",
        "db_path": "generations_dogs.db",
        "output_prefix": "dog",
        "subjects": [
            "dog", "puppy", "fluffy dog", "golden retriever", "husky", "corgi",
            "german shepherd", "poodle", "shiba inu", "labrador",
            "french bulldog", "beagle", "dachshund", "border collie",
        ],
        "accessories": [
            "wearing golden blockchain collar",
            "with bitcoin tag",
            "wearing ethereum bandana",
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
            "with diamond teeth",
            "wearing superhero cape",
            "with rocket backpack",
            "",  # no accessory
        ],
    },
}

# Shared components (same for all themes)
SHARED_STYLES = [
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

SHARED_COLORS = [
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

SHARED_BACKGROUNDS = [
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

SHARED_QUALITY = [
    "4k, highly detailed",
    "8k, ultra detailed",
    "masterpiece, best quality",
    "photorealistic, sharp focus",
    "cinematic lighting, detailed",
    "studio lighting, professional",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_theme():
    """Get the currently active theme configuration."""
    if ACTIVE_THEME not in THEMES:
        raise ValueError(f"Unknown theme: {ACTIVE_THEME}. Available: {list(THEMES.keys())}")
    return THEMES[ACTIVE_THEME]


def get_db_path():
    """Get database path for current theme."""
    return get_theme()["db_path"]


def get_app_name():
    """Get app name for ARKIV uploads."""
    return get_theme()["app_name"]


def get_output_prefix():
    """Get output filename prefix."""
    return get_theme()["output_prefix"]


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def init_db():
    """Initialize SQLite database for tracking generations."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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
    """Generate all possible prompt combinations for current theme."""
    theme = get_theme()
    subjects = theme["subjects"]
    accessories = theme["accessories"]

    prompts = []
    for subject, accessory, style, color, bg, quality in itertools.product(
        subjects, accessories, SHARED_STYLES, SHARED_COLORS, SHARED_BACKGROUNDS, SHARED_QUALITY
    ):
        parts = [f"a {subject}"]
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

    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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

    theme = get_theme()
    print(f"[{theme['name']}] Database seeded: {total} total prompts, {pending} pending, {completed} completed")
    return total


def get_next_prompt():
    """Get next pending prompt from database."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'in_progress' WHERE id = ?",
        (prompt_id,)
    )
    conn.commit()
    conn.close()


def mark_completed(prompt_id: int, filename: str):
    """Mark a prompt as completed with the output filename."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'pending' WHERE id = ?",
        (prompt_id,)
    )
    conn.commit()
    conn.close()


def get_stats():
    """Get generation statistics."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM generations")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'in_progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'generated'")
    generated = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "in_progress": in_progress,
        "generated": generated,
        "progress_percent": (completed / total * 100) if total > 0 else 0
    }


def reset_in_progress():
    """Reset any 'in_progress' items back to 'pending' (for crash recovery).

    Note: This is the legacy function. For threaded mode, use reset_interrupted().
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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


# =============================================================================
# THREADED MODE FUNCTIONS
# =============================================================================

def mark_generated(prompt_id: int, filename: str):
    """Mark a prompt as generated (image created, ready for upload)."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE generations SET status = 'generated', filename = ? WHERE id = ?",
        (filename, prompt_id)
    )
    conn.commit()
    conn.close()


def get_next_generated():
    """Get next item ready for upload (status='generated')."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, prompt, filename FROM generations
        WHERE status = 'generated'
        ORDER BY id
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"id": result[0], "prompt": result[1], "filename": result[2]}
    return None


def get_generated_count():
    """Get count of items waiting for upload."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'generated'")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def reset_interrupted():
    """Reset interrupted items for crash recovery (threaded mode).

    - 'in_progress' -> 'pending' (generation was interrupted)
    - 'generated' items stay as-is (image exists, just needs upload)
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    # Reset interrupted generations
    cursor.execute(
        "UPDATE generations SET status = 'pending' WHERE status = 'in_progress'"
    )
    gen_reset = cursor.rowcount

    # Count items waiting for upload
    cursor.execute("SELECT COUNT(*) FROM generations WHERE status = 'generated'")
    pending_uploads = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    if gen_reset > 0:
        print(f"Reset {gen_reset} interrupted generations back to pending")
    if pending_uploads > 0:
        print(f"Found {pending_uploads} images waiting for upload")

    return {"gen_reset": gen_reset, "pending_uploads": pending_uploads}


def list_themes():
    """List all available themes."""
    print("Available themes:")
    for key, theme in THEMES.items():
        marker = " (ACTIVE)" if key == ACTIVE_THEME else ""
        subjects_count = len(theme["subjects"])
        accessories_count = len(theme["accessories"])
        total = subjects_count * accessories_count * len(SHARED_STYLES) * len(SHARED_COLORS) * len(SHARED_BACKGROUNDS) * len(SHARED_QUALITY)
        print(f"  - {key}: {theme['name']} ({total:,} combinations){marker}")


if __name__ == "__main__":
    import sys

    # Allow theme selection via command line
    if len(sys.argv) > 1:
        requested_theme = sys.argv[1]
        if requested_theme in THEMES:
            ACTIVE_THEME = requested_theme
        elif requested_theme == "--list":
            list_themes()
            sys.exit(0)
        else:
            print(f"Unknown theme: {requested_theme}")
            list_themes()
            sys.exit(1)

    theme = get_theme()

    # Show what we can generate
    subjects = theme["subjects"]
    accessories = theme["accessories"]
    total = len(subjects) * len(accessories) * len(SHARED_STYLES) * len(SHARED_COLORS) * len(SHARED_BACKGROUNDS) * len(SHARED_QUALITY)

    print(f"Theme: {theme['name']}")
    print(f"App name: {theme['app_name']}")
    print(f"Database: {theme['db_path']}")
    print(f"Output prefix: {theme['output_prefix']}")
    print(f"\nPossible combinations: {total:,}")
    print(f"\nComponents:")
    print(f"  - Subjects: {len(subjects)}")
    print(f"  - Accessories: {len(accessories)}")
    print(f"  - Styles: {len(SHARED_STYLES)}")
    print(f"  - Colors: {len(SHARED_COLORS)}")
    print(f"  - Backgrounds: {len(SHARED_BACKGROUNDS)}")
    print(f"  - Quality tags: {len(SHARED_QUALITY)}")

    print(f"\nExample prompts:")
    prompts = generate_all_prompts()
    for p in random.sample(prompts, min(5, len(prompts))):
        print(f"  - {p[:100]}...")

    print(f"\n" + "=" * 40)
    list_themes()
