"""Alias registry for Aegis system components and subsystems.

Maintains known mappings between canonical component IDs, human-readable names,
HMI display labels, and legacy engineering tags.
"""

import logging
from typing import Dict, List, Optional, Set
from app.entity_resolution.component_ids import normalize_component_id, strip_component_prefix

logger = logging.getLogger(__name__)

# Hardcoded known aliases for the Aegis system
KNOWN_ALIASES: Dict[str, List[str]] = {
    "PA-7100": ["Primary Actuator", "Main Hydraulic Ram", "primary actuator", "ACT-PRI"],
    "SV-4200": ["Servo Valve", "servo valve", "SRV-V1"],
    "SV-4200A": ["Servo Valve A", "servo valve a", "SRV-V1"],
    "HX-3300": ["Heat Exchanger", "heat exchanger", "HX-MAIN"],
    "FLT-2100": ["Filter Assembly", "Main Filter Assembly", "filter assembly", "FLT-PRI"],
    "PMP-5000": ["Primary Hydraulic Pump", "Primary Pump", "Hydraulic Pump", "PMP-1"],
    "ACC-1800": ["Hydraulic Accumulator", "Accumulator", "ACC-1"],
    "RES-0900": ["Hydraulic Reservoir", "Reservoir", "RES-1"],
    "PRV-6600": ["Pressure Relief Valve", "Relief Valve", "PRV-SYS"],
}


class AliasRegistry:
    """Registry maintaining bidirectional lookup for canonical component IDs and their aliases."""

    def __init__(self, initial_aliases: Optional[Dict[str, List[str]]] = None):
        """Initialize registry with default known aliases.

        Args:
            initial_aliases: Optional dictionary overriding the default KNOWN_ALIASES.
        """
        self._canonical_to_aliases: Dict[str, Set[str]] = {}
        self._alias_to_canonical: Dict[str, str] = {}

        source = initial_aliases if initial_aliases is not None else KNOWN_ALIASES
        for canonical, aliases in source.items():
            self.register(canonical, aliases)

    def register(self, canonical_id: str, aliases: List[str]) -> None:
        """Register a canonical ID and its known aliases.

        Args:
            canonical_id: Canonical ID (e.g. 'PA-7100').
            aliases: List of alternate names, HMI tags, etc.
        """
        norm_canonical = normalize_component_id(canonical_id) or canonical_id.upper().strip()
        if norm_canonical not in self._canonical_to_aliases:
            self._canonical_to_aliases[norm_canonical] = set()

        # Self-mapping
        self._canonical_to_aliases[norm_canonical].add(norm_canonical)
        self._alias_to_canonical[norm_canonical.lower()] = norm_canonical

        for alias in aliases:
            cleaned = alias.strip()
            if not cleaned:
                continue
            self._canonical_to_aliases[norm_canonical].add(cleaned)
            # Store lowercase alias for case-insensitive lookup
            self._alias_to_canonical[cleaned.lower()] = norm_canonical

            # Also check if alias is an unhyphenated component ID
            norm_alias = normalize_component_id(cleaned)
            if norm_alias:
                self._alias_to_canonical[norm_alias.lower()] = norm_canonical
                self._canonical_to_aliases[norm_canonical].add(norm_alias)

    def lookup(self, term: str) -> Optional[str]:
        """Look up the canonical entity ID from an alias, raw name, or unhyphenated ID.

        Examples:
            'primary actuator' -> 'PA-7100'
            'PA7100' -> 'PA-7100'
            'Component PA-7100' -> 'PA-7100'
            'ACT-PRI' -> 'PA-7100'

        Args:
            term: Entity label, tag, or component ID candidate.

        Returns:
            Canonical entity ID if recognized, otherwise None.
        """
        if not term:
            return None

        # Try direct component ID normalization first
        norm_id = normalize_component_id(term)
        if norm_id and norm_id in self._canonical_to_aliases:
            return norm_id

        # Strip prefixes
        stripped = strip_component_prefix(term)
        norm_stripped = normalize_component_id(stripped)
        if norm_stripped and norm_stripped in self._canonical_to_aliases:
            return norm_stripped

        # Check in alias dictionary (case-insensitive)
        cleaned_key = stripped.lower()
        if cleaned_key in self._alias_to_canonical:
            return self._alias_to_canonical[cleaned_key]

        # Also try raw term lowercase
        raw_key = term.strip().lower()
        if raw_key in self._alias_to_canonical:
            return self._alias_to_canonical[raw_key]

        return None

    def get_aliases(self, canonical_id: str) -> List[str]:
        """Return all registered aliases for a given canonical entity ID.

        Args:
            canonical_id: Canonical ID.

        Returns:
            List of alias strings.
        """
        norm_id = normalize_component_id(canonical_id) or canonical_id.upper().strip()
        aliases = self._canonical_to_aliases.get(norm_id, set())
        return sorted(list(aliases))

    def get_all_canonical_ids(self) -> List[str]:
        """Return list of all canonical IDs in registry."""
        return sorted(list(self._canonical_to_aliases.keys()))

    def get_all_terms(self) -> List[str]:
        """Return all searchable names, aliases, and IDs."""
        terms = set()
        for canonical, aliases in self._canonical_to_aliases.items():
            terms.add(canonical)
            terms.update(aliases)
        return sorted(list(terms))


# Global default registry instance
registry = AliasRegistry()


def lookup_alias(term: str) -> Optional[str]:
    """Convenience function to look up canonical entity ID using default registry.

    Args:
        term: Alias or candidate name.

    Returns:
        Canonical component ID or None.
    """
    return registry.lookup(term)
