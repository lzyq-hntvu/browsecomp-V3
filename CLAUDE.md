# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

# Use specific template
python -m browsecomp_v3.main --template A --count 20

# Output format (json/markdown/both)
python -m browsecomp_v3.main --format json

# Multi-constraint generation
python -m browsecomp_v3.main --min-constraints 3 --max-constraints 6

# Verbose mode for debugging
python -m browsecomp_v3.main -v
```

### Development
```bash
# Format code
black browsecomp_v3/

# Type checking
mypy browsecomp_v3/

# Lint
ruff browsecomp_v3/

# Run all tests
pytest

# Run tests with coverage
pytest --cov=tests --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py
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
├── templates/      # Reasoning chain templates (A-G)
├── constraints/    # Constraint generation and mapping
├── graph/          # Knowledge graph operations (NetworkX)
├── generator/      # Question generation and answer extraction
├── validator/      # Quality validation and diversity
├── output/         # Export to JSON/Markdown
└── utils/          # Logging utilities
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

Access config via: `from browsecomp_v3.core.config import get_config`

## External Dependencies

This project relies on external data from related projects:
- **Knowledge graph**: From QandA project at `/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json`
- **Templates and mappings**: From browsecomp-V2 project at `/home/huyuming/browsecomp-V2/deliverables/`

## Data Models

All data structures use Pydantic for type safety:
- `core/models.py` - Defines `Question`, `Constraint`, `ReasoningChain`, `Answer`, etc.
- Models are used throughout the pipeline for data validation and serialization

## Key Design Patterns

- **Pipeline Pattern** - Sequential processing stages
- **Strategy Pattern** - Template selection and constraint generation
- **Repository Pattern** - Knowledge graph access via `KnowledgeGraphLoader`
- **Factory Pattern** - Component instantiation

## Entry Points

- **CLI**: `python -m browsecomp_v3.main` or `browsecomp` command
- **Main function**: `main.py:generate_questions()` - Core generation pipeline

## Testing

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Test framework: pytest with coverage support
