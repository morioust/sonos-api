import re


def normalize_room_name(name: str) -> str:
    """Normalize a room name for URL matching.

    Lowercase, strip leading/trailing whitespace,
    collapse whitespace and replace with underscores.
    """
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    return name
