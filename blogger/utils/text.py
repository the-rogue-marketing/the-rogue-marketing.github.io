"""
Text processing utilities for the Blogger Agent.
"""

import re
import unicodedata
from html import unescape


def slugify(text: str, max_length: int = 80) -> str:
    """
    Convert a text string to a URL-safe slug.

    Args:
        text: The text to slugify.
        max_length: Maximum length of the slug.

    Returns:
        A lowercase, hyphenated slug string.
    """
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    text = text.lower()

    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)

    # Truncate to max length (don't break mid-word)
    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0]

    return text


def clean_text(text: str) -> str:
    """
    Clean raw text by removing HTML tags and normalizing whitespace.

    Args:
        text: The raw text to clean.

    Returns:
        Cleaned text string.
    """
    if not text:
        return ""

    # Unescape HTML entities
    text = unescape(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """
    Extract keywords from text using simple word frequency.

    Args:
        text: Input text.
        min_length: Minimum word length to consider.

    Returns:
        List of keywords sorted by frequency.
    """
    # Common stop words to filter out
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "this", "that",
        "these", "those", "it", "its", "they", "them", "their", "we", "our",
        "you", "your", "he", "she", "his", "her", "not", "no", "nor", "so",
        "if", "then", "than", "too", "very", "just", "about", "up", "out",
        "new", "also", "more", "some", "any", "all", "most", "other", "into",
        "over", "after", "before", "between", "under", "through", "during",
        "each", "few", "both", "such", "while", "where", "when", "who",
        "what", "which", "how", "why", "because", "since", "until", "here",
        "there", "many", "much", "only", "still", "even", "back", "now",
        "get", "got", "one", "two", "said", "says", "like", "make", "way",
    }

    # Tokenize and clean
    words = re.findall(r"[a-zA-Z]+", text.lower())
    words = [w for w in words if len(w) >= min_length and w not in stop_words]

    # Count frequency
    freq: dict[str, int] = {}
    for word in words:
        freq[word] = freq.get(word, 0) + 1

    # Sort by frequency descending
    sorted_words = sorted(freq.keys(), key=lambda w: freq[w], reverse=True)

    return sorted_words[:20]


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rsplit(" ", 1)[0] + "..."
