"""
Ontology Schema for Computer Science Domain Knowledge Graphs.

Defines concept types, relationship types, and validation rules for
the Data Structures / Algorithms / OS domain.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ConceptType(str, Enum):
    """Types of concepts in the CS domain ontology."""
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"
    OPERATION = "operation"
    PROPERTY = "property"
    COMPLEXITY_CLASS = "complexity_class"
    DESIGN_PATTERN = "design_pattern"
    ABSTRACT_CONCEPT = "abstract_concept"
    PROGRAMMING_CONSTRUCT = "programming_construct"


class RelationshipType(str, Enum):
    """Types of relationships between concepts."""
    IS_A = "is_a"                           # Taxonomy: stack is_a data_structure
    HAS_PART = "has_part"                   # Composition: linked_list has_part node
    PREREQUISITE_FOR = "prerequisite_for"   # Dependency: array prerequisite_for hash_table
    IMPLEMENTS = "implements"               # Realization: binary_search implements divide_and_conquer
    USES = "uses"                           # Usage: BFS uses queue
    VARIANT_OF = "variant_of"              # Variation: doubly_linked_list variant_of linked_list
    HAS_PROPERTY = "has_property"          # Attribute: binary_search_tree has_property ordered
    HAS_COMPLEXITY = "has_complexity"       # Performance: quicksort has_complexity O(n_log_n)
    OPERATES_ON = "operates_on"            # Target: traversal operates_on tree
    PRODUCES = "produces"                   # Output: sorting produces sorted_sequence
    CONTRASTS_WITH = "contrasts_with"      # Comparison: BFS contrasts_with DFS


@dataclass
class Concept:
    """A domain concept node in the knowledge graph."""
    id: str                                 # Unique identifier (snake_case)
    name: str                               # Human-readable name
    concept_type: ConceptType               # Type classification
    description: str = ""                   # Brief definition
    aliases: list[str] = field(default_factory=list)  # Alternative names
    difficulty_level: int = 1               # 1-5 scale (1=intro, 5=advanced)
    is_primary: bool = True                 # Hierarchical KG: True=core, False=advanced/supplementary

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "concept_type": self.concept_type.value,
            "description": self.description,
            "aliases": self.aliases,
            "difficulty_level": self.difficulty_level,
            "is_primary": self.is_primary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Concept":
        return cls(
            id=data["id"],
            name=data["name"],
            concept_type=ConceptType(data["concept_type"]),
            description=data.get("description", ""),
            aliases=data.get("aliases", []),
            difficulty_level=data.get("difficulty_level", 1),
            is_primary=data.get("is_primary", True),  # default True if missing
        )


@dataclass
class Relationship:
    """A typed edge between two concepts."""
    source_id: str                          # Source concept ID
    target_id: str                          # Target concept ID
    relation_type: RelationshipType         # Type of relationship
    weight: float = 1.0                     # Importance weight (0-1)
    description: str = ""                   # Optional explanation
    
    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationshipType(data["relation_type"]),
            weight=data.get("weight", 1.0),
            description=data.get("description", "")
        )

    def as_triple(self) -> tuple[str, str, str]:
        """Return as (subject, predicate, object) triple."""
        return (self.source_id, self.relation_type.value, self.target_id)


# Validation rules for relationship types
VALID_RELATIONSHIPS = {
    RelationshipType.IS_A: {
        "description": "Taxonomic hierarchy (child is_a parent)",
        "example": "stack is_a data_structure"
    },
    RelationshipType.HAS_PART: {
        "description": "Compositional relationship",
        "example": "linked_list has_part node"
    },
    RelationshipType.PREREQUISITE_FOR: {
        "description": "Learning dependency",
        "example": "array prerequisite_for hash_table"
    },
    RelationshipType.IMPLEMENTS: {
        "description": "Implementation relationship",
        "example": "binary_search implements divide_and_conquer"
    },
    RelationshipType.USES: {
        "description": "Usage/dependency relationship",
        "example": "BFS uses queue"
    },
    RelationshipType.VARIANT_OF: {
        "description": "Variation or specialization",
        "example": "doubly_linked_list variant_of linked_list"
    },
    RelationshipType.HAS_PROPERTY: {
        "description": "Attribute or characteristic",
        "example": "BST has_property ordered"
    },
    RelationshipType.HAS_COMPLEXITY: {
        "description": "Time/space complexity",
        "example": "quicksort has_complexity O(n_log_n)"
    },
    RelationshipType.OPERATES_ON: {
        "description": "Data structure an algorithm works on",
        "example": "traversal operates_on tree"
    },
    RelationshipType.PRODUCES: {
        "description": "Output relationship",
        "example": "sorting produces sorted_sequence"
    },
    RelationshipType.CONTRASTS_WITH: {
        "description": "Contrastive/comparative relationship",
        "example": "BFS contrasts_with DFS"
    },
}
