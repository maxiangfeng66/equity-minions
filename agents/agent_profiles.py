"""
Agent Profiles - Comprehensive definition of all agents in the equity research system.

Each agent has:
- Exact name and ID
- AI model and provider
- Exact tasks (what it does)
- Required skills (capabilities needed)
- Tools needed (to build or outsource)
- Input/output specifications
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ToolStatus(Enum):
    """Status of tool availability"""
    AVAILABLE = "available"          # Tool exists and is ready
    TO_BUILD = "to_build"            # Need to build this tool
    TO_OUTSOURCE = "to_outsource"    # Can use external API/service
    NOT_NEEDED = "not_needed"        # Agent doesn't need tools


@dataclass
class Tool:
    """Definition of a tool an agent can use"""
    name: str
    description: str
    status: ToolStatus
    implementation: Optional[str] = None  # File path or API name if available
    priority: str = "medium"  # high, medium, low
    notes: str = ""


@dataclass
class AgentProfile:
    """Complete profile of an agent"""
    # Identity
    id: str                          # Exact node ID in workflow
    name: str                        # Human-readable name
    tier: str                        # Workflow tier

    # AI Configuration
    ai_model: str                    # Model name
    ai_provider: str                 # Provider (openai, google, xai, etc.)
    is_ai: bool = True               # False for Python-based nodes

    # Tasks (exact list of what this agent does)
    tasks: List[str] = field(default_factory=list)

    # Skills (capabilities required)
    skills: List[str] = field(default_factory=list)

    # Tools
    tools: List[Tool] = field(default_factory=list)

    # Workflow connections
    inputs_from: List[str] = field(default_factory=list)
    outputs_to: List[str] = field(default_factory=list)

    # Routing keywords this agent produces
    output_keywords: List[str] = field(default_factory=list)

    # Context window setting
    context_window: int = 10

    # Notes
    notes: str = ""


# ============================================================
# AGENT PROFILES REGISTRY
# ============================================================

AGENT_PROFILES: Dict[str, AgentProfile] = {}


def register_agent(profile: AgentProfile):
    """Register an agent profile"""
    AGENT_PROFILES[profile.id] = profile
    return profile


# ============================================================
# TIER 0: ORCHESTRATION
# ============================================================

register_agent(AgentProfile(
    id="Research Supervisor",
    name="Research Supervisor",
    tier="Orchestration",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Create research plan for target equity",
        "Identify key questions and data sources",
        "Establish expected price range for verification",
        "Dispatch workers to collect data",
        "Final sign-off on completed reports",
        "Verify company identity matches request",
        "Ensure verified price used consistently",
        "Confirm all report sections complete",
        "Give final approval or request fixes"
    ],

    skills=[
        "Research planning and prioritization",
        "Quality assessment",
        "Gap identification",
        "Final approval decision-making",
        "Report quality evaluation"
    ],

    tools=[
        Tool(
            name="research_template_generator",
            description="Generate structured research templates based on equity type",
            status=ToolStatus.TO_BUILD,
            priority="low",
            notes="Could improve consistency of research plans"
        ),
        Tool(
            name="checklist_validator",
            description="Validate report against completion checklist",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Automate final sign-off checks"
        )
    ],

    inputs_from=["START", "Synthesizer"],
    outputs_to=["Market Data Collector", "Industry Deep Dive", "Company Deep Dive"],
    output_keywords=["RESEARCH: INITIATED", "FINAL: APPROVED", "FINAL: NEEDS_REVISION"],
    context_window=10
))


# ============================================================
# TIER 1: RESEARCH WORKERS
# ============================================================

register_agent(AgentProfile(
    id="Market Data Collector",
    name="Market Data Collector",
    tier="Research Workers",
    ai_model="gemini-2.0-flash",
    ai_provider="google",

    tasks=[
        "Collect current stock price (verify from START message)",
        "Gather 52-week price range",
        "Collect market capitalization",
        "Gather trading volume data",
        "Collect beta coefficient",
        "Gather revenue and growth data (3-5 years)",
        "Collect margin data (gross, operating, net)",
        "Gather EPS and FCF data",
        "Collect debt and cash position",
        "Gather valuation multiples (P/E, P/S, P/B, EV/EBITDA)",
        "Collect analyst consensus data"
    ],

    skills=[
        "Financial data extraction",
        "Source triangulation",
        "Data verification",
        "Structured data output"
    ],

    tools=[
        Tool(
            name="yfinance_fetcher",
            description="Fetch real-time stock data from Yahoo Finance",
            status=ToolStatus.AVAILABLE,
            implementation="utils/price_fetcher.py",
            priority="high"
        ),
        Tool(
            name="financial_api",
            description="Access to financial data API (Alpha Vantage, Polygon, etc.)",
            status=ToolStatus.TO_OUTSOURCE,
            priority="high",
            notes="Consider: Alpha Vantage (free tier), Polygon.io, Financial Modeling Prep"
        ),
        Tool(
            name="sec_edgar_fetcher",
            description="Fetch SEC filings for US stocks",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="For 10-K, 10-Q filings"
        ),
        Tool(
            name="hkex_fetcher",
            description="Fetch HKEX filings for HK stocks",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="For annual reports, announcements"
        )
    ],

    inputs_from=["Research Supervisor"],
    outputs_to=["Data Gate"],
    output_keywords=["DATA: COLLECTED"],
    context_window=5
))

register_agent(AgentProfile(
    id="Industry Deep Dive",
    name="Industry Deep Dive",
    tier="Research Workers",
    ai_model="gemini-2.0-flash",
    ai_provider="google",

    tasks=[
        "Analyze Total Addressable Market (TAM)",
        "Analyze Serviceable Addressable Market (SAM)",
        "Analyze Serviceable Obtainable Market (SOM)",
        "Calculate market growth rates",
        "Map competitive landscape",
        "Identify key competitors and market shares",
        "Analyze industry trends (tailwinds/headwinds)",
        "Assess regulatory environment",
        "Identify growth drivers",
        "Analyze industry profit pools"
    ],

    skills=[
        "Industry analysis",
        "Market sizing",
        "Competitive dynamics assessment",
        "Trend identification",
        "Regulatory analysis"
    ],

    tools=[
        Tool(
            name="web_search",
            description="Search web for industry reports and news",
            status=ToolStatus.AVAILABLE,
            implementation="Built into Gemini",
            priority="high"
        ),
        Tool(
            name="industry_report_fetcher",
            description="Access industry reports (IBISWorld, Statista, etc.)",
            status=ToolStatus.TO_OUTSOURCE,
            priority="medium",
            notes="Consider: Statista API, IBISWorld (expensive)"
        ),
        Tool(
            name="news_aggregator",
            description="Aggregate recent news about industry",
            status=ToolStatus.TO_BUILD,
            priority="low",
            notes="Could use NewsAPI or Google News RSS"
        )
    ],

    inputs_from=["Research Supervisor"],
    outputs_to=["Data Gate"],
    output_keywords=["INDUSTRY: ANALYZED"],
    context_window=5
))

register_agent(AgentProfile(
    id="Company Deep Dive",
    name="Company Deep Dive",
    tier="Research Workers",
    ai_model="gemini-2.0-flash",
    ai_provider="google",

    tasks=[
        "Analyze business model",
        "Identify revenue streams",
        "Assess competitive position",
        "Evaluate economic moat",
        "Analyze management quality",
        "Review management track record",
        "Assess capital allocation history",
        "Identify company-specific risks",
        "Analyze recent developments",
        "Review insider transactions"
    ],

    skills=[
        "Business model analysis",
        "Competitive advantage assessment",
        "Management evaluation",
        "Risk identification",
        "Corporate governance analysis"
    ],

    tools=[
        Tool(
            name="web_search",
            description="Search web for company information",
            status=ToolStatus.AVAILABLE,
            implementation="Built into Gemini",
            priority="high"
        ),
        Tool(
            name="company_filings_reader",
            description="Read and parse company filings (10-K, annual reports)",
            status=ToolStatus.TO_BUILD,
            priority="high",
            notes="PDF parsing for annual reports"
        ),
        Tool(
            name="insider_transaction_tracker",
            description="Track insider buying/selling",
            status=ToolStatus.TO_OUTSOURCE,
            priority="low",
            notes="OpenInsider API or SEC Form 4 parsing"
        ),
        Tool(
            name="glassdoor_scraper",
            description="Get employee sentiment data",
            status=ToolStatus.TO_BUILD,
            priority="low",
            notes="For management quality assessment"
        )
    ],

    inputs_from=["Research Supervisor"],
    outputs_to=["Data Gate"],
    output_keywords=["COMPANY: ANALYZED"],
    context_window=5
))


# ============================================================
# TIER 2: QUALITY CONTROL - DATA
# ============================================================

register_agent(AgentProfile(
    id="Data Gate",
    name="Data Gate",
    tier="Quality Control",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Extract verified price from START message",
        "Validate company identity matches request",
        "Detect hallucinated company names (Apple, Microsoft, etc.)",
        "Check data consistency across sources",
        "Verify market cap = price x shares",
        "Block contaminated data from proceeding",
        "Pass clean data to debate stage"
    ],

    skills=[
        "Data validation",
        "Hallucination detection",
        "Consistency checking",
        "Pattern matching for errors"
    ],

    tools=[
        Tool(
            name="ticker_validator",
            description="Validate ticker symbol and company name match",
            status=ToolStatus.TO_BUILD,
            priority="high",
            notes="Cross-reference with yfinance ticker info"
        ),
        Tool(
            name="math_consistency_checker",
            description="Verify mathematical relationships (mcap = price x shares)",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Simple Python calculations"
        ),
        Tool(
            name="hallucination_detector",
            description="Detect when AI outputs wrong company data",
            status=ToolStatus.AVAILABLE,
            implementation="workflow/graph_executor.py:_validate_ticker_output",
            priority="high"
        )
    ],

    inputs_from=["Market Data Collector", "Industry Deep Dive", "Company Deep Dive"],
    outputs_to=["Debate Moderator", "Research Supervisor"],
    output_keywords=["DATA: VERIFIED", "DATA: FAILED"],
    context_window=15
))


# ============================================================
# TIER 3: DEBATE
# ============================================================

register_agent(AgentProfile(
    id="Debate Moderator",
    name="Debate Moderator",
    tier="Debate",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Set up structured bull/bear debate",
        "Provide research context to advocates",
        "Ensure verified price is communicated",
        "Frame key questions for debate",
        "Set debate ground rules"
    ],

    skills=[
        "Debate facilitation",
        "Context summarization",
        "Neutral framing"
    ],

    tools=[],  # No tools needed - reasoning only

    inputs_from=["Data Gate"],
    outputs_to=["Bull Advocate", "Bear Advocate"],
    output_keywords=["DEBATE: INITIATED"],
    context_window=10
))

register_agent(AgentProfile(
    id="Bull Advocate",
    name="Bull Advocate",
    tier="Debate",
    ai_model="grok-3-fast",
    ai_provider="xai",

    tasks=[
        "Present strongest investment case",
        "Identify growth catalysts with evidence",
        "Quantify upside potential",
        "Highlight competitive advantages",
        "Present positive industry trends",
        "Argue for management execution capability"
    ],

    skills=[
        "Investment thesis construction",
        "Upside identification",
        "Evidence-based argumentation",
        "Persuasive communication"
    ],

    tools=[],  # No tools needed - reasoning only

    inputs_from=["Debate Moderator"],
    outputs_to=["Debate Synthesizer"],
    output_keywords=["BULL: COMPLETE"],
    context_window=10
))

register_agent(AgentProfile(
    id="Bear Advocate",
    name="Bear Advocate",
    tier="Debate",
    ai_model="grok-3-fast",
    ai_provider="xai",

    tasks=[
        "Present strongest counter-case",
        "Identify risks and threats with evidence",
        "Quantify downside risk",
        "Highlight competitive threats",
        "Present negative industry trends",
        "Argue against management execution"
    ],

    skills=[
        "Risk identification",
        "Downside analysis",
        "Critical thinking",
        "Devil's advocacy"
    ],

    tools=[],  # No tools needed - reasoning only

    inputs_from=["Debate Moderator"],
    outputs_to=["Debate Synthesizer"],
    output_keywords=["BEAR: COMPLETE"],
    context_window=10
))

register_agent(AgentProfile(
    id="Debate Synthesizer",
    name="Debate Synthesizer",
    tier="Debate",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Synthesize bull and bear arguments",
        "Rank key points by conviction",
        "Identify key uncertainties",
        "Determine which arguments are strongest",
        "Provide preliminary investment lean",
        "Identify assumptions needing DCF validation"
    ],

    skills=[
        "Argument synthesis",
        "Uncertainty identification",
        "Balanced assessment",
        "Priority ranking"
    ],

    tools=[],  # No tools needed - reasoning only

    inputs_from=["Bull Advocate", "Bear Advocate"],
    outputs_to=["Dot Connector"],
    output_keywords=["DEBATE: SYNTHESIZED"],
    context_window=15
))


# ============================================================
# TIER 4: VALUATION
# ============================================================

register_agent(AgentProfile(
    id="Dot Connector",
    name="Dot Connector",
    tier="Valuation",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Bridge qualitative research to quantitative DCF",
        "Extract revenue growth parameters with reasoning",
        "Extract margin parameters with reasoning",
        "Calculate WACC components",
        "Set scenario probabilities",
        "Avoid repeating failed parameters",
        "Use binary search for convergence"
    ],

    skills=[
        "Parameter extraction",
        "Evidence-based quantification",
        "Financial modeling knowledge",
        "Convergence logic"
    ],

    tools=[
        Tool(
            name="parameter_history",
            description="Track previous parameter attempts to avoid oscillation",
            status=ToolStatus.AVAILABLE,
            implementation="workflow/graph_executor.py:_track_parameter_attempt",
            priority="high"
        ),
        Tool(
            name="wacc_calculator",
            description="Calculate WACC from components",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Simple formula: WACC = E/V x Re + D/V x Rd x (1-T)"
        ),
        Tool(
            name="parameter_validator",
            description="Validate parameters are within reasonable ranges",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Check growth < 50%, WACC 5-20%, etc."
        )
    ],

    inputs_from=["Debate Synthesizer", "Quality Gate"],
    outputs_to=["Financial Modeler"],
    output_keywords=["PARAMETERS: CONNECTED"],
    context_window=20
))

register_agent(AgentProfile(
    id="Financial Modeler",
    name="Financial Modeler",
    tier="Valuation",
    ai_model="dcf_engine",
    ai_provider="python",
    is_ai=False,

    tasks=[
        "Calculate DCF across 5 scenarios (super_bear to super_bull)",
        "Compute probability-weighted value (PWV)",
        "Generate yearly projections",
        "Calculate terminal value",
        "Perform reverse DCF analysis",
        "Generate valuation summary"
    ],

    skills=[
        "DCF calculation",
        "Scenario modeling",
        "Mathematical precision",
        "Financial formula implementation"
    ],

    tools=[
        Tool(
            name="dcf_engine",
            description="Python DCF calculation engine",
            status=ToolStatus.AVAILABLE,
            implementation="agents/tools/dcf_engine.py",
            priority="high"
        ),
        Tool(
            name="sensitivity_calculator",
            description="Calculate sensitivity tables",
            status=ToolStatus.AVAILABLE,
            implementation="agents/tools/dcf_engine.py",
            priority="high"
        )
    ],

    inputs_from=["Dot Connector"],
    outputs_to=["DCF Validator", "Comparable Validator", "Sensitivity Auditor"],
    output_keywords=[],  # Python node, no keywords
    context_window=10
))

register_agent(AgentProfile(
    id="DCF Validator",
    name="DCF Validator",
    tier="Valuation QC",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Validate reasoning behind DCF assumptions",
        "Check internal consistency of assumptions",
        "Verify assumptions are supported by research",
        "Stress-test assumptions (what if 50% lower?)",
        "Identify what breaks the thesis",
        "Defend sound reasoning (not market alignment)",
        "Flag ONLY logical errors, not market divergence"
    ],

    skills=[
        "Reasoning validation",
        "Assumption stress testing",
        "Logical consistency checking",
        "Independent thinking"
    ],

    tools=[
        Tool(
            name="assumption_stress_tester",
            description="Automatically stress test key assumptions",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Calculate value impact of +/-20% on each parameter"
        )
    ],

    inputs_from=["Financial Modeler"],
    outputs_to=["Quality Gate", "Dot Connector"],
    output_keywords=["DCF: VALIDATED", "DCF: VALIDATED - DIVERGENT BUT JUSTIFIED", "DCF: NEEDS_REVISION"],
    context_window=20
))

register_agent(AgentProfile(
    id="Comparable Validator",
    name="Comparable Validator",
    tier="Valuation QC",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Identify 3-5 true peer companies",
        "Gather peer valuation multiples",
        "Calculate implied value from peers",
        "Cross-check DCF vs peer-implied value",
        "Explain any divergence"
    ],

    skills=[
        "Peer identification",
        "Relative valuation",
        "Comparative analysis",
        "Multiple analysis"
    ],

    tools=[
        Tool(
            name="peer_finder",
            description="Find comparable companies by sector, size, geography",
            status=ToolStatus.TO_BUILD,
            priority="high",
            notes="Use industry classification + size filters"
        ),
        Tool(
            name="peer_multiples_fetcher",
            description="Fetch valuation multiples for peer companies",
            status=ToolStatus.TO_BUILD,
            priority="high",
            notes="Use yfinance or financial API"
        ),
        Tool(
            name="comps_calculator",
            description="Calculate implied value from peer multiples",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="Apply median multiples to target financials"
        )
    ],

    inputs_from=["Financial Modeler"],
    outputs_to=["Quality Gate"],
    output_keywords=["COMPS: VALIDATED", "COMPS: DIVERGENT"],
    context_window=15
))

register_agent(AgentProfile(
    id="Sensitivity Auditor",
    name="Sensitivity Auditor",
    tier="Valuation QC",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Test sensitivity to revenue growth (+/-5%, +/-10%)",
        "Test sensitivity to EBIT margin (+/-2%, +/-5%)",
        "Test sensitivity to WACC (+/-1%, +/-2%)",
        "Test sensitivity to terminal growth",
        "Identify key value drivers",
        "Calculate break-even points",
        "Assess overall model robustness"
    ],

    skills=[
        "Sensitivity analysis",
        "Risk quantification",
        "Scenario testing",
        "Driver identification"
    ],

    tools=[
        Tool(
            name="sensitivity_table_generator",
            description="Generate sensitivity tables automatically",
            status=ToolStatus.AVAILABLE,
            implementation="agents/tools/dcf_engine.py",
            priority="high"
        ),
        Tool(
            name="tornado_chart_generator",
            description="Generate tornado charts for key drivers",
            status=ToolStatus.TO_BUILD,
            priority="low",
            notes="Visual representation of sensitivities"
        )
    ],

    inputs_from=["Financial Modeler"],
    outputs_to=["Quality Gate"],
    output_keywords=["SENSITIVITY: COMPLETE"],
    context_window=15
))


# ============================================================
# TIER 5: QUALITY CONTROL - FINAL
# ============================================================

register_agent(AgentProfile(
    id="Quality Gate",
    name="Quality Gate",
    tier="Quality Control",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Holistic quality review (bird's eye view)",
        "Check logical consistency across all sections",
        "Verify recommendation matches analysis",
        "Identify any glaring omissions",
        "Count previous iterations (loop prevention)",
        "Force exit to Synthesizer after 3 iterations",
        "Route to appropriate node based on issues"
    ],

    skills=[
        "Holistic assessment",
        "Logical consistency checking",
        "Decision routing",
        "Loop prevention"
    ],

    tools=[
        Tool(
            name="loop_counter",
            description="Track iteration count to prevent infinite loops",
            status=ToolStatus.AVAILABLE,
            implementation="workflow/graph_executor.py:_check_loop_limit",
            priority="high"
        ),
        Tool(
            name="consistency_checker",
            description="Check for contradictions across report sections",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="NLP-based contradiction detection"
        )
    ],

    inputs_from=["DCF Validator", "Comparable Validator", "Sensitivity Auditor"],
    outputs_to=["Synthesizer", "Data Gate", "DCF Validator", "Dot Connector"],
    output_keywords=["ROUTE: Synthesizer", "ROUTE: Data Gate", "ROUTE: DCF Validator", "ROUTE: Dot Connector"],
    context_window=25
))


# ============================================================
# TIER 6: SYNTHESIS
# ============================================================

register_agent(AgentProfile(
    id="Synthesizer",
    name="Synthesizer",
    tier="Synthesis",
    ai_model="gpt-4o",
    ai_provider="openai",

    tasks=[
        "Create final research report",
        "Write executive summary",
        "Compile investment thesis",
        "Summarize company overview",
        "Summarize industry analysis",
        "Present financial analysis",
        "Present valuation with scenarios",
        "List risks and monitoring points",
        "Formulate final recommendation"
    ],

    skills=[
        "Report writing",
        "Information synthesis",
        "Clear communication",
        "Professional formatting"
    ],

    tools=[
        Tool(
            name="report_template",
            description="Structured report template",
            status=ToolStatus.TO_BUILD,
            priority="medium",
            notes="HTML/Markdown template for consistent output"
        ),
        Tool(
            name="chart_generator",
            description="Generate charts for report (price, valuation scenarios)",
            status=ToolStatus.TO_BUILD,
            priority="low",
            notes="Use matplotlib or plotly"
        )
    ],

    inputs_from=["Quality Gate"],
    outputs_to=["Research Supervisor"],
    output_keywords=["REPORT: COMPLETE"],
    context_window=30
))


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_agent(agent_id: str) -> Optional[AgentProfile]:
    """Get agent profile by ID"""
    return AGENT_PROFILES.get(agent_id)


def get_agents_by_tier(tier: str) -> List[AgentProfile]:
    """Get all agents in a tier"""
    return [a for a in AGENT_PROFILES.values() if a.tier == tier]


def get_agents_needing_tools() -> Dict[str, List[Tool]]:
    """Get agents that need tools to be built"""
    result = {}
    for agent in AGENT_PROFILES.values():
        tools_to_build = [t for t in agent.tools if t.status == ToolStatus.TO_BUILD]
        if tools_to_build:
            result[agent.id] = tools_to_build
    return result


def get_tools_to_outsource() -> Dict[str, List[Tool]]:
    """Get tools that should be outsourced to external APIs"""
    result = {}
    for agent in AGENT_PROFILES.values():
        tools_to_outsource = [t for t in agent.tools if t.status == ToolStatus.TO_OUTSOURCE]
        if tools_to_outsource:
            result[agent.id] = tools_to_outsource
    return result


def display_all_profiles():
    """Display all agent profiles"""
    print("=" * 80)
    print("AGENT PROFILES SUMMARY")
    print("=" * 80)

    tiers = ["Orchestration", "Research Workers", "Quality Control", "Debate", "Valuation", "Valuation QC", "Synthesis"]

    for tier in tiers:
        agents = get_agents_by_tier(tier)
        if not agents:
            continue

        print(f"\n{'='*40}")
        print(f"TIER: {tier.upper()}")
        print(f"{'='*40}")

        for agent in agents:
            print(f"\n  {agent.id}")
            print(f"  {'-'*30}")
            print(f"  Model: {agent.ai_model} ({agent.ai_provider})")
            print(f"  Tasks: {len(agent.tasks)}")
            print(f"  Tools: {len(agent.tools)} ({len([t for t in agent.tools if t.status == ToolStatus.TO_BUILD])} to build)")


def display_tools_roadmap():
    """Display roadmap of tools to build"""
    print("\n" + "=" * 80)
    print("TOOLS ROADMAP")
    print("=" * 80)

    print("\n--- HIGH PRIORITY (To Build) ---")
    for agent_id, tools in get_agents_needing_tools().items():
        high_priority = [t for t in tools if t.priority == "high"]
        if high_priority:
            print(f"\n  {agent_id}:")
            for tool in high_priority:
                print(f"    - {tool.name}: {tool.description}")
                if tool.notes:
                    print(f"      Note: {tool.notes}")

    print("\n--- TO OUTSOURCE (External APIs) ---")
    for agent_id, tools in get_tools_to_outsource().items():
        print(f"\n  {agent_id}:")
        for tool in tools:
            print(f"    - {tool.name}: {tool.description}")
            if tool.notes:
                print(f"      Note: {tool.notes}")


if __name__ == "__main__":
    display_all_profiles()
    display_tools_roadmap()
