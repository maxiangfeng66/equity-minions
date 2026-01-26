# Equity Minions System Investigation Summary

**Generated:** 2026-01-23
**Investigator Agents Used:**
- Project Structure Investigator
- Workflow Integrity Checker
- Data Flow Tracer

---

## Executive Summary

The investigation reveals **critical systemic issues** in the Multi-AI Equity Research workflow. The main problems are:

1. **Price Hallucination**: Agents use prices from training data instead of verified real-time prices
2. **Company Data Contamination**: Research outputs contain data from big tech companies (Amazon, Microsoft, Google) instead of the target company
3. **Validation Bypass**: Critical quality gates (Data Checkpoint, Pre-Model Validator) are not executing properly
4. **Workflow Version Mismatch**: System was running v3 workflow (missing quality gates) instead of v4

---

## Investigation Results

### 1. Project Structure Analysis

| Metric | Value |
|--------|-------|
| Total Python Files | 73 |
| Entry Points | 27 |
| Orphaned Files | 34 |
| Missing Imports | 67 |

**Key Issues:**
- 34 orphaned files not integrated into workflow
- 67 missing import errors (code referencing non-existent modules)
- Multiple legacy entry points causing confusion

**Critical Orphaned Files:**
- `agents/ai_providers.py` - AI provider abstraction (should be core)
- `agents/debate_system.py` - Debate orchestration
- `research/dcf.py` - DCF calculations
- `utils/html_generator.py` - Report generation

### 2. Workflow Integrity Analysis

| Workflow | Nodes | Edges | Issues |
|----------|-------|-------|--------|
| v1 | 10 | 15 | None (basic) |
| v2 | 17 | 26 | None (good) |
| v3 | 21 | 36 | Missing quality gates |
| v4 | 25 | 40 | 3 routing issues |
| portfolio | 7 | 9 | None |

**v4 Workflow Issues:**
1. `Synthesizer` is a dead-end node (no outgoing edges)
2. `Quality Supervisor -> Data Checkpoint` edge missing routing keyword in prompt
3. `Quality Supervisor -> Debate Moderator` edge missing routing keyword in prompt

### 3. Data Flow Analysis

#### LEGN US Workflow Result
| Metric | Value |
|--------|-------|
| Data Integrity Score | 25/100 |
| Critical Failures | 10 |
| Expected Price | USD 19.34 |
| Actual Price Found | USD 9 (hallucinated) |

**Issues Found:**
- "Amazon" data found in 6 nodes (should be Legend Biotech)
- DATA: VERIFIED keyword missing
- INPUTS: VALIDATED keyword missing
- ROUTE: Synthesizer keyword missing

#### 9660 HK Workflow Result
| Metric | Value |
|--------|-------|
| Data Integrity Score | 31.2/100 |
| Critical Failures | 10 |
| Expected Price | HKD 8.50 |
| Actual Price Found | HKD 445 (hallucinated) |

**Issues Found:**
- Microsoft, Amazon, Google data found in multiple nodes
- Same missing routing keywords as LEGN US

---

## Root Cause Analysis

### Why Prices Are Wrong

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT FLOW (BROKEN)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User: "Research LEGN US"                                   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ run_workflow.py │ ◄─ No prefetch! Goes straight to       │
│  └────────┬────────┘   workflow                             │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ Market Data     │ ◄─ Asks "what ticker?" instead of      │
│  │ Collector       │   actually searching                   │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ Financial       │ ◄─ Uses price from training data       │
│  │ Modeler         │   ($53.30 for LEGN in 2024)           │
│  └─────────────────┘                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Wrong Company Data Appears

The Industry Deep Dive agent is using LLM training data about tech companies as "examples" of industry analysis, and this data is bleeding into the actual research output.

### Why Validation Nodes Don't Execute

1. Workflow was running v3 (default was wrong in run_workflow_live.py)
2. Edge conditions require specific keywords that upstream nodes don't produce
3. Some nodes marked as "passthrough" but actually need execution

---

## Recommended Fixes

### Immediate (Critical Priority)

1. **Always run prefetch_data.py first**
   ```python
   # In run_workflow_live.py, add at start:
   from prefetch_data import prefetch_market_data, build_price_context
   price_data = await prefetch_market_data(ticker)
   task_prompt = build_price_context(price_data) + original_prompt
   ```

2. **Fix default workflow version**
   - Already fixed: Changed from v3 to v4 in both runner scripts

3. **Fix routing keywords in Quality Supervisor**
   - Add to prompt: "If routing back, explicitly state ROUTE: Data Checkpoint or ROUTE: Debate Moderator"

### Short-term (High Priority)

4. **Fix Market Data Collector prompt**
   - Change from: "What data would you like me to collect?"
   - Change to: "Search for current market data for {ticker}"

5. **Strengthen company identity in prompts**
   - Add: "IMPORTANT: Only return data for {company_name} ({ticker}). Do NOT include data from Apple, Amazon, Microsoft, Google, or other unrelated companies."

6. **Add price validation at every tier**
   - Each node should check: "Is the price I'm using {verified_price}?"

### Medium-term (Medium Priority)

7. **Clean up orphaned files**
   - Either integrate or delete the 34 orphaned files
   - Update imports to use correct module paths

8. **Add end-to-end testing**
   - Run investigation agents after each workflow
   - Fail if data integrity score < 70%

9. **Create node unit tests**
   - Test each node individually with known inputs
   - Verify outputs contain correct company data

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| `agents/investigators/project_structure_investigator.py` | Maps codebase structure |
| `agents/investigators/workflow_integrity_checker.py` | Validates workflow YAML |
| `agents/investigators/data_flow_tracer.py` | Traces data through execution |
| `agents/investigators/node_function_validator.py` | Tests individual nodes |
| `brain/system_flowchart.md` | Complete architecture diagram |
| `brain/investigation_summary.md` | This summary |

---

## Investigation Agent Usage

```bash
# Run all investigators
python agents/investigators/project_structure_investigator.py
python agents/investigators/workflow_integrity_checker.py
python agents/investigators/data_flow_tracer.py context/LEGN_US_workflow_result.json 19.34

# Check generated reports
cat context/investigation_report.json
cat context/workflow_integrity_reports.json
cat context/trace_LEGN_US_workflow_result.json
```

---

## Next Steps

1. Fix the critical issues listed above
2. Re-run workflow for one ticker (LEGN US) with fixes
3. Run investigators again to verify improvements
4. If data integrity > 70%, proceed with remaining tickers
5. Monitor ongoing executions with investigation agents
