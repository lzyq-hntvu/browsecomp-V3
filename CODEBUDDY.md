# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

Browsecomp-V3 is a **constraint-driven complex academic question generator** based on a knowledge graph. It generates multi-hop reasoning QA pairs in Browsecomp style using 7 reasoning chain templates (A-G) and 30+ constraint mapping rules. The system supports 5-10 jump reasoning paths and outputs both JSON and Markdown formats.

## Common Commands

### Installation
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Install as package
pip install -e .
```

### Running the Application
```bash
# Generate questions (default: 50)
python -m browsecomp_v3.main --count 50
# OR use the installed command
browsecomp --count 50

# Use specific template
python -m browsecomp_v3.main --template A --count 20

# Output format (json/markdown/both)
python -m browsecomp_v3.main --format json

# Multi-constraint generation (RECOMMENDED: enables multi-hop constraints)
python -m browsecomp_v3.main --min-constraints 2 --max-constraints 3

# Verbose mode for debugging
python -m browsecomp_v3.main -v

# Custom knowledge graph path
python -m browsecomp_v3.main --kg-path /path/to/knowledge_graph.json
```

### Development
```bash
# Format code (line-length: 100)
black browsecomp_v3/

# Type checking
mypy browsecomp_v3/

# Lint
ruff browsecomp_v3/

# Run all tests
pytest

# Run tests with coverage
pytest --cov=browsecomp_v3 --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestClassName::test_method_name
```

### Debug Scripts
```bash
# Test constraint generation
python test_constraints.py
python test_single_constraints.py

# Debug query execution
python debug_query.py

# Debug graph traversal
python debug_traversal.py

# Debug question generation
python debug_generation.py

# Test multi-hop traversal (NEW)
python test_multi_hop_traversal.py

# Test multi-constraint configurations
python test_multi_constraints.py
```

## Architecture

### Pipeline Pattern

The system follows a modular pipeline architecture with clear separation of concerns:

1. **Template Selector** (`templates/`) → Choose reasoning template (A-G)
2. **Constraint Generator** (`constraints/`) → Generate 3-6 constraints based on template
3. **Query Executor** (`graph/`) → Traverse knowledge graph with constraints
4. **Answer Extractor** (`generator/`) → Extract and format answer
5. **Question Generator** (`generator/`) → Generate natural language question
6. **Quality Validator** (`validator/`) → Ensure unique, valid answers
7. **Diversity Checker** (`validator/`) → Maintain question diversity
8. **Exporter** (`output/`) → Output in JSON/Markdown formats

### Module Structure

```
browsecomp_v3/
├── core/           # Global config, Pydantic models, exceptions
│   ├── config.py      # Configuration management (Config class, get_config())
│   ├── models.py      # Pydantic models: Question, Constraint, ReasoningChain, Answer
│   └── exceptions.py  # Custom exceptions
├── templates/      # Reasoning chain templates (A-G)
│   ├── template_loader.py    # Load templates from markdown
│   └── template_selector.py  # Select template by ID or randomly
├── constraints/    # Constraint generation and mapping
│   ├── constraint_generator.py  # Generate constraints for templates
│   ├── value_generator.py       # Generate constraint values
│   └── mapping_loader.py        # Load constraint mappings
├── graph/          # Knowledge graph operations (NetworkX)
│   ├── kg_loader.py       # Load knowledge graph from JSON
│   ├── query_executor.py  # Execute queries with constraints
│   └── traversal.py       # Graph traversal algorithms
├── generator/      # Question generation and answer extraction
│   ├── question_generator.py  # Generate natural language questions
│   ├── answer_extractor.py    # Extract answers from entities
│   └── reasoning_builder.py   # Build reasoning chains
├── validator/      # Quality validation and diversity
│   ├── question_validator.py  # Validate question quality
│   └── diversity_checker.py   # Check question diversity
├── output/         # Export to JSON/Markdown
│   └── exporter.py  # Export questions in various formats
└── utils/          # Logging utilities
    └── logging.py   # Setup logging with rich console
```

### Reasoning Templates (A-G)

| Template | Name | Frequency | Coverage |
|----------|------|-----------|----------|
| A | Paper-Author-Institution | 30% | Paper → Author → Institution |
| B | Person-Academic-Path | 22% | Education → Awards → Positions |
| C | Citation-Network | 15% | Citation relationships |
| D | Collaboration-Network | 10% | Multi-paper collaboration |
| E | Event-Participation | 16% | Conference presentations |
| F | Technical-Content | 5% | Technical content analysis |
| G | Acknowledgment-Relation | 2% | Acknowledgment relationships |

## Configuration

Configuration is loaded from multiple sources (in priority order):
1. `config/default.yaml` - Runtime configuration
2. Environment variables (prefixed with `BROWSECOMP_`)
3. Code defaults (fallback)

Key configuration options:
- `knowledge_graph.path` - Path to knowledge graph JSON
- `templates.dir` - Directory containing template files
- `generation.min_constraints/max_constraints` - Constraint count range
- `output.format` - Output format (json/markdown/both)
- `logging.level` - Log level (DEBUG/INFO/WARNING/ERROR)

Access config via:
```python
from browsecomp_v3.core.config import get_config
config = get_config()
```

Environment variables:
- `BROWSECOMP_KG_PATH` - Knowledge graph path (default: `/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json`)
- `BROWSECOMP_LOG_LEVEL` - Log level (default: INFO)
- `BROWSECOMP_VERBOSE` - Enable verbose mode (default: false)
- `BROWSECOMP_BATCH_SIZE` - Batch size for generation (default: 50)

## External Dependencies

This project relies on external data from related projects:
- **Knowledge graph**: From QandA project at `/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json`
- **Templates and mappings**: From browsecomp-V2 project at `/home/huyuming/browsecomp-V2/deliverables/`
  - `推理链模板.md` - Template definitions
  - `constraint_to_graph_mapping.json` - Constraint mapping rules

If working on a different machine, update these paths in `config/default.yaml` or via environment variables.

## Data Models

All data structures use Pydantic for type safety:
- `core/models.py` - Defines `Question`, `Constraint`, `ReasoningChain`, `Answer`, etc.
- Models are used throughout the pipeline for data validation and serialization
- All models have `.model_dump()` for JSON serialization and `.model_validate()` for deserialization

## Key Design Patterns

- **Pipeline Pattern** - Sequential processing stages with clear interfaces
- **Strategy Pattern** - Template selection and constraint generation
- **Repository Pattern** - Knowledge graph access via `KnowledgeGraphLoader`
- **Factory Pattern** - Component instantiation in main.py
- **Singleton Pattern** - Global configuration via `get_config()` with thread-safe double-checked locking

## Entry Points

- **CLI**: `python -m browsecomp_v3.main` or `browsecomp` command (defined in pyproject.toml)
- **Main function**: `main.py:generate_questions()` - Core generation pipeline (lines 28-192)
- **Main CLI**: `main.py:main()` - Argument parsing and entry point (lines 194-299)

## Testing

- Unit tests: `tests/unit/` - Test individual components
- Integration tests: `tests/integration/` - Test end-to-end workflows
- Test framework: pytest with coverage support
- Test configuration: `pyproject.toml` under `[tool.pytest.ini_options]`

## Output Structure

Generated questions are saved to:
- JSON: `output/questions/questions_YYYYMMDD_HHMMSS.json`
- Markdown: `output/questions/questions_YYYYMMDD_HHMMSS.md`
- Logs: `output/logs/browsecomp.log`

## Key Implementation Details

1. **Constraint Filtering**: Constraints are filtered by `ConstraintGenerator` based on valid constraint types to avoid incompatible graph operations
2. **Candidate Selection**: When multiple candidates exist, one is randomly selected (main.py:119-123)
3. **Retry Logic**: Generation retries up to `max_generation_retries * count` times to ensure sufficient questions
4. **Diversity Checking**: Uses Jaccard similarity to maintain question diversity (threshold: 0.8)
5. **Thread Safety**: Configuration uses double-checked locking pattern for thread-safe singleton access
6. **Multi-Hop Traversal** (NEW): Supports 2-5 hop reasoning chains for complex constraints
   - `person_name`: Paper → HAS_AUTHOR → Author[name=X] (2-hop)
   - `author_order`: Paper → HAS_AUTHOR[order=X] → Author (2-hop)
   - `institution_affiliation`: Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution (3-hop)
7. **Backtracking Support**: Multi-hop constraints can backtrack to original nodes after filtering

## Development Workflow

When adding new features:
1. Update data models in `core/models.py` if needed
2. Implement core logic in appropriate module
3. Add unit tests in `tests/unit/`
4. Add integration tests if touching multiple components
5. Update this documentation if adding new commands or changing architecture
6. Run formatters and linters before committing: `black browsecomp_v3/ && ruff browsecomp_v3/ && mypy browsecomp_v3/`

### Recent Updates

**2026-02-02**: Multi-hop traversal implementation (Phase 2 complete)
- Added support for 3 new constraint types: `person_name`, `author_order`, `institution_affiliation`
- Implemented 4 new traversal methods: `traverse_with_filter`, `traverse_reverse`, `chain_traverse`, `multi_hop_traverse`
- System now supports 2-5 hop reasoning chains
- Diversity rate improved to 80% with multi-hop constraints
- See `docs/MULTI_HOP_IMPLEMENTATION_REPORT.md` for details
