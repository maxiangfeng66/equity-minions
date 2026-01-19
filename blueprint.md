# Equity Research Multi-Agent System - Blueprint

## Project Overview
A multi-agent system to perform thorough equity research on 14 stocks, producing HTML reports with DCF-based intrinsic value calculations and scenario analysis.

## Input
- `list.txt` - Contains the equities to analyze (ticker and company name)
- `AI prompt template.txt` - Analysis template for each equity

---

## File & Folder Management Rules

### Creation Rules

**Before creating any new file or folder:**
1. Check if similar functionality already exists - extend existing files when possible
2. New files must fit into the established folder structure below
3. Update the "Current Project Structure" section in this blueprint when adding new files/folders

**Folder purposes (only create files in appropriate folders):**
| Folder | Purpose | File Types |
|--------|---------|------------|
| `/` (root) | Entry points, config, documentation | `.py` (main scripts), `.md`, `.txt`, `.bat` |
| `agents/` | AI agent logic and providers | `.py` only |
| `research/` | Data analysis and valuation modules | `.py` only |
| `utils/` | Helper utilities | `.py` only |
| `context/` | Runtime data, session state | `.json` only (auto-generated) |
| `context/debates/` | Debate results | `.json` only (auto-generated) |
| `reports/` | Output reports | `.html` only (auto-generated) |
| `visualizer/` | Visualization tools | `.py`, `.html`, `.json`, `.bat` |
| `_archive/` | Obsolete files (see Archive Rules) | Any |

**Naming conventions:**
- Python files: `snake_case.py`
- JSON data files: `[TICKER]_[COMPANY].json` or `debate_[TICKER]_[COMPANY].json`
- HTML reports: `[TICKER]_[COMPANY].html`

### Archive & Deletion Rules

**When to archive (move to `_archive/` folder):**
- File is no longer used but may have reference value
- Replaced by a newer implementation
- Experimental code that didn't work out

**When to delete outright:**
- Temporary/test files with no value
- Duplicate files
- Auto-generated files that can be regenerated (e.g., `reports/`, `context/`)

**Archive process:**
1. Move file to `_archive/[YYYY-MM]/` subfolder
2. Add a one-line comment at top of file explaining why archived
3. Log the archive action in Development Log section

**Periodic cleanup (do this when project feels cluttered):**
1. Review `_archive/` - delete anything older than 3 months with no recent reference
2. Review root folder - move any one-off scripts to appropriate subfolder or archive
3. Update "Current Project Structure" section

---

## Architecture Design

### Current Project Structure

```
equity-minions/
├── blueprint.md           # This file - architecture design
├── log.md                 # Development & session log
├── config.py              # API keys and configuration
├── main.py                # Main orchestrator
├── run_debates.py         # Debate runner script
├── generate_reports.py    # Report generation script
├── requirements.txt       # Python dependencies
├── list.txt               # Input equity list
├── Project brief.txt      # Requirements
├── AI prompt template.txt # Analysis template
├── Visualizer.bat         # Launch visualizer
│
├── agents/                # Multi-agent system
│   ├── __init__.py
│   ├── ai_providers.py    # GPT, Gemini, Grok, Qwen, DeepSeek APIs
│   ├── base_agent.py      # Base agent class
│   ├── analyst_agent.py   # Primary research agent (+ bull, bear)
│   ├── critic_agent.py    # Challenges assumptions (+ synthesizer)
│   ├── debate_system.py   # Debate orchestration
│   └── multi_ai_debate.py # Multi-AI debate system
│
├── research/              # Research modules
│   ├── __init__.py
│   ├── data_fetcher.py    # Data fetching
│   └── dcf.py             # DCF valuation model
│
├── utils/                 # Utilities
│   ├── __init__.py
│   ├── context_manager.py # Context persistence
│   └── html_generator.py  # HTML report generation
│
├── visualizer/            # Visualization tools
│   ├── server.py          # Local server (optional)
│   ├── visualizer_bridge.py # Real-time sync bridge
│   ├── minions_client.py  # Client connector
│   ├── minions_template.json
│   ├── Claude Minions.html # 3D visualization UI
│   └── Run Visualizer.bat
│
├── reports/               # Output HTML reports (auto-generated)
│   ├── index.html                      # Portfolio overview with card grid
│   ├── [TICKER]_[COMPANY].html         # Summary reports (key findings)
│   └── [TICKER]_[COMPANY]_detailed.html # Full detailed reports (all data)
│
├── context/               # Session persistence (auto-generated)
│   ├── session_state.json
│   ├── minions_state.json  # Real-time visualizer state
│   ├── verified_prices.json
│   ├── [TICKER]_[COMPANY].json
│   └── debates/
│       └── debate_[TICKER]_[COMPANY].json
│
└── _archive/              # Archived/obsolete files
    └── [YYYY-MM]/
```

### Multi-Agent Debate System

**Agent Roles:**
1. **Analyst Agent** - Performs initial research and valuation
2. **Bull Agent** - Argues for optimistic scenarios
3. **Bear Agent** - Argues for pessimistic scenarios
4. **Critic Agent** - Challenges all assumptions
5. **Synthesizer Agent** - Reconciles debates into final view
6. **Due Diligence Agent** - Deep verification for high-conviction calls (see below)

---

### Due Diligence Agent (Quality Gate)

**Trigger Condition:**
Activated automatically when the final target price differs significantly from current market price:
- **Upside ≥ 40%** → Triggers due diligence
- **Downside ≤ -20%** → Triggers due diligence

**Purpose:** Ensure high-conviction calls are thoroughly validated before publication. **Quality over speed** - take the time needed to get it right.

**Due Diligence Process:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUE DILIGENCE WORKFLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: LOGIC VERIFICATION                                     │
│  ├── Review the entire analytical chain                         │
│  ├── Check if assumptions are internally consistent             │
│  ├── Verify cause-effect relationships make sense               │
│  └── Flag any logical leaps or gaps                             │
│                                                                 │
│  Step 2: DATA VERIFICATION                                      │
│  ├── Cross-check key financial figures with multiple sources    │
│  ├── Verify market data (revenue, margins, growth rates)        │
│  ├── Confirm industry statistics and competitive data           │
│  └── Validate any unusual or outlier data points                │
│                                                                 │
│  Step 3: MARKET CONSENSUS COMPARISON                            │
│  ├── Fetch analyst consensus target prices                      │
│  ├── Gather sell-side estimates (if available)                  │
│  ├── Document the market estimate range (low/median/high)       │
│  └── Calculate deviation from our target                        │
│                                                                 │
│  Step 4: DISCREPANCY ANALYSIS                                   │
│  ├── If our target differs significantly from consensus:        │
│  │   ├── Identify specific assumptions that differ              │
│  │   ├── List key drivers where our view diverges               │
│  │   └── Document why we believe market is wrong                │
│  └── Create a "Key Differences" summary                         │
│                                                                 │
│  Step 5: DEEP DIVE RESEARCH (spawn sub-agents)                  │
│  ├── For each major discrepancy identified:                     │
│  │   ├── Spawn specialized research agent                       │
│  │   ├── Conduct focused investigation on that specific area    │
│  │   ├── Gather additional evidence (news, filings, data)       │
│  │   └── Report findings back to Due Diligence Agent            │
│  ├── Allow multiple iterations if needed                        │
│  └── QUALITY IS PARAMOUNT - take necessary time!!!              │
│                                                                 │
│  Step 6: FINAL CONVICTION ASSESSMENT                            │
│  ├── If conclusion remains unchanged after deep dive:           │
│  │   ├── Articulate findings with HIGH CONFIDENCE               │
│  │   ├── Explain differences vs market CLEARLY                  │
│  │   ├── Provide supporting evidence trail                      │
│  │   └── Assign a "Conviction Level" (High/Very High)           │
│  ├── If conclusion changes:                                     │
│  │   ├── Update target price with new findings                  │
│  │   ├── Document what changed and why                          │
│  │   └── Re-run trigger check (may exit due diligence)          │
│  └── Document everything for transparency                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Due Diligence Output Additions:**

When Due Diligence Agent activates, the report includes additional sections:

| Section | Description |
|---------|-------------|
| Due Diligence Summary | Overview of verification process undertaken |
| Data Verification Log | Sources checked, data points confirmed |
| Market Consensus Comparison | Our target vs street estimates (low/median/high) |
| Key Differences Explained | Why we differ from consensus - specific assumptions |
| Deep Dive Findings | Results from specialized sub-agent research |
| Conviction Statement | Final articulation with confidence level |

**Sub-Agents (spawned during Step 5 as needed):**

| Sub-Agent | Focus Area |
|-----------|------------|
| Industry Deep Dive Agent | Investigates industry-specific assumptions |
| Financial Verification Agent | Re-validates financial projections and models |
| Competitive Analysis Agent | Deeper look at competitive dynamics and moat |
| Risk Factor Agent | Investigates specific risk scenarios in detail |
| Catalyst Agent | Researches timing and probability of key catalysts |

**Quality Principles:**

```
⏱️  Time is NOT a constraint - thoroughness is MANDATORY
📊  Every major assumption must have supporting evidence
🔍  Extraordinary claims require extraordinary proof
📝  Full documentation of the verification trail
💪  High conviction ONLY after rigorous validation
🎯  If we differ from market, we MUST articulate WHY with confidence
```

---

**Debate Process (10 rounds per equity):**
```
Round 1-3: Initial positions established
Round 4-6: Cross-examination and challenges
Round 7-9: Refinement based on critiques
Round 10: Final synthesis and probability weighting
```

### DCF Model Parameters

**Discount Rates:** 8%, 9%, 10%, 11%

**Scenarios:**
| Scenario | Probability | Description |
|----------|-------------|-------------|
| Super Bear | 5% | Worst case - major disruption |
| Bear | 20% | Below expectations |
| Base | 50% | Most likely outcome |
| Bull | 20% | Above expectations |
| Super Bull | 5% | Best case - exceptional growth |

**Growth Phases:**
- Years 1-5: High growth phase
- Years 5-10: Transition phase
- Years 10+: Terminal growth (GDP-like)

### Output Format

**Two-tier report structure:**

**Summary Report** (`[TICKER].html`) - Quick overview:
- Investment thesis and recommendation
- Price targets and upside/downside
- Key metrics grid
- Valuation scenarios table
- Key risks and catalysts
- Debate summary highlights
- Link to detailed report

**Detailed Report** (`[TICKER]_detailed.html`) - Comprehensive analysis:
1. Executive Summary with key highlights
2. Industry Analysis (market size, competitive landscape, trends)
3. Company Analysis (products, pipeline, partnerships, moat)
4. Financial Data (income statement, balance sheet, key ratios)
5. DCF Valuation (assumptions, sensitivity analysis)
6. Scenario Analysis (5 cases with probability weighting)
7. Risk Assessment (categorized with mitigations)
8. Recommendation (catalysts, position sizing)
9. Full Multi-AI Debate Log (all rounds)

### Parallel Execution Strategy

- Research all equities simultaneously using async/parallel processing
- Each equity gets its own agent team
- Controlled concurrency to avoid API rate limits
- Results aggregated at the end

### Context Persistence

To handle context window limits:
1. Save intermediate results to JSON files in `context/`
2. Summarize completed research before moving to next equity
3. Maintain a session state file for resumption
4. Each equity's research is self-contained

---

## Real-Time Visualizer Integration

The system includes a 3D visualizer showing agent activity in real-time.

### How It Works

1. **visualizer_bridge.py** writes agent state to `context/minions_state.json`
2. **Claude Minions.html** reads this file every 2 seconds
3. Updates are automatic - no server required

### Data Flow

```
main.py / run_debates.py
    ↓
VisualizerBridge.start_research(ticker)
VisualizerBridge.update_progress(ticker, 50)
VisualizerBridge.complete_research(ticker)
    ↓
context/minions_state.json (auto-updated)
    ↓
Claude Minions.html (reads every 2 seconds)
    ↓
3D visualization updates in real-time
```

### Agent Types in Visualizer

| Agent | Color | Role |
|-------|-------|------|
| Orchestrator | Cyan | Coordinates all research |
| Researcher | Pink | Gathers data for each equity |
| Analyst | Red | Bull case analysis |
| Critic | Yellow | Bear case analysis |
| Debater | Purple | Synthesizes debate results |

---

## How to Run

**Option 1: With External AI APIs**
1. Edit `config.py` and add your API keys
2. Run: `python main.py`
3. For a single equity: `python main.py --ticker "9660 HK"`
4. Open visualizer: `Visualizer.bat` (optional, for real-time monitoring)

**Option 2: Direct Research (Claude-powered)**
Using Claude Code, research can be run directly using web search and analysis capabilities.

**Visualizer Only:**
1. Run `Visualizer.bat` or open `visualizer/Claude Minions.html` directly
2. Click "Open Project Folder" and select the `equity minions` folder
3. The visualizer will auto-detect and display agent activity
