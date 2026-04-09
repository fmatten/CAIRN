"""
FM-2 Type System — Directed Acyclic Graph (DAG).

The type system represents clinical concept hierarchies as a DAG.
Edges run child → parent (more specific → more general).

Key properties:
- nx.descendants(G, node) returns all nodes ABOVE (more general than) node
- Least Common Ancestor (LCA) = node with maximum number of descendants
  among all shared ancestors of two nodes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import networkx as nx


@dataclass(frozen=True)
class TypeNode:
    """A node in the FM-2 type DAG."""

    code: str
    system: str = "local"
    display: str = ""

    def __str__(self) -> str:
        return f"{self.system}|{self.code}" + (f" ({self.display})" if self.display else "")


class TypeDAG:
    """
    FM-2 Type System as a directed acyclic graph.

    Edges run child → parent:
        child.code → parent.code
    means "child is a subtype of parent".

    Example:
        dag = TypeDAG()
        dag.add_type(TypeNode("Observation"))
        dag.add_type(TypeNode("LabResult"))
        dag.add_subtype(TypeNode("LabResult"), TypeNode("Observation"))
        # LabResult IS-A Observation
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_type(self, node: TypeNode) -> None:
        """Register a type node."""
        self._graph.add_node(node.code, node=node)

    def add_subtype(self, child: TypeNode, parent: TypeNode) -> None:
        """
        Declare child as a subtype of parent.
        Edge direction: child → parent.
        """
        self.add_type(child)
        self.add_type(parent)
        self._graph.add_edge(child.code, parent.code)

    def is_subtype(self, child: TypeNode, parent: TypeNode) -> bool:
        """Return True if child is a subtype of (or equal to) parent."""
        if child.code == parent.code:
            return True
        return parent.code in nx.descendants(self._graph, child.code)

    def ancestors(self, node: TypeNode) -> set[str]:
        """
        Return all ancestor codes (more general types) of node.
        Uses nx.descendants because edges run child→parent.
        """
        return nx.descendants(self._graph, node.code)

    def least_common_ancestor(
        self, a: TypeNode, b: TypeNode
    ) -> Optional[TypeNode]:
        """
        Return the most specific shared ancestor of a and b.

        The LCA is the shared ancestor with the maximum number of
        descendants (i.e., the most specific one).
        """
        ancestors_a = self.ancestors(a) | {a.code}
        ancestors_b = self.ancestors(b) | {b.code}
        shared = ancestors_a & ancestors_b

        if not shared:
            return None

        # Most specific = maximum descendants (deepest in hierarchy)
        lca_code = max(shared, key=lambda c: len(nx.descendants(self._graph, c)))
        node_data = self._graph.nodes[lca_code].get("node")
        if node_data is None:
            node_data = TypeNode(lca_code)
        return node_data

    def validate_dag(self) -> bool:
        """Assert the graph is acyclic."""
        return nx.is_directed_acyclic_graph(self._graph)

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    def __len__(self) -> int:
        return len(self._graph)

    def __contains__(self, node: TypeNode) -> bool:
        return node.code in self._graph


def build_clinical_type_dag() -> TypeDAG:
    """
    Build a minimal clinical type DAG for FM-2 demonstration.
    Covers core FHIR resource types and common clinical concepts.
    """
    dag = TypeDAG()

    hierarchy = [
        # (child, parent)
        ("Observation",       "Resource"),
        ("LabResult",         "Observation"),
        ("VitalSign",         "Observation"),
        ("Condition",         "Resource"),
        ("Diagnosis",         "Condition"),
        ("Problem",           "Condition"),
        ("Procedure",         "Resource"),
        ("SurgicalProcedure", "Procedure"),
        ("Anaesthesia",       "Procedure"),
        ("MedicationRequest", "Resource"),
        ("MedicationAdmin",   "Resource"),
        ("Encounter",         "Resource"),
        ("InpatientEncounter","Encounter"),
        ("AllergyStatement",  "Resource"),
        ("AllergyIntolerance","AllergyStatement"),
    ]

    for child_code, parent_code in hierarchy:
        dag.add_subtype(
            TypeNode(child_code, system="cairn"),
            TypeNode(parent_code, system="cairn"),
        )

    assert dag.validate_dag(), "Type DAG contains cycles — invariant violated"
    return dag
