"""Text normalization utilities for the Aegis Knowledge System.

Provides deterministic cleaning and standardization of raw strings extracted from
documents: unicode NFKC normalization, newline standardization, control character removal,
and quotation mark homogenization.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Control characters regex: match ASCII control characters except \t and \n
_CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Smart quotes mappings
_QUOTE_MAP = {
    "\u2018": "'",  # Left single quote
    "\u2019": "'",  # Right single quote
    "\u201a": "'",  # Single low-9 quote
    "\u201b": "'",  # Single high-reversed-9 quote
    "\u2039": "'",  # Single left-pointing angle quote
    "\u203a": "'",  # Single right-pointing angle quote
    "\u201c": '"',  # Left double quote
    "\u201d": '"',  # Right double quote
    "\u201e": '"',  # Double low-9 quote
    "\u201f": '"',  # Double high-reversed-9 quote
    "\u00ab": '"',  # Left-pointing double angle quote
    "\u00bb": '"',  # Right-pointing double angle quote
    "\u2033": '"',  # Double prime
    "\u2032": "'",  # Prime
    "`": "'",       # Backtick used as quote
}


def strip_control_characters(text: str) -> str:
    """Remove non-printable control characters from text, preserving newlines and tabs.

    Args:
        text: Input string.

    Returns:
        Cleaned string without control characters.
    """
    if not text:
        return ""
    return _CONTROL_CHAR_REGEX.sub("", text)


def standardize_quotes(text: str) -> str:
    """Convert typographic/curly quotation marks and primes into ASCII single or double quotes.

    Args:
        text: Input string with potential smart quotes.

    Returns:
        Standardized string with ASCII quotes.
    """
    if not text:
        return ""
    for orig, target in _QUOTE_MAP.items():
        if orig in text:
            text = text.replace(orig, target)
    return text


def normalize_line_endings(text: str) -> str:
    """Normalize Windows CRLF and Mac CR line endings to Unix LF.

    Args:
        text: Input string.

    Returns:
        String with uniform LF line breaks.
    """
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive spaces/tabs into a single space while keeping line structures.

    Lines with only spaces will become empty lines, and consecutive empty lines
    are reduced to at most two newlines (paragraph boundary).

    Args:
        text: Input string.

    Returns:
        Whitespace-normalized string.
    """
    if not text:
        return ""

    # Replace horizontal whitespace runs (spaces, tabs) with a single space
    lines = []
    for line in text.split("\n"):
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(cleaned_line)

    # Join and reduce multiple blank lines to max 2
    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def clean_line(line: str) -> str:
    """Clean and standardize a single line of text.

    Args:
        line: Single text line.

    Returns:
        Stripped, normalized line.
    """
    if not line:
        return ""
    norm = unicodedata.normalize("NFKC", line)
    norm = strip_control_characters(norm)
    norm = standardize_quotes(norm)
    norm = re.sub(r"[ \t]+", " ", norm).strip()
    return norm


def normalize_text(text: str) -> str:
    """Perform full standard normalization on an input text.

    Steps applied:
    1. Unicode NFKC normalization
    2. Removal of non-printable control characters
    3. Normalization of line endings to \\n
    4. Standardization of smart quotation marks
    5. Normalization of horizontal whitespace and excessive blank lines

    Args:
        text: Raw text string from extraction or user input.

    Returns:
        Clean, standardized text.
    """
    if not text:
        return ""

    logger.debug("Normalizing text of length %d", len(text))
    # Step 1: Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Remove control chars
    text = strip_control_characters(text)

    # Step 3: Normalize line endings
    text = normalize_line_endings(text)

    # Step 4: Standardize quotes
    text = standardize_quotes(text)

    # Step 5: Normalize whitespace
    text = normalize_whitespace(text)

    return text
