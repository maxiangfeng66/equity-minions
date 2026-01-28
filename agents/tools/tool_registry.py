"""
Tool Registry - Central registry of all tools in the Equity Research system.

This module provides:
1. Complete inventory of all tools
2. Tool lookup by name, category, or agent
3. Tool status tracking (available, to_build, to_outsource)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Import existing ToolStatus from agent_profiles
from agents.agent_profiles import ToolStatus


class ToolCategory(Enum):
    """Tool categories"""
    MCP = "mcp"
    CALCULATOR = "calculator"
    MARKET_DATA = "market_data"
    VALIDATION = "validation"
    PRICE_FETCHER = "price_fetcher"


@dataclass
class ToolEntry:
    """Definition of a single tool in the registry"""
    name: str
    description: str
    category: ToolCategory
    status: ToolStatus
    module: str
    function_or_class: str
    used_by: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    notes: Optional[str] = None


# =============================================================================
# TOOL REGISTRY
# =============================================================================

TOOL_REGISTRY: Dict[str, ToolEntry] = {
    # =========================================================================
    # MCP TOOLS
    # =========================================================================
    "get_stock_price": ToolEntry(
        name="get_stock_price",
        description="Fetch current stock price and basic market data",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_get_stock_price",
        used_by=["Market Data Collector"],
        inputs={"ticker": "str", "include_history": "bool"},
        outputs={"price": "float", "currency": "str", "52_week_high": "float", "market_cap": "float"}
    ),
    "validate_ticker": ToolEntry(
        name="validate_ticker",
        description="Validate ticker exists and matches expected company (anti-hallucination)",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_validate_ticker",
        used_by=["Data Gate"],
        inputs={"ticker": "str", "expected_company_name": "str"},
        outputs={"valid": "bool", "actual_company_name": "str", "match_confidence": "float"}
    ),
    "get_peer_companies": ToolEntry(
        name="get_peer_companies",
        description="Find comparable peer companies for valuation",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_get_peer_companies",
        used_by=["Comparable Validator"],
        inputs={"ticker": "str", "sector": "str", "market_cap_range": "list", "max_peers": "int"},
        outputs={"peers": "list", "sector": "str", "peer_count": "int"}
    ),
    "get_peer_multiples": ToolEntry(
        name="get_peer_multiples",
        description="Get valuation multiples for peer companies",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_get_peer_multiples",
        used_by=["Comparable Validator"],
        inputs={"tickers": "list[str]", "multiples": "list[str]"},
        outputs={"peer_multiples": "dict", "median_multiples": "dict"}
    ),
    "get_company_financials": ToolEntry(
        name="get_company_financials",
        description="Get historical financial data for DCF modeling",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_get_company_financials",
        used_by=["Market Data Collector", "Dot Connector"],
        inputs={"ticker": "str", "years": "int", "metrics": "list[str]"},
        outputs={"financials": "dict", "years_available": "int"}
    ),
    "compute_wacc": ToolEntry(
        name="compute_wacc",
        description="Calculate WACC with full formula breakdown",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_compute_wacc",
        used_by=["Dot Connector", "Financial Modeler"],
        inputs={
            "risk_free_rate": "float",
            "beta": "float",
            "equity_risk_premium": "float",
            "cost_of_debt": "float",
            "tax_rate": "float",
            "debt_ratio": "float"
        },
        outputs={"wacc": "float", "cost_of_equity": "float", "calculation_breakdown": "str"}
    ),
    "validate_dcf_parameters": ToolEntry(
        name="validate_dcf_parameters",
        description="Validate DCF model parameters for reasonableness",
        category=ToolCategory.MCP,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.mcp_tools",
        function_or_class="MCPToolExecutor._invoke_validate_dcf_parameters",
        used_by=["DCF Validator", "Quality Gate"],
        inputs={"growth_rate": "float", "terminal_growth": "float", "wacc": "float", "ebit_margin": "float"},
        outputs={"is_valid": "bool", "errors": "list", "warnings": "list"}
    ),

    # =========================================================================
    # FINANCIAL CALCULATORS
    # =========================================================================
    "calculate_wacc": ToolEntry(
        name="calculate_wacc",
        description="Calculate WACC using CAPM formula",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="FinancialCalculator.calculate_wacc",
        used_by=["Financial Modeler", "DCF Validator"],
        inputs={
            "risk_free_rate": "float",
            "beta": "float",
            "equity_risk_premium": "float",
            "country_risk_premium": "float",
            "cost_of_debt": "float",
            "tax_rate": "float",
            "debt_ratio": "float"
        },
        outputs={"wacc": "float", "cost_of_equity": "float", "calculation_str": "str"}
    ),
    "calculate_fcf": ToolEntry(
        name="calculate_fcf",
        description="Calculate Free Cash Flow",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="FinancialCalculator.calculate_fcf",
        used_by=["Financial Modeler"],
        inputs={
            "revenue": "float",
            "ebit_margin": "float",
            "tax_rate": "float",
            "depreciation": "float",
            "capex": "float",
            "working_capital_change": "float"
        },
        outputs={"fcf": "float", "calculation_str": "str"}
    ),
    "calculate_terminal_value": ToolEntry(
        name="calculate_terminal_value",
        description="Calculate Terminal Value using Gordon Growth",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="FinancialCalculator.calculate_terminal_value",
        used_by=["Financial Modeler"],
        inputs={"terminal_fcf": "float", "wacc": "float", "terminal_growth": "float"},
        outputs={"terminal_value": "float", "calculation_str": "str"}
    ),
    "dcf_calculate": ToolEntry(
        name="dcf_calculate",
        description="Full 10-year DCF valuation",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="DCFCalculator.calculate",
        used_by=["Financial Modeler"],
        inputs={"inputs": "DCFInputs"},
        outputs={"DCFOutput": "enterprise_value, equity_value, fair_value_per_share, yearly_projections"}
    ),
    "dcf_scenarios": ToolEntry(
        name="dcf_scenarios",
        description="Multi-scenario DCF calculation",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="DCFCalculator.calculate_scenarios",
        used_by=["Financial Modeler", "Sensitivity Auditor"],
        inputs={"base_inputs": "DCFInputs", "scenario_adjustments": "dict"},
        outputs={"scenarios": "dict[str, DCFOutput]"}
    ),
    "probability_weighted_value": ToolEntry(
        name="probability_weighted_value",
        description="Calculate probability-weighted fair value across scenarios",
        category=ToolCategory.CALCULATOR,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.financial_calculator",
        function_or_class="DCFCalculator.calculate_probability_weighted_value",
        used_by=["Financial Modeler", "Synthesizer"],
        inputs={"scenario_results": "dict", "probabilities": "dict"},
        outputs={"pwv": "float", "calculation_str": "str"}
    ),

    # =========================================================================
    # MARKET DATA APIs
    # =========================================================================
    "get_quote": ToolEntry(
        name="get_quote",
        description="Get real-time stock quote from Yahoo Finance",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.market_data_api",
        function_or_class="MarketDataAPI.get_quote",
        used_by=["Market Data Collector"],
        inputs={"ticker": "str"},
        outputs={"StockQuote": "price, currency, change, volume, market_cap, 52wk"}
    ),
    "get_financials": ToolEntry(
        name="get_financials",
        description="Get historical financial statements",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.market_data_api",
        function_or_class="MarketDataAPI.get_financials",
        used_by=["Market Data Collector"],
        inputs={"ticker": "str", "years": "int"},
        outputs={"List[FinancialData]": "revenue, margins, debt, cash flow"}
    ),
    "get_analyst_estimates": ToolEntry(
        name="get_analyst_estimates",
        description="Get analyst consensus estimates",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.market_data_api",
        function_or_class="MarketDataAPI.get_analyst_estimates",
        used_by=["Market Data Collector", "DCF Validator"],
        inputs={"ticker": "str"},
        outputs={"AnalystEstimates": "target prices, ratings, EPS/revenue estimates"}
    ),
    "verify_price": ToolEntry(
        name="verify_price",
        description="Verify claimed price against real market data",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.market_data_api",
        function_or_class="MarketDataAPI.verify_price",
        used_by=["Data Gate"],
        inputs={"ticker": "str", "claimed_price": "float", "tolerance": "float"},
        outputs={"verified": "bool", "actual_price": "float", "deviation": "float"}
    ),
    "verify_multiple_sources": ToolEntry(
        name="verify_multiple_sources",
        description="Cross-validate data across multiple sources",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.market_data_api",
        function_or_class="MultiSourceVerifier.verify_with_multiple_sources",
        used_by=["Data Gate"],
        inputs={"ticker": "str"},
        outputs={"consensus_price": "float", "price_variance": "float", "is_reliable": "bool"}
    ),

    # =========================================================================
    # VALIDATION TOOLS
    # =========================================================================
    "validate_dcf_math": ToolEntry(
        name="validate_dcf_math",
        description="Verify DCF mathematical calculations",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.validate_dcf_math",
        used_by=["DCF Validator", "Quality Gate"],
        inputs={"fcf_projections": "list", "wacc": "float", "terminal_growth": "float", "terminal_value": "float", "enterprise_value": "float"},
        outputs={"List[ValidationResult]": "check_name, passed, severity, message"}
    ),
    "validate_wacc_calculation": ToolEntry(
        name="validate_wacc_calculation",
        description="Validate WACC formula and components",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.validate_wacc_calculation",
        used_by=["DCF Validator"],
        inputs={"stated_wacc": "float", "risk_free_rate": "float", "beta": "float"},
        outputs={"List[ValidationResult]": "component checks, formula check"}
    ),
    "validate_scenario_consistency": ToolEntry(
        name="validate_scenario_consistency",
        description="Check scenario analysis for logical consistency",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.validate_scenario_consistency",
        used_by=["Quality Gate"],
        inputs={"scenarios": "dict", "current_price": "float"},
        outputs={"List[ValidationResult]": "probability sum, ordering, return reasonableness"}
    ),
    "validate_price_consistency": ToolEntry(
        name="validate_price_consistency",
        description="Compare stated price vs verified market price",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.validate_price_consistency",
        used_by=["Data Gate"],
        inputs={"stated_price": "float", "verified_price": "float", "tolerance": "float"},
        outputs={"ValidationResult": "passed, deviation, fix_suggestion"}
    ),
    "validate_fcf_calculation": ToolEntry(
        name="validate_fcf_calculation",
        description="Verify Free Cash Flow formula",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.validate_fcf_calculation",
        used_by=["DCF Validator"],
        inputs={"revenue": "float", "ebit_margin": "float", "tax_rate": "float"},
        outputs={"ValidationResult": "passed, expected vs actual"}
    ),
    "run_full_validation": ToolEntry(
        name="run_full_validation",
        description="Comprehensive DCF validation (all checks)",
        category=ToolCategory.VALIDATION,
        status=ToolStatus.AVAILABLE,
        module="agents.tools.validation_tools",
        function_or_class="ValidationTools.run_full_validation",
        used_by=["Quality Gate"],
        inputs={"dcf_output": "dict", "verified_price": "float"},
        outputs={"overall_passed": "bool", "critical_failures": "int", "warnings": "int", "results": "list"}
    ),

    # =========================================================================
    # TO BUILD
    # =========================================================================
    "sec_edgar_fetcher": ToolEntry(
        name="sec_edgar_fetcher",
        description="Fetch SEC 10-K, 10-Q filings",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_BUILD,
        module="agents.tools.sec_fetcher",
        function_or_class="SECFetcher.get_filing",
        used_by=["Market Data Collector", "Company Deep Dive"],
        notes="Priority: HIGH - needed for US stocks"
    ),
    "hkex_fetcher": ToolEntry(
        name="hkex_fetcher",
        description="Fetch HKEX announcements and filings",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_BUILD,
        module="agents.tools.hkex_fetcher",
        function_or_class="HKEXFetcher.get_announcements",
        used_by=["Market Data Collector", "Company Deep Dive"],
        notes="Priority: HIGH - needed for HK stocks"
    ),
    "company_filings_reader": ToolEntry(
        name="company_filings_reader",
        description="PDF parsing for annual reports",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_BUILD,
        module="agents.tools.pdf_reader",
        function_or_class="PDFReader.extract_financials",
        used_by=["Company Deep Dive"],
        notes="Priority: MEDIUM"
    ),

    # =========================================================================
    # TO OUTSOURCE
    # =========================================================================
    "financial_api": ToolEntry(
        name="financial_api",
        description="Premium financial data API",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_OUTSOURCE,
        module="external",
        function_or_class="AlphaVantage/Polygon/FMP",
        used_by=["Market Data Collector"],
        notes="Consider: Alpha Vantage, Polygon.io, Financial Modeling Prep"
    ),
    "industry_report_fetcher": ToolEntry(
        name="industry_report_fetcher",
        description="Industry research reports",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_OUTSOURCE,
        module="external",
        function_or_class="Statista/IBISWorld API",
        used_by=["Industry Deep Dive"],
        notes="Consider: Statista API, IBISWorld"
    ),
    "insider_transaction_tracker": ToolEntry(
        name="insider_transaction_tracker",
        description="Insider trading data",
        category=ToolCategory.MARKET_DATA,
        status=ToolStatus.TO_OUTSOURCE,
        module="external",
        function_or_class="OpenInsider API",
        used_by=["Company Deep Dive"],
        notes="Consider: OpenInsider API"
    ),
}


# =============================================================================
# REGISTRY FUNCTIONS
# =============================================================================

def get_all_tools() -> Dict[str, ToolEntry]:
    """Get all tools in the registry"""
    return TOOL_REGISTRY


def get_tool_by_name(name: str) -> Optional[ToolEntry]:
    """Get a specific tool by name"""
    return TOOL_REGISTRY.get(name)


def get_tools_by_category(category: ToolCategory) -> List[ToolEntry]:
    """Get all tools in a category"""
    return [t for t in TOOL_REGISTRY.values() if t.category == category]


def get_tools_by_status(status: ToolStatus) -> List[ToolEntry]:
    """Get all tools with a specific status"""
    return [t for t in TOOL_REGISTRY.values() if t.status == status]


def get_tools_for_agent(agent_name: str) -> List[ToolEntry]:
    """Get all tools used by a specific agent"""
    return [t for t in TOOL_REGISTRY.values() if agent_name in t.used_by]


def list_available_tool_names() -> List[str]:
    """Get names of all available tools"""
    return [t.name for t in TOOL_REGISTRY.values() if t.status == ToolStatus.AVAILABLE]


def count_tools_by_status() -> Dict[str, int]:
    """Get count of tools by status"""
    counts = {}
    for status in ToolStatus:
        counts[status.value] = len(get_tools_by_status(status))
    return counts


def count_tools_by_category() -> Dict[str, int]:
    """Get count of tools by category"""
    counts = {}
    for category in ToolCategory:
        counts[category.value] = len(get_tools_by_category(category))
    return counts


def display_tool_summary():
    """Print a summary of all tools"""
    print("=" * 70)
    print("TOOL REGISTRY SUMMARY")
    print("=" * 70)

    print("\nBy Status:")
    for status, count in count_tools_by_status().items():
        print(f"  {status}: {count}")

    print("\nBy Category:")
    for category, count in count_tools_by_category().items():
        print(f"  {category}: {count}")

    print(f"\nTotal Tools: {len(TOOL_REGISTRY)}")

    print("\n" + "=" * 70)
    print("AVAILABLE TOOLS")
    print("=" * 70)
    for tool in get_tools_by_status(ToolStatus.AVAILABLE):
        print(f"\n  {tool.name}")
        print(f"    Category: {tool.category.value}")
        print(f"    Module: {tool.module}")
        print(f"    Used by: {', '.join(tool.used_by)}")

    print("\n" + "=" * 70)
    print("TOOLS TO BUILD")
    print("=" * 70)
    for tool in get_tools_by_status(ToolStatus.TO_BUILD):
        print(f"\n  {tool.name}: {tool.description}")
        print(f"    Notes: {tool.notes}")

    print("\n" + "=" * 70)
    print("TOOLS TO OUTSOURCE")
    print("=" * 70)
    for tool in get_tools_by_status(ToolStatus.TO_OUTSOURCE):
        print(f"\n  {tool.name}: {tool.description}")
        print(f"    Notes: {tool.notes}")


if __name__ == "__main__":
    display_tool_summary()
