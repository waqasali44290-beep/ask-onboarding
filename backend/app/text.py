"""Small text helpers shared by routes."""


def shorten(text: str, limit: int) -> str:
    """First `limit` characters of `text`, cut at a word boundary, with … when cut."""
    text = " ".join(text.split())  # collapse newlines and double spaces
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"
