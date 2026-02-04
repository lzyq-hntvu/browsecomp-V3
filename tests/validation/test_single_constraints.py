#!/usr/bin/env python3
"""Test single constraint generation"""

from browsecomp_v3.core.config import get_config
from browsecomp_v3.templates.template_selector import TemplateSelector
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.query_executor import QueryExecutor
from browsecomp_v3.generator.question_generator import QuestionGenerator
from browsecomp_v3.generator.answer_extractor import AnswerExtractor
import random

config = get_config()

# Initialize
kg_loader = KnowledgeGraphLoader()
kg_loader.load()
constraint_generator = ConstraintGenerator(kg_loader)
query_executor = QueryExecutor(kg_loader)
question_generator = QuestionGenerator(kg_loader)
answer_extractor = AnswerExtractor()
template_selector = TemplateSelector()

print(f"KG loaded: {kg_loader.node_count} nodes, {kg_loader.edge_count} edges\n")

# Try single constraints only
success_count = 0
max_attempts = 50

for attempt in range(max_attempts):
    if success_count >= 5:
        break

    # Select template A only (Paper-based)
    tid = "A"

    # Generate just 1 constraint
    try:
        constraint_set = constraint_generator.generate(
            template_id=tid,
            min_constraints=1,
            max_constraints=1
        )

        # Skip if constraint value is None or "unknown"
        constraint = constraint_set.constraints[0]
        if constraint.filter_condition is None or constraint.filter_condition == "unknown":
            print(f"Attempt {attempt+1}: Skipping {constraint.constraint_type} (unknown value)")
            continue

        print(f"Attempt {attempt+1}: {constraint.constraint_type}: {constraint.filter_condition}")

        # Execute query
        query_result = query_executor.execute(constraint_set)

        if len(query_result.candidates) == 0:
            print(f"  -> No candidates")
            continue

        # Pick a candidate
        candidate_id = random.choice(query_result.candidates) if len(query_result.candidates) > 1 else query_result.candidates[0]

        # Generate question
        candidate_data = kg_loader.get_node(candidate_id)
        answer = answer_extractor.extract(candidate_id, candidate_data, kg_loader)

        question = question_generator.generate(
            constraint_set=constraint_set,
            reasoning_chain=query_result.reasoning_chain,
            answer_entity_id=candidate_id,
            answer_text=answer.text
        )

        success_count += 1
        print(f"  -> SUCCESS! Q: {question.question_text[:60]}...")
        print(f"     A: {answer.text[:50]}...")
        print()

    except Exception as e:
        print(f"  -> ERROR: {e}")
        continue

print(f"\nGenerated {success_count} questions out of {max_attempts} attempts")
