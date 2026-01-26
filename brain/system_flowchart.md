# Equity Minions System Flowchart

**Version**: 4.2
**Last Updated**: 2026-01-24
**Purpose**: Complete system architecture documentation with flowcharts, AI provider mapping, oversight agents, and known issues

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Master Flowchart](#master-flowchart)
3. [AI Providers Map](#ai-providers-map)
4. [New Agent Architecture (v4.2)](#new-agent-architecture-v42)
5. [Folder Structure](#folder-structure)
6. [Detailed Tier Flowcharts](#detailed-tier-flowcharts)
7. [Data Flow Diagram](#data-flow-diagram)
8. [Key Design Principles](#key-design-principles)
9. [Known Issues by Tier](#known-issues-by-tier)
10. [Files to Investigate](#files-to-investigate)

---

## Project Overview

This is a **Multi-AI Equity Research System** that:
- Uses **5 different AI providers** (GPT-4o, Grok-4, Qwen-Max, Gemini, Claude) for diverse perspectives
- Implements **Bull/Bear debates** with multiple rounds
- Performs **DCF valuation** with 5 scenarios (super_bear, bear, base, bull, super_bull)
- Has **quality gates** to validate data, logic, and assumptions
- Generates **HTML reports** with investment recommendations and probability-weighted target prices

---

## Master Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                             │
│                     "Research TICKER (e.g., 6682 HK)"                           │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 1: ENTRY & CONFIGURATION                                               │
│  ┌───────────────────┐   ┌───────────────┐   ┌─────────────────────────────┐   │
│  │run_workflow_live.py│   │ config.py     │   │ prefetch_data.py            │   │
│  │(single equity)    │──►│ - API keys    │──►│ - Fetch REAL price          │   │
│  │                   │   │ - 14 equities │   │ - Yahoo Finance             │   │
│  └───────────────────┘   │ - Scenarios   │   │ - Build price context       │   │
│                          └───────────────┘   └──────────────┬──────────────┘   │
└─────────────────────────────────────────────────────────────┼───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 2: WORKFLOW ENGINE                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                             │ │
│  │   workflow_loader.py ──► equity_research_v4.yaml ──► graph_executor.py     │ │
│  │   (load YAML)            (25 nodes, 40 edges)        (execute DAG)         │ │
│  │                                   │                                        │ │
│  │                                   ▼                                        │ │
│  │                          node_executor.py                                  │ │
│  │                          (call AI providers)                               │ │
│  │                                                                             │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┬───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 3: RESEARCH PHASE (TIER 0-2)                                           │
│                                                                                  │
│  Research Supervisor ──► [4 Parallel Collectors] ──► Data Checkpoint Gate       │
│                                                                                  │
│  See: Detailed Tier 0-2 Flowcharts below                                        │
└─────────────────────────────────────────────────────────────┬───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 4: DEBATE PHASE (TIER 3)                                               │
│                                                                                  │
│  Moderator ──► [Bull R1 | Bear R1] ──► Devil's Advocate ──► [Bull R2 | Bear R2]│
│           ──► Debate Critic                                                     │
│                                                                                  │
│  See: Detailed Tier 3 Flowchart below                                           │
└─────────────────────────────────────────────────────────────┬───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 5: VALUATION PHASE (TIER 4-5)                                          │
│                                                                                  │
│  Pre-Model Validator ──► Financial Modeler (DCF) ──► [3 QC Agents]              │
│                     ──► Valuation Committee                                     │
│                                                                                  │
│  See: Detailed Tier 4-5 Flowcharts below                                        │
└─────────────────────────────────────────────────────────────┬───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 6: QUALITY CONTROL (TIER 6)                                            │
│                                                                                  │
│  [Data Gate | Logic Gate | Bird's Eye] ──► Quality Supervisor ──► ROUTING       │
│                                                                                  │
│  See: Detailed Tier 6 Flowchart below                                           │
└─────────────────────────────────────────────────────────────┬───────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECTION 7: OUTPUT GENERATION (TIER 7)                                          │
│                                                                                  │
│  Synthesizer ──► generate_workflow_report.py ──► HTML Reports                   │
│                                                                                  │
│  See: Detailed Tier 7 Flowchart below                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## AI Providers Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AI PROVIDER ASSIGNMENTS                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐                 │
│  │    OpenAI     │     │      xAI      │     │   Alibaba     │                 │
│  │    GPT-4o     │     │   Grok-4      │     │   Qwen-Max    │                 │
│  ├───────────────┤     ├───────────────┤     ├───────────────┤                 │
│  │ • Supervisor  │     │ • Bull        │     │ • Bear        │                 │
│  │ • QC Gates    │     │   Advocate R1 │     │   Advocate R1 │                 │
│  │ • Moderator   │     │ • Bull        │     │ • Bear        │                 │
│  │ • Critic      │     │   Advocate R2 │     │   Advocate R2 │                 │
│  │ • Committee   │     │               │     │               │                 │
│  │ • Synthesizer │     │ (Optimistic   │     │ (Risk-focused │                 │
│  │               │     │  viewpoint)   │     │  viewpoint)   │                 │
│  └───────────────┘     └───────────────┘     └───────────────┘                 │
│                                                                                  │
│  ┌───────────────┐     ┌───────────────┐                                       │
│  │    Google     │     │  Anthropic    │                                       │
│  │ Gemini-2.0    │     │ Claude-3.5    │                                       │
│  ├───────────────┤     ├───────────────┤                                       │
│  │ • Market Data │     │ • Final       │                                       │
│  │   Collector   │     │   Reports     │                                       │
│  │ • Financial   │     │ • Synthesis   │                                       │
│  │   Modeler     │     │               │                                       │
│  │ • Comparable  │     │               │                                       │
│  │   Validator   │     │               │                                       │
│  └───────────────┘     └───────────────┘                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Provider Details Table

| Provider | Model | Use Cases | Personality |
|----------|-------|-----------|-------------|
| OpenAI | gpt-4o | Research Supervisor, QC Gates, Debate Critic, Synthesizer | Balanced, analytical |
| xAI | grok-4-0709 | Bull Advocate R1 & R2 | Optimistic, growth-focused |
| Alibaba | qwen-max | Bear Advocate R1 & R2 | Risk-focused, conservative |
| Google | gemini-2.0-flash | Market Data Collector, Financial Modeler, Comparable Validator | Data-driven, quantitative |
| Anthropic | claude-3.5-sonnet | Final Report Generation | Clear, structured writing |

---

## New Agent Architecture (v4.2)

### Overview

v4.2 introduces **tool-equipped specialized agents** and a **Chief Engineer oversight system** to solve the DCF reliability problem:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         NEW AGENT ARCHITECTURE (v4.2)                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                        CHIEF ENGINEER (Oversight Layer)                          │    │
│  │                                                                                   │    │
│  │  chief_engineer.py                                                               │    │
│  │  ├── Reads brain/ documentation to understand project                           │    │
│  │  ├── Monitors all components continuously                                        │    │
│  │  ├── Spawns sub-agents for specialized inspections                              │    │
│  │  └── Persists state across sessions                                              │    │
│  │                                                                                   │    │
│  │  Sub-Agents:                                                                      │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────┐ │    │
│  │  │ Component        │ │ Workflow         │ │ DCF Quality      │ │ Performance │ │    │
│  │  │ Inspector        │ │ Auditor          │ │ Controller       │ │ Monitor     │ │    │
│  │  │                  │ │                  │ │                  │ │             │ │    │
│  │  │ - Read files     │ │ - Parse YAML     │ │ - Validate DCF   │ │ - Track API │ │    │
│  │  │ - Check syntax   │ │ - Check edges    │ │ - Verify prices  │ │ - Track cost│ │    │
│  │  │ - Check imports  │ │ - Detect cycles  │ │ - Recalculate    │ │ - Track time│ │    │
│  │  │ - Analyze code   │ │ - Audit providers│ │ - Compare values │ │ - Bottleneck│ │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────┘ │    │
│  │                                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                        SPECIALIZED AGENTS (Tool Layer)                           │    │
│  │                                                                                   │    │
│  │  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐   │    │
│  │  │ DCF Modeling Agent   │  │ Market Data Agent    │  │ Validation Agent     │   │    │
│  │  │ dcf_agent.py         │  │ market_data_agent.py │  │ validation_agent.py  │   │    │
│  │  │                      │  │                      │  │                      │   │    │
│  │  │ TOOLS:               │  │ TOOLS:               │  │ VALIDATES:           │   │    │
│  │  │ - DCFCalculator      │  │ - Yahoo Finance API  │  │ - DCF outputs        │   │    │
│  │  │ - FinancialCalculator│  │ - Price fetcher      │  │ - Debate outputs     │   │    │
│  │  │ - MarketDataAPI      │  │ - Financials API     │  │ - Research outputs   │   │    │
│  │  │                      │  │ - Analyst estimates  │  │ - Price consistency  │   │    │
│  │  │ OUTPUTS:             │  │                      │  │                      │   │    │
│  │  │ - VERIFIED DCF model │  │ OUTPUTS:             │  │ OUTPUTS:             │   │    │
│  │  │ - 5 scenarios        │  │ - VERIFIED prices    │  │ - ValidationReport   │   │    │
│  │  │ - PWV calculation    │  │ - Real financials    │  │ - Corrections needed │   │    │
│  │  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘   │    │
│  │                                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                        CALCULATION TOOLS (Foundation)                            │    │
│  │                                                                                   │    │
│  │  agents/tools/                                                                    │    │
│  │  ├── financial_calculator.py                                                     │    │
│  │  │   ├── DCFCalculator - Full DCF with FCF, Terminal Value, NPV                 │    │
│  │  │   ├── FinancialCalculator - WACC, sensitivity tables                         │    │
│  │  │   └── Actual formulas: WACC = (E/V)×Re + (D/V)×Rd×(1-T)                      │    │
│  │  │                                                                               │    │
│  │  ├── market_data_api.py                                                          │    │
│  │  │   ├── MarketDataAPI - Yahoo Finance wrapper                                   │    │
│  │  │   ├── get_quote() - Real-time prices                                          │    │
│  │  │   ├── get_financials() - Historical financials                               │    │
│  │  │   └── verify_price() - Compare claimed vs actual (±2%)                       │    │
│  │  │                                                                               │    │
│  │  └── validation_tools.py                                                         │    │
│  │      ├── ValidationTools - Mathematical validation                               │    │
│  │      ├── validate_dcf_math() - Check calculations                               │    │
│  │      └── validate_wacc() - Verify WACC formula                                  │    │
│  │                                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Chief Engineer Commands

```bash
# Run from project root
python run_chief_engineer.py health      # Check all components
python run_chief_engineer.py report      # Generate system report
python run_chief_engineer.py monitor     # Continuous monitoring (Ctrl+C to stop)
python run_chief_engineer.py validate "6682 HK"  # Validate specific workflow
python run_chief_engineer.py audit       # Audit all YAML workflows
python run_chief_engineer.py dcf AAPL    # Test DCF agent with real data
```

### Integration with YAML Workflow

The new agents integrate with the existing YAML workflow by:

1. **MarketDataAgent** provides verified prices at workflow START
2. **DCFModelingAgent** replaces AI-generated DCF with real calculations
3. **ValidationAgent** validates all AI outputs before final synthesis
4. **ChiefEngineer** monitors the entire workflow for issues

```
YAML Workflow (v4)                    New Specialized Agents
─────────────────────                 ─────────────────────────
START                        ◄──────  MarketDataAgent.fetch_for_workflow()
  │                                   (Injects VERIFIED PRICE at start)
  ▼
[Research Phase]
  │
  ▼
[Debate Phase]
  │
  ▼
Financial Modeler            ◄──────  DCFModelingAgent.build_dcf_model()
  │                                   (Real calculations, not AI guesses)
  ▼
[QC Phase]                   ◄──────  ValidationAgent.validate_dcf_output()
  │                                   (Verify against real market data)
  ▼
END
  │
  └───────────────────────── ◄──────  ChiefEngineer.run_health_check()
                                      (Continuous monitoring)
```

---

## Folder Structure

```
equity-minions/
│
├── brain/                      ◄── Documentation (system design)
│   ├── blueprint.md            # Architecture design v4
│   ├── system_flowchart.md     # THIS FILE - Complete flowcharts
│   ├── idea.txt                # Original project goals
│   ├── housecleaning.md        # Cleanup rules
│   └── investigation_summary.md # System issues found
│
│   └── definitions/            ◄── YAML Workflow Definitions
│   ├── equity_research_v4.yaml # CURRENT (25 nodes, 40 edges)
│   ├── portfolio_workflow.yaml # Multi-equity parallel execution
│   └── subgraphs/              # Reusable workflow components
│
├── workflow/                   ◄── Workflow Engine Code
│   ├── engine.py               # Core workflow executor
│   ├── workflow_loader.py      # YAML parser
│   ├── graph_executor.py       # DAG execution with conditions
│   ├── node_executor.py        # Individual AI agent calls
│   └── visualizer_bridge.py    # WebSocket bridge to visualizer
│
├── agents/                     ◄── AI Agent Code
│   ├── ai_providers.py         # Multi-AI provider wrapper
│   │
│   ├── core/                   # Core infrastructure
│   │   ├── base_agent.py       # BaseAgent class
│   │   ├── spawnable_agent.py  # SpawnableAgent with lifecycle
│   │   ├── agent_registry.py   # Central agent registry
│   │   └── lifecycle.py        # Agent state machine
│   │
│   ├── tools/                  # NEW (v4.2): Real calculation tools
│   │   ├── financial_calculator.py  # DCF math, WACC, FCF, NPV
│   │   ├── market_data_api.py  # Yahoo Finance API
│   │   └── validation_tools.py # Mathematical validation
│   │
│   ├── specialized/            # NEW (v4.2): Tool-equipped agents
│   │   ├── dcf_agent.py        # Real DCF modeling
│   │   ├── market_data_agent.py # Market data fetching
│   │   └── validation_agent.py # AI output validation
│   │
│   ├── oversight/              # NEW (v4.2): Project monitoring
│   │   ├── chief_engineer.py   # Master oversight agent
│   │   ├── component_inspector.py # Code inspection
│   │   ├── workflow_auditor.py # YAML workflow validation
│   │   ├── dcf_quality_controller.py # DCF validation
│   │   └── performance_monitor.py # Metrics tracking
│   │
│   ├── goalkeepers/            # Quality gate agents
│   ├── supervisor/             # Supervisor agents
│   ├── workers/                # Worker agents
│   ├── investigators/          # Debug/audit agents
│   └── [legacy agents]         # Older implementations
│
├── visualizer/                 ◄── Real-time UI
│   ├── live_visualizer_v2.html # CURRENT - Main visualizer
│   ├── portfolio_visualizer.html # Multi-equity view
│   ├── visualizer_bridge.py    # WebSocket server
│   └── serve_visualizer.py     # HTTP server
│
├── reports/                    ◄── OUTPUT: Generated HTML reports
│   ├── index.html              # Portfolio dashboard
│   └── {ticker}_detailed.html  # Per-equity detailed reports
│
├── context/                    ◄── Runtime Data (auto-generated)
│   ├── {ticker}_workflow_result.json  # Workflow execution results
│   ├── {ticker}_context.json   # Research context
│   ├── debates/                # Debate logs
│   │   └── debate_{ticker}.json
│   ├── minions_state.json      # System state
│   └── session_state.json      # Session tracking
│
├── utils/                      ◄── Helper Utilities
│   ├── html_generator.py       # Report HTML generation
│   ├── price_fetcher.py        # Real-time price fetching
│   └── local_research_loader.py
│
├── run_workflow_live.py        ◄── MAIN ENTRY POINT (single equity)
├── run_portfolio_live.py       # Multi-equity parallel runner
├── run_parallel_live.py        # Multiple workflows in parallel
├── run_chief_engineer.py       # NEW (v4.2): Chief Engineer CLI
├── generate_workflow_report.py # HTML report generator
├── prefetch_data.py            # Price prefetcher (Yahoo Finance)
├── config.py                   # API keys, equity list, scenarios
├── list.txt                    # Equity watchlist
└── log.md                      # Development changelog
```

---

## Detailed Tier Flowcharts

### TIER 0-2: Research Phase

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   run_workflow_live.py          run_portfolio_live.py           main.py                 │
│   (Single equity)               (3 equities parallel)           (14 equities batch)     │
│          │                              │                              │                 │
│          └──────────────────────────────┼──────────────────────────────┘                 │
│                                         │                                                │
│                                         ▼                                                │
│                              ┌─────────────────────┐                                     │
│                              │    config.py        │                                     │
│                              │  - API_KEYS         │                                     │
│                              │  - EQUITIES (14)    │                                     │
│                              │  - SCENARIOS        │                                     │
│                              └─────────────────────┘                                     │
│                                         │                                                │
└─────────────────────────────────────────┼────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 0: PRICE PREFETCH                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────┐                                                           │
│   │   prefetch_data.py      │◄─── Fetches REAL prices from Yahoo Finance               │
│   │   - fetch_price_yfinance│     BEFORE workflow starts                               │
│   │   - build_price_context │                                                           │
│   └───────────┬─────────────┘                                                           │
│               │                                                                          │
│               ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐                   │
│   │ VERIFIED MARKET DATA                                            │                   │
│   │ VERIFIED CURRENT PRICE: HKD 52.30                              │                   │
│   │ DATA CONFIDENCE: HIGH                                           │                   │
│   │ CRITICAL: Use this price, NOT hallucinated prices               │                   │
│   └─────────────────────────────────────────────────────────────────┘                   │
│                                                                                          │
└─────────────────────────────────────────┼────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW EXECUTION ENGINE                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   workflow/workflow_loader.py ──► Load equity_research_v4.yaml                          │
│              │                                                                           │
│              ▼                                                                           │
│   workflow/graph_executor.py ──► Execute DAG with conditional edges                     │
│              │                                                                           │
│              ▼                                                                           │
│   workflow/node_executor.py ──► Execute individual AI agents                            │
│                                                                                          │
└─────────────────────────────────────────┼────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 0: ORCHESTRATION                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────┐                                                                           │
│   │  START  │ (passthrough node)                                                        │
│   └────┬────┘                                                                           │
│        │                                                                                 │
│        ▼                                                                                 │
│   ┌─────────────────────┐                                                               │
│   │ Research Supervisor │ (GPT-4o)                                                      │
│   │ - Create research   │                                                               │
│   │   plan              │                                                               │
│   │ - Set expected      │                                                               │
│   │   price range       │                                                               │
│   └─────────┬───────────┘                                                               │
│             │                                                                            │
│             │ triggers 4 parallel nodes                                                  │
│             │                                                                            │
└─────────────┼────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 1: DATA COLLECTION (PARALLEL)                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────┐ │
│   │ Market Data       │  │ Industry Deep     │  │ Company Deep      │  │ Data        │ │
│   │ Collector         │  │ Dive              │  │ Dive              │  │ Verifier    │ │
│   │ (Gemini-2.0)      │  │ (GPT-4o)          │  │ (GPT-4o)          │  │ (GPT-4o)    │ │
│   │                   │  │                   │  │                   │  │             │ │
│   │ TOOLS: web_search │  │ TOOLS: web_search │  │ TOOLS: web_search │  │ INDEPENDENT │ │
│   │                   │  │                   │  │                   │  │ VERIFICATION│ │
│   │ Collects:         │  │ Analyzes:         │  │ Analyzes:         │  │             │ │
│   │ - Current price   │  │ - Industry TAM    │  │ - Business model  │  │ Must check  │ │
│   │ - Market cap      │  │ - Growth drivers  │  │ - Competitive moat│  │ VERIFIED    │ │
│   │ - Volume          │  │ - Competition     │  │ - Management      │  │ price       │ │
│   │ - 52-week range   │  │ - Regulations     │  │ - Financials      │  │             │ │
│   └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘  └──────┬──────┘ │
│             │                      │                      │                   │         │
│             └──────────────────────┴──────────────────────┴───────────────────┘         │
│                                           │                                              │
│                                           ▼                                              │
│                              ALL 4 feed into Data Checkpoint                            │
│                                                                                          │
└─────────────────────────────────────────────┼────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 2: DATA QUALITY GATE                                            │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                        DATA CHECKPOINT (GPT-4o)                              │       │
│   │                                                                              │       │
│   │  CHECKS:                                                                     │       │
│   │  1. Company Identity - Is data for the RIGHT company?                       │       │
│   │  2. Price Verification - Does collector price match verified price?         │       │
│   │  3. Market Cap Sanity - Is market cap reasonable?                           │       │
│   │  4. Completeness - Do we have all required data?                            │       │
│   │                                                                              │       │
│   │  OUTPUTS:                                                                    │       │
│   │  - "DATA: VERIFIED" → proceed to Debate Moderator                           │       │
│   │  - "DATA: FAILED" → loop back to Research Supervisor                        │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
│                          ┌───────────────────┴───────────────────┐                      │
│                          │                                       │                      │
│                   DATA: VERIFIED                           DATA: FAILED                 │
│                          │                                       │                      │
│                          ▼                                       ▼                      │
│                   Debate Moderator              ◄──────── Research Supervisor           │
│                                                           (LOOP BACK)                   │
│                                                                                          │
└─────────────────────────────────────────────┼────────────────────────────────────────────┘
                                              │
                                              ▼
                                    [Continue to TIER 3]
```

### TIER 3: Debate Phase

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 3: DEBATE SYSTEM                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                      DEBATE MODERATOR (GPT-4o)                               │       │
│   │  - Summarizes research findings                                              │       │
│   │  - Confirms VERIFIED current price                                           │       │
│   │  - Poses questions for debate                                                │       │
│   │  - Sets debate ground rules                                                  │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
│                          triggers parallel Bull/Bear R1                                 │
│                                              │                                           │
│             ┌────────────────────────────────┴────────────────────────────────┐         │
│             │                                                                  │         │
│             ▼                                                                  ▼         │
│   ┌───────────────────────┐                                      ┌───────────────────┐ │
│   │ BULL ADVOCATE R1      │                                      │ BEAR ADVOCATE R1  │ │
│   │ (Grok-4 / xAI)        │                                      │ (Qwen-Max/Alibaba)│ │
│   │                       │                                      │                   │ │
│   │ 5 bullish arguments:  │                                      │ 5 bearish args:   │ │
│   │ - Growth potential    │                                      │ - Valuation risk  │ │
│   │ - Market position     │                                      │ - Competition     │ │
│   │ - Innovation          │                                      │ - Execution risk  │ │
│   │ - Management quality  │                                      │ - Market headwinds│ │
│   │ - Financial strength  │                                      │ - Regulatory risk │ │
│   └───────────┬───────────┘                                      └─────────┬─────────┘ │
│               │                                                            │            │
│               └────────────────────────┬───────────────────────────────────┘            │
│                                        │                                                │
│                                        ▼                                                │
│                         ┌───────────────────────────────┐                               │
│                         │    DEVIL'S ADVOCATE (GPT-4o)  │                               │
│                         │                               │                               │
│                         │  Challenge BOTH sides:        │                               │
│                         │  - What evidence is weak?     │                               │
│                         │  - What assumptions are wrong?│                               │
│                         │  - Black swan scenarios?      │                               │
│                         │  - Hidden risks/opportunities?│                               │
│                         └───────────────┬───────────────┘                               │
│                                         │                                               │
│             ┌───────────────────────────┴───────────────────────────┐                   │
│             │                                                       │                   │
│             ▼                                                       ▼                   │
│   ┌───────────────────────┐                           ┌───────────────────────┐         │
│   │ BULL ADVOCATE R2      │                           │ BEAR ADVOCATE R2      │         │
│   │ (Grok-4 / xAI)        │                           │ (Qwen-Max / Alibaba)  │         │
│   │                       │                           │                       │         │
│   │ - Rebuttals to bear   │                           │ - Rebuttals to bull   │         │
│   │ - Counter-arguments   │                           │ - Counter-arguments   │         │
│   │ - DCF input proposal: │                           │ - DCF input proposal: │         │
│   │   * Growth rates      │                           │   * Growth rates      │         │
│   │   * Margins           │                           │   * Margins           │         │
│   │   * Probabilities     │                           │   * Probabilities     │         │
│   └───────────┬───────────┘                           └───────────┬───────────┘         │
│               │                                                   │                     │
│               └───────────────────────┬───────────────────────────┘                     │
│                                       │                                                 │
│                                       ▼                                                 │
│                         ┌───────────────────────────────┐                               │
│                         │    DEBATE CRITIC (GPT-4o)     │                               │
│                         │                               │                               │
│                         │  - Score Bull side (1-10)     │                               │
│                         │  - Score Bear side (1-10)     │                               │
│                         │  - Identify strongest args    │                               │
│                         │  - Synthesize DCF inputs      │                               │
│                         │  - Confirm price for DCF      │                               │
│                         │  - Set scenario probabilities │                               │
│                         └───────────────┬───────────────┘                               │
│                                         │                                               │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          │
                                          ▼
                                [Continue to TIER 4]
```

### TIER 4-5: Valuation Phase

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 4: PRE-MODEL VALIDATION                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                   PRE-MODEL VALIDATOR (GPT-4o)                               │       │
│   │                                                                              │       │
│   │  VALIDATES BEFORE DCF:                                                       │       │
│   │  1. Is the price being used the VERIFIED price?                             │       │
│   │  2. Are growth rates reasonable for this industry?                          │       │
│   │  3. Are margin assumptions realistic?                                        │       │
│   │  4. Is WACC calculated correctly?                                           │       │
│   │  5. Is terminal growth rate < GDP growth?                                   │       │
│   │                                                                              │       │
│   │  OUTPUTS:                                                                    │       │
│   │  - "INPUTS: VALIDATED" → proceed to Financial Modeler                       │       │
│   │  - "INPUTS: REVIEW NEEDED" → loop back to Debate Critic                     │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
└─────────────────────────────────────────────┼───────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 5: DCF VALUATION                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                    FINANCIAL MODELER (Gemini-2.0-flash)                      │       │
│   │                                                                              │       │
│   │  BUILDS DCF MODEL:                                                           │       │
│   │  - 10-year revenue projections                                              │       │
│   │  - Margin trajectories                                                       │       │
│   │  - WACC calculation                                                          │       │
│   │  - Terminal value                                                            │       │
│   │                                                                              │       │
│   │  5 SCENARIOS:                                                                │       │
│   │  ┌────────────┬────────────┬────────────┬────────────┬────────────────┐     │       │
│   │  │ Super Bear │    Bear    │    Base    │    Bull    │   Super Bull   │     │       │
│   │  │    5%      │    15%     │    40%     │    25%     │      15%       │     │       │
│   │  │  -30% TV   │  -15% TV   │  Base TV   │  +15% TV   │    +30% TV     │     │       │
│   │  └────────────┴────────────┴────────────┴────────────┴────────────────┘     │       │
│   │                                   │                                          │       │
│   │                                   ▼                                          │       │
│   │                  Probability-Weighted Value (PWV)                            │       │
│   │                                                                              │       │
│   │  MUST USE: VERIFIED current price from Pre-Model Validator                  │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
│                          triggers 3 parallel QC agents                                  │
│                                              │                                           │
│        ┌─────────────────────────────────────┼─────────────────────────────────────┐    │
│        │                                     │                                     │    │
│        ▼                                     ▼                                     ▼    │
│  ┌──────────────────┐              ┌──────────────────┐              ┌──────────────┐  │
│  │ ASSUMPTION       │              │ COMPARABLE       │              │ SENSITIVITY  │  │
│  │ CHALLENGER       │              │ VALIDATOR        │              │ AUDITOR      │  │
│  │ (GPT-4o)         │              │ (Gemini-2.0)     │              │ (GPT-4o)     │  │
│  │                  │              │                  │              │              │  │
│  │ Stress-test each │              │ Compare to peer  │              │ Test model   │  │
│  │ assumption:      │              │ valuations:      │              │ robustness:  │  │
│  │ - Growth rates   │              │ - P/E ratios     │              │ - WACC ±1%   │  │
│  │ - Margins        │              │ - EV/Revenue     │              │ - Growth ±2% │  │
│  │ - WACC           │              │ - EV/EBITDA      │              │ - Margin ±3% │  │
│  │ - Terminal value │              │ - PEG ratio      │              │ - Terminal   │  │
│  └────────┬─────────┘              └────────┬─────────┘              └──────┬───────┘  │
│           │                                 │                               │          │
│           └─────────────────────────────────┴───────────────────────────────┘          │
│                                             │                                           │
│                                             ▼                                           │
│                          ┌───────────────────────────────┐                              │
│                          │  VALUATION COMMITTEE (GPT-4o) │                              │
│                          │                               │                              │
│                          │  CHECKS:                      │                              │
│                          │  - Correct price used?        │                              │
│                          │  - No CRITICAL issues?        │                              │
│                          │  - Debate insights included?  │                              │
│                          │  - Scenarios reasonable?      │                              │
│                          │                               │                              │
│                          │  OUTPUTS:                     │                              │
│                          │  - "VALUATION: APPROVED"      │                              │
│                          │  - "VALUATION: REVISE"        │                              │
│                          └───────────────┬───────────────┘                              │
│                                          │                                              │
└──────────────────────────────────────────┼──────────────────────────────────────────────┘
                                           │
                                           ▼
                                 [Continue to TIER 6]
```

### TIER 6: Quality Control

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 6: QUALITY GATES                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│        ┌────────────────────────────────┬────────────────────────────────┐              │
│        │                                │                                │              │
│        ▼                                ▼                                ▼              │
│  ┌──────────────────┐          ┌──────────────────┐          ┌────────────────────┐    │
│  │ DATA VERIFICATION│          │ LOGIC VERIFICATION│          │ BIRD'S EYE        │    │
│  │ GATE (GPT-4o)    │          │ GATE (GPT-4o)     │          │ REVIEWER (GPT-4o) │    │
│  │                  │          │                   │          │                    │    │
│  │ CHECKS:          │          │ CHECKS:           │          │ HOLISTIC REVIEW:   │    │
│  │ - Price match?   │          │ - Recommendation  │          │ - Does this make   │    │
│  │ - Market cap?    │          │   matches value?  │          │   sense overall?   │    │
│  │ - Internal       │          │ - Bull/bear       │          │ - Any red flags?   │    │
│  │   consistency?   │          │   arguments       │          │ - Contradictions?  │    │
│  │ - Data sources   │          │   consistent?     │          │ - Missing pieces?  │    │
│  │   reliable?      │          │ - Logic sound?    │          │                    │    │
│  │                  │          │ - Math correct?   │          │ CAN ROUTE BACK TO: │    │
│  │ OUTPUT:          │          │                   │          │ - Data Checkpoint   │    │
│  │ PASS / FAIL      │          │ OUTPUT:           │          │ - Debate Moderator  │    │
│  │                  │          │ PASS / FAIL       │          │ - Financial Modeler │    │
│  └────────┬─────────┘          └────────┬──────────┘          └──────────┬──────────┘   │
│           │                             │                                │              │
│           └─────────────────────────────┴────────────────────────────────┘              │
│                                                │                                         │
│                                                ▼                                         │
│                          ┌───────────────────────────────┐                              │
│                          │  QUALITY SUPERVISOR (GPT-4o)  │                              │
│                          │                               │                              │
│                          │  AGGREGATES ALL GATE RESULTS  │                              │
│                          │                               │                              │
│                          │  ROUTING DECISION:            │                              │
│                          │  ┌─────────────────────────┐  │                              │
│                          │  │ All PASS                │  │                              │
│                          │  │        │                │  │                              │
│                          │  │        ▼                │  │                              │
│                          │  │   Synthesizer           │  │                              │
│                          │  └─────────────────────────┘  │                              │
│                          │  ┌─────────────────────────┐  │                              │
│                          │  │ Data FAIL               │  │                              │
│                          │  │        │                │  │                              │
│                          │  │        ▼                │  │                              │
│                          │  │ Research Supervisor     │  │                              │
│                          │  │   (loop back)           │  │                              │
│                          │  └─────────────────────────┘  │                              │
│                          │  ┌─────────────────────────┐  │                              │
│                          │  │ Logic FAIL              │  │                              │
│                          │  │        │                │  │                              │
│                          │  │        ▼                │  │                              │
│                          │  │ Financial Modeler       │  │                              │
│                          │  │   (loop back)           │  │                              │
│                          │  └─────────────────────────┘  │                              │
│                          └───────────────┬───────────────┘                              │
│                                          │                                              │
└──────────────────────────────────────────┼──────────────────────────────────────────────┘
                                           │
                                           ▼
                                 [Continue to TIER 7]
```

### TIER 7: Synthesis & Output

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    TIER 7: SYNTHESIS & OUTPUT                                           │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                       SYNTHESIZER (GPT-4o)                                   │       │
│   │                                                                              │       │
│   │  CREATES FINAL REPORT STRUCTURE:                                             │       │
│   │                                                                              │       │
│   │  1. Executive Summary                                                        │       │
│   │     - Key thesis, rating, price target                                      │       │
│   │                                                                              │       │
│   │  2. Investment Thesis                                                        │       │
│   │     - Bull case summary                                                      │       │
│   │     - Bear case summary                                                      │       │
│   │                                                                              │       │
│   │  3. Company Overview                                                         │       │
│   │     - Business model, products, markets                                     │       │
│   │                                                                              │       │
│   │  4. Industry Analysis                                                        │       │
│   │     - TAM, growth drivers, competition                                      │       │
│   │                                                                              │       │
│   │  5. Financial Analysis                                                       │       │
│   │     - Historical performance, projections                                   │       │
│   │                                                                              │       │
│   │  6. Valuation (5 scenarios)                                                 │       │
│   │     - DCF methodology, WACC, scenarios table                               │       │
│   │     - Probability-weighted target price                                     │       │
│   │                                                                              │       │
│   │  7. Risks                                                                    │       │
│   │     - Key risks with probabilities and impact                              │       │
│   │                                                                              │       │
│   │  8. Recommendation                                                           │       │
│   │     - BUY / HOLD / SELL with rationale                                      │       │
│   │     - Catalysts and monitoring triggers                                     │       │
│   │                                                                              │       │
│   │  MUST USE: VERIFIED current price throughout                                │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
│                                              ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────────┐       │
│   │                 generate_workflow_report.py                                  │       │
│   │                                                                              │       │
│   │  - Extracts data from all node outputs                                      │       │
│   │  - Generates styled HTML report                                             │       │
│   │  - Calculates upside/downside percentages                                   │       │
│   │  - Creates scenario visualization tables                                    │       │
│   │  - Saves to reports/{ticker}_detailed.html                                  │       │
│   └─────────────────────────────────────────────────────────────────────────────┘       │
│                                              │                                           │
│                               ┌──────────────┴──────────────┐                           │
│                               ▼                             ▼                           │
│                ┌──────────────────────────┐  ┌──────────────────────────────────┐      │
│                │ context/                 │  │ reports/                          │      │
│                │ {ticker}_workflow_result │  │ index.html (portfolio dashboard)  │      │
│                │         .json            │  │ {ticker}_detailed.html            │      │
│                │                          │  │ {ticker}.html (summary)           │      │
│                │ Contains:                │  │                                    │      │
│                │ - All node outputs       │  │ Contains:                          │      │
│                │ - Execution timestamps   │  │ - Full research report             │      │
│                │ - Routing decisions      │  │ - Interactive charts               │      │
│                │ - Debug information      │  │ - Scenario tables                  │      │
│                └──────────────────────────┘  └──────────────────────────────────┘      │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
USER INPUT: "LEGN US"
      │
      ▼
┌─────────────────────┐
│  prefetch_data.py   │ ◄── MUST fetch real price FIRST
│  Price: USD 19.34   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ VERIFIED PRICE      │
│ injected into       │
│ task_prompt         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                   WORKFLOW v4                           │
│                                                         │
│  START → Research Supervisor                            │
│           ↓                                             │
│  [Market Data] [Industry] [Company] [Data Verifier]    │
│           ↓                                             │
│  Data Checkpoint (GATE) ─── FAIL ──► Loop back         │
│           ↓ PASS                                        │
│  Debate Moderator                                       │
│           ↓                                             │
│  [Bull R1] [Bear R1] → Devil's Advocate                │
│           ↓                                             │
│  [Bull R2] [Bear R2] → Debate Critic                   │
│           ↓                                             │
│  Pre-Model Validator ─── FAIL ──► Loop back            │
│           ↓ PASS                                        │
│  Financial Modeler                                      │
│           ↓                                             │
│  [Assumption] [Comparable] [Sensitivity]               │
│           ↓                                             │
│  Valuation Committee ─── REVISE ──► Loop back          │
│           ↓ APPROVED                                    │
│  [Data Gate] [Logic Gate] [Bird's Eye]                 │
│           ↓                                             │
│  Quality Supervisor ─── ROUTE BACK ──► Any tier        │
│           ↓ PASS                                        │
│  Synthesizer                                            │
│           ↓                                             │
│  FINAL OUTPUT                                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│ context/{ticker}_   │
│ workflow_result.json│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ generate_workflow_  │
│ report.py           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ reports/{ticker}_   │
│ detailed.html       │
└─────────────────────┘
```

---

## Key Design Principles

### 1. DCF After Debates
Financial modeling happens AFTER all debate rounds complete, incorporating both bull and bear insights into the valuation assumptions.

### 2. Multi-AI Diversity
5 different AI providers (OpenAI, xAI, Alibaba, Google, Anthropic) ensure diverse perspectives and prevent groupthink. Each provider has a designated "personality":
- **Grok-4 (xAI)**: Optimistic bull advocate
- **Qwen-Max (Alibaba)**: Risk-focused bear advocate
- **GPT-4o (OpenAI)**: Balanced orchestrator and critic
- **Gemini (Google)**: Data-driven quantitative analysis

### 3. Continuous Quality Control
Multiple checkpoints throughout the workflow:
- **Data Checkpoint** (Tier 2): Validates research data
- **Pre-Model Validator** (Tier 4): Validates DCF inputs
- **Valuation Committee** (Tier 5): Validates DCF outputs
- **Quality Gates** (Tier 6): Final validation before synthesis

### 4. Loop-Back Routing
Failed gates can route back to earlier stages for correction:
- Data issues → Research Supervisor
- Logic issues → Financial Modeler
- Bird's Eye concerns → Any appropriate tier

### 5. Price Verification
Real prices are fetched BEFORE workflow starts and validated at every tier to prevent hallucination.

### 6. Parallel Execution
Where possible, agents run in parallel to reduce total execution time:
- 4 parallel data collectors (Tier 1)
- 2 parallel debate advocates (Tier 3, both rounds)
- 3 parallel QC agents (Tier 5)
- 3 parallel quality gates (Tier 6)

---

## Known Issues by Tier

### TIER 0: Orchestration
| Issue | Severity | Status |
|-------|----------|--------|
| Research Supervisor doesn't always pass ticker to collectors | HIGH | OPEN |

### TIER 1: Data Collection
| Issue | Severity | Status |
|-------|----------|--------|
| Market Data Collector often asks for ticker instead of searching | CRITICAL | OPEN |
| Gemini web_search tool may not execute | CRITICAL | OPEN |
| Data Verifier was not triggered (v3 workflow) | CRITICAL | FIXED (use v4) |
| No prefetch of real prices | HIGH | FIXED (prefetch_data.py) |

### TIER 2: Data Quality Gate
| Issue | Severity | Status |
|-------|----------|--------|
| Data Checkpoint was completely skipped (v3) | CRITICAL | FIXED (use v4) |
| Price verification logic exists but untested | MEDIUM | OPEN |

### TIER 3: Debate System
| Issue | Severity | Status |
|-------|----------|--------|
| Debate uses hallucinated prices from training data | CRITICAL | FIXED (v4.2: MarketDataAgent injects verified prices) |
| Bull/Bear advocates work correctly | - | OK |
| Devil's Advocate works correctly | - | OK |

### TIER 4: Pre-Model Validation
| Issue | Severity | Status |
|-------|----------|--------|
| Pre-Model Validator was skipped (v3) | HIGH | FIXED (use v4) |

### TIER 5: DCF Valuation
| Issue | Severity | Status |
|-------|----------|--------|
| Financial Modeler uses hallucinated prices | CRITICAL | FIXED (v4.2: DCFModelingAgent with real API) |
| Scenarios calculated correctly | - | OK |
| QC agents work but receive bad input | HIGH | FIXED (v4.2: ValidationAgent validates inputs) |
| No real DCF calculation, just AI numbers | CRITICAL | FIXED (v4.2: DCFCalculator with formulas) |

### TIER 6: Quality Gates
| Issue | Severity | Status |
|-------|----------|--------|
| Bird's Eye Reviewer was skipped (v3) | HIGH | FIXED (use v4) |
| Quality Supervisor routing works | - | OK |
| Gates don't catch price errors (data already wrong) | HIGH | OPEN |

### TIER 7: Synthesis
| Issue | Severity | Status |
|-------|----------|--------|
| Synthesizer was never reached | HIGH | OPEN |
| Report generator uses wrong upside calc | MEDIUM | FIXED |

---

## Files to Investigate

| File | Purpose | Investigation Priority |
|------|---------|----------------------|
| workflow/node_executor.py | Executes AI agents | HIGH - check tool execution |
| agents/ai_providers.py | AI provider interface | HIGH - check Gemini tools |
| workflow/graph_executor.py | DAG execution | HIGH - check edge routing |
| workflow/definitions/equity_research_v4.yaml | Workflow definition | MEDIUM - verify all edges |
| prefetch_data.py | Price prefetch | HIGH - verify integration |
| run_workflow_live.py | Entry point | MEDIUM - verify prefetch call |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v4.2 | 2026-01-24 | Added tool-equipped agents (DCF, MarketData, Validation), Chief Engineer oversight system, real calculation tools |
| v4.0 | 2026-01-23 | Combined flowchart with AI providers map, folder structure, design principles |
| v3.0 | 2026-01-23 | Added detailed tier flowcharts, known issues tables |
| v2.0 | 2026-01-22 | Initial system flowchart |
