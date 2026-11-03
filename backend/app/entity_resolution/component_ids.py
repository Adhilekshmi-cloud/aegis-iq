"""Component ID normalization utilities for the Aegis Knowledge System.

Detects and standardizes component identifiers across varying representations
(e.g., 'PA7100', 'pa-7100', 'Component PA-7100', 'PMP-5000').
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Regular expression matching component ID patterns like PA-7100, SV-4200A, FLT-2100, ACT-PRI
# Pattern allows optional hyphen between 2-4 uppercase letters and digits/alpha
_PREFIX_STRIP_REGEX = re.compile(
    r"^(?:component|part|item|module|assembly|subsystem|pn|p\/n|model|id)\s*[:#-]?\s*",
    re.IGNORECASE,
)

# Standard Aegis component pattern: 2-4 letters, optional hyphen, 3-5 digits, optional single letter suffix
_COMPONENT_ID_REGEX = re.compile(
    r"^([A-Za-z]{2,4})-?(\d{3,5})([A-Za-z]?)$"
)

# Generic system tag pattern like ACT-PRI, SRV-V1, HX-MAIN
_TAG_PATTERN_REGEX = re.compile(
    r"^([A-Za-z]{2,4})-?([A-Za-z0-9]{2,5})$"
)


def strip_component_prefix(text: str) -> str:
    """Strip common descriptive prefixes such as 'Component', 'Part #', 'Item:'.

    Args:
        text: Raw text or entity label.

    Returns:
        Stripped string.
    """
    if not text:
        return ""
    cleaned = text.strip()
    return _PREFIX_STRIP_REGEX.sub("", cleaned).strip()


def normalize_component_id(raw_id: str) -> Optional[str]:
    """Standardize a component identifier to the canonical uppercase hyphenated format.

    Examples:
        'PA7100' -> 'PA-7100'
        'pa-7100' -> 'PA-7100'
        'Component PA-7100' -> 'PA-7100'
        'sv-4200a' -> 'SV-4200A'
        'FLT2100' -> 'FLT-2100'
        'PMP-5000' -> 'PMP-5000'

    Args:
        raw_id: Input identifier string.

    Returns:
        Canonical component ID string if matched, otherwise None.
    """
    if not raw_id:
        return None

    stripped = strip_component_prefix(raw_id)
    # Remove any surrounding quotes or brackets
    stripped = stripped.strip("[](){}\"' `")

    match = _COMPONENT_ID_REGEX.match(stripped)
    if match:
        prefix = match.group(1).upper()
        digits = match.group(2)
        suffix = match.group(3).upper() if match.group(3) else ""
        return f"{prefix}-{digits}{suffix}"

    return None


def is_component_id(candidate: str) -> bool:
    """Check if a string matches the standard Aegis component ID pattern.

    Args:
        candidate: String to test.

    Returns:
        True if the candidate matches component ID structure.
    """
    return normalize_component_id(candidate) is not None
