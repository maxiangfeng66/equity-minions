"""
MCP (Model Context Protocol) Tool Definitions for Equity Research Agents.

This module defines tools in MCP format for integration with Claude Code
and other MCP-compatible systems. It wraps existing functionality and
adds new tools needed by the agent workflow.

Usage:
    Tools can be invoked via MCP protocol or directly via Python.
    Each tool returns a standardized MCPToolResult.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import json

# Import existing tools - DO NOT DUPLICATE
from .financial_calculator import FinancialCalculator, DCFCalculator, DCFInputs
from .market_data_api import MarketDataAPI
from .validation_tools import ValidationTools

# Import utilities
import sys
sys.path.append('..')
try:
    from utils.price_fetcher import get_stock_price as fetch_price
except ImportError:
    fetch_price = None


@dataclass
class MCPToolResult:
    """Standardized result format for MCP tools"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def serialize_to_dict(self) -> Dict:
        """Serialize result to dictionary format"""
        return asdict(self)

    def serialize_to_json_string(self) -> str:
        """Serialize result to JSON string"""
        return json.dumps(self.serialize_to_dict(), indent=2, default=str)


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

MCP_TOOLS = {
    "get_stock_price": {
        "name": "get_stock_price",
        "description": "Get current stock price and basic market data for a ticker symbol",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., 'AAPL', '6682.HK')"
                },
                "include_history": {
                    "type": "boolean",
                    "description": "Include 52-week high/low",
                    "default": True
                }
            },
            "required": ["ticker"]
        }
    },

    "validate_ticker": {
        "name": "validate_ticker",
        "description": "Validate that a ticker symbol exists and matches the expected company",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol to validate"
                },
                "expected_company_name": {
                    "type": "string",
                    "description": "Expected company name to verify against"
                }
            },
            "required": ["ticker"]
        }
    },

    "get_peer_companies": {
        "name": "get_peer_companies",
        "description": "Find comparable peer companies for valuation analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Target company ticker"
                },
                "sector": {
                    "type": "string",
                    "description": "Industry sector (e.g., 'Technology', 'Healthcare')"
                },
                "market_cap_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Market cap range [min, max] in millions USD"
                },
                "region": {
                    "type": "string",
                    "description": "Geographic region filter",
                    "enum": ["US", "HK", "CN", "EU", "GLOBAL"]
                },
                "max_peers": {
                    "type": "integer",
                    "description": "Maximum number of peers to return",
                    "default": 5
                }
            },
            "required": ["ticker"]
        }
    },

    "get_peer_multiples": {
        "name": "get_peer_multiples",
        "description": "Get valuation multiples for a list of peer companies",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of peer ticker symbols"
                },
                "multiples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiples to fetch",
                    "default": ["P/E", "EV/EBITDA", "P/S", "P/B"]
                }
            },
            "required": ["tickers"]
        }
    },

    "get_company_financials": {
        "name": "get_company_financials",
        "description": "Get historical financial data for DCF modeling",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                },
                "years": {
                    "type": "integer",
                    "description": "Number of historical years",
                    "default": 5
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Financial metrics to fetch",
                    "default": ["revenue", "ebit", "net_income", "fcf", "total_debt", "cash"]
                }
            },
            "required": ["ticker"]
        }
    },

    "compute_wacc": {
        "name": "compute_wacc",
        "description": "Calculate Weighted Average Cost of Capital with full formula breakdown",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_free_rate": {
                    "type": "number",
                    "description": "Risk-free rate (e.g., 0.04 for 4%)"
                },
                "beta": {
                    "type": "number",
                    "description": "Company beta"
                },
                "equity_risk_premium": {
                    "type": "number",
                    "description": "Equity risk premium (e.g., 0.05 for 5%)"
                },
                "country_risk_premium": {
                    "type": "number",
                    "description": "Country risk premium",
                    "default": 0.0
                },
                "cost_of_debt": {
                    "type": "number",
                    "description": "Pre-tax cost of debt"
                },
                "tax_rate": {
                    "type": "number",
                    "description": "Corporate tax rate"
                },
                "debt_ratio": {
                    "type": "number",
                    "description": "Debt / Total Value ratio"
                }
            },
            "required": ["risk_free_rate", "beta", "equity_risk_premium", "cost_of_debt", "tax_rate", "debt_ratio"]
        }
    },

    "validate_dcf_parameters": {
        "name": "validate_dcf_parameters",
        "description": "Validate DCF model parameters for reasonableness",
        "input_schema": {
            "type": "object",
            "properties": {
                "growth_rate": {
                    "type": "number",
                    "description": "Revenue growth rate assumption"
                },
                "terminal_growth": {
                    "type": "number",
                    "description": "Terminal growth rate"
                },
                "wacc": {
                    "type": "number",
                    "description": "Weighted average cost of capital"
                },
                "ebit_margin": {
                    "type": "number",
                    "description": "Target EBIT margin"
                },
                "industry": {
                    "type": "string",
                    "description": "Industry for benchmark comparison"
                }
            },
            "required": ["growth_rate", "terminal_growth", "wacc"]
        }
    }
}


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

class MCPToolExecutor:
    """
    Executes MCP tools and returns standardized results.

    This class wraps existing tool implementations and provides
    a unified interface for MCP tool invocation.
    """

    def __init__(self):
        self.market_api = MarketDataAPI()
        self.financial_calc = FinancialCalculator()
        self.dcf_calc = DCFCalculator()
        self.validation = ValidationTools()

    def invoke_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPToolResult:
        """Invoke an MCP tool by name with given parameters"""
        method_name = f"_invoke_{tool_name}"
        if hasattr(self, method_name):
            try:
                return getattr(self, method_name)(parameters)
            except Exception as e:
                return MCPToolResult(success=False, error=str(e))
        else:
            return MCPToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )

    def _invoke_get_stock_price(self, params: Dict) -> MCPToolResult:
        """Get stock price using existing market data API"""
        ticker = params.get("ticker")
        include_history = params.get("include_history", True)

        try:
            # Try yfinance via existing utility
            if fetch_price:
                price_data = fetch_price(ticker)
                if price_data:
                    return MCPToolResult(
                        success=True,
                        data={
                            "ticker": ticker,
                            "price": price_data.get("price"),
                            "currency": price_data.get("currency", "USD"),
                            "52_week_high": price_data.get("52_week_high"),
                            "52_week_low": price_data.get("52_week_low"),
                            "market_cap": price_data.get("market_cap"),
                            "volume": price_data.get("volume")
                        }
                    )

            # Fallback to market API
            data = self.market_api.get_price(ticker)
            if data:
                return MCPToolResult(success=True, data=data)

            return MCPToolResult(
                success=False,
                error=f"Could not fetch price for {ticker}"
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _invoke_validate_ticker(self, params: Dict) -> MCPToolResult:
        """Validate ticker exists and matches expected company"""
        ticker = params.get("ticker")
        expected_name = params.get("expected_company_name")

        try:
            # Fetch actual company info
            info = self.market_api.get_company_info(ticker)

            if not info:
                return MCPToolResult(
                    success=True,
                    data={
                        "valid": False,
                        "ticker": ticker,
                        "reason": "Ticker not found"
                    }
                )

            actual_name = info.get("company_name", "")

            # Check for name match if expected name provided
            if expected_name:
                # Simple similarity check
                name_match = self._check_company_name_similarity(expected_name, actual_name)
                return MCPToolResult(
                    success=True,
                    data={
                        "valid": name_match,
                        "ticker": ticker,
                        "actual_company_name": actual_name,
                        "expected_company_name": expected_name,
                        "match_confidence": 1.0 if name_match else 0.0,
                        "reason": "Names match" if name_match else "Company name mismatch - possible hallucination"
                    },
                    warnings=[] if name_match else ["HALLUCINATION_RISK: Company name does not match ticker"]
                )

            return MCPToolResult(
                success=True,
                data={
                    "valid": True,
                    "ticker": ticker,
                    "company_name": actual_name,
                    "exchange": info.get("exchange"),
                    "sector": info.get("sector")
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _check_company_name_similarity(self, expected: str, actual: str) -> bool:
        """Check if two company names are similar enough"""
        expected_lower = expected.lower().strip()
        actual_lower = actual.lower().strip()

        # Direct match
        if expected_lower == actual_lower:
            return True

        # Check if one contains the other
        if expected_lower in actual_lower or actual_lower in expected_lower:
            return True

        # Check key words
        expected_words = set(expected_lower.split())
        actual_words = set(actual_lower.split())

        # Remove common suffixes
        common_suffixes = {'inc', 'inc.', 'corp', 'corp.', 'ltd', 'ltd.', 'limited',
                          'company', 'co', 'co.', 'plc', 'holdings', 'group'}
        expected_words -= common_suffixes
        actual_words -= common_suffixes

        # Check overlap
        if expected_words and actual_words:
            overlap = len(expected_words & actual_words) / max(len(expected_words), len(actual_words))
            return overlap >= 0.5

        return False

    def _invoke_get_peer_companies(self, params: Dict) -> MCPToolResult:
        """Find peer companies for comparison"""
        ticker = params.get("ticker")
        sector = params.get("sector")
        market_cap_range = params.get("market_cap_range")
        region = params.get("region", "GLOBAL")
        max_peers = params.get("max_peers", 5)

        try:
            # Get company info first to determine sector if not provided
            info = self.market_api.get_company_info(ticker)
            if not sector and info:
                sector = info.get("sector")

            # Get peers from market API
            peers = self.market_api.get_peers(
                ticker=ticker,
                sector=sector,
                market_cap_range=market_cap_range,
                max_results=max_peers
            )

            if peers:
                return MCPToolResult(
                    success=True,
                    data={
                        "target_ticker": ticker,
                        "sector": sector,
                        "peers": peers,
                        "peer_count": len(peers)
                    }
                )

            return MCPToolResult(
                success=True,
                data={
                    "target_ticker": ticker,
                    "sector": sector,
                    "peers": [],
                    "peer_count": 0
                },
                warnings=["No peers found matching criteria"]
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _invoke_get_peer_multiples(self, params: Dict) -> MCPToolResult:
        """Get valuation multiples for peer companies"""
        tickers = params.get("tickers", [])
        multiples = params.get("multiples", ["P/E", "EV/EBITDA", "P/S", "P/B"])

        try:
            results = {}
            warnings = []

            for ticker in tickers:
                ticker_data = self.market_api.get_multiples(ticker)
                if ticker_data:
                    # Filter to requested multiples
                    filtered = {k: v for k, v in ticker_data.items() if k in multiples}
                    results[ticker] = filtered
                else:
                    warnings.append(f"Could not fetch multiples for {ticker}")

            # Calculate medians
            medians = {}
            for multiple in multiples:
                values = [results[t][multiple] for t in results if multiple in results.get(t, {})]
                if values:
                    sorted_vals = sorted(values)
                    mid = len(sorted_vals) // 2
                    medians[multiple] = sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid-1] + sorted_vals[mid]) / 2

            return MCPToolResult(
                success=True,
                data={
                    "peer_multiples": results,
                    "median_multiples": medians,
                    "peer_count": len(results)
                },
                warnings=warnings
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _invoke_get_company_financials(self, params: Dict) -> MCPToolResult:
        """Get historical financials for a company"""
        ticker = params.get("ticker")
        years = params.get("years", 5)
        metrics = params.get("metrics", ["revenue", "ebit", "net_income", "fcf", "total_debt", "cash"])

        try:
            financials = self.market_api.get_financials(ticker, years=years)

            if financials:
                # Filter to requested metrics
                filtered = {k: v for k, v in financials.items() if k in metrics or k == "years"}

                return MCPToolResult(
                    success=True,
                    data={
                        "ticker": ticker,
                        "financials": filtered,
                        "years_available": len(financials.get("years", []))
                    }
                )

            return MCPToolResult(
                success=False,
                error=f"Could not fetch financials for {ticker}"
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _invoke_compute_wacc(self, params: Dict) -> MCPToolResult:
        """Calculate WACC using existing FinancialCalculator"""
        try:
            wacc, cost_of_equity, calculation = self.financial_calc.calculate_wacc(
                risk_free_rate=params["risk_free_rate"],
                beta=params["beta"],
                equity_risk_premium=params["equity_risk_premium"],
                country_risk_premium=params.get("country_risk_premium", 0.0),
                cost_of_debt=params["cost_of_debt"],
                tax_rate=params["tax_rate"],
                debt_ratio=params["debt_ratio"]
            )

            warnings = []
            if wacc > 0.15:
                warnings.append(f"WACC ({wacc:.1%}) is high - verify inputs")
            if wacc < 0.06:
                warnings.append(f"WACC ({wacc:.1%}) is low - verify inputs")

            return MCPToolResult(
                success=True,
                data={
                    "wacc": wacc,
                    "cost_of_equity": cost_of_equity,
                    "calculation_breakdown": calculation,
                    "inputs": {
                        "risk_free_rate": params["risk_free_rate"],
                        "beta": params["beta"],
                        "equity_risk_premium": params["equity_risk_premium"],
                        "country_risk_premium": params.get("country_risk_premium", 0.0),
                        "cost_of_debt": params["cost_of_debt"],
                        "tax_rate": params["tax_rate"],
                        "debt_ratio": params["debt_ratio"]
                    }
                },
                warnings=warnings
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def _invoke_validate_dcf_parameters(self, params: Dict) -> MCPToolResult:
        """Validate DCF parameters for reasonableness"""
        growth_rate = params.get("growth_rate")
        terminal_growth = params.get("terminal_growth")
        wacc = params.get("wacc")
        ebit_margin = params.get("ebit_margin")
        industry = params.get("industry")

        warnings = []
        errors = []

        # Terminal growth checks
        if terminal_growth >= 0.04:
            warnings.append(f"Terminal growth ({terminal_growth:.1%}) >= 4% is aggressive")
        if terminal_growth >= wacc:
            errors.append(f"INVALID: Terminal growth ({terminal_growth:.1%}) >= WACC ({wacc:.1%})")
        if wacc - terminal_growth < 0.02:
            warnings.append(f"WACC-g spread ({(wacc - terminal_growth):.2%}) < 2% creates unstable terminal value")

        # Growth rate checks
        if growth_rate > 0.50:
            warnings.append(f"Growth rate ({growth_rate:.1%}) > 50% is very aggressive")
        if growth_rate > 0.30 and industry not in ["Technology", "Biotech", "High Growth"]:
            warnings.append(f"Growth rate ({growth_rate:.1%}) > 30% unusual outside high-growth sectors")

        # Margin checks
        if ebit_margin:
            if ebit_margin > 0.40:
                warnings.append(f"EBIT margin ({ebit_margin:.1%}) > 40% is very high")
            if ebit_margin < 0:
                warnings.append(f"Negative EBIT margin ({ebit_margin:.1%}) - company unprofitable")

        is_valid = len(errors) == 0

        return MCPToolResult(
            success=True,
            data={
                "is_valid": is_valid,
                "parameters_checked": {
                    "growth_rate": growth_rate,
                    "terminal_growth": terminal_growth,
                    "wacc": wacc,
                    "ebit_margin": ebit_margin,
                    "industry": industry
                },
                "errors": errors,
                "validation_passed": is_valid
            },
            warnings=warnings
        )


# =============================================================================
# MCP INTERFACE FUNCTIONS
# =============================================================================

def get_mcp_tool_definitions() -> List[Dict]:
    """Return list of MCP tool definitions for registration"""
    return list(MCP_TOOLS.values())


def invoke_mcp_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict:
    """Invoke an MCP tool and return result as dict"""
    executor = MCPToolExecutor()
    result = executor.invoke_mcp_tool(tool_name, parameters)
    return result.serialize_to_dict()


def list_mcp_tools() -> List[str]:
    """List names of all available MCP tools"""
    return list(MCP_TOOLS.keys())


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP TOOLS FOR EQUITY RESEARCH")
    print("=" * 60)

    print("\nAvailable tools:")
    for name, tool in MCP_TOOLS.items():
        print(f"  - {name}: {tool['description'][:60]}...")

    print("\nTool schemas:")
    for name, tool in MCP_TOOLS.items():
        print(f"\n{name}:")
        print(f"  Required: {tool['input_schema'].get('required', [])}")
        props = tool['input_schema'].get('properties', {})
        for prop_name, prop_def in props.items():
            print(f"    - {prop_name}: {prop_def.get('type')} - {prop_def.get('description', '')[:40]}")

    # Test WACC calculation
    print("\n" + "=" * 60)
    print("TEST: compute_wacc")
    print("=" * 60)

    executor = MCPToolExecutor()
    result = executor.invoke_mcp_tool("compute_wacc", {
        "risk_free_rate": 0.04,
        "beta": 1.2,
        "equity_risk_premium": 0.05,
        "country_risk_premium": 0.02,
        "cost_of_debt": 0.06,
        "tax_rate": 0.25,
        "debt_ratio": 0.3
    })

    print(result.serialize_to_json_string())
