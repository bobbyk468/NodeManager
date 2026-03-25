"""
Domain Knowledge Graph — stores expert-validated concept knowledge.

Uses NetworkX as the underlying graph structure with JSON serialization
for portability and integration with the NodeGrade pipeline.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Optional

from .ontology import Concept, Relationship, ConceptType, RelationshipType


class DomainKnowledgeGraph:
    """
    Expert-validated domain knowledge graph for a specific CS topic.
    
    Stores concepts as nodes and typed relationships as edges.
    Supports querying, comparison, and serialization.
    """

    def __init__(self, domain: str = "data_structures", version: str = "1.0"):
        self.domain = domain
        self.version = version
        self.graph = nx.DiGraph()
        self._concepts: dict[str, Concept] = {}
        self._relationships: list[Relationship] = []

    @property
    def num_concepts(self) -> int:
        return len(self._concepts)

    @property
    def num_relationships(self) -> int:
        return len(self._relationships)

    def add_concept(self, concept: Concept) -> None:
        """Add a concept node to the knowledge graph."""
        self._concepts[concept.id] = concept
        self.graph.add_node(
            concept.id,
            name=concept.name,
            concept_type=concept.concept_type.value,
            description=concept.description,
            aliases=concept.aliases,
            difficulty_level=concept.difficulty_level,
            is_primary=concept.is_primary,
        )

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a typed relationship edge to the knowledge graph."""
        if relationship.source_id not in self._concepts:
            raise ValueError(f"Source concept '{relationship.source_id}' not found in graph")
        if relationship.target_id not in self._concepts:
            raise ValueError(f"Target concept '{relationship.target_id}' not found in graph")
        
        self._relationships.append(relationship)
        self.graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            relation_type=relationship.relation_type.value,
            weight=relationship.weight,
            description=relationship.description
        )

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Retrieve a concept by ID."""
        return self._concepts.get(concept_id)

    def find_concept_by_alias(self, name: str) -> Optional[Concept]:
        """Find a concept by name or alias (case-insensitive)."""
        name_lower = name.lower().strip()
        for concept in self._concepts.values():
            if concept.name.lower() == name_lower:
                return concept
            if concept.id.lower() == name_lower:
                return concept
            if name_lower in [a.lower() for a in concept.aliases]:
                return concept
        return None

    def get_neighbors(self, concept_id: str) -> list[tuple[str, str, str]]:
        """Get all neighbors of a concept as (neighbor_id, relation_type, direction)."""
        neighbors = []
        for _, target, data in self.graph.out_edges(concept_id, data=True):
            neighbors.append((target, data["relation_type"], "outgoing"))
        for source, _, data in self.graph.in_edges(concept_id, data=True):
            neighbors.append((source, data["relation_type"], "incoming"))
        return neighbors

    def get_subgraph_for_question(self, question_concepts: list[str], depth: int = 2) -> "DomainKnowledgeGraph":
        """
        Extract a relevant subgraph centered on the concepts expected in a question.
        
        Args:
            question_concepts: List of concept IDs relevant to the question
            depth: How many hops from the question concepts to include
            
        Returns:
            A new DomainKnowledgeGraph containing the relevant subgraph
        """
        relevant_nodes = set()
        for concept_id in question_concepts:
            if concept_id in self.graph:
                # BFS to find nearby concepts
                for node in nx.single_source_shortest_path_length(
                    self.graph, concept_id, cutoff=depth
                ):
                    relevant_nodes.add(node)
                # Also check reverse direction
                reverse = self.graph.reverse()
                for node in nx.single_source_shortest_path_length(
                    reverse, concept_id, cutoff=depth
                ):
                    relevant_nodes.add(node)

        subgraph = DomainKnowledgeGraph(
            domain=self.domain, 
            version=self.version + "-subgraph"
        )
        for node_id in relevant_nodes:
            if node_id in self._concepts:
                subgraph.add_concept(self._concepts[node_id])
        
        for rel in self._relationships:
            if rel.source_id in relevant_nodes and rel.target_id in relevant_nodes:
                subgraph.add_relationship(rel)
        
        return subgraph

    def get_prerequisites(self, concept_id: str, _visited: set = None) -> list[str]:
        """Get all prerequisites for a concept (transitive).

        _visited guards against infinite recursion in cyclic prerequisite chains.
        """
        if _visited is None:
            _visited = set()
        if concept_id in _visited:
            return []
        _visited.add(concept_id)

        prereqs = set()
        for source, target, data in self.graph.in_edges(concept_id, data=True):
            if data["relation_type"] == RelationshipType.PREREQUISITE_FOR.value:
                prereqs.add(source)
                prereqs.update(self.get_prerequisites(source, _visited))
        return list(prereqs)

    def tag_hierarchical_concepts(self) -> None:
        """Auto-tag each concept as primary or secondary using graph structure.

        Heuristic (topology-first, then known-secondary set, then difficulty):
        - Primary  (is_primary=True):  concepts that serve as a prerequisite for
          at least one other concept (outgoing PREREQUISITE_FOR edge).  These are
          foundational — they *enable* other learning.  All others default primary.
        - Secondary (is_primary=False): non-prereq-source concepts that are either
          (a) well-known variants/specializations (doubly linked list, AVL tree,
          specific traversals, advanced graph algorithms, hash collision strategies,
          sort variants, etc.) or (b) difficulty_level >= 4.

        After calling this method all Concept objects and their corresponding
        NetworkX node attributes are updated in-place.  Aims for ~65% primary /
        35% secondary split on the standard DS domain graph.
        """
        prereq_type = RelationshipType.PREREQUISITE_FOR.value

        # Concepts that are topology-source of a prerequisite edge → always primary
        prereq_sources: set[str] = set()
        for rel in self._relationships:
            if rel.relation_type.value == prereq_type:
                prereq_sources.add(rel.source_id)

        # Known secondary concept IDs (variants, specialisations, advanced topics)
        known_secondary: set[str] = {
            # Linked-list variants
            "doubly_linked_list", "circular_linked_list",
            # Queue / deque variants
            "circular_queue", "deque",
            # Array / heap variants
            "dynamic_array", "max_heap", "min_heap",
            # Tree variants and internals
            "avl_tree", "red_black_tree", "b_tree", "trie",
            "subtree", "tree_height", "balanced_tree",
            # Specific traversals (general tree_traversal is primary)
            "inorder", "preorder", "postorder", "level_order",
            # Graph types / representations
            "directed_graph", "weighted_graph",
            "adjacency_list", "adjacency_matrix",
            # Advanced graph algorithms
            "dijkstra", "topological_sort", "minimum_spanning_tree", "shortest_path",
            # Hash-table internals
            "chaining", "open_addressing", "load_factor",
            # Memory edge-cases
            "static_memory", "stack_overflow", "stack_underflow",
            # Specific complexity classes (general big-O reasoning is primary)
            "o_n2", "o_n_log_n",
            # Sort variants
            "heap_sort", "comparison_sort", "stable_sort",
        }

        for concept in self._concepts.values():
            if concept.id in prereq_sources:
                concept.is_primary = True
            elif concept.id in known_secondary:
                concept.is_primary = False
            elif concept.difficulty_level >= 4:
                concept.is_primary = False
            else:
                concept.is_primary = True  # safe default

            # Sync back to NetworkX node attribute
            if concept.id in self.graph:
                self.graph.nodes[concept.id]["is_primary"] = concept.is_primary

    def get_concept_ids(self) -> list[str]:
        """Get all concept IDs."""
        return list(self._concepts.keys())

    def get_all_concepts(self) -> list[Concept]:
        """Get all concepts."""
        return list(self._concepts.values())

    def get_all_relationships(self) -> list[Relationship]:
        """Get all relationships."""
        return list(self._relationships)

    def get_relationships_for_concept(self, concept_id: str) -> list[Relationship]:
        """Get all relationships involving a concept."""
        return [
            r for r in self._relationships
            if r.source_id == concept_id or r.target_id == concept_id
        ]

    def to_dict(self) -> dict:
        """Serialize the entire graph to a dictionary."""
        return {
            "domain": self.domain,
            "version": self.version,
            "concepts": [c.to_dict() for c in self._concepts.values()],
            "relationships": [r.to_dict() for r in self._relationships],
            "stats": {
                "num_concepts": self.num_concepts,
                "num_relationships": self.num_relationships,
                "concept_types": self._get_type_distribution(),
                "relationship_types": self._get_relationship_distribution()
            }
        }

    def _get_type_distribution(self) -> dict[str, int]:
        dist = {}
        for c in self._concepts.values():
            key = c.concept_type.value
            dist[key] = dist.get(key, 0) + 1
        return dist

    def _get_relationship_distribution(self) -> dict[str, int]:
        dist = {}
        for r in self._relationships:
            key = r.relation_type.value
            dist[key] = dist.get(key, 0) + 1
        return dist

    @classmethod
    def from_dict(cls, data: dict) -> "DomainKnowledgeGraph":
        """Deserialize from a dictionary."""
        graph = cls(
            domain=data.get("domain", "unknown"),
            version=data.get("version", "1.0")
        )
        for c_data in data.get("concepts", []):
            graph.add_concept(Concept.from_dict(c_data))
        for r_data in data.get("relationships", []):
            graph.add_relationship(Relationship.from_dict(r_data))
        return graph

    def save(self, filepath: str | Path) -> None:
        """Save the knowledge graph to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "DomainKnowledgeGraph":
        """Load a knowledge graph from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def summary(self) -> str:
        """Return a human-readable summary of the graph."""
        type_dist = self._get_type_distribution()
        rel_dist = self._get_relationship_distribution()
        lines = [
            f"Domain Knowledge Graph: {self.domain} v{self.version}",
            f"  Concepts: {self.num_concepts}",
            f"  Relationships: {self.num_relationships}",
            f"  Concept Types: {type_dist}",
            f"  Relationship Types: {rel_dist}",
        ]
        return "\n".join(lines)
