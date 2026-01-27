# Equity Minions - Detailed System Flowcharts

**Version**: 4.2
**Last Updated**: 2026-01-27
**Purpose**: Complete visual documentation of the Multi-AI Equity Research System

---

## Table of Contents

1. [Master Overview Flowchart](#1-master-overview-flowchart)
2. [Section A: Entry & Price Prefetch](#2-section-a-entry--price-prefetch)
3. [Section B: Workflow Engine](#3-section-b-workflow-engine)
4. [Section C: Research Phase (Tier 0-2)](#4-section-c-research-phase-tier-0-2)
5. [Section D: Debate Phase (Tier 3)](#5-section-d-debate-phase-tier-3)
6. [Section E: Valuation Phase (Tier 4-5)](#6-section-e-valuation-phase-tier-4-5)
7. [Section F: Quality Control (Tier 6)](#7-section-f-quality-control-tier-6)
8. [Section G: Output Generation (Tier 7)](#8-section-g-output-generation-tier-7)
9. [Agent Hierarchy Diagram](#9-agent-hierarchy-diagram)
10. [Data Flow Diagram](#10-data-flow-diagram)

---

## 1. Master Overview Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MASTER OVERVIEW                                       │
│                          Equity Minions Research System v4.2                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │   USER INPUT    │
                                    │  "Research      │
                                    │   TICKER"       │
                                    └────────┬────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SECTION A: ENTRY & PRICE PREFETCH                                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────────┐  │
│  │ run_workflow_   │───▶│   config.py     │───▶│      prefetch_data.py               │  │
│  │ live.py         │    │ (API keys,      │    │  • Yahoo Finance API                │  │
│  │                 │    │  equities)      │    │  • VERIFIED PRICE injection         │  │
│  └─────────────────┘    └─────────────────┘    └──────────────────┬──────────────────┘  │
└──────────────────────────────────────────────────────────────────┬──────────────────────┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SECTION B: WORKFLOW ENGINE                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │  workflow_loader.py ──▶ equity_research_v4.yaml ──▶ graph_executor.py           │    │
│  │       (YAML)                 (25 nodes)                  (DAG)                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┬──────────────────────┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SECTION C: RESEARCH PHASE (Tier 0-2)                                                    │
│                                                                                          │
│  ┌──────────────┐    ┌────────────────────────────────────┐    ┌──────────────────┐     │
│  │    START     │───▶│     Research Supervisor            │───▶│  4 PARALLEL      │     │
│  │              │    │         (GPT-4o)                   │    │  COLLECTORS      │     │
│  └──────────────┘    └────────────────────────────────────┘    └────────┬─────────┘     │
│                                                                         │               │
│                                                                         ▼               │
│                                                              ┌──────────────────┐       │
│                                                              │ DATA CHECKPOINT  │       │
│                                                              │     (GATE)       │       │
│                                                              └────────┬─────────┘       │
└──────────────────────────────────────────────────────────────────────┬──────────────────┘
                                                                       │
                          ┌────────────────────────────────────────────┴────────┐
                          │ DATA: VERIFIED                         DATA: FAILED │
                          ▼                                                     ▼
┌─────────────────────────────────────────────────────┐              ┌──────────────────┐
│  SECTION D: DEBATE PHASE (Tier 3)                   │              │   LOOP BACK TO   │
│                                                     │              │   RESEARCH       │
│  Moderator ──▶ Bull R1 ──▶ Devil's ──▶ Bull R2     │              │   SUPERVISOR     │
│            ──▶ Bear R1 ──▶ Advocate ──▶ Bear R2    │              └──────────────────┘
│                              │                      │
│                              ▼                      │
│                       Debate Critic                 │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SECTION E: VALUATION PHASE (Tier 4-5)                                                   │
│                                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │  Pre-Model       │───▶│  Financial       │───▶│  3 PARALLEL QC AGENTS            │   │
│  │  Validator       │    │  Modeler         │    │  • Assumption Challenger         │   │
│  │  (GPT-4o)        │    │  (Python DCF)    │    │  • Comparable Validator          │   │
│  └──────────────────┘    └──────────────────┘    │  • Sensitivity Auditor           │   │
│                                                   └────────────────┬─────────────────┘   │
│                                                                    ▼                     │
│                                                   ┌──────────────────────────────────┐   │
│                                                   │     VALUATION COMMITTEE          │   │
│                                                   │  APPROVED / REVISE               │   │
│                                                   └────────────────┬─────────────────┘   │
└──────────────────────────────────────────────────────────────────┬──────────────────────┘
                                                                   │
                           ┌───────────────────────────────────────┴────────┐
                           │ APPROVED                              REVISE   │
                           ▼                                                ▼
┌─────────────────────────────────────────────────────┐     ┌──────────────────────────┐
│  SECTION F: QUALITY CONTROL (Tier 6)                │     │   LOOP BACK TO           │
│                                                     │     │   FINANCIAL MODELER      │
│  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │     └──────────────────────────┘
│  │Data        │ │Logic       │ │Bird's Eye      │  │
│  │Verification│ │Verification│ │Reviewer        │  │
│  │Gate        │ │Gate        │ │                │  │
│  └─────┬──────┘ └─────┬──────┘ └───────┬────────┘  │
│        └──────────────┴────────────────┘           │
│                       │                            │
│                       ▼                            │
│              ┌─────────────────┐                   │
│              │Quality          │                   │
│              │Supervisor       │                   │
│              │ROUTE DECISION   │                   │
│              └────────┬────────┘                   │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │ ALL PASS      │ DATA FAIL     │ LOGIC FAIL    │
        ▼               ▼               ▼               │
┌───────────────┐ ┌───────────┐ ┌───────────────┐      │
│ SECTION G:    │ │Loop to    │ │Loop to        │      │
│ OUTPUT        │ │Research   │ │Financial      │      │
│ GENERATION    │ │Supervisor │ │Modeler        │      │
└───────┬───────┘ └───────────┘ └───────────────┘      │
        │                                               │
        ▼                                               │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SECTION G: OUTPUT GENERATION (Tier 7)                                                   │
│                                                                                          │
│  ┌──────────────────┐    ┌──────────────────────────┐    ┌─────────────────────────┐    │
│  │   Synthesizer    │───▶│ generate_workflow_       │───▶│   HTML REPORTS          │    │
│  │   (GPT-4o)       │    │ report.py                │    │   • index.html          │    │
│  │                  │    │                          │    │   • {ticker}_detailed   │    │
│  └──────────────────┘    └──────────────────────────┘    └─────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │      END        │
                                    │  Research       │
                                    │  Complete       │
                                    └─────────────────┘
```

---

## 2. Section A: Entry & Price Prefetch

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        SECTION A: ENTRY & PRICE PREFETCH                                 │
│                        ─────────────────────────────────                                 │
│  Purpose: Initialize system, load configuration, fetch VERIFIED market price            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │     USER COMMAND      │
                              │                       │
                              │ python run_workflow_  │
                              │ live.py "6682 HK"     │
                              └───────────┬───────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────┐
                    │           ENTRY POINTS                   │
                    ├─────────────────────────────────────────┤
                    │                                         │
                    │  ┌─────────────────┐  ┌──────────────┐ │
                    │  │run_workflow_    │  │run_parallel_ │ │
                    │  │live.py          │  │live.py       │ │
                    │  │(Single ticker)  │  │(Multiple)    │ │
                    │  └────────┬────────┘  └──────┬───────┘ │
                    │           │                  │         │
                    │           └────────┬─────────┘         │
                    │                    │                   │
                    └────────────────────┼───────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │              config.py                   │
                    ├─────────────────────────────────────────┤
                    │                                         │
                    │  API_KEYS = {                           │
                    │      "openai": "sk-...",                │
                    │      "google": "AIza...",               │
                    │      "xai": "xai-...",                  │
                    │      "dashscope": "sk-..."              │
                    │  }                                      │
                    │                                         │
                    │  EQUITIES = {                           │
                    │      "6682 HK": {                       │
                    │          "name": "Tongcheng Travel",    │
                    │          "sector": "Consumer",          │
                    │          "industry": "OTA"              │
                    │      },                                 │
                    │      ...                                │
                    │  }                                      │
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           prefetch_data.py                                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         prefetch_market_data(ticker)                              │   │
│  │                                                                                   │   │
│  │  1. Parse ticker format (e.g., "6682 HK" → "6682.HK" for Yahoo Finance)          │   │
│  │  2. Call Yahoo Finance API (yfinance library)                                    │   │
│  │  3. Extract:                                                                      │   │
│  │     • Current price (REAL-TIME)                                                  │   │
│  │     • Market cap                                                                 │   │
│  │     • Revenue TTM                                                                │   │
│  │     • EBIT / Operating Income                                                    │   │
│  │     • Beta                                                                       │   │
│  │     • Shares outstanding                                                         │   │
│  │     • Analyst targets (broker consensus)                                         │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                                │
│                                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         build_price_context(price_data)                           │   │
│  │                                                                                   │   │
│  │  Returns formatted string:                                                        │   │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  ╔══════════════════════════════════════════════════════════════════════╗  │  │   │
│  │  │  ║ VERIFIED MARKET DATA - USE THIS PRICE                               ║  │  │   │
│  │  │  ╠══════════════════════════════════════════════════════════════════════╣  │  │   │
│  │  │  ║ VERIFIED CURRENT PRICE: HKD 52.30                                   ║  │  │   │
│  │  │  ║ DATA CONFIDENCE: HIGH                                               ║  │  │   │
│  │  │  ║ CRITICAL: All agents MUST use this verified price                   ║  │  │   │
│  │  │  ║           Do NOT hallucinate or use training data prices            ║  │  │   │
│  │  │  ╚══════════════════════════════════════════════════════════════════════╝  │  │   │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ Price context injected into task_prompt
                                         ▼
                              ┌───────────────────────┐
                              │   TO WORKFLOW ENGINE  │
                              │   (Section B)         │
                              └───────────────────────┘
```

---

## 3. Section B: Workflow Engine

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SECTION B: WORKFLOW ENGINE                                     │
│                           ──────────────────────────                                     │
│  Purpose: Load YAML workflow definition and execute nodes as a DAG                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                         ┌────────────────────────────┐
                         │  FROM PRICE PREFETCH       │
                         │  (task_prompt with         │
                         │   verified price)          │
                         └─────────────┬──────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         workflow/workflow_loader.py                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  load("equity_research_v4")                                                             │
│       │                                                                                  │
│       ▼                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │  workflow/definitions/equity_research_v4.yaml                                     │   │
│  │                                                                                   │   │
│  │  graph:                                                                           │   │
│  │    id: equity_research_v4                                                        │   │
│  │    max_iterations: 40                                                            │   │
│  │                                                                                   │   │
│  │    nodes:                          edges:                                        │   │
│  │      - id: START                     - from: START                               │   │
│  │      - id: Research Supervisor         to: Research Supervisor                   │   │
│  │      - id: Market Data Collector       trigger: true                             │   │
│  │      - id: Industry Deep Dive                                                    │   │
│  │      - id: Company Deep Dive         - from: Research Supervisor                 │   │
│  │      - id: Data Verifier               to: Market Data Collector                 │   │
│  │      - id: Data Checkpoint             trigger: true                             │   │
│  │      - id: Debate Moderator            carry_data: true                          │   │
│  │      - id: Bull Advocate R1          ...                                         │   │
│  │      - id: Bear Advocate R1                                                      │   │
│  │      ... (25 nodes total)                                                        │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│  Returns: GraphConfig object with nodes, edges, start_nodes, end_nodes                  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         workflow/graph_executor.py                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  class GraphExecutor:                                                                    │
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │  INITIALIZATION                                                                   │   │
│  │                                                                                   │   │
│  │  1. Build execution layers (topological sort)                                    │   │
│  │  2. Initialize NodeState for each node                                           │   │
│  │  3. Set MAX_ITERATIONS = 36                                                      │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                                  │
│                                       ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │  EXECUTION LOOP                                                                   │   │
│  │                                                                                   │   │
│  │  while iteration < MAX_ITERATIONS:                                               │   │
│  │      │                                                                            │   │
│  │      ├──▶ Find all triggered nodes                                               │   │
│  │      │                                                                            │   │
│  │      ├──▶ Execute triggered nodes in PARALLEL                                    │   │
│  │      │    ┌────────────────────────────────────────────────────┐                 │   │
│  │      │    │  asyncio.gather(*[execute_node(n) for n in nodes]) │                 │   │
│  │      │    └────────────────────────────────────────────────────┘                 │   │
│  │      │                                                                            │   │
│  │      ├──▶ Process outgoing edges (evaluate conditions)                           │   │
│  │      │                                                                            │   │
│  │      ├──▶ Trigger downstream nodes (if conditions met)                           │   │
│  │      │                                                                            │   │
│  │      └──▶ Check if workflow is complete (end nodes executed)                     │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         workflow/node_executor.py                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  get_executor(node_config) → Returns appropriate executor:                              │
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                                   │   │
│  │  IF node_id == "Financial Modeler":                                              │   │
│  │      ┌────────────────────────────────────────────────────────────┐              │   │
│  │      │  PythonValuationExecutor                                   │              │   │
│  │      │  • Uses REAL Python math (DCFEngine, CompsEngine, etc.)   │              │   │
│  │      │  • NOT AI hallucination                                    │              │   │
│  │      │  • Extracts assumptions from prior debate outputs          │              │   │
│  │      └────────────────────────────────────────────────────────────┘              │   │
│  │                                                                                   │   │
│  │  ELIF node_type == "passthrough":                                                │   │
│  │      ┌────────────────────────────────────────────────────────────┐              │   │
│  │      │  PassthroughExecutor                                       │              │   │
│  │      │  • Simply forwards input to output                         │              │   │
│  │      └────────────────────────────────────────────────────────────┘              │   │
│  │                                                                                   │   │
│  │  ELSE:                                                                            │   │
│  │      ┌────────────────────────────────────────────────────────────┐              │   │
│  │      │  NodeExecutor (AI-based)                                   │              │   │
│  │      │  • Calls appropriate AI provider based on config           │              │   │
│  │      │  • OpenAI, Google, xAI, DashScope, DeepSeek                │              │   │
│  │      │  • Streams output to visualizer                            │              │   │
│  │      └────────────────────────────────────────────────────────────┘              │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│  AI PROVIDER ROUTING:                                                                    │
│  ┌────────────────────────────────────────────────────────────────────────────────┐     │
│  │  Provider      │  Method              │  Models                                │     │
│  │  ─────────────────────────────────────────────────────────────────────────────│     │
│  │  openai        │  _execute_openai()   │  gpt-4o                                │     │
│  │  google/gemini │  _execute_google()   │  gemini-2.0-flash                      │     │
│  │  xai/grok      │  _execute_xai()      │  grok-4                                │     │
│  │  dashscope/qwen│  _execute_dashscope()│  qwen-max                              │     │
│  │  deepseek      │  _execute_deepseek() │  deepseek-chat                         │     │
│  └────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Nodes execute and produce outputs
                                       ▼
                              ┌───────────────────────┐
                              │   TO RESEARCH PHASE   │
                              │   (Section C)         │
                              └───────────────────────┘
```

---

## 4. Section C: Research Phase (Tier 0-2)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     SECTION C: RESEARCH PHASE (Tier 0-2)                                 │
│                     ────────────────────────────────────                                 │
│  Purpose: Gather comprehensive research data and validate before debates                │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │  FROM WORKFLOW ENGINE │
                              │  (Initial task_prompt │
                              │   with verified price)│
                              └───────────┬───────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              TIER 0: ORCHESTRATION                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│                              ┌───────────────────────┐                                   │
│                              │        START          │                                   │
│                              │    (passthrough)      │                                   │
│                              │                       │                                   │
│                              │  Forwards task_prompt │                                   │
│                              │  to Research          │                                   │
│                              │  Supervisor           │                                   │
│                              └───────────┬───────────┘                                   │
│                                          │                                               │
│                                          ▼                                               │
│                     ┌─────────────────────────────────────────┐                          │
│                     │        RESEARCH SUPERVISOR              │                          │
│                     │            (GPT-4o)                     │                          │
│                     ├─────────────────────────────────────────┤                          │
│                     │                                         │                          │
│                     │  RESPONSIBILITIES:                      │                          │
│                     │  • Review equity ticker                 │                          │
│                     │  • Create research plan                 │                          │
│                     │  • Set expected price range             │                          │
│                     │  • Define data sources to consult       │                          │
│                     │  • Establish research standards         │                          │
│                     │                                         │                          │
│                     │  KEY OUTPUT:                            │                          │
│                     │  "CONFIRMED TICKER: {ticker}"           │                          │
│                     │  "VERIFIED PRICE: {price}"              │                          │
│                     │                                         │                          │
│                     └───────────────────┬─────────────────────┘                          │
│                                         │                                                │
│                                         │ Triggers 4 parallel collectors                 │
│                                         │                                                │
└─────────────────────────────────────────┼────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 1: DATA COLLECTION (PARALLEL)                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│    ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│    │                              PARALLEL EXECUTION                                  │  │
│    │                                                                                  │  │
│    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │  │
│    │  │ Market Data     │  │ Industry Deep   │  │ Company Deep    │  │ Data       │ │  │
│    │  │ Collector       │  │ Dive            │  │ Dive            │  │ Verifier   │ │  │
│    │  │                 │  │                 │  │                 │  │            │ │  │
│    │  │ (Gemini-2.0)    │  │ (GPT-4o)        │  │ (Qwen-Max)      │  │ (GPT-4o)   │ │  │
│    │  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤  ├────────────┤ │  │
│    │  │                 │  │                 │  │                 │  │            │ │  │
│    │  │ TOOLS:          │  │ TOOLS:          │  │ TOOLS:          │  │ CROSS-     │ │  │
│    │  │ • web_search    │  │ • web_search    │  │ • web_search    │  │ REFERENCE  │ │  │
│    │  │                 │  │                 │  │                 │  │ CHECK      │ │  │
│    │  │ COLLECTS:       │  │ ANALYZES:       │  │ ANALYZES:       │  │            │ │  │
│    │  │ • Current price │  │ • Industry TAM  │  │ • Business model│  │ VALIDATES: │ │  │
│    │  │ • Market cap    │  │ • Growth drivers│  │ • Moat strength │  │ • Price    │ │  │
│    │  │ • Volume        │  │ • Competition   │  │ • Management    │  │   matches  │ │  │
│    │  │ • 52-week range │  │ • Regulations   │  │ • Financials    │  │ • Data     │ │  │
│    │  │ • Beta          │  │ • Macro trends  │  │ • Growth plans  │  │   complete │ │  │
│    │  │ • Revenue       │  │                 │  │ • Key risks     │  │ • Sources  │ │  │
│    │  │                 │  │                 │  │                 │  │   agree    │ │  │
│    │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └─────┬──────┘ │  │
│    │           │                    │                    │                 │        │  │
│    │           └────────────────────┴────────────────────┴─────────────────┘        │  │
│    │                                         │                                       │  │
│    └─────────────────────────────────────────┼───────────────────────────────────────┘  │
│                                              │                                          │
│                                              │ All outputs feed into Data Checkpoint    │
│                                              │                                          │
└──────────────────────────────────────────────┼──────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            TIER 2: DATA QUALITY GATE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│           ╔═══════════════════════════════════════════════════════════════════╗         │
│           ║                    DATA CHECKPOINT                                 ║         │
│           ║                       (GPT-4o)                                     ║         │
│           ╠═══════════════════════════════════════════════════════════════════╣         │
│           ║                                                                    ║         │
│           ║  VALIDATION CHECKS:                                                ║         │
│           ║                                                                    ║         │
│           ║  1. COMPANY IDENTITY                                               ║         │
│           ║     □ Is data for the CORRECT company?                            ║         │
│           ║     □ No data from Apple/Amazon/Google contamination?             ║         │
│           ║                                                                    ║         │
│           ║  2. PRICE VERIFICATION                                             ║         │
│           ║     □ Does collector price match VERIFIED price?                  ║         │
│           ║     □ Tolerance: ±2%                                              ║         │
│           ║                                                                    ║         │
│           ║  3. MARKET CAP SANITY                                              ║         │
│           ║     □ Is market cap reasonable for this company?                  ║         │
│           ║     □ Consistent with shares × price?                             ║         │
│           ║                                                                    ║         │
│           ║  4. COMPLETENESS                                                   ║         │
│           ║     □ Do we have all required data points?                        ║         │
│           ║     □ Revenue, margins, growth rates available?                   ║         │
│           ║                                                                    ║         │
│           ╠═══════════════════════════════════════════════════════════════════╣         │
│           ║                                                                    ║         │
│           ║  OUTPUT KEYWORDS:                                                  ║         │
│           ║  • "DATA: VERIFIED" → Proceed to Debate Moderator                 ║         │
│           ║  • "DATA: FAILED"   → Loop back to Research Supervisor            ║         │
│           ║                                                                    ║         │
│           ╚═══════════════════════════════════════════════════════════════════╝         │
│                                              │                                          │
│                      ┌───────────────────────┴───────────────────────┐                  │
│                      │                                               │                  │
│                      ▼                                               ▼                  │
│           ┌───────────────────────┐                       ┌───────────────────────┐     │
│           │    DATA: VERIFIED     │                       │    DATA: FAILED       │     │
│           │                       │                       │                       │     │
│           │  Proceed to           │                       │  Loop back to         │     │
│           │  Debate Phase         │                       │  Research Supervisor  │     │
│           │  (Section D)          │                       │  for re-collection    │     │
│           └───────────┬───────────┘                       └───────────┬───────────┘     │
│                       │                                               │                  │
│                       ▼                                               │                  │
│              TO DEBATE PHASE                                          │                  │
│                                                                       │                  │
│                       ┌───────────────────────────────────────────────┘                  │
│                       │                                                                  │
│                       ▼                                                                  │
│           ┌───────────────────────────────────────────────────────────┐                 │
│           │              FEEDBACK LOOP (if DATA: FAILED)              │                 │
│           │                                                           │                 │
│           │  Research Supervisor receives failure notification        │                 │
│           │  → Re-dispatches collectors with refined instructions     │                 │
│           │  → May specify different data sources                     │                 │
│           │  → Adds emphasis on verified price requirement            │                 │
│           │                                                           │                 │
│           │  Max loop iterations: 3                                   │                 │
│           └───────────────────────────────────────────────────────────┘                 │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Section D: Debate Phase (Tier 3)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          SECTION D: DEBATE PHASE (Tier 3)                                │
│                          ───────────────────────────────                                 │
│  Purpose: Multi-AI debate between Bull and Bear advocates to challenge assumptions      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │  FROM DATA CHECKPOINT │
                              │  (DATA: VERIFIED)     │
                              │                       │
                              │  Carries all research │
                              │  data collected       │
                              └───────────┬───────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              DEBATE MODERATOR                                            │
│                                 (GPT-4o)                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  RESPONSIBILITIES:                                                                       │
│  • Summarize all research findings from Tier 1                                          │
│  • CONFIRM and state the VERIFIED current price                                         │
│  • Frame the key debate questions:                                                      │
│    - Is the company undervalued or overvalued?                                          │
│    - What are the key growth catalysts?                                                 │
│    - What are the major risks?                                                          │
│  • Set debate ground rules and expectations                                             │
│                                                                                          │
│  KEY OUTPUT:                                                                             │
│  "The VERIFIED current price is {currency} {price}..."                                  │
│  "Bull advocate should argue for upside..."                                             │
│  "Bear advocate should argue for downside..."                                           │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Triggers parallel Bull/Bear Round 1
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    ▼                                           ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│       BULL ADVOCATE ROUND 1         │   │       BEAR ADVOCATE ROUND 1         │
│           (Grok-4 / xAI)            │   │       (Qwen-Max / Alibaba)          │
├─────────────────────────────────────┤   ├─────────────────────────────────────┤
│                                     │   │                                     │
│  AI PERSONALITY: Optimistic         │   │  AI PERSONALITY: Risk-focused       │
│                                     │   │                                     │
│  PRESENTS 5 BULLISH ARGUMENTS:      │   │  PRESENTS 5 BEARISH ARGUMENTS:      │
│                                     │   │                                     │
│  1. Growth Potential                │   │  1. Valuation Risk                  │
│     • Revenue growth trajectory     │   │     • Current multiple too high     │
│     • Market expansion opportunities│   │     • Peer comparison concerns      │
│                                     │   │                                     │
│  2. Market Position                 │   │  2. Competition                     │
│     • Competitive advantages        │   │     • Market share threats          │
│     • Barriers to entry             │   │     • Pricing pressure              │
│                                     │   │                                     │
│  3. Innovation                      │   │  3. Execution Risk                  │
│     • Product pipeline              │   │     • Operational challenges        │
│     • Technology leadership         │   │     • Management concerns           │
│                                     │   │                                     │
│  4. Management Quality              │   │  4. Market Headwinds                │
│     • Track record                  │   │     • Macro economic risks          │
│     • Capital allocation            │   │     • Sector-specific challenges    │
│                                     │   │                                     │
│  5. Financial Strength              │   │  5. Regulatory Risk                 │
│     • Balance sheet health          │   │     • Policy changes                │
│     • Cash flow generation          │   │     • Compliance costs              │
│                                     │   │                                     │
│  PROPOSED DCF INPUTS:               │   │  PROPOSED DCF INPUTS:               │
│  • Revenue growth: 15-25%           │   │  • Revenue growth: 5-10%            │
│  • Target margin: 20-25%            │   │  • Target margin: 12-18%            │
│  • Probability weights              │   │  • Probability weights              │
│                                     │   │                                     │
└────────────────────┬────────────────┘   └────────────────────┬────────────────┘
                     │                                          │
                     └────────────────────┬─────────────────────┘
                                          │
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────���─────────┐
│                              DEVIL'S ADVOCATE                                            │
│                                 (GPT-4o)                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  CONTRARIAN CHALLENGE - Questions BOTH sides:                                           │
│                                                                                          │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐               │
│  │  CHALLENGES TO BULL CASE        │  │  CHALLENGES TO BEAR CASE        │               │
│  ├─────────────────────────────────┤  ├─────────────────────────────────┤               │
│  │                                 │  │                                 │               │
│  │  • What evidence is weak?       │  │  • Are risks overstated?        │               │
│  │  • What assumptions are         │  │  • What opportunities are       │               │
│  │    optimistic?                  │  │    being ignored?               │               │
│  │  • What could go wrong that     │  │  • What catalysts could         │               │
│  │    hasn't been considered?      │  │    change the narrative?        │               │
│  │  • Historical precedents for    │  │  • Competitor failures that     │               │
│  │    similar situations?          │  │    could benefit the company?   │               │
│  │                                 │  │                                 │               │
│  └─────────────────────────────────┘  └─────────────────────────────────┘               │
│                                                                                          │
│  BLACK SWAN SCENARIOS:                                                                   │
│  • What unexpected events could dramatically change the thesis?                         │
│  • Hidden risks or opportunities neither side has addressed?                            │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Triggers parallel Bull/Bear Round 2
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    ▼                                           ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│       BULL ADVOCATE ROUND 2         │   │       BEAR ADVOCATE ROUND 2         │
│           (Grok-4 / xAI)            │   │       (Qwen-Max / Alibaba)          │
├─────────────────────────────────────┤   ├─────────────────────────────────────┤
│                                     │   │                                     │
│  REBUTTALS:                         │   │  REBUTTALS:                         │
│  • Addresses Devil's Advocate       │   │  • Addresses Devil's Advocate       │
│    challenges                       │   │    challenges                       │
│  • Counters Bear arguments          │   │  • Counters Bull arguments          │
│  • Strengthens core thesis          │   │  • Reinforces risk concerns         │
│                                     │   │                                     │
│  REFINED DCF INPUTS:                │   │  REFINED DCF INPUTS:                │
│  ┌─────────────────────────────┐    │   │  ┌─────────────────────────────┐    │
│  │ Y1-3 Growth: 18%            │    │   │  │ Y1-3 Growth: 8%             │    │
│  │ Y4-5 Growth: 12%            │    │   │  │ Y4-5 Growth: 5%             │    │
│  │ Terminal Growth: 3%         │    │   │  │ Terminal Growth: 2%         │    │
│  │ Target Margin: 22%          │    │   │  │ Target Margin: 15%          │    │
│  │ Bull Probability: 25%       │    │   │  │ Bear Probability: 20%       │    │
│  │ Super Bull Prob: 15%        │    │   │  │ Super Bear Prob: 10%        │    │
│  └─────────────────────────────┘    │   │  └─────────────────────────────┘    │
│                                     │   │                                     │
└────────────────────┬────────────────┘   └────────────────────┬────────────────┘
                     │                                          │
                     └────────────────────┬─────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                DEBATE CRITIC                                             │
│                                  (GPT-4o)                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  SCORES AND SYNTHESIZES:                                                                 │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────┐     │
│  │  SCORING                                                                       │     │
│  │                                                                                │     │
│  │  Bull Case Score: [1-10]   │   Bear Case Score: [1-10]                        │     │
│  │  Evidence Quality: X/10    │   Evidence Quality: X/10                         │     │
│  │  Logic Coherence: X/10     │   Logic Coherence: X/10                          │     │
│  │  Rebuttal Strength: X/10   │   Rebuttal Strength: X/10                        │     │
│  │                                                                                │     │
│  └────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                          │
│  SYNTHESIZES DCF INPUTS FOR FINANCIAL MODELER:                                          │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────┐     │
│  │  SCENARIO PROBABILITIES AND ASSUMPTIONS                                        │     │
│  │                                                                                │     │
│  │  ┌──────────────┬───────────┬────────────┬───────────┬────────────┬─────────┐│     │
│  │  │  Scenario    │ Prob (%)  │ Growth Y1-3│ Growth Y4+│ Margin (%) │ Rationale│     │
│  │  ├──────────────┼───────────┼────────────┼───────────┼────────────┼─────────┤│     │
│  │  │ Super Bear   │    5%     │    2%      │    0%     │    10%     │ Worst   ││     │
│  │  │ Bear         │   15%     │    5%      │    3%     │    14%     │ Downside││     │
│  │  │ Base         │   40%     │   12%      │    6%     │    18%     │ Expected││     │
│  │  │ Bull         │   25%     │   18%      │   10%     │    22%     │ Upside  ││     │
│  │  │ Super Bull   │   15%     │   25%      │   15%     │    26%     │ Best    ││     │
│  │  └──────────────┴───────────┴────────────┴───────────┴────────────┴─────────┘│     │
│  │                                                                                │     │
│  │  CONFIRMED PRICE FOR DCF: {currency} {verified_price}                         │     │
│  │                                                                                │     │
│  └────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                          │
│  KEY OUTPUT:                                                                             │
│  "DCF_INPUTS_READY: YES"                                                                │
│  "VERIFIED_PRICE: {price}"                                                              │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Structured assumptions flow to Valuation
                                          ▼
                              ┌───────────────────────┐
                              │  TO VALUATION PHASE   │
                              │  (Section E)          │
                              └───────────────────────┘
```

---

## 6. Section E: Valuation Phase (Tier 4-5)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        SECTION E: VALUATION PHASE (Tier 4-5)                             │
│                        ─────────────────────────────────────                             │
│  Purpose: Build DCF model with Python math, validate assumptions, cross-check methods   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │  FROM DEBATE CRITIC   │
                              │                       │
                              │  • DCF assumptions    │
                              │  • Scenario probs     │
                              │  • Verified price     │
                              └───────────┬───────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 4: PRE-MODEL VALIDATION                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│           ╔═══════════════════════════════════════════════════════════════════╗         │
│           ║                    PRE-MODEL VALIDATOR                             ║         │
│           ║                        (GPT-4o)                                    ║         │
│           ╠═══════════════════════════════════════════════════════════════════╣         │
│           ║                                                                    ║         │
│           ║  VALIDATES INPUTS BEFORE DCF RUNS:                                 ║         │
│           ║                                                                    ║         │
│           ║  1. PRICE VERIFICATION                                             ║         │
│           ║     □ Is the price being used the VERIFIED price?                 ║         │
│           ║     □ No hallucinated prices from training data?                  ║         │
│           ║                                                                    ║         │
│           ║  2. GROWTH RATE SANITY                                             ║         │
│           ║     □ Are growth rates reasonable for this industry?              ║         │
│           ║     □ Y1-3 growth < 40% (unless justified biotech/tech)           ║         │
│           ║     □ Terminal growth < GDP growth (2-3%)                         ║         │
│           ║                                                                    ║         │
│           ║  3. MARGIN ASSUMPTIONS                                             ║         │
│           ║     □ Are margin assumptions realistic?                           ║         │
│           ║     □ Compared to industry benchmarks?                            ║         │
│           ║     □ Path from current to target margin plausible?               ║         │
│           ║                                                                    ║         │
│           ║  4. WACC COMPONENTS                                                ║         │
│           ║     □ Risk-free rate current?                                     ║         │
│           ║     □ Beta reasonable for company risk?                           ║         │
│           ║     □ Equity risk premium standard (5-6%)?                        ║         │
│           ║                                                                    ║         │
│           ║  5. SCENARIO PROBABILITIES                                         ║         │
│           ║     □ Do probabilities sum to 100%?                               ║         │
│           ║     □ Base case has highest probability?                          ║         │
│           ║                                                                    ║         │
│           ╠═══════════════════════════════════════════════════════════════════╣         │
│           ║                                                                    ║         │
│           ║  OUTPUT KEYWORDS:                                                  ║         │
│           ║  • "INPUTS: VALIDATED" → Proceed to Financial Modeler             ║         │
│           ║  • "INPUTS: REVIEW NEEDED" → Loop back to Debate Critic           ║         │
│           ║                                                                    ║         │
│           ╚═══════════════════════════════════════════════════════════════════╝         │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ INPUTS: VALIDATED
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              TIER 5: DCF VALUATION                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         FINANCIAL MODELER                                          │  │
│  │                   (PythonValuationExecutor - NOT AI)                              │  │
│  ├───────────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                                    │  │
│  │  THIS NODE USES REAL PYTHON MATH - NOT AI HALLUCINATION!                          │  │
│  │                                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    VALUATION ORCHESTRATOR                                    │ │  │
│  │  │                                                                              │ │  │
│  │  │  1. MULTI-AI ASSUMPTION EXTRACTION                                          │ │  │
│  │  │     • Extracts parameters from Debate Critic output                         │ │  │
│  │  │     • Uses GPT-4o to parse growth rates, margins, probabilities            │ │  │
│  │  │     • NO HARDCODED DEFAULTS - all from debate                              │ │  │
│  │  │                                                                              │ │  │
│  │  │  2. RUN VALUATION ENGINES (Python math):                                    │ │  │
│  │  │                                                                              │ │  │
│  │  │     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │ │  │
│  │  │     │ DCF Engine  │ │ Comps       │ │ DDM Engine  │ │ Reverse DCF │        │ │  │
│  │  │     │             │ │ Engine      │ │             │ │ Engine      │        │ │  │
│  │  │     │ 5 scenarios │ │ Peer comps  │ │ Gordon      │ │ Implied     │        │ │  │
│  │  │     │ 10yr FCF    │ │ P/E, EV/    │ │ Growth      │ │ growth from │        │ │  │
│  │  │     │ Terminal    │ │ EBITDA      │ │ Model       │ │ market      │        │ │  │
│  │  │     │ value       │ │             │ │             │ │ price       │        │ │  │
│  │  │     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘        │ │  │
│  │  │            │               │               │               │               │ │  │
│  │  │            └───────────────┴───────────────┴───────────────┘               │ │  │
│  │  │                                    │                                        │ │  │
│  │  │                                    ▼                                        │ │  │
│  │  │  3. CROSS-CHECKER                                                          │ │  │
│  │  │     • Compares values from all methods                                     │ │  │
│  │  │     • Checks convergence (STRONG/MODERATE/WEAK)                            │ │  │
│  │  │     • Flags if methods diverge significantly                               │ │  │
│  │  │                                                                              │ │  │
│  │  │  4. CONSENSUS BUILDER                                                       │ │  │
│  │  │     • Builds probability-weighted value (PWV)                              │ │  │
│  │  │     • Determines recommendation (BUY/HOLD/SELL)                            │ │  │
│  │  │     • Calculates implied upside/downside                                   │ │  │
│  │  │                                                                              │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  │  DCF FORMULAS USED (financial_calculator.py):                                     │  │
│  │                                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  WACC = (E/V) × Re + (D/V) × Rd × (1-T)                                     │ │  │
│  │  │  Re = Rf + β × ERP + CRP                                                    │ │  │
│  │  │                                                                              │ │  │
│  │  │  FCF = EBIT × (1-T) + D&A - CapEx - ΔWC                                     │ │  │
│  │  │  Terminal Value = FCF_terminal × (1 + g) / (WACC - g)                       │ │  │
│  │  │                                                                              │ │  │
│  │  │  Enterprise Value = Σ FCF_t / (1 + WACC)^t + TV / (1 + WACC)^n             │ │  │
│  │  │  Equity Value = EV - Net Debt                                               │ │  │
│  │  │  Fair Value = Equity Value / Shares Outstanding                             │ │  │
│  │  │                                                                              │ │  │
│  │  │  PWV = Σ (Scenario Fair Value × Scenario Probability)                       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  │  OUTPUT: 5 SCENARIO DCF TABLE                                                     │  │
│  │  ┌──────────────┬──────────┬──────────┬──────────────┬────────────────────────┐  │  │
│  │  │  Scenario    │ Target   │ Upside   │ Probability  │ Weighted Contribution  │  │  │
│  │  ├──────────────┼──────────┼──────────┼──────────────┼────────────────────────┤  │  │
│  │  │ Super Bear   │  $35.20  │  -32.7%  │     5%       │         $1.76          │  │  │
│  │  │ Bear         │  $42.80  │  -18.1%  │    15%       │         $6.42          │  │  │
│  │  │ Base         │  $58.50  │  +11.8%  │    40%       │        $23.40          │  │  │
│  │  │ Bull         │  $72.30  │  +38.3%  │    25%       │        $18.08          │  │  │
│  │  │ Super Bull   │  $89.60  │  +71.4%  │    15%       │        $13.44          │  │  │
│  │  ├──────────────┴──────────┴──────────┼──────────────┼────────────────────────┤  │  │
│  │  │         PROBABILITY-WEIGHTED VALUE │    100%      │  PWV = $63.10          │  │  │
│  │  └────────────────────────────────────┴──────────────┴────────────────────────┘  │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Triggers 3 parallel QC agents
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 5B: VALUATION QC (PARALLEL)                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           PARALLEL EXECUTION                                     │    │
│  │                                                                                  │    │
│  │  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐       │    │
│  │  │ ASSUMPTION          │ │ COMPARABLE          │ │ SENSITIVITY         │       │    │
│  │  │ CHALLENGER          │ │ VALIDATOR           │ │ AUDITOR             │       │    │
│  │  │ (GPT-4o)            │ │ (Gemini-2.0)        │ │ (GPT-4o)            │       │    │
│  │  ├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤       │    │
│  │  │                     │ │                     │ │                     │       │    │
│  │  │ STRESS-TESTS:       │ │ PEER COMPARISON:    │ │ MODEL ROBUSTNESS:   │       │    │
│  │  │                     │ │                     │ │                     │       │    │
│  │  │ • Growth rates      │ │ • P/E vs peers      │ │ • WACC ±1%          │       │    │
│  │  │   realistic?        │ │ • EV/Revenue        │ │ • Growth ±2%        │       │    │
│  │  │ • Margins           │ │ • EV/EBITDA         │ │ • Margin ±3%        │       │    │
│  │  │   achievable?       │ │ • PEG ratio         │ │ • Terminal value    │       │    │
│  │  │ • WACC appropriate? │ │ • Premium/discount  │ │   sensitivity       │       │    │
│  │  │ • Terminal value    │ │   justified?        │ │ • Tornado chart     │       │    │
│  │  │   reasonable?       │ │                     │ │                     │       │    │
│  │  │                     │ │                     │ │                     │       │    │
│  │  │ FLAGS:              │ │ FLAGS:              │ │ FLAGS:              │       │    │
│  │  │ • CRITICAL ISSUE    │ │ • OUTLIER           │ │ • HIGH SENSITIVITY  │       │    │
│  │  │ • WARNING           │ │ • MISALIGNED        │ │ • MODEL UNSTABLE    │       │    │
│  │  │ • OK                │ │ • ALIGNED           │ │ • OK                │       │    │
│  │  │                     │ │                     │ │                     │       │    │
│  │  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘       │    │
│  │             │                       │                       │                  │    │
│  │             └───────────────────────┴───────────────────────┘                  │    │
│  │                                     │                                          │    │
│  └─────────────────────────────────────┼──────────────────────────────────────────┘    │
│                                        │                                               │
│                                        ▼                                               │
│           ╔═══════════════════════════════════════════════════════════════════╗        │
│           ║                    VALUATION COMMITTEE                             ║        │
│           ║                        (GPT-4o)                                    ║        │
│           ╠═══════════════════════════════════════════════════════════════════╣        │
│           ║                                                                    ║        │
│           ║  AGGREGATES ALL QC RESULTS:                                        ║        │
│           ║                                                                    ║        │
│           ║  CHECKS:                                                           ║        │
│           ║  □ Is the CORRECT VERIFIED price used throughout?                 ║        │
│           ║  □ No CRITICAL issues from QC agents?                             ║        │
│           ║  □ Debate insights properly incorporated?                         ║        │
│           ║  □ Scenarios span reasonable range?                               ║        │
│           ║  □ Cross-check convergence acceptable?                            ║        │
│           ║                                                                    ║        │
│           ║  OUTPUTS:                                                          ║        │
│           ║  • "VALUATION: APPROVED" → Proceed to Quality Gates               ║        │
│           ║  • "VALUATION: REVISE"   → Loop back to Financial Modeler         ║        │
│           ║                                                                    ║        │
│           ║  FINAL TARGET: {currency} {pwv}                                   ║        │
│           ║  RECOMMENDATION: BUY / HOLD / SELL                                ║        │
│           ║                                                                    ║        │
│           ╚═══════════════════════════════════════════════════════════════════╝        │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ VALUATION: APPROVED
                                          ▼
                              ┌───────────────────────┐
                              │   TO QUALITY CONTROL  │
                              │   (Section F)         │
                              └───────────────────────┘
```

---

## 7. Section F: Quality Control (Tier 6)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                       SECTION F: QUALITY CONTROL (Tier 6)                                │
│                       ───────────────────────────────────                                │
│  Purpose: Final validation gates before report synthesis                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │  FROM VALUATION       │
                              │  COMMITTEE            │
                              │  (APPROVED)           │
                              └───────────┬───────────┘
                                          │
                                          │ Triggers 3 parallel quality gates
                                          │
           ┌──────────────────────────────┼──────────────────────────────┐
           │                              │                              │
           ▼                              ▼                              ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  DATA VERIFICATION  │      │  LOGIC VERIFICATION │      │   BIRD'S EYE        │
│  GATE               │      │  GATE               │      │   REVIEWER          │
│  (GPT-4o)           │      │  (GPT-4o)           │      │   (GPT-4o)          │
├─────────────────────┤      ├─────────────────────┤      ├─────────────────────┤
│                     │      │                     │      │                     │
│ FINAL DATA CHECK:   │      │ FINAL LOGIC CHECK:  │      │ HOLISTIC REVIEW:    │
│                     │      │                     │      │                     │
│ □ Price in report   │      │ □ Recommendation    │      │ □ Does this make    │
│   matches verified  │      │   aligns with       │      │   sense overall?    │
│   price?            │      │   valuation?        │      │                     │
│                     │      │                     │      │ □ Any red flags     │
│ □ Market cap        │      │ □ Bull/bear args    │      │   missed by other   │
│   consistent?       │      │   support the       │      │   gates?            │
│                     │      │   conclusion?       │      │                     │
│ □ All data points   │      │                     │      │ □ Internal          │
│   internally        │      │ □ DCF assumptions   │      │   contradictions?   │
│   consistent?       │      │   match debate      │      │                     │
│                     │      │   conclusions?      │      │ □ Missing critical  │
│ □ Data sources      │      │                     │      │   information?      │
│   reliable?         │      │ □ Math calculations │      │                     │
│                     │      │   correct?          │      │ □ Quality bar       │
│                     │      │                     │      │   met for           │
│ OUTPUT:             │      │ OUTPUT:             │      │   publication?      │
│ • PASS / FAIL       │      │ • PASS / FAIL       │      │                     │
│                     │      │                     │      │ CAN ROUTE BACK TO:  │
│                     │      │                     │      │ • Data Checkpoint   │
│                     │      │                     │      │ • Debate Moderator  │
│                     │      │                     │      │ • Financial Modeler │
│                     │      │                     │      │                     │
│                     │      │                     │      │ OUTPUT:             │
│                     │      │                     │      │ • PASS / FAIL       │
│                     │      │                     │      │ • ROUTE: {node}     │
│                     │      │                     │      │                     │
└──────────┬──────────┘      └──────────┬──────────┘      └──────────┬──────────┘
           │                            │                            │
           └────────────────────────────┼────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              QUALITY SUPERVISOR                                          │
│                                  (GPT-4o)                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  AGGREGATES ALL GATE RESULTS AND MAKES ROUTING DECISION:                                │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │  GATE RESULTS:                                                                     │  │
│  │  ┌─────────────────────┬─────────────────────┬─────────────────────┐              │  │
│  │  │ Data Verification   │ Logic Verification  │ Bird's Eye Reviewer │              │  │
│  │  │      [PASS/FAIL]    │      [PASS/FAIL]    │      [PASS/FAIL]    │              │  │
│  │  └─────────────────────┴─────────────────────┴─────────────────────┘              │  │
│  │                                                                                    │  │
│  │  ROUTING DECISION TREE:                                                           │  │
│  │                                                                                    │  │
│  │                           ┌─────────────────┐                                      │  │
│  │                           │  All PASS?      │                                      │  │
│  │                           └────────┬────────┘                                      │  │
│  │                     ┌──────────────┴──────────────┐                                │  │
│  │                     │ YES                    NO   │                                │  │
│  │                     ▼                             │                                │  │
│  │          ┌─────────────────────┐                  │                                │  │
│  │          │ ROUTE: Synthesizer  │                  │                                │  │
│  │          │ (Proceed to output) │                  │                                │  │
│  │          └─────────────────────┘                  │                                │  │
│  │                                                   │                                │  │
│  │                                    ┌──────────────┴──────────────┐                 │  │
│  │                                    │ Which gate failed?          │                 │  │
│  │                                    └──────────────┬──────────────┘                 │  │
│  │                     ┌──────────────┬──────────────┴──────────────┐                 │  │
│  │                     ▼              ▼                             ▼                 │  │
│  │          ┌───────────────┐ ┌───────────────┐           ┌───────────────┐          │  │
│  │          │ Data FAIL     │ │ Logic FAIL    │           │ Bird's Eye    │          │  │
│  │          │               │ │               │           │ FAIL          │          │  │
│  │          │ ROUTE:        │ │ ROUTE:        │           │               │          │  │
│  │          │ Research      │ │ Financial     │           │ ROUTE:        │          │  │
│  │          │ Supervisor    │ │ Modeler       │           │ (Per Bird's   │          │  │
│  │          │               │ │               │           │ Eye routing)  │          │  │
│  │          └───────────────┘ └───────────────┘           └───────────────┘          │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  OUTPUT KEYWORDS:                                                                        │
│  • "ROUTE: Synthesizer"        → Proceed to final synthesis                             │
│  • "ROUTE: Research Supervisor" → Loop back to data collection                          │
│  • "ROUTE: Financial Modeler"  → Loop back to valuation                                 │
│  • "ROUTE: Debate Moderator"   → Loop back to debate                                    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ ROUTE: Synthesizer
                                          ▼
                              ┌───────────────────────┐
                              │   TO OUTPUT GENERATION│
                              │   (Section G)         │
                              └───────────────────────┘
```

---

## 8. Section G: Output Generation (Tier 7)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      SECTION G: OUTPUT GENERATION (Tier 7)                               │
│                      ─────────────────────────────────────                               │
│  Purpose: Synthesize all research into final report and generate HTML                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │  FROM QUALITY         │
                              │  SUPERVISOR           │
                              │  (ROUTE: Synthesizer) │
                              │                       │
                              │  All gates PASSED     │
                              └───────────┬───────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                  SYNTHESIZER                                             │
│                                   (GPT-4o)                                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  CREATES FINAL REPORT STRUCTURE:                                                        │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │  1. EXECUTIVE SUMMARY                                                             │  │
│  │     ├── Investment Rating: BUY / HOLD / SELL                                      │  │
│  │     ├── Price Target: {currency} {pwv}                                            │  │
│  │     ├── Current Price: {currency} {verified_price}                                │  │
│  │     ├── Implied Upside/Downside: +XX.X%                                           │  │
│  │     └── Key Thesis (1-2 sentences)                                                │  │
│  │                                                                                    │  │
│  │  2. INVESTMENT THESIS                                                             │  │
│  │     ├── Bull Case Summary (top 3 arguments)                                       │  │
│  │     ├── Bear Case Summary (top 3 arguments)                                       │  │
│  │     └── Key Debate Conclusions                                                    │  │
│  │                                                                                    │  │
│  │  3. COMPANY OVERVIEW                                                              │  │
│  │     ├── Business Model                                                            │  │
│  │     ├── Products/Services                                                         │  │
│  │     ├── Key Markets                                                               │  │
│  │     └── Competitive Position                                                      │  │
│  │                                                                                    │  │
│  │  4. INDUSTRY ANALYSIS                                                             │  │
│  │     ├── Total Addressable Market (TAM)                                            │  │
│  │     ├── Growth Drivers                                                            │  │
│  │     ├── Competitive Landscape                                                     │  │
│  │     └── Regulatory Environment                                                    │  │
│  │                                                                                    │  │
│  │  5. FINANCIAL ANALYSIS                                                            │  │
│  │     ├── Historical Performance                                                    │  │
│  │     ├── Key Metrics (Revenue, Margins, ROE)                                       │  │
│  │     └── Forward Projections                                                       │  │
│  │                                                                                    │  │
│  │  6. VALUATION                                                                     │  │
│  │     ├── DCF Methodology & Assumptions                                             │  │
│  │     ├── WACC Calculation                                                          │  │
│  │     ├── 5-Scenario Analysis Table                                                 │  │
│  │     ├── Probability-Weighted Target                                               │  │
│  │     ├── Comparable Analysis (if applicable)                                       │  │
│  │     └── Broker Consensus Comparison                                               │  │
│  │                                                                                    │  │
│  │  7. KEY RISKS                                                                     │  │
│  │     ├── Risk 1: Description, Probability, Impact                                  │  │
│  │     ├── Risk 2: Description, Probability, Impact                                  │  │
│  │     └── Risk 3: Description, Probability, Impact                                  │  │
│  │                                                                                    │  │
│  │  8. RECOMMENDATION                                                                │  │
│  │     ├── Final Rating: BUY / HOLD / SELL                                           │  │
│  │     ├── Target Price: {currency} {pwv}                                            │  │
│  │     ├── Key Catalysts                                                             │  │
│  │     └── Monitoring Triggers                                                       │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  CRITICAL: Must use VERIFIED current price throughout                                   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Synthesized output passed to report generator
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW RESULT SAVED                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  graph_executor.save_results(ticker)                                                    │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │  context/{ticker}_workflow_result.json                                             │  │
│  │                                                                                    │  │
│  │  {                                                                                 │  │
│  │    "ticker": "6682 HK",                                                           │  │
│  │    "workflow_id": "equity_research_v4",                                           │  │
│  │    "executed_at": "2026-01-27T10:30:00",                                          │  │
│  │    "verified_price": 52.30,                                                       │  │
│  │    "currency": "HKD",                                                             │  │
│  │    "context": {...},                                                              │  │
│  │    "node_outputs": {                                                              │  │
│  │      "Research Supervisor": [...],                                                │  │
│  │      "Market Data Collector": [...],                                              │  │
│  │      "Debate Critic": [...],                                                      │  │
│  │      "Financial Modeler": [...],                                                  │  │
│  │      "Synthesizer": [...]                                                         │  │
│  │    },                                                                             │  │
│  │    "execution_log": [...]                                                         │  │
│  │  }                                                                                 │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         generate_workflow_report.py                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  HTML REPORT GENERATION:                                                                │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │  1. EXTRACT DATA FROM WORKFLOW RESULT                                             │  │
│  │     ├── Verified price from START/context                                         │  │
│  │     ├── DCF scenarios from Financial Modeler                                      │  │
│  │     ├── Final target from Valuation Committee (LAST output)                       │  │
│  │     ├── Broker consensus from DCF Validator                                       │  │
│  │     └── Debate assumptions from Debate Critic                                     │  │
│  │                                                                                    │  │
│  │  2. BUILD SCENARIO ANALYSIS TABLE                                                 │  │
│  │     ├── Calculate upside/downside for each scenario                               │  │
│  │     ├── Apply probability weights                                                 │  │
│  │     └── Cap extreme values (±200%)                                                │  │
│  │                                                                                    │  │
│  │  3. BUILD DCF ASSUMPTIONS CHAIN                                                   │  │
│  │     └── Debate → Model flow showing assumption linkage                            │  │
│  │                                                                                    │  │
│  │  4. BUILD BROKER CONSENSUS COMPARISON                                             │  │
│  │     ├── Our target vs. Broker average                                             │  │
│  │     ├── Divergence percentage                                                     │  │
│  │     └── Divergence classification (ALIGNED/MODERATE/SIGNIFICANT)                  │  │
│  │                                                                                    │  │
│  │  5. GENERATE STYLED HTML                                                          │  │
│  │     ├── Professional investment report styling                                    │  │
│  │     ├── Interactive scenario tables                                               │  │
│  │     ├── Color-coded upside/downside indicators                                    │  │
│  │     └── Expandable sections for detailed analysis                                 │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  OUTPUT FILES:                                                                          │
│                                                                                          │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │  reports/index.html                 │  │  reports/{ticker}_detailed.html         │  │
│  │  (Portfolio dashboard)              │  │  (Full equity report)                   │  │
│  │                                     │  │                                         │  │
│  │  • List of all researched equities  │  │  • Executive summary                    │  │
│  │  • Quick view: price, target,       │  │  • Investment thesis                    │  │
│  │    upside, rating                   │  │  • Company & industry analysis          │  │
│  │  • Links to detailed reports        │  │  • Financial analysis                   │  │
│  │  • Generation timestamp             │  │  • DCF valuation with scenarios         │  │
│  │                                     │  │  • Risk assessment                      │  │
│  │                                     │  │  • Final recommendation                 │  │
│  └─────────────────────────────────────┘  └─────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │         END           │
                              │                       │
                              │  Research Complete    │
                              │                       │
                              │  Reports available in │
                              │  reports/ directory   │
                              └───────────────────────┘
```

---

## 9. Agent Hierarchy Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              AGENT HIERARCHY                                             │
│                              ───────────────                                             │
│  Shows the spawnable agent structure with tiers and responsibilities                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘


                    ┌─────────────────────────────────────────────────────────┐
                    │                     TIER 0: ARCHITECTS                   │
                    │                     (Strategy Layer)                     │
                    └─────────────────────────────────────────────────────────┘

                              ┌───────────────────────────────┐
                              │        CHIEF ENGINEER         │
                              │   (chief_engineer.py)         │
                              ├───────────────────────────────┤
                              │                               │
                              │  • Reads brain/ documentation │
                              │  • Monitors all components    │
                              │  • Spawns sub-agents          │
                              │  • Persists state             │
                              │  • Investigates failures      │
                              │                               │
                              └───────────────┬───────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
     ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
     │   Component           │ │   Workflow            │ │   DCF Quality         │
     │   Inspector           │ │   Auditor             │ │   Controller          │
     │                       │ │                       │ │                       │
     │   • Read files        │ │   • Parse YAML        │ │   • Validate DCF      │
     │   • Check syntax      │ │   • Check edges       │ │   • Verify prices     │
     │   • Check imports     │ │   • Detect cycles     │ │   • Recalculate       │
     │   • Analyze code      │ │   • Audit providers   │ │   • Compare values    │
     └───────────────────────┘ └───────────────────────┘ └───────────────────────┘


                    ┌─────────────────────────────────────────────────────────┐
                    │                     TIER 1: SUPERVISORS                  │
                    │                     (Oversight Layer)                    │
                    └─────────────────────────────────────────────────────────┘

           ┌───────────────────────────────┐    ┌───────────────────────────────┐
           │      RESEARCH SUPERVISOR      │    │      DEBATE MODERATOR         │
           │   (research_supervisor.py)    │    │   (debate_moderator.py)       │
           ├───────────────────────────────┤    ├───────────────────────────────┤
           │                               │    │                               │
           │  • Create research plan       │    │  • Frame debate questions     │
           │  • Dispatch data collectors   │    │  • Set ground rules           │
           │  • Review worker outputs      │    │  • Summarize research         │
           │  • Ensure quality standards   │    │  • Confirm verified price     │
           │  • Route to next phase        │    │  • Trigger Bull/Bear          │
           │                               │    │                               │
           └───────────────┬───────────────┘    └───────────────┬───────────────┘
                           │                                    │
                           │ Spawns workers                     │ Spawns debaters
                           │                                    │
                           ▼                                    ▼


                    ┌─────────────────────────────────────────────────────────┐
                    │                      TIER 2: WORKERS                     │
                    │                     (Execution Layer)                    │
                    └─────────────────────────────────────────────────────────┘

  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  Market    │  │  Industry  │  │  Company   │  │  Bull      │  │  Bear      │
  │  Data      │  │  Deep      │  │  Deep      │  │  Advocate  │  │  Advocate  │
  │  Collector │  │  Dive      │  │  Dive      │  │            │  │            │
  │            │  │            │  │            │  │  (Grok)    │  │  (Qwen)    │
  │  (Gemini)  │  │  (GPT-4o)  │  │  (Qwen)    │  │            │  │            │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘

  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  Devil's   │  │  Debate    │  │  Financial │  │  Validation│
  │  Advocate  │  │  Critic    │  │  Modeler   │  │  Agent     │
  │            │  │            │  │            │  │            │
  │  (GPT-4o)  │  │  (GPT-4o)  │  │  (Python)  │  │  (Python)  │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘


                    ┌─────────────────────────────────────────────────────────┐
                    │                    TIER 3: GOALKEEPERS                   │
                    │                     (Quality Layer)                      │
                    └─────────────────────────────────────────────────────────┘

  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
  │ Data           │ │ Logic          │ │ Bird's Eye     │ │ Publish        │
  │ Checkpoint     │ │ Verification   │ │ Reviewer       │ │ Gatekeeper     │
  │                │ │ Gate           │ │                │ │                │
  │ • Verify data  │ │ • Check logic  │ │ • Holistic     │ │ • Final        │
  │ • Check price  │ │ • Validate     │ │   review       │ │   approval     │
  │ • Block bad    │ │   reasoning    │ │ • Route back   │ │ • Quality      │
  │   data         │ │                │ │   authority    │ │   score        │
  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘


                    ┌─────────────────────────────────────────────────────────┐
                    │                   SPECIALIZED AGENTS                     │
                    │              (Tool-Equipped, agents/specialized/)        │
                    └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
  │    DCF MODELING AGENT   │ │   MARKET DATA AGENT     │ │   VALIDATION AGENT      │
  │    (dcf_agent.py)       │ │   (market_data_agent.py)│ │   (validation_agent.py) │
  ├─────────────────────────┤ ├─────────────────────────┤ ├─────────────────────────┤
  │                         │ │                         │ │                         │
  │  TOOLS:                 │ │  TOOLS:                 │ │  VALIDATES:             │
  │  • DCFCalculator        │ │  • Yahoo Finance API    │ │  • DCF outputs          │
  │  • FinancialCalculator  │ │  • Price fetcher        │ │  • Debate outputs       │
  │  • MarketDataAPI        │ │  • Financials API       │ │  • Research outputs     │
  │                         │ │  • Analyst estimates    │ │  • Price consistency    │
  │  OUTPUTS:               │ │                         │ │                         │
  │  • VERIFIED DCF model   │ │  OUTPUTS:               │ │  OUTPUTS:               │
  │  • 5 scenarios          │ │  • VERIFIED prices      │ │  • ValidationReport     │
  │  • PWV calculation      │ │  • Real financials      │ │  • Corrections needed   │
  │                         │ │  • Broker targets       │ │                         │
  └─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
```

---

## 10. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW DIAGRAM                                         │
│                                ─────────────────                                         │
│  Shows how data flows through the system from input to output                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘


 USER INPUT                                                              OUTPUT
    │                                                                       │
    │  "Research 6682 HK"                                                   │
    │                                                                       │
    ▼                                                                       │
┌───────────────────┐                                                       │
│   config.py       │                                                       │
│                   │                                                       │
│  ticker: 6682 HK  │                                                       │
│  name: Tongcheng  │                                                       │
│  sector: Consumer │                                                       │
│  API keys: {...}  │                                                       │
└─────────┬─────────┘                                                       │
          │                                                                 │
          ▼                                                                 │
┌─────────────────────────────────────────────────────────────────┐        │
│                    PRICE PREFETCH                                │        │
│                                                                  │        │
│    Yahoo Finance API ───▶ verified_price: HKD 52.30             │        │
│                      ───▶ market_cap: 60.5B HKD                 │        │
│                      ───▶ revenue_ttm: 15.2B HKD                │        │
│                      ───▶ beta: 1.15                            │        │
│                      ───▶ broker_target: HKD 62.00              │        │
│                                                                  │        │
└─────────────────────────────┬───────────────────────────────────┘        │
                              │                                             │
                              │ VERIFIED MARKET DATA                        │
                              ▼                                             │
┌─────────────────────────────────────────────────────────────────┐        │
│                    WORKFLOW ENGINE                               │        │
│                                                                  │        │
│  ┌────────────────────────────────────────────────────────────┐ │        │
│  │                     DATA COLLECTION                         │ │        │
│  │                                                             │ │        │
│  │  Market Data ──┬──▶ price, volume, fundamentals            │ │        │
│  │  Industry     ──┼──▶ TAM, growth, competition              │ │        │
│  │  Company      ──┼──▶ moat, management, financials          │ │        │
│  │  Verifier     ──┴──▶ cross-reference validation            │ │        │
│  │                                                             │ │        │
│  └──────────────────────────┬──────────────────────────────────┘ │        │
│                             │                                    │        │
│                             ▼                                    │        │
│  ┌────────────────────────────────────────────────────────────┐ │        │
│  │                     DEBATE PHASE                            │ │        │
│  │                                                             │ │        │
│  │  Bull R1 ────┬──▶ 5 bullish arguments + DCF inputs         │ │        │
│  │  Bear R1 ────┤                                              │ │        │
│  │  Devil's ────┼──▶ challenges to both sides                 │ │        │
│  │  Bull R2 ────┤                                              │ │        │
│  │  Bear R2 ────┴──▶ rebuttals + refined DCF inputs           │ │        │
│  │                                                             │ │        │
│  │  Debate Critic ──▶ scores + synthesized assumptions        │ │        │
│  │                                                             │ │        │
│  │  OUTPUT: {                                                  │ │        │
│  │    scenarios: {                                             │ │        │
│  │      super_bear: {prob: 5%, growth: 2%, margin: 10%},      │ │        │
│  │      bear:       {prob: 15%, growth: 5%, margin: 14%},     │ │        │
│  │      base:       {prob: 40%, growth: 12%, margin: 18%},    │ │        │
│  │      bull:       {prob: 25%, growth: 18%, margin: 22%},    │ │        │
│  │      super_bull: {prob: 15%, growth: 25%, margin: 26%}     │ │        │
│  │    }                                                        │ │        │
│  │  }                                                          │ │        │
│  │                                                             │ │        │
│  └──────────────────────────┬──────────────────────────────────┘ │        │
│                             │                                    │        │
│                             ▼                                    │        │
│  ┌────────────────────────────────────────────────────────────┐ │        │
│  │                    VALUATION PHASE                          │ │        │
│  │                    (Python Math)                            │ │        │
│  │                                                             │ │        │
│  │  Multi-AI Extraction ──▶ parse assumptions from debate     │ │        │
│  │                                                             │ │        │
│  │  DCF Engine ──▶ {                                          │ │        │
│  │    wacc: 9.8%,                                             │ │        │
│  │    scenarios: {                                             │ │        │
│  │      super_bear: {fair_value: 35.20, pv_fcf: 12.5B},       │ │        │
│  │      bear:       {fair_value: 42.80, pv_fcf: 18.2B},       │ │        │
│  │      base:       {fair_value: 58.50, pv_fcf: 28.7B},       │ │        │
│  │      bull:       {fair_value: 72.30, pv_fcf: 38.1B},       │ │        │
│  │      super_bull: {fair_value: 89.60, pv_fcf: 51.2B}        │ │        │
│  │    },                                                       │ │        │
│  │    pwv: 63.10                                              │ │        │
│  │  }                                                          │ │        │
│  │                                                             │ │        │
│  │  Comps Engine ──▶ peer_implied_value: 61.50                │ │        │
│  │  DDM Engine   ──▶ dividend_value: 55.20                    │ │        │
│  │  Reverse DCF  ──▶ implied_growth: 10.2%                    │ │        │
│  │                                                             │ │        │
│  │  Cross-Check ──▶ convergence: STRONG (spread: 8.2%)        │ │        │
│  │                                                             │ │        │
│  └──────────────────────────┬──────────────────────────────────┘ │        │
│                             │                                    │        │
│                             ▼                                    │        │
│  ┌────────────────────────────────────────────────────────────┐ │        │
│  │                    QUALITY GATES                            │ │        │
│  │                                                             │ │        │
│  │  Data Gate   ──▶ PASS (price verified: ✓)                  │ │        │
│  │  Logic Gate  ──▶ PASS (recommendation aligned: ✓)          │ │        │
│  │  Bird's Eye  ──▶ PASS (no red flags: ✓)                    │ │        │
│  │                                                             │ │        │
│  └──────────────────────────┬──────────────────────────────────┘ │        │
│                             │                                    │        │
│                             ▼                                    │        │
│  ┌────────────────────────────────────────────────────────────┐ │        │
│  │                    SYNTHESIS                                │ │        │
│  │                                                             │ │        │
│  │  Synthesizer ──▶ Final Report Structure                    │ │        │
│  │    • Executive Summary                                      │ │        │
│  │    • Investment Thesis                                      │ │        │
│  │    • Company Overview                                       │ │        │
│  │    • Industry Analysis                                      │ │        │
│  │    • Financial Analysis                                     │ │        │
│  │    • Valuation (5 scenarios)                               │ │        │
│  │    • Risks                                                  │ │        │
│  │    • Recommendation: BUY, Target: HKD 63.10                │ │        │
│  │                                                             │ │        │
│  └──────────────────────────┬──────────────────────────────────┘ │        │
│                             │                                    │        │
└─────────────────────────────┼────────────────────────────────────┘        │
                              │                                             │
                              ▼                                             │
┌─────────────────────────────────────────────────────────────────┐        │
│                    REPORT GENERATION                             │        │
│                                                                  │        │
│  graph_executor.save_results()                                  │        │
│    └──▶ context/6682_HK_workflow_result.json                    │        │
│                                                                  │        │
│  generate_workflow_report.py                                    │        │
│    └──▶ reports/6682_HK_Tongcheng_detailed.html                 │ ───────┘
│    └──▶ reports/index.html                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


                           LEGEND
         ─────────────────────────────────────

         ───▶   Data flow direction
         {...}  JSON/structured data
         ✓      Validation passed
         HKD    Hong Kong Dollar (currency)
```

---

## Summary

This document provides comprehensive flowcharts for the Equity Minions Multi-AI Equity Research System:

| Section | Description | Key Components |
|---------|-------------|----------------|
| A | Entry & Price Prefetch | config.py, prefetch_data.py, Yahoo Finance API |
| B | Workflow Engine | workflow_loader.py, graph_executor.py, node_executor.py |
| C | Research Phase (Tier 0-2) | Research Supervisor, Data Collectors, Data Checkpoint |
| D | Debate Phase (Tier 3) | Moderator, Bull/Bear Advocates, Devil's Advocate, Debate Critic |
| E | Valuation Phase (Tier 4-5) | Pre-Model Validator, Financial Modeler (Python), QC Agents, Valuation Committee |
| F | Quality Control (Tier 6) | Data/Logic/Bird's Eye Gates, Quality Supervisor |
| G | Output Generation (Tier 7) | Synthesizer, generate_workflow_report.py, HTML Reports |

The system uses **5 AI providers** (GPT-4o, Grok, Qwen, Gemini) and features **real Python DCF calculations** rather than AI-hallucinated numbers.
