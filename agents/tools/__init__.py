"""
Tools module - Provides real computation and API tools for agents.

This module contains tools that give agents actual computational capabilities
rather than relying on AI to generate/hallucinate numbers.
"""

from .financial_calculator import FinancialCalculator, DCFCalculator
from .market_data_api import MarketDataAPI
from .validation_tools import ValidationTools
from .mcp_tools import (
    MCPToolExecutor,
    MCPToolResult,
    MCP_TOOLS,
    get_mcp_tool_definitions,
    invoke_mcp_tool,
    list_mcp_tools
)
from .tool_registry import (
    TOOL_REGISTRY,
    ToolCategory,
    ToolEntry,
    get_all_tools,
    get_tool_by_name,
    get_tools_by_category,
    get_tools_by_status,
    get_tools_for_agent,
    list_available_tool_names,
    count_tools_by_status,
    count_tools_by_category,
    display_tool_summary
)

__all__ = [
    # Core calculators
    'FinancialCalculator',
    'DCFCalculator',
    'MarketDataAPI',
    'ValidationTools',
    # MCP tools
    'MCPToolExecutor',
    'MCPToolResult',
    'MCP_TOOLS',
    'get_mcp_tool_definitions',
    'invoke_mcp_tool',
    'list_mcp_tools',
    # Tool registry
    'TOOL_REGISTRY',
    'ToolCategory',
    'ToolEntry',
    'get_all_tools',
    'get_tool_by_name',
    'get_tools_by_category',
    'get_tools_by_status',
    'get_tools_for_agent',
    'list_available_tool_names',
    'count_tools_by_status',
    'count_tools_by_category',
    'display_tool_summary'
]
