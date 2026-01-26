# Multi-AI Equity Research System - Blueprint

**Version**: 4.1
**Last Updated**: 2026-01-24
**Architecture**: YAML-based Workflow Engine with Multi-AI Debate

---

## System Overview

A multi-AI equity research platform that produces comprehensive investment reports through:
1. **Multi-AI Debate** - Bull/Bear advocates from different AI providers argue investment thesis
2. **YAML Workflow Engine** - Declarative workflow definitions with conditional routing
3. **Quality Control Gates** - Automated validation of assumptions, logic, and data
4. **Live Visualization** - Real-time workflow monitoring with animated agent nodes
5. **DCF Valuation** - Probability-weighted 5-scenario DCF model with broker consensus validation

---

## Current Architecture (v4.1)

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
│  │                  TIER 3A: VALUATION MODELS                           │    │
│  │                                                                      │    │
│  │  Pre-Model Validator (GPT-4o)                                        │    │
│  │  Validates: Price confirmed? Assumptions reasonable?                 │    │
│  │           │                                                          │    │
│  │    ┌──────┼──────────────┬──────────────┐                            │    │
│  │    ▼      ▼              ▼              ▼                            │    │
│  │  Financial  Relative     SOTP          DCF                           │    │
│  │  Modeler    Valuation    Valuation     Validator                     │    │
│  │  (Gemini)   (GPT-4o)     (GPT-4o)      (GPT-4o)                       │    │
│  │  DCF Model  Peer Comps   Sum-of-Parts  Broker Compare                │    │
│  │    │          │            │             │                           │    │
│  │    └──────────┴────────────┴─────────────┘                           │    │
│  │                       │                                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  TIER 3B: VALUATION QC (PARALLEL)                    │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │    │
│  │  │ Assumption       │  │ Comparable       │  │ Sensitivity      │   │    │
│  │  │ Challenger       │  │ Validator        │  │ Auditor          │   │    │
│  │  │ (GPT-4o)         │  │ (GPT-4o)         │  │ (GPT-4o)         │   │    │
│  │  │ Stress tests     │  │ Peer comparison  │  │ WACC/Growth sens │   │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │    │
│  │           │                     │                     │              │    │
│  │           └─────────────────────┼─────────────────────┘              │    │
│  │                                 ▼                                    │    │
│  │  ╔══════════════════════════════════════════════════════════════╗   │    │
│  │  ║ VALUATION COMMITTEE (GPT-4o)                                 ║   │    │
│  │  ║ Checks: All prices match? Methods converge? QC issues?       ║   │    │
│  │  ║ Output: "VALUATION: APPROVED" or "VALUATION: REVISE"         ║   │    │
│  │  ╚══════════════════════════════════════════════════════════════╝   │    │
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
| OpenAI | gpt-4o | Research Supervisor, QC Gates, Debate Critic, Valuation Committee |
| xAI | grok-4-0709 | Bull Advocate (optimistic viewpoint) |
| Alibaba | qwen-max | Bear Advocate (risk-focused viewpoint), Company Deep Dive |
| Google | gemini-2.0-flash | Market Data Collector (web search), Financial Modeler |
| DeepSeek | deepseek-chat | Alternative for cost-sensitive tasks |

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
| v4.2 | 2026-01-24 | Tool-equipped agents: DCFModelingAgent, MarketDataAgent, ValidationAgent; Oversight system: ChiefEngineer with sub-agents; Real DCF calculations with Yahoo Finance API |
| v4.1 | 2026-01-24 | DCF assumptions chain, broker consensus comparison, parallel execution |
| v4.0 | 2026-01-23 | Data Verifier, Data Checkpoint, Pre-Model Validator, Birds Eye Reviewer |
| v3.0 | 2026-01-23 | Quality Control gates, routing loop |
| v2.0 | 2026-01-22 | DCF moved after debates |
| v1.0 | 2026-01-21 | Initial YAML workflow engine |
