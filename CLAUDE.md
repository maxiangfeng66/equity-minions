# Architecture Guide for Claude

This document helps Claude understand the codebase structure and avoid creating duplicate code.

## Housekeeper System

A semantic housekeeper automatically runs on every conversation start and before every file write.

**How it works:**
1. On conversation start: Rebuilds function/class index
2. Before writing .py files: Checks for similar existing code
3. If duplicate found: BLOCKS and tells Claude to modify existing code instead

**Location:** `scripts/housekeeper/`

## Project Structure

```
equity minions/
├── agents/                    # All agent classes
│   ├── core/                  # Base infrastructure
│   │   ├── spawnable_agent.py # USE THIS for new agents
│   │   ├── agent_registry.py  # Global agent registry
│   │   └── types.py          # Shared dataclasses (TODO: create)
│   ├── goalkeepers/          # Quality gate agents
│   ├── oversight/            # Monitoring agents
│   ├── supervisors/          # Management agents
│   ├── workers/              # Execution agents
│   └── ai_providers.py       # Multi-AI provider manager
├── utils/                    # Shared utilities
│   ├── html_generator.py     # Report generation
│   ├── context_manager.py    # Data management
│   └── price_fetcher.py      # Price data
├── workflow/                 # Workflow execution
│   ├── graph_executor.py     # DAG execution
│   └── workflow_loader.py    # YAML loading
├── scripts/                  # CLI scripts
│   └── housekeeper/          # Code duplication checker
└── config.py                 # API keys and settings
```

## Rules for New Code

### Creating New Agents
- ALWAYS extend `SpawnableAgent` from `agents/core/spawnable_agent.py`
- NEVER extend `BaseAgent` from `agents/base_agent.py` (deprecated)
- Register in `agents/__init__.py`

### Creating New Functions
- First check if similar function exists (housekeeper will catch this)
- If extending functionality, modify the existing function
- Utilities go in `utils/`, not scattered in agent files

### Creating New Classes
- Check for existing similar classes first
- Shared dataclasses should go in `agents/core/types.py`
- Don't create `ValidationResult` - it already exists

### Debate Systems
- USE: `agents/hierarchical_debate_system.py`
- DEPRECATED: `debate_system.py`, `multi_ai_debate.py`

### Validation
- Validators go in `agents/goalkeepers/` or `agents/validation/`
- Validation utilities go in `agents/tools/validation_tools.py`

## Known Duplications to Avoid

| Don't Create | Use Instead | Location |
|--------------|-------------|----------|
| `ValidationResult` | Existing class | `agents/tools/validation_tools.py` |
| `FactCheckerAgent` | Existing class | `agents/goalkeepers/fact_checker_gate.py` |
| `validate_dcf()` | Existing function | `agents/tools/validation_tools.py` |
| `fetch_stock_price()` | Existing function | `utils/price_fetcher.py` |
| New debate system | Hierarchical system | `agents/hierarchical_debate_system.py` |

## Entry Points

- `main.py` - Primary entry point for all workflows
- Avoid creating new `run_*.py` files

## File Location Rules

| Type | Allowed Locations |
|------|-------------------|
| Agent classes | `agents/` and subdirectories |
| Utilities | `utils/` |
| Workflows | `workflow/` |
| Scripts | `scripts/` |
| Validators | `agents/goalkeepers/`, `agents/validation/` |
