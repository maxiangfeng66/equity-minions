# Multi-AI Equity Research System - Blueprint

**Version**: 4.3
**Last Updated**: 2026-01-27
**Architecture**: YAML-based Workflow Engine with Multi-AI Debate + Python DCF Engine

---

## System Overview

A multi-AI equity research platform that produces comprehensive investment reports through:
1. **Multi-AI Debate** - Bull/Bear advocates from different AI providers argue investment thesis
2. **YAML Workflow Engine** - Declarative workflow definitions with conditional routing
3. **Quality Control Gates** - Automated validation of assumptions, logic, and data
4. **Live Visualization** - Real-time workflow monitoring with animated agent nodes
5. **DCF Valuation** - Probability-weighted 5-scenario DCF model with broker consensus validation

---

## Current Architecture (v4.4)

### Key Changes in v4.4 (2026-01-27)

1. **LEGN_US Valuation Emergency Fix** - Manual report correction after catastrophic AI failure
2. **Quality Gate Design Flaw Investigation** - Identified 6 critical architectural issues
3. **6682_HK Shares Outstanding Correction** - Fixed from 519M to 320M (HKEx official filing)
4. **Multi-Source Shares Validator** - New utility for cross-validating shares data

### Design Flaws Identified (v4.4 Investigation)

The investigation revealed why 36 rounds of debate and multiple quality gates failed to catch obvious errors:

| Flaw | Description | Impact |
|------|-------------|--------|
| **Validation Data Isolation** | `*_investigation.json` and `*_validation.json` files exist but gates don't read them | Gates re-ask AI instead of using verified data |
| **AI-Based Gates Instead of Hard Checks** | Gates ask "Is this reasonable?" instead of checking "Is target within 0.5x-2.0x of price?" | AI can hallucinate "looks good" for garbage data |
| **No Pre-Flight Validation** | Workflow starts debate without verifying basic data (price, shares, market cap) | Garbage in → garbage out |
| **Force-Approval After Max Iterations** | `quality_loop_iteration` hits MAX → forces approval even if broken | Bad reports get published |
| **Investigation Results Never Checked** | Investigation files created but never read by quality gates | Duplicated effort, no integration |
| **Four Independent Systems** | ContextManager, Validation, Investigation, Quality Gates don't coordinate | Each system works in isolation |

### Key Changes in v4.3 (2026-01-27)

1. **Python DCF Valuation Engine** - Real mathematical calculations replace AI-generated numbers
2. **Dot Connector Agent** - Bridges qualitative analysis to quantitative DCF parameters
3. **DCF → Dot Connector Feedback Loop** - Kicks back parameters if broker divergence >30%
4. **AgentExecutor Hybrid Approach** - Temporarily disabled (interface alignment needed)
5. **Multi-Path Local Research Loader** - Supports both C: and E: drive paths
6. **Unicode Fix** - Replaced [✓] with [x] for Windows GBK encoding compatibility
7. **Terminal Growth Hardcoded to 0%** - Conservative assumption for all scenarios

### Complete System Flow
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTRY POINTS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  run_parallel_live.py         run_workflow_live.py                          │
│  (Multiple tickers)           (Single ticker)                               │
│         │                            │                                       │
│         └────────────┬───────────────┘                                       │
│                      ▼                                                       │
│  ┌───────────────────────────────────────┐                                  │
│  │         PRICE PREFETCH                │                                  │
│  │   prefetch_market_data() via Gemini   │                                  │
│  │   → Verified price injected to prompt │                                  │
│  └───────────────────┬───────────────────┘                                  │
│                      ▼                                                       │
│  ┌───────────────────────────────────────┐                                  │
│  │      LOCAL RESEARCH LOADER            │                                  │
│  │   research/local_research.py          │                                  │
│  │   → Loads broker PDFs, Excel models   │                                  │
│  └───────────────────┬───────────────────┘                                  │
│                      ▼                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                       WORKFLOW ENGINE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  workflow/graph_executor.py    ◄── workflow/definitions/equity_research_v4.yaml │
│  workflow/node_executor.py     ◄── Multi-provider API calls                 │
│  workflow/workflow_loader.py   ◄── YAML parsing                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TIER 0: ORCHESTRATION                             │    │
│  │                                                                      │    │
│  │  START ──► Research Supervisor (GPT-4o)                              │    │
│  │                    │                                                 │    │
│  │                    ▼                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              TIER 1: PRIMARY RESEARCH (PARALLEL)                     │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │    │
│  │  │ Market Data      │  │ Industry Deep    │  │ Company Deep     │   │    │
│  │  │ Collector        │  │ Dive             │  │ Dive             │   │    │
│  │  │ (Gemini 2.0)     │  │ (GPT-4o)         │  │ (Qwen-Max)       │   │    │
│  │  │ + Web Search     │  │                  │  │                  │   │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │    │
│  │           │                     │                     │              │    │
│  │           └─────────────────────┼─────────────────────┘              │    │
│  │                                 ▼                                    │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │ Data Verifier (GPT-4o) - PARALLEL                            │   │    │
│  │  │ Cross-references all collected data                          │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │                                 │                                    │    │
│  │                                 ▼                                    │    │
│  │  ╔══════════════════════════════════════════════════════════════╗   │    │
│  │  ║ DATA CHECKPOINT GATE (GPT-4o)                                ║   │    │
│  │  ║ Validates: Price verified? Data complete? Sources agree?     ║   │    │
│  │  ║ Output: "DATA: VERIFIED" or "DATA: FAILED"                   ║   │    │
│  │  ╚══════════════════════════════════════════════════════════════╝   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TIER 2: MULTI-AI DEBATE                           │    │
│  │                                                                      │    │
│  │  Debate Moderator (GPT-4o)                                           │    │
│  │           │                                                          │    │
│  │    ┌──────┴──────┐                                                   │    │
│  │    ▼             ▼                                                   │    │
│  │  Bull R1       Bear R1       ◄── ROUND 1: Opening Arguments          │    │
│  │  (Grok-4)      (Qwen-Max)                                            │    │
│  │    │             │                                                   │    │
│  │    └──────┬──────┘                                                   │    │
│  │           ▼                                                          │    │
│  │  Devils Advocate (GPT-4o)    ◄── Contrarian challenge                │    │
│  │           │                                                          │    │
│  │    ┌──────┴──────┐                                                   │    │
│  │    ▼             ▼                                                   │    │
│  │  Bull R2       Bear R2       ◄── ROUND 2: Rebuttals                  │    │
│  │  (Grok-4)      (Qwen-Max)                                            │    │
│  │    │             │                                                   │    │
│  │    └──────┬──────┘                                                   │    │
│  │           ▼                                                          │    │
│  │  Debate Critic (GPT-4o)      ◄── Scores arguments, extracts          │    │
│  │                                   valuation inputs for DCF           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  TIER 3A: VALUATION MODELS (v4.3)                    │    │
│  │                                                                      │    │
│  │  Pre-Model Validator (GPT-4o)                                        │    │
│  │  Validates: Price confirmed? Assumptions reasonable?                 │    │
│  │           │                                                          │    │
│  │           ▼                                                          │    │
│  │  ┌────────────────────────────────────────────────────────────┐     │    │
│  │  │ DOT CONNECTOR (GPT-4o) - NEW in v4.3                       │     │    │
│  │  │ Bridges qualitative debate → quantitative DCF parameters   │     │    │
│  │  │ Extracts: Growth rates, WACC inputs, margins from debate   │     │    │
│  │  │ References broker research for parameter validation        │     │    │
│  │  └────────────────────────┬───────────────────────────────────┘     │    │
│  │                           │                                          │    │
│  │                           ▼                                          │    │
│  │  ┌────────────────────────────────────────────────────────────┐     │    │
│  │  │ FINANCIAL MODELER (Gemini 2.0) + PYTHON DCF ENGINE         │     │    │
│  │  │ Uses PythonValuationExecutor for real DCF calculations     │     │    │
│  │  │ - DCF math: NPV, WACC, FCF projections                     │     │    │
│  │  │ - 5 scenarios: Super Bear / Bear / Base / Bull / Super Bull│     │    │
│  │  │ - Terminal growth hardcoded to 0% (conservative)           │     │    │
│  │  │ - Broker consensus injected from local research            │     │    │
│  │  └────────────────────────┬───────────────────────────────────┘     │    │
│  │                           │                                          │    │
│  │    ┌──────────────────────┼────────────────────┐                    │    │
│  │    ▼                      ▼                    ▼                    │    │
│  │  DCF Validator      Assumption          Comparable                  │    │
│  │  (GPT-4o)          Challenger          Validator                    │    │
│  │  Broker Compare     (GPT-4o)           (GPT-4o)                      │    │
│  │    │                   │                  │                          │    │
│  │    │                   │                  │                          │    │
│  │    │   ┌───────────────┴──────────────────┘                         │    │
│  │    │   │                                                             │    │
│  │    ▼   ▼                                                             │    │
│  │  ╔═══════════════════════════════════════════════════════════╗      │    │
│  │  ║ FEEDBACK LOOP: DCF Validator → Dot Connector              ║      │    │
│  │  ║ If "NEEDS_PARAMETER_REVISION" (divergence >30%):          ║      │    │
│  │  ║   → Kicks back to Dot Connector for parameter adjustment  ║      │    │
│  │  ╚═══════════════════════════════════════════════════════════╝      │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  TIER 3B: VALUATION QC (PARALLEL)                    │    │
│  │                                                                      │    │
│  │  NOTE: Valuation Committee REMOVED in v4.3 - it was corrupting      │    │
│  │  Python DCF output. QC agents now feed directly to Quality Gates.    │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │    │
│  │  │ Assumption       │  │ Comparable       │  │ Sensitivity      │   │    │
│  │  │ Challenger       │  │ Validator        │  │ Auditor          │   │    │
│  │  │ (GPT-4o)         │  │ (GPT-4o)         │  │ (GPT-4o)         │   │    │
│  │  │ Stress tests     │  │ Peer comparison  │  │ WACC/Growth sens │   │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │    │
│  │           │                     │                     │              │    │
│  │           └─────────────────────┼─────────────────────┘              │    │
│  │                                 │                                    │    │
│  │                          (Direct to Quality Gates)                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TIER 4: QUALITY GATES                             │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │    │
│  │  │ Data Verification│  │ Logic            │  │ Birds Eye        │   │    │
│  │  │ Gate             │  │ Verification     │  │ Reviewer         │   │    │
│  │  │ (GPT-4o)         │  │ Gate (GPT-4o)    │  │ (GPT-4o)         │   │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │    │
│  │           │                     │                     │              │    │
│  │           └─────────────────────┼─────────────────────┘              │    │
│  │                                 ▼                                    │    │
│  │  ╔══════════════════════════════════════════════════════════════╗   │    │
│  │  ║ QUALITY SUPERVISOR (GPT-4o)                                  ║   │    │
│  │  ║ Routes: SYNTHESIZER | RESEARCH SUPERVISOR | FINANCIAL MODELER║   │    │
│  │  ╚══════════════════════════════════════════════════════════════╝   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TIER 5: FINAL OUTPUT                              │    │
│  │                                                                      │    │
│  │  Synthesizer (GPT-4o) ──► Research Supervisor Final Sign-off        │    │
│  │                                      │                               │    │
│  │                                      ▼                               │    │
│  │                                    END                               │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                        REPORT GENERATION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  generate_workflow_report.py                                                 │
│         │                                                                    │
│         ├── Extract verified price from START/Data Checkpoint                │
│         ├── Extract DCF data from Financial Modeler                          │
│         ├── Extract target from Valuation Committee (LAST output)            │
│         ├── Extract broker consensus from DCF Validator                      │
│         ├── Extract debate assumptions from Debate Critic                    │
│         ├── Build 5-scenario analysis with calculations                      │
│         ├── Build DCF assumptions chain (debate → model)                     │
│         ├── Build broker consensus comparison with divergence                │
│         │                                                                    │
│         ▼                                                                    │
│  reports/[TICKER]_[COMPANY]_detailed.html                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## AI Providers

| Provider | Model | Use Cases |
|----------|-------|-----------|
| OpenAI | gpt-4o | Research Supervisor, QC Gates, Debate Critic, Dot Connector, Quality Gates |
| xAI | grok-4-0709 | Bull Advocate R1/R2 (optimistic viewpoint) |
| Alibaba | qwen-max | Bear Advocate R1/R2 (risk-focused viewpoint) |
| Google | gemini-2.0-flash | Market Data Collector (web search), Financial Modeler + Python DCF Engine |

**Note**: DeepSeek provider removed from agent_executor.py (interface incompatibility).

---

## Folder Structure

```
equity-minions/
├── brain/                        # System documentation
│   ├── blueprint.md              # THIS FILE - Architecture (latest)
│   ├── housecleaning.md          # Cleanup rules
│   ├── investigation_summary.md  # Issue investigations
│   └── system_flowchart.md       # Visual flowcharts
│
│   └── definitions/              # YAML workflow definitions
│   ├── equity_research_v4.yaml   # CURRENT - Main workflow (25 nodes)
│   └── [deprecated versions]
│
├── workflow/                     # Workflow engine code
│   ├── graph_executor.py         # DAG execution with parallel nodes
│   ├── node_executor.py          # AI provider calls with retry
│   ├── workflow_loader.py        # YAML parser
│   └── visualizer_bridge.py      # WebSocket bridge
│
├── agents/                       # AI Agent System
│   ├── core/                     # Core infrastructure
│   │   ├── base_agent.py         # BaseAgent class
│   │   ├── spawnable_agent.py    # SpawnableAgent with lifecycle
│   │   ├── agent_registry.py     # Central agent registry
│   │   └── lifecycle.py          # Agent state machine
│   │
│   ├── tools/                    # NEW: Real calculation tools
│   │   ├── financial_calculator.py  # DCF math, WACC, FCF formulas
│   │   ├── market_data_api.py    # Yahoo Finance API integration
│   │   └── validation_tools.py   # Mathematical validation
│   │
│   ├── specialized/              # NEW: Tool-equipped agents
│   │   ├── dcf_agent.py          # Real DCF modeling agent
│   │   ├── market_data_agent.py  # Market data fetching agent
│   │   └── validation_agent.py   # AI output validation agent
│   │
│   ├── oversight/                # NEW: Project monitoring
│   │   ├── chief_engineer.py     # Master oversight agent
│   │   ├── component_inspector.py # Code inspection sub-agent
│   │   ├── workflow_auditor.py   # YAML workflow validation
│   │   ├── dcf_quality_controller.py # DCF validation
│   │   └── performance_monitor.py # Metrics tracking
│   │
│   ├── goalkeepers/              # Quality gate agents
│   │   ├── publish_gatekeeper.py
│   │   └── due_diligence_agent.py
│   │
│   ├── supervisor/               # Supervisor agents
│   │   ├── research_supervisor.py
│   │   └── debate_moderator.py
│   │
│   ├── workers/                  # Worker agents
│   │   ├── analyst_agent.py
│   │   ├── critic_agent.py
│   │   └── devils_advocate.py
│   │
│   └── ai_providers.py           # Multi-AI provider wrapper
│
├── research/                     # Research utilities
│   ├── local_research.py         # Load broker PDFs/Excel
│   └── price_fetcher.py          # Market price fetching
│
├── visualizer/                   # Real-time visualization
│   ├── live_visualizer_v2.html   # CURRENT - Single workflow
│   ├── live_visualizer_parallel.html  # Multi-workflow parallel
│   └── serve_visualizer.py       # HTTP server
│
├── reports/                      # Generated HTML reports
│   ├── index.html                # Portfolio dashboard
│   └── [TICKER]_detailed.html    # Individual reports
│
├── context/                      # Runtime data
│   ├── [TICKER]_workflow_result.json
│   └── debates/
│
├── run_parallel_live.py          # Run multiple workflows in parallel
├── run_workflow_live.py          # Run single workflow with visualizer
├── run_chief_engineer.py         # NEW: Chief Engineer CLI
├── generate_workflow_report.py   # Generate HTML from workflow results
├── config.py                     # API keys configuration
└── log.md                        # Development changelog
```

---

## CRITICAL ISSUES - DCF Model (2026-01-24)

**Status**: BROKEN - Needs major overhaul

### Problem Summary

The DCF model is producing **unreliable, inconsistent, and often nonsensical results**:

1. **LEGN US**: Target extracted as $254.89 instead of correct $23.54 (10x error!)
2. **9660 HK**: Target extracted as HKD 1.80 with -80% downside (completely wrong)
3. Scenarios show 500%+ upside (capped but still broken)

### Root Causes

#### 1. No Real DCF Calculation
- Current "Financial Modeler" just asks AI to generate numbers
- No actual FCF projections with formulas
- No proper discounting of cash flows
- Terminal value is fabricated, not calculated

#### 2. Target Extraction Chaos
- Valuation Committee runs multiple times during quality loops
- Each run produces different targets
- Report generator may pick wrong one
- No clear "FINAL APPROVED TARGET" marker

#### 3. Scenario Values Are Made Up
- Super Bear/Bear/Base/Bull/Super Bull targets are invented
- Not mathematically derived from base case adjustments
- Can produce impossible values (negative prices, 500% upside)

#### 4. Debate-DCF Disconnect
- Debate produces insights about revenue growth, margins, risks
- But Financial Modeler doesn't use structured data from debate
- Just gets raw text and makes up numbers

#### 5. Broker Consensus Ignored
- DCF Validator correctly finds broker targets
- But this data doesn't constrain Financial Modeler output
- Divergence warnings shown but not enforced

---

## DCF Model Fix - IMPLEMENTED (v4.2)

**Status**: FIXED - New tool-equipped agents with real calculations

### Solution Architecture

We implemented **specialized agents with real tools and APIs** to replace AI-hallucinated calculations:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEW AGENT ARCHITECTURE (v4.2)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  agents/tools/              ◄── Real calculation tools                       │
│  ├── financial_calculator.py     DCF math, WACC, FCF, NPV formulas          │
│  ├── market_data_api.py          Yahoo Finance API for verified prices      │
│  └── validation_tools.py         Mathematical validation utilities          │
│                                                                              │
│  agents/specialized/        ◄── Tool-equipped agents                        │
│  ├── dcf_agent.py               Real DCF modeling with verified calculations│
│  ├── market_data_agent.py       Real market data fetching                   │
│  └── validation_agent.py        AI output validation against real data      │
│                                                                              │
│  agents/oversight/          ◄── Project monitoring                          │
│  ├── chief_engineer.py          Master oversight agent (project-aware)      │
│  ├── component_inspector.py     Code inspection sub-agent                   │
│  ├── workflow_auditor.py        YAML workflow validation                    │
│  ├── dcf_quality_controller.py  DCF output validation                       │
│  └── performance_monitor.py     API usage and metrics tracking              │
│                                                                              │
│  run_chief_engineer.py      ◄── CLI for Chief Engineer commands             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How It Works

#### 1. Real DCF Calculations (`agents/tools/financial_calculator.py`)
```python
# Actual formulas implemented:
WACC = (E/V) × Re + (D/V) × Rd × (1-T)
Re = Rf + β × ERP + CRP

FCF = EBIT × (1-T) + D&A - CapEx - ΔWC
Terminal Value = FCF_terminal × (1 + g) / (WACC - g)

Enterprise Value = Σ FCF_t / (1 + WACC)^t + TV / (1 + WACC)^n
Equity Value = EV - Net Debt
Fair Value = Equity Value / Shares Outstanding
```

#### 2. Verified Market Data (`agents/tools/market_data_api.py`)
- Fetches REAL prices from Yahoo Finance API
- Gets actual financials, market cap, beta
- Retrieves analyst consensus targets
- Verifies prices against claimed values (±2% tolerance)

#### 3. Scenario Calculations
Scenarios are now mathematically derived from base case:
```python
DEFAULT_SCENARIO_ADJUSTMENTS = {
    'super_bear': {'growth_adj': -0.15, 'beta_adj': +0.3, 'terminal_adj': -0.01},
    'bear':       {'growth_adj': -0.08, 'beta_adj': +0.15, 'terminal_adj': -0.005},
    'bull':       {'growth_adj': +0.10, 'beta_adj': -0.10, 'terminal_adj': +0.005},
    'super_bull': {'growth_adj': +0.20, 'beta_adj': -0.20, 'terminal_adj': +0.01}
}
```

#### 4. Chief Engineer Oversight (`agents/oversight/chief_engineer.py`)
The Chief Engineer:
- Reads brain/ documentation to understand project structure
- Monitors all components continuously
- Spawns sub-agents for specialized inspections
- Persists state across sessions
- Can run health checks, generate reports, validate workflows

### CLI Commands
```bash
python run_chief_engineer.py health      # Check all components
python run_chief_engineer.py report      # Generate system report
python run_chief_engineer.py monitor     # Continuous monitoring
python run_chief_engineer.py validate "6682 HK"  # Validate workflow
python run_chief_engineer.py audit       # Audit YAML workflows
python run_chief_engineer.py dcf AAPL    # Test DCF agent
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v4.4 | 2026-01-27 | **Quality Gate Investigation**: Identified 6 critical design flaws explaining why errors pass; **LEGN_US Emergency Fix**: Manual correction from $4.24 garbage to $60 target; **6682_HK Shares Fix**: 519M→320M via HKEx filing; **Multi-Source Shares Validator**: New utility (`utils/shares_validator.py`) |
| v4.3 | 2026-01-27 | **Dot Connector agent** bridges debate→DCF; **Python DCF Engine** (PythonValuationExecutor); DCF→Dot Connector feedback loop; Terminal growth hardcoded 0%; AgentExecutor disabled (interface issues); Multi-path LocalResearchLoader; Unicode fix ([✓]→[x]); Successful 6682 HK run (100/100 score) |
| v4.2 | 2026-01-24 | Tool-equipped agents: DCFModelingAgent, MarketDataAgent, ValidationAgent; Oversight system: ChiefEngineer with sub-agents; Real DCF calculations with Yahoo Finance API |
| v4.1 | 2026-01-24 | DCF assumptions chain, broker consensus comparison, parallel execution |
| v4.0 | 2026-01-23 | Data Verifier, Data Checkpoint, Pre-Model Validator, Birds Eye Reviewer |
| v3.0 | 2026-01-23 | Quality Control gates, routing loop |
| v2.0 | 2026-01-22 | DCF moved after debates |
| v1.0 | 2026-01-21 | Initial YAML workflow engine |

---

## Python DCF Engine (v4.3)

The Financial Modeler node now uses `PythonValuationExecutor` for real mathematical DCF calculations:

```
workflow/node_executor.py → PythonValuationExecutor
    │
    ├── Reads Dot Connector parameters (WACC, growth rates, margins)
    ├── Fetches verified price from Yahoo Finance
    ├── Loads broker consensus from local research (Excel/PDF)
    ├── Runs 5-scenario DCF with formula-based calculations:
    │   - Super Bear: WACC+3%, Growth-15%, Terminal=0%
    │   - Bear: WACC+1.5%, Growth-8%, Terminal=0%
    │   - Base: WACC from Dot Connector, Terminal=0%
    │   - Bull: WACC-1%, Growth+10%, Terminal=0%
    │   - Super Bull: WACC-2%, Growth+20%, Terminal=0%
    │
    └── Outputs: PWV (Probability-Weighted Value), scenario table, broker comparison
```

### DCF Validation Flow

```
Dot Connector → Financial Modeler → DCF Validator
                                         │
                                   ┌─────┴─────┐
                                   │ Divergence │
                                   │ Check     │
                                   └─────┬─────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
              <15% ALIGNED                           >30% SIGNIFICANT
                    │                                         │
                    ▼                                         ▼
            "DCF: VALIDATED"               "DCF: NEEDS_PARAMETER_REVISION"
                    │                                         │
                    ▼                                         ▼
            Quality Gates                           Dot Connector (loop back)
```

---

## AgentExecutor Status (v4.3)

**Status**: TEMPORARILY DISABLED

The hybrid AgentExecutor approach (using real Agent classes instead of NodeExecutor) is disabled in `workflow/agent_executor.py`:

```python
def create_agent_executor_if_applicable(...) -> Optional[AgentExecutor]:
    # Temporarily disabled - hybrid approach needs agent class interface alignment
    return None  # Fall back to standard NodeExecutor for all nodes
```

**Reason**: Interface mismatches between SpawnableAgent classes and the YAML workflow system:
- MarketDataAgent and ValidationAgent are abstract classes
- Agent.activate()/terminate() require async await
- Some agents have different constructor signatures

**To Re-enable**: Fix agent class interfaces to match AgentExecutor expectations.

---

## Local Research Loader (v4.3)

Multi-path support for broker research files across different machines:

```python
# utils/local_research_loader.py
class LocalResearchLoader:
    POSSIBLE_PATHS = [
        Path("C:/Users/MaXiangFeng/Desktop/平衡表/平衡表/Equities"),
        Path("E:/其他计算机/My Computer/平衡表/平衡表/Equities"),
    ]

    def __init__(self):
        # Tries each path, uses first one that exists
        for path in self.POSSIBLE_PATHS:
            if path.exists():
                self.base_path = path
                break
```

---

## Latest Report Corrections (v4.4)

### LEGN_US (Legend Biotech) - Manual Correction

**Problem**: Workflow produced garbage values ($4.24 target, SELL rating) despite 36 debate rounds
**Root Cause**: Quality gates isolated from validation data + force-approval after max iterations

**Before Fix**:
- Target: USD 4.24 (nonsensical)
- Rating: SELL
- Upside: -77.7%
- All scenario values garbage ($3.07, $3.64, $4.23, etc.)

**After Fix**:
- Current Price: USD 19.00
- Target: USD 60.00 (based on broker consensus and CARVYKTI analysis)
- Rating: OUTPERFORM
- Upside: +216%
- Scenarios: $18 (5%) / $37.50 (20%) / $59 (50%) / $88 (20%) / $128 (5%)
- PWV Calculation: 0.90 + 7.50 + 29.50 + 17.60 + 6.40 = $61.90 → $60

### 6682 HK (Beijing Fourth Paradigm) - Shares Correction

**Problem**: Yahoo Finance showed 519M shares, HKEx filing shows 320M
**Fix**: Manual override via `shares_validator.py --set 320`
**Impact**: PWV corrected to HKD 99.76

## Latest Successful Run (v4.3)

**Ticker**: 6682 HK (Beijing Fourth Paradigm Technology)
**Date**: 2026-01-27
**Duration**: 1009.2 seconds (~17 minutes)
**Iterations**: 36
**Nodes Executed**: 25

**Results**:
- Report Quality Score: **100/100** - PASSED
- PWV: HKD 40.59
- Current Price: HKD 51.70
- Implied Upside: -21.5% (overvalued)
- WACC: 10.7% (Rf=3.5%, β=1.2, ERP=6.0%, CRP=1.5%)
- Report: `reports/6682_HK_Beijing_Fourth_Paradigm_Techno_detailed.html`
