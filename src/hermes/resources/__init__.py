"""Resource loader for skill templates and other bundled data."""

from pathlib import Path

RESOURCES_DIR = Path(__file__).parent


def get_skill(name: str) -> str:
    """Load a skill template by name. E.g. get_skill('evaluate_stock') returns the full markdown."""
    path = RESOURCES_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill template not found: {path}")
    return path.read_text(encoding="utf-8")