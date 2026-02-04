#!/usr/bin/env python3
"""Test which constraint types actually work"""

from browsecomp_v3.core.config import get_config
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.traversal import GraphTraversal
from browsecomp_v3.core.models import Constraint, NodeType, EdgeType, ActionType

config = get_config()

# Initialize
kg_loader = KnowledgeGraphLoader()
kg_loader.load()
traversal = GraphTraversal(kg_loader.get_graph())

print(f"KG loaded: {kg_loader.node_count} nodes, {kg_loader.edge_count} edges\n")

# Test different constraint types
test_cases = [
    # (name, constraint)
    ("temporal >", Constraint(
        constraint_id="C01",
        constraint_type="temporal",
        target_node=NodeType.PAPER,
        action=ActionType.FILTER_CURRENT_NODE,
        filter_attribute="publication_year",
        filter_condition={">": 2010},
        description="After 2010"
    )),
    ("temporal <=", Constraint(
        constraint_id="C01",
        constraint_type="temporal",
        target_node=NodeType.PAPER,
        action=ActionType.FILTER_CURRENT_NODE,
        filter_attribute="publication_year",
        filter_condition={"<=": 2010},
        description="2010 or earlier"
    )),
    ("author_count >", Constraint(
        constraint_id="C02",
        constraint_type="author_count",
        target_node=NodeType.AUTHOR,
        action=ActionType.TRAVERSE_AND_COUNT,
        edge_type=EdgeType.HAS_AUTHOR,
        filter_condition={">": 3},
        description="> 3 authors"
    )),
    ("author_count =", Constraint(
        constraint_id="C02",
        constraint_type="author_count",
        target_node=NodeType.AUTHOR,
        action=ActionType.TRAVERSE_AND_COUNT,
        edge_type=EdgeType.HAS_AUTHOR,
        filter_condition={"=": 5},
        description="= 5 authors"
    )),
]

papers = kg_loader.get_nodes_by_type("Paper")
print(f"Starting with {len(papers)} papers\n")

for name, constraint in test_cases:
    try:
        candidates, steps = traversal.traverse(papers, [constraint], return_steps=True)
        print(f"{name}: {len(candidates)} candidates")

        if len(candidates) > 0 and len(candidates) <= 5:
            print(f"  Sample: {candidates[:3]}")
        print()
    except Exception as e:
        print(f"{name}: ERROR - {e}\n")
