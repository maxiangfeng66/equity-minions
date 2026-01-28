# Tool Registry

Complete inventory of all tools available in the Equity Research system.

---

## Tool Categories

| Category | Count | Status |
|----------|-------|--------|
| MCP Tools | 7 | Available |
| Financial Calculators | 6 | Available |
| Market Data APIs | 8 | Available |
| Validation Tools | 7 | Available |
| Price Fetchers | 3 | Available |
| **TOTAL** | **31** | |

---

## 1. MCP Tools (agents/tools/mcp_tools.py)

Protocol-compliant tools for AI agent integration.

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `get_stock_price` | Fetch current price and market data | ticker, include_history | price, currency, 52wk range, market_cap |
| `validate_ticker` | Verify ticker matches company (anti-hallucination) | ticker, expected_company_name | valid, actual_name, match_confidence |
| `get_peer_companies` | Find comparable companies | ticker, sector, market_cap_range | peers list, sector |
| `get_peer_multiples` | Get valuation multiples for peers | tickers[], multiples[] | peer_multiples, median_multiples |
| `get_company_financials` | Historical financial metrics | ticker, years, metrics[] | financials dict |
| `compute_wacc` | Calculate WACC with breakdown | risk_free_rate, beta, erp, cod, tax, debt_ratio | wacc, cost_of_equity, calculation |
| `validate_dcf_parameters` | Check DCF inputs reasonableness | growth_rate, terminal_growth, wacc, margin | is_valid, errors, warnings |

**Usage:**
```python
from agents.tools import invoke_mcp_tool, list_mcp_tools

result = invoke_mcp_tool('compute_wacc', {
    'risk_free_rate': 0.04,
    'beta': 1.2,
    'equity_risk_premium': 0.05,
    'cost_of_debt': 0.06,
    'tax_rate': 0.25,
    'debt_ratio': 0.3
})
```

---

## 2. Financial Calculators (agents/tools/financial_calculator.py)

Mathematical computation engines - NO AI hallucination.

### FinancialCalculator Class

| Method | Description | Formula |
|--------|-------------|---------|
| `calculate_wacc()` | Weighted Average Cost of Capital | WACC = E/V × Re + D/V × Rd × (1-T) |
| `calculate_fcf()` | Free Cash Flow | FCF = EBIT(1-T) + D&A - CapEx - ΔWC |
| `calculate_terminal_value()` | Gordon Growth Terminal Value | TV = FCF × (1+g) / (WACC-g) |
| `npv()` | Net Present Value | NPV = Σ CF/(1+r)^t |
| `discount_value()` | Present Value | PV = FV / (1+r)^n |

### DCFCalculator Class

| Method | Description | Output |
|--------|-------------|--------|
| `calculate()` | Full 10-year DCF valuation | DCFOutput with EV, fair value, yearly projections |
| `validate_inputs()` | Check inputs for reasonableness | List of warnings |
| `calculate_scenarios()` | Multi-scenario DCF | Dict of scenario -> DCFOutput |
| `calculate_probability_weighted_value()` | PWV across scenarios | (pwv, calculation_string) |

**Usage:**
```python
from agents.tools import DCFCalculator, DCFInputs

calc = DCFCalculator()
inputs = DCFInputs(
    revenue_base=1000,
    ebit_margin=0.15,
    tax_rate=0.25,
    # ... more inputs
)
result = calc.calculate(inputs)
print(f"Fair Value: ${result.fair_value_per_share:.2f}")
```

---

## 3. Market Data APIs (agents/tools/market_data_api.py)

Real market data from Yahoo Finance and other sources.

### MarketDataAPI Class

| Method | Description | Returns |
|--------|-------------|---------|
| `get_quote()` | Real-time stock quote | StockQuote (price, volume, market_cap, 52wk) |
| `get_financials()` | Historical financials (3-5 years) | List[FinancialData] |
| `get_analyst_estimates()` | Analyst consensus | AnalystEstimates (targets, ratings, EPS) |
| `get_peers()` | Peer companies | List[str] |
| `verify_price()` | Verify claimed vs actual price | Dict with verified status |

### MultiSourceVerifier Class

| Method | Description | Returns |
|--------|-------------|---------|
| `verify_with_multiple_sources()` | Cross-validate across sources | consensus_price, variance, reliability |

### Data Classes

| Class | Fields |
|-------|--------|
| `StockQuote` | ticker, price, currency, change, volume, market_cap, 52wk high/low |
| `FinancialData` | revenue, gross_profit, operating_income, net_income, ebitda, margins, debt, cash |
| `AnalystEstimates` | target prices, ratings count, EPS/revenue estimates |

**Usage:**
```python
from agents.tools import MarketDataAPI
import asyncio

api = MarketDataAPI()
quote = asyncio.run(api.get_quote("6682 HK"))
print(f"Price: {quote.currency} {quote.price}")
```

---

## 4. Validation Tools (agents/tools/validation_tools.py)

Mathematical and logical validation utilities.

| Method | Description | Checks |
|--------|-------------|--------|
| `validate_dcf_math()` | Verify DCF calculations | NPV, terminal value formula, EV sum |
| `validate_wacc_calculation()` | Verify WACC formula | Component ranges, formula correctness |
| `validate_scenario_consistency()` | Check scenario logic | Probabilities sum to 1, ordering, returns |
| `validate_price_consistency()` | Compare stated vs market price | Deviation within tolerance |
| `validate_fcf_calculation()` | Verify FCF formula | EBIT(1-T) + D&A - CapEx - ΔWC |
| `run_full_validation()` | Comprehensive DCF validation | All checks combined |

### Valid Ranges (Built-in)

| Metric | Valid Range |
|--------|-------------|
| WACC | 4% - 25% |
| Terminal Growth | 1% - 4% |
| Beta | 0.3 - 3.0 |
| Risk-Free Rate | 1% - 8% |
| Equity Risk Premium | 4% - 10% |
| Operating Margin | -50% - 60% |
| Revenue Growth | -30% - 100% |
| Terminal Value % of EV | 30% - 75% |

**Usage:**
```python
from agents.tools import ValidationTools

results = ValidationTools.validate_wacc_calculation(
    stated_wacc=0.10,
    risk_free_rate=0.04,
    beta=1.2,
    equity_risk_premium=0.05,
    country_risk_premium=0.02,
    cost_of_debt=0.06,
    tax_rate=0.25,
    debt_ratio=0.3
)

for r in results:
    print(f"{r.check_name}: {'✓' if r.passed else '✗'} {r.message}")
```

---

## 5. Price Fetchers (utils/price_fetcher.py)

Multi-source price validation.

| Class/Function | Description |
|----------------|-------------|
| `MultiSourcePriceFetcher` | Fetches from multiple sources and cross-validates |
| `fetch_equity_price()` | Convenience async function |
| `PriceData` | Single source price data |
| `ValidatedPrice` | Cross-validated price with confidence |

**Confidence Levels:**
- **HIGH**: 3+ sources, <2% deviation
- **MEDIUM**: 2+ sources, <5% deviation
- **LOW**: Single source or high deviation
- **FAILED**: No price found

---

## 6. Tool Usage by Agent

| Agent | Tools Used |
|-------|------------|
| Market Data Collector | `get_stock_price`, `get_company_financials`, MarketDataAPI |
| Data Gate | `validate_ticker`, `validate_price_consistency` |
| Dot Connector | `compute_wacc`, `validate_dcf_parameters` |
| Financial Modeler | DCFCalculator, FinancialCalculator |
| DCF Validator | ValidationTools, `validate_dcf_parameters` |
| Comparable Validator | `get_peer_companies`, `get_peer_multiples` |
| Sensitivity Auditor | DCFCalculator sensitivity functions |
| Quality Gate | ValidationTools.run_full_validation |

---

## 7. Tools Roadmap

### Available Now
- All MCP tools (7)
- Financial calculators (6)
- Market data via yfinance (8)
- Validation tools (7)

### To Build
| Tool | Priority | Description |
|------|----------|-------------|
| `sec_edgar_fetcher` | HIGH | SEC 10-K, 10-Q filings |
| `hkex_fetcher` | HIGH | HKEX announcements |
| `company_filings_reader` | MEDIUM | PDF parsing for annual reports |

### To Outsource
| Tool | API Options |
|------|-------------|
| `financial_api` | Alpha Vantage, Polygon.io, FMP |
| `industry_report_fetcher` | Statista, IBISWorld |
| `insider_transaction_tracker` | OpenInsider API |

---

## Quick Reference

```python
# Import all tools
from agents.tools import (
    # MCP
    invoke_mcp_tool,
    list_mcp_tools,
    get_mcp_tool_definitions,

    # Calculators
    FinancialCalculator,
    DCFCalculator,

    # Market Data
    MarketDataAPI,

    # Validation
    ValidationTools
)

# List all MCP tools
print(list_mcp_tools())
# ['get_stock_price', 'validate_ticker', 'get_peer_companies',
#  'get_peer_multiples', 'get_company_financials', 'compute_wacc',
#  'validate_dcf_parameters']
```
