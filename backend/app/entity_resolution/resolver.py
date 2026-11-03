"""Multi-tier entity resolution pipeline for the Aegis Knowledge System.

Executes a hierarchical resolution strategy:
1. Exact Match (case-insensitive)
2. Deterministic Normalization (strip prefixes, normalize component IDs)
3. Known Alias Registry Lookup
4. Fuzzy Matching (rapidfuzz, threshold > 0.85)
5. Flag ambiguous matches as needs_review
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entity_resolution.alias_registry import registry as default_alias_registry
from app.entity_resolution.component_ids import (
    is_component_id,
    normalize_component_id,
    strip_component_prefix,
)
from app.entity_resolution.fuzzy_matcher import (
    DEFAULT_MATCH_THRESHOLD,
    fuzzy_match,
)
from app.knowledge.models import (
    Entity,
    EntityAlias,
    EntityType,
    ResolutionMethod,
)

logger = logging.getLogger(__name__)


@dataclass
class EntityResolutionResult:
    """Detailed result of an entity resolution operation."""
    raw_name: str
    canonical_name: str
    entity_id: Optional[str] = None
    entity_type: EntityType = EntityType.COMPONENT
    resolution_method: ResolutionMethod = ResolutionMethod.EXACT
    confidence: float = 1.0
    needs_review: bool = False
    is_ambiguous: bool = False
    notes: str = ""


class EntityResolver:
    """Orchestrates multi-tier entity resolution with both in-memory and database backing."""

    def __init__(self, alias_reg=None):
        """Initialize resolver with an alias registry instance."""
        self.alias_registry = alias_reg or default_alias_registry

    def resolve_name_sync(
        self,
        raw_name: str,
        known_canonical_names: Optional[List[str]] = None,
    ) -> EntityResolutionResult:
        """Resolve a raw name string to its canonical identity synchronously.

        Evaluation order:
        1. Exact match (case-insensitive against known canonicals)
        2. Deterministic normalization (strip prefixes, hyphenate component ID)
        3. Alias registry lookup
        4. Fuzzy matching (threshold > 0.85)

        Args:
            raw_name: Raw entity name or string extracted from document.
            known_canonical_names: Optional list of known canonical names to match against.

        Returns:
            EntityResolutionResult describing the matched entity and confidence.
        """
        if not raw_name or not raw_name.strip():
            return EntityResolutionResult(
                raw_name=raw_name,
                canonical_name="",
                confidence=0.0,
                needs_review=True,
                notes="Empty raw name provided.",
            )

        trimmed = raw_name.strip()
        candidates = known_canonical_names or self.alias_registry.get_all_canonical_ids()

        # Step 1: Exact match (case-insensitive) against known canonical IDs/names
        for c in candidates:
            if c.lower() == trimmed.lower():
                return EntityResolutionResult(
                    raw_name=raw_name,
                    canonical_name=c,
                    resolution_method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    needs_review=False,
                )

        # Step 2: Deterministic component ID normalization
        norm_id = normalize_component_id(trimmed)
        if norm_id:
            # Check if this normalized ID is known or standard
            return EntityResolutionResult(
                raw_name=raw_name,
                canonical_name=norm_id,
                resolution_method=ResolutionMethod.NORMALIZED,
                confidence=1.0,
                needs_review=False,
            )

        stripped = strip_component_prefix(trimmed)
        norm_stripped = normalize_component_id(stripped)
        if norm_stripped:
            return EntityResolutionResult(
                raw_name=raw_name,
                canonical_name=norm_stripped,
                resolution_method=ResolutionMethod.NORMALIZED,
                confidence=0.98,
                needs_review=False,
            )

        # Step 3: Alias registry lookup
        alias_match = self.alias_registry.lookup(trimmed)
        if alias_match:
            return EntityResolutionResult(
                raw_name=raw_name,
                canonical_name=alias_match,
                resolution_method=ResolutionMethod.HMI_MAPPING,
                confidence=0.95,
                needs_review=False,
            )

        # Step 4: Fuzzy matching against all registered terms and canonical names
        all_terms = self.alias_registry.get_all_terms()
        if all_terms:
            f_res = fuzzy_match(stripped, all_terms, threshold=DEFAULT_MATCH_THRESHOLD)
            if f_res:
                matched_canonical = self.alias_registry.lookup(f_res.target_entity) or f_res.target_entity
                return EntityResolutionResult(
                    raw_name=raw_name,
                    canonical_name=matched_canonical,
                    resolution_method=ResolutionMethod.FUZZY,
                    confidence=f_res.score,
                    needs_review=f_res.needs_review,
                    is_ambiguous=f_res.is_ambiguous,
                    notes=f"Fuzzy match with score {f_res.score:.2f} on '{f_res.target_entity}'",
                )

        # Fallback: Treat normalized/cleaned string as its own canonical name
        cleaned_fallback = stripped if stripped else trimmed
        return EntityResolutionResult(
            raw_name=raw_name,
            canonical_name=cleaned_fallback,
            resolution_method=ResolutionMethod.NORMALIZED,
            confidence=0.60,
            needs_review=True,
            notes="No direct or fuzzy match found. Defaulting to cleaned string.",
        )

    async def resolve_or_create(
        self,
        session: AsyncSession,
        raw_name: str,
        entity_type: EntityType = EntityType.COMPONENT,
        system_context: Optional[str] = None,
    ) -> Tuple[Entity, EntityResolutionResult]:
        """Resolve a raw name against the database; create Entity and EntityAlias if needed.

        Args:
            session: Active database AsyncSession.
            raw_name: Raw name from extracted facts.
            entity_type: Expected EntityType enum.
            system_context: Context string (e.g., 'Hydraulic System').

        Returns:
            Tuple of (Entity model instance, EntityResolutionResult).
        """
        # Fetch all existing canonical names from DB
        stmt = select(Entity.canonical_name)
        res = await session.execute(stmt)
        existing_names = [row[0] for row in res.fetchall()]

        # Combine with known registry canonical IDs
        known_pool = list(set(existing_names + self.alias_registry.get_all_canonical_ids()))

        # Run resolution logic
        res_info = self.resolve_name_sync(raw_name, known_canonical_names=known_pool)

        # Check if Entity exists in DB
        entity_stmt = select(Entity).where(Entity.canonical_name == res_info.canonical_name)
        existing_entity_res = await session.execute(entity_stmt)
        entity = existing_entity_res.scalars().first()

        if not entity:
            # Create new Entity
            logger.info("Creating new Entity in database: %s", res_info.canonical_name)
            entity = Entity(
                canonical_name=res_info.canonical_name,
                entity_type=entity_type,
                system_context=system_context or "Aegis Series-7 Hydraulic System",
                meta_info={"auto_created": True, "initial_raw_name": raw_name},
            )
            session.add(entity)
            await session.flush()

        res_info.entity_id = entity.entity_id

        # Record EntityAlias if raw_name differs from canonical
        if raw_name.strip().lower() != res_info.canonical_name.lower():
            alias_stmt = select(EntityAlias).where(
                EntityAlias.entity_id == entity.entity_id,
                EntityAlias.alias_name == raw_name.strip(),
            )
            alias_res = await session.execute(alias_stmt)
            existing_alias = alias_res.scalars().first()

            if not existing_alias:
                logger.debug(
                    "Recording EntityAlias: '%s' -> '%s' (method=%s, confidence=%.2f)",
                    raw_name,
                    entity.canonical_name,
                    res_info.resolution_method,
                    res_info.confidence,
                )
                alias_record = EntityAlias(
                    entity_id=entity.entity_id,
                    alias_name=raw_name.strip(),
                    resolution_method=res_info.resolution_method,
                    confidence_score=res_info.confidence,
                )
                session.add(alias_record)
                await session.flush()

        return entity, res_info


# Global default resolver
default_resolver = EntityResolver()


def resolve_entity_name(
    raw_name: str,
    known_canonical_names: Optional[List[str]] = None,
) -> EntityResolutionResult:
    """Convenience function to synchronously resolve an entity name.

    Args:
        raw_name: Raw entity name.
        known_canonical_names: Optional list of known canonical names.

    Returns:
        EntityResolutionResult.
    """
    return default_resolver.resolve_name_sync(raw_name, known_canonical_names)
