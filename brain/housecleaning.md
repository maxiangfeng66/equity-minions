# Housecleaning Rules

**Purpose**: Keep the project folder clean and organized by defining what to keep, what to delete, and when.

---

## Folder Structure Rules

### Keep (Core)
| Folder/File | Purpose |
|-------------|---------|
| `brain/` | Documentation (blueprint.md, housecleaning.md, idea.txt) |
| `workflow/definitions/` | YAML workflow definitions |
| `workflow/` | Workflow engine code |
| `agents/` | AI agent implementations |
| `visualizer/` | Live visualization HTML/JS |
| `reports/` | Generated HTML reports (output) |
| `context/` | Runtime data and workflow results |
| `utils/` | Helper utilities |
| `config.py` | API keys configuration |
| `log.md` | Development changelog |

### Keep (Entry Points)
| File | Purpose |
|------|---------|
| `run_workflow_live.py` | Main workflow runner |
| `generate_report_from_workflow.py` | Report generator |
| `*.bat` launchers | Windows convenience scripts |

### Delete Immediately
| Pattern | Reason |
|---------|--------|
| `nul` | Windows command artifact |
| `*.pyc`, `__pycache__/` | Python bytecode (regenerated) |
| `*.log` (except log.md) | Temporary logs |
| `.DS_Store` | macOS artifact |
| `Thumbs.db` | Windows artifact |
| `*.tmp`, `*.temp` | Temporary files |
| `*.bak` | Backup files |

---

## Workflow Files Rules

### Current (Keep)
- `workflow/definitions/equity_research_v4.yaml` - Current production workflow
- `workflow/definitions/portfolio_workflow.yaml` - Multi-equity parallel execution

### Deprecated (Delete after migration)
- Old v1/v2/v3 workflow files (already deleted)

**Rule**: Only keep the latest version. Delete older versions once v4 is stable.

---

## Visualizer Rules

### Current (Keep)
- `visualizer/live_visualizer_v2.html` - Current v4 workflow layout
- `visualizer/portfolio_visualizer.html` - Multi-equity parallel view
- `visualizer/visualizer_bridge.py` - WebSocket server
- `visualizer/serve_visualizer.py` - HTTP server

### Deprecated (Delete)
- Any `visualizer/*.html` not listed above
- `visualizer/Workflow Visualizer.html` - Old version
- `visualizer/agent_flowchart.html` - Experimental

---

## Reports Rules

### Keep
- `reports/index.html` - Portfolio dashboard
- `reports/*_detailed.html` - Detailed equity reports
- `reports/*.html` - Summary reports

### Delete Criteria
- Reports older than 30 days without updates
- Duplicate reports (keep only latest)
- Incomplete/error reports

---

## Context Rules

### Keep
- `context/*_workflow_result.json` - Latest workflow results
- `context/debates/*.json` - Debate logs
- `context/minions_state.json` - System state

### Delete Criteria
- Workflow results older than 7 days (unless latest for ticker)
- Intermediate/debug files
- Orphaned files (no corresponding ticker in config)

---

## Root Folder Rules

### Allowed in Root
- `*.py` entry point scripts
- `*.bat` launcher scripts
- `config.py`
- `log.md`
- `.gitignore`
- `requirements.txt`

### Should NOT be in Root
- `*.txt` documentation (move to `brain/`)
- `*.md` documentation except log.md (move to `brain/`)
- Research files (move to `context/`)
- Report files (move to `reports/`)

---

## Cleanup Schedule

| Frequency | Action |
|-----------|--------|
| On-demand | Run `cleanup.bat` manually |
| Weekly | Review and delete old workflow results |
| Monthly | Archive or delete old reports |
| Per release | Delete deprecated workflow/visualizer versions |

---

## Cleanup Script Behavior

The `cleanup.bat` script will:

1. **Always Delete**:
   - `nul`, `*.pyc`, `__pycache__/`
   - `.DS_Store`, `Thumbs.db`
   - `*.tmp`, `*.temp`, `*.bak`

2. **Report but Don't Delete** (manual review):
   - Deprecated workflow versions
   - Old visualizer files
   - Files in root that should be moved

3. **Never Delete**:
   - Any file in `brain/`
   - `config.py`
   - `log.md`
   - Active workflow results
   - Generated reports

---

## Manual Cleanup Checklist

Before major releases:

- [ ] Delete deprecated workflow YAML versions
- [ ] Delete old visualizer HTML files
- [ ] Move stray documentation to `brain/`
- [ ] Review `context/` for orphaned files
- [ ] Update `log.md` with deletions
- [ ] Run `cleanup.bat` for automated cleanup
