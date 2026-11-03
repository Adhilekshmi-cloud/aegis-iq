"""Query analyzer - identifies entities, predicates, and question types from natural language."""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Result of analyzing a natural language question."""
    original_question: str
    identified_entities: list[str] = field(default_factory=list)
    identified_predicates: list[str] = field(default_factory=list)
    question_type: str = "general"  # specification, comparison, version, alias, existence
    component_ids: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# Known component patterns
COMPONENT_ID_PATTERN = re.compile(r'\b([A-Z]{2,4}[-]?\d{3,5}[A-Z]?)\b', re.IGNORECASE)

# Known predicates/parameters
KNOWN_PREDICATES = [
    "operating pressure", "pressure", "max pressure", "proof pressure", "burst pressure",
    "temperature", "temperature range", "operating temperature",
    "flow rate", "response time", "displacement", "max speed",
    "precharge pressure", "precharge", "filtration rating", "bypass pressure",
    "heat rejection", "weight", "material",
    "maintenance interval", "mtbf", "part number",
    "hydraulic fluid", "fluid",
    "redundancy",
]

# Known entity names
KNOWN_ENTITIES = [
    "primary actuator", "main hydraulic ram", "actuator",
    "servo valve", "servo valve a",
    "heat exchanger",
    "filter assembly", "main filter", "filtration module",
    "primary pump", "hydraulic pump", "primary hydraulic pump",
    "accumulator", "hydraulic accumulator",
    "reservoir", "hydraulic reservoir",
    "pressure relief valve", "relief valve",
    "aegis series-7", "series-7", "aegis", "series 7",
    "series-5", "series 5",
]

# Question type indicators
VERSION_KEYWORDS = ["version", "revision", "rev ", "ecn", "change", "changed", "update", "updated", "upgrade"]
ALIAS_KEYWORDS = ["name", "names", "known as", "called", "identifier", "identifiers", "alias", "label"]
COMPARISON_KEYWORDS = ["compatible", "compatibility", "difference", "compare", "vs", "versus"]
EXISTENCE_KEYWORDS = ["mtbf", "mean time", "does it", "is there", "what is the"]


class QueryAnalyzer:
    """Analyzes natural language questions to identify entities, predicates, and intent."""

    def analyze(self, question: str) -> QueryAnalysis:
        """Analyze a natural language question.
        
        Args:
            question: The user's question string.
            
        Returns:
            QueryAnalysis with identified entities, predicates, and question type.
        """
        logger.info(f"Analyzing query: {question}")
        
        q_lower = question.lower().strip()
        analysis = QueryAnalysis(original_question=question)
        
        # Extract component IDs
        id_matches = COMPONENT_ID_PATTERN.findall(question)
        analysis.component_ids = [m.upper() for m in id_matches]
        
        # Find known entities mentioned
        for entity in KNOWN_ENTITIES:
            if entity in q_lower:
                analysis.identified_entities.append(entity)
        
        # Add component IDs as entities too
        for cid in analysis.component_ids:
            if cid not in analysis.identified_entities:
                analysis.identified_entities.append(cid)
        
        # Find known predicates mentioned
        for predicate in KNOWN_PREDICATES:
            if predicate in q_lower:
                analysis.identified_predicates.append(predicate)
        
        # Determine question type
        analysis.question_type = self._classify_question(q_lower)
        
        # Extract general keywords
        analysis.keywords = self._extract_keywords(q_lower)
        
        logger.info(
            f"Query analysis: entities={analysis.identified_entities}, "
            f"predicates={analysis.identified_predicates}, "
            f"type={analysis.question_type}"
        )
        
        return analysis

    def _classify_question(self, q_lower: str) -> str:
        """Classify the question type based on keywords."""
        if any(kw in q_lower for kw in VERSION_KEYWORDS):
            return "version"
        if any(kw in q_lower for kw in ALIAS_KEYWORDS):
            return "alias"
        if any(kw in q_lower for kw in COMPARISON_KEYWORDS):
            return "comparison"
        if any(pred in q_lower for pred in KNOWN_PREDICATES[:10]):
            return "specification"
        return "general"

    def _extract_keywords(self, q_lower: str) -> list[str]:
        """Extract significant keywords from the question."""
        stop_words = {
            "what", "is", "the", "of", "a", "an", "and", "or", "for", "in", "on",
            "to", "with", "are", "does", "do", "how", "which", "that", "this",
            "it", "be", "was", "were", "been", "all", "any", "each", "from",
        }
        words = re.findall(r'[a-z]+(?:-[a-z]+)*', q_lower)
        return [w for w in words if w not in stop_words and len(w) > 2]
