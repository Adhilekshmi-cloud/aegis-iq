"""Entity resolution module for Aegis Knowledge System."""

from app.entity_resolution.alias_registry import (
    KNOWN_ALIASES,
    AliasRegistry,
    lookup_alias,
    registry,
)
from app.entity_resolution.component_ids import (
    is_component_id,
    normalize_component_id,
    strip_component_prefix,
)
from app.entity_resolution.fuzzy_matcher import (
    DEFAULT_MATCH_THRESHOLD,
    FuzzyMatchResult,
    calculate_similarity,
    fuzzy_match,
    match_against_dictionary,
)
from app.entity_resolution.resolver import (
    EntityResolutionResult,
    EntityResolver,
    default_resolver,
    resolve_entity_name,
)

__all__ = [
    "KNOWN_ALIASES",
    "AliasRegistry",
    "lookup_alias",
    "registry",
    "is_component_id",
    "normalize_component_id",
    "strip_component_prefix",
    "DEFAULT_MATCH_THRESHOLD",
    "FuzzyMatchResult",
    "calculate_similarity",
    "fuzzy_match",
    "match_against_dictionary",
    "EntityResolutionResult",
    "EntityResolver",
    "default_resolver",
    "resolve_entity_name",
]
