# Agent Reference Guide

## Overview

The Equity Research system uses 16 agents organized in 7 tiers.

## Agent Directory

### TIER 0: ORCHESTRATION

#### Research Supervisor
| Attribute | Value |
|-----------|-------|
| **ID** | `Research Supervisor` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 10 |

**Tasks:**
1. Create research plan for target equity
2. Identify key questions and data sources
3. Establish expected price range for verification
4. Dispatch workers to collect data
5. Final sign-off on completed reports
6. Verify company identity matches request
7. Ensure verified price used consistently
8. Confirm all report sections complete
9. Give final approval or request fixes

**Output Keywords:** `RESEARCH: INITIATED`, `FINAL: APPROVED`, `FINAL: NEEDS_REVISION`

**Tools Needed:**
- `checklist_validator` (TO BUILD) - Automate final sign-off checks

---

### TIER 1: RESEARCH WORKERS

#### Market Data Collector
| Attribute | Value |
|-----------|-------|
| **ID** | `Market Data Collector` |
| **Model** | gemini-2.0-flash (Google) |
| **Context Window** | 5 |

**Tasks:**
1. Collect current stock price (verify from START message)
2. Gather 52-week price range
3. Collect market capitalization
4. Gather trading volume data
5. Collect beta coefficient
6. Gather revenue and growth data (3-5 years)
7. Collect margin data (gross, operating, net)
8. Gather EPS and FCF data
9. Collect debt and cash position
10. Gather valuation multiples (P/E, P/S, P/B, EV/EBITDA)
11. Collect analyst consensus data

**Output Keywords:** `DATA: COLLECTED`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `yfinance_fetcher` | AVAILABLE | utils/price_fetcher.py |
| `financial_api` | OUTSOURCE | Alpha Vantage, Polygon.io, FMP |
| `sec_edgar_fetcher` | TO BUILD | For 10-K, 10-Q filings |
| `hkex_fetcher` | TO BUILD | For HK stocks |

---

#### Industry Deep Dive
| Attribute | Value |
|-----------|-------|
| **ID** | `Industry Deep Dive` |
| **Model** | gemini-2.0-flash (Google) |
| **Context Window** | 5 |

**Tasks:**
1. Analyze TAM/SAM/SOM
2. Calculate market growth rates
3. Map competitive landscape
4. Identify key competitors and market shares
5. Analyze industry trends
6. Assess regulatory environment
7. Identify growth drivers

**Output Keywords:** `INDUSTRY: ANALYZED`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `web_search` | AVAILABLE | Built into Gemini |
| `industry_report_fetcher` | OUTSOURCE | Statista, IBISWorld |
| `news_aggregator` | TO BUILD | NewsAPI, Google News |

---

#### Company Deep Dive
| Attribute | Value |
|-----------|-------|
| **ID** | `Company Deep Dive` |
| **Model** | gemini-2.0-flash (Google) |
| **Context Window** | 5 |

**Tasks:**
1. Analyze business model
2. Identify revenue streams
3. Assess competitive position
4. Evaluate economic moat
5. Analyze management quality
6. Review management track record
7. Assess capital allocation history
8. Identify company-specific risks
9. Analyze recent developments
10. Review insider transactions

**Output Keywords:** `COMPANY: ANALYZED`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `web_search` | AVAILABLE | Built into Gemini |
| `company_filings_reader` | TO BUILD | PDF parsing for annual reports |
| `insider_transaction_tracker` | OUTSOURCE | OpenInsider API |

---

### TIER 2: QUALITY CONTROL

#### Data Gate
| Attribute | Value |
|-----------|-------|
| **ID** | `Data Gate` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 15 |

**Tasks:**
1. Extract verified price from START message
2. Validate company identity matches request
3. Detect hallucinated company names
4. Check data consistency across sources
5. Verify market cap = price × shares
6. Block contaminated data
7. Pass clean data to debate

**Output Keywords:** `DATA: VERIFIED`, `DATA: FAILED`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `hallucination_detector` | AVAILABLE | graph_executor.py |
| `ticker_validator` | TO BUILD | Cross-ref with yfinance |
| `math_consistency_checker` | TO BUILD | Verify calculations |

---

### TIER 3: DEBATE

#### Debate Moderator
| Attribute | Value |
|-----------|-------|
| **ID** | `Debate Moderator` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 10 |

**Tasks:**
1. Set up structured bull/bear debate
2. Provide research context to advocates
3. Ensure verified price is communicated
4. Frame key questions for debate

**Output Keywords:** `DEBATE: INITIATED`

**Tools:** None (reasoning only)

---

#### Bull Advocate
| Attribute | Value |
|-----------|-------|
| **ID** | `Bull Advocate` |
| **Model** | grok-3-fast (xAI) |
| **Context Window** | 10 |

**Tasks:**
1. Present strongest investment case
2. Identify growth catalysts with evidence
3. Quantify upside potential
4. Highlight competitive advantages

**Output Keywords:** `BULL: COMPLETE`

**Tools:** None (reasoning only)

---

#### Bear Advocate
| Attribute | Value |
|-----------|-------|
| **ID** | `Bear Advocate` |
| **Model** | grok-3-fast (xAI) |
| **Context Window** | 10 |

**Tasks:**
1. Present strongest counter-case
2. Identify risks and threats
3. Quantify downside risk
4. Highlight competitive threats

**Output Keywords:** `BEAR: COMPLETE`

**Tools:** None (reasoning only)

---

#### Debate Synthesizer
| Attribute | Value |
|-----------|-------|
| **ID** | `Debate Synthesizer` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 15 |

**Tasks:**
1. Synthesize bull and bear arguments
2. Rank key points by conviction
3. Identify key uncertainties
4. Provide preliminary investment lean

**Output Keywords:** `DEBATE: SYNTHESIZED`

**Tools:** None (reasoning only)

---

### TIER 4: VALUATION

#### Dot Connector
| Attribute | Value |
|-----------|-------|
| **ID** | `Dot Connector` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 20 |

**Tasks:**
1. Bridge qualitative to quantitative
2. Extract revenue growth parameters
3. Extract margin parameters
4. Calculate WACC components
5. Set scenario probabilities
6. Avoid repeating failed parameters
7. Use binary search for convergence

**Output Keywords:** `PARAMETERS: CONNECTED`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `parameter_history` | AVAILABLE | graph_executor.py |
| `wacc_calculator` | TO BUILD | WACC formula |
| `parameter_validator` | TO BUILD | Range validation |

---

#### Financial Modeler
| Attribute | Value |
|-----------|-------|
| **ID** | `Financial Modeler` |
| **Model** | Python DCF Engine (not AI) |
| **Context Window** | 10 |

**Tasks:**
1. Calculate DCF across 5 scenarios
2. Compute probability-weighted value
3. Generate yearly projections
4. Calculate terminal value
5. Perform reverse DCF analysis

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `dcf_engine` | AVAILABLE | agents/tools/dcf_engine.py |
| `sensitivity_calculator` | AVAILABLE | agents/tools/dcf_engine.py |

---

### TIER 5: VALUATION QC

#### DCF Validator
| Attribute | Value |
|-----------|-------|
| **ID** | `DCF Validator` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 20 |

**Tasks:**
1. Validate reasoning behind DCF
2. Check internal consistency
3. Verify assumptions supported by research
4. Stress-test assumptions
5. Defend sound reasoning (not market alignment)
6. Flag ONLY logical errors

**Output Keywords:** `DCF: VALIDATED`, `DCF: VALIDATED - DIVERGENT BUT JUSTIFIED`, `DCF: NEEDS_REVISION`

---

#### Comparable Validator
| Attribute | Value |
|-----------|-------|
| **ID** | `Comparable Validator` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 15 |

**Tasks:**
1. Identify 3-5 peer companies
2. Gather peer valuation multiples
3. Calculate implied value from peers
4. Cross-check DCF vs peers
5. Explain divergence

**Output Keywords:** `COMPS: VALIDATED`, `COMPS: DIVERGENT`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `peer_finder` | TO BUILD | Industry + size filters |
| `peer_multiples_fetcher` | TO BUILD | Use yfinance |
| `comps_calculator` | TO BUILD | Apply multiples |

---

#### Sensitivity Auditor
| Attribute | Value |
|-----------|-------|
| **ID** | `Sensitivity Auditor` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 15 |

**Tasks:**
1. Test sensitivity to growth (±5%, ±10%)
2. Test sensitivity to margin (±2%, ±5%)
3. Test sensitivity to WACC (±1%, ±2%)
4. Identify key value drivers
5. Calculate break-even points

**Output Keywords:** `SENSITIVITY: COMPLETE`

---

### TIER 6: QUALITY GATE

#### Quality Gate
| Attribute | Value |
|-----------|-------|
| **ID** | `Quality Gate` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 25 |

**Tasks:**
1. Holistic quality review
2. Check logical consistency
3. Verify recommendation matches analysis
4. Count iterations (loop prevention)
5. Force exit after 3 iterations
6. Route to appropriate node

**Output Keywords:** `ROUTE: Synthesizer`, `ROUTE: Data Gate`, `ROUTE: DCF Validator`, `ROUTE: Dot Connector`

**Tools:**
| Tool | Status | Notes |
|------|--------|-------|
| `loop_counter` | AVAILABLE | graph_executor.py |
| `consistency_checker` | TO BUILD | NLP contradiction detection |

---

### TIER 7: SYNTHESIS

#### Synthesizer
| Attribute | Value |
|-----------|-------|
| **ID** | `Synthesizer` |
| **Model** | gpt-4o (OpenAI) |
| **Context Window** | 30 |

**Tasks:**
1. Create final research report
2. Write executive summary
3. Compile investment thesis
4. Summarize company/industry
5. Present valuation with scenarios
6. List risks and monitoring points
7. Formulate recommendation

**Output Keywords:** `REPORT: COMPLETE`

---

## Tools Roadmap

### IMPLEMENTED - MCP Tools (agents/tools/mcp_tools.py)

| Tool | Agent | Status |
|------|-------|--------|
| `get_stock_price` | Market Data Collector | AVAILABLE |
| `validate_ticker` | Data Gate | AVAILABLE |
| `get_peer_companies` | Comparable Validator | AVAILABLE |
| `get_peer_multiples` | Comparable Validator | AVAILABLE |
| `get_company_financials` | Market Data Collector | AVAILABLE |
| `compute_wacc` | Dot Connector | AVAILABLE |
| `validate_dcf_parameters` | DCF Validator | AVAILABLE |

### TO BUILD - Remaining Priority

| Tool | Agent | Description |
|------|-------|-------------|
| `company_filings_reader` | Company Deep Dive | PDF parsing for annual reports |
| `sec_edgar_fetcher` | Market Data Collector | SEC 10-K, 10-Q filings |
| `hkex_fetcher` | Market Data Collector | HK stocks data |

### TO OUTSOURCE - External APIs

| Tool | Agent | Candidates |
|------|-------|------------|
| `financial_api` | Market Data Collector | Alpha Vantage, Polygon.io, FMP |
| `industry_report_fetcher` | Industry Deep Dive | Statista API, IBISWorld |
| `insider_transaction_tracker` | Company Deep Dive | OpenInsider API |

---

## MCP Integration

MCP (Model Context Protocol) tools are implemented in `agents/tools/mcp_tools.py`.

### Usage

```python
from agents.tools import invoke_mcp_tool, list_mcp_tools

# List available tools
print(list_mcp_tools())
# ['get_stock_price', 'validate_ticker', 'get_peer_companies', ...]

# Invoke a tool
result = invoke_mcp_tool('compute_wacc', {
    'risk_free_rate': 0.04,
    'beta': 1.2,
    'equity_risk_premium': 0.05,
    'cost_of_debt': 0.06,
    'tax_rate': 0.25,
    'debt_ratio': 0.3
})

print(result['data']['wacc'])  # 0.0975 (9.75%)
```

### Tool Definitions for MCP Registration

```python
from agents.tools import get_mcp_tool_definitions

# Returns list of MCP-compliant tool definitions
tools = get_mcp_tool_definitions()
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 16 |
| AI Agents | 15 |
| Python Tools | 1 |
| OpenAI Agents | 10 |
| Google Agents | 3 |
| xAI Agents | 2 |
| MCP Tools Available | 7 |
| Tools To Build | 3 |
| Tools To Outsource | 3 |
