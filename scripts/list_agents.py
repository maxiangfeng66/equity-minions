"""
List all agents in Equity Research v5 with their duties, skills, and tools.
"""

agents = {
    # ==================== ORCHESTRATION ====================
    "Research Supervisor": {
        "tier": "Orchestration",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Initiate research and create research plan",
            "Identify key questions and data sources",
            "Final sign-off on completed reports",
            "Verify company identity and price consistency",
            "Ensure all sections are complete"
        ],
        "skills": [
            "Research planning and prioritization",
            "Quality assessment and gap identification",
            "Final approval decision-making"
        ],
        "tools": [],
        "inputs_from": ["START", "Synthesizer"],
        "outputs_to": ["Market Data Collector", "Industry Deep Dive", "Company Deep Dive"]
    },

    # ==================== RESEARCH WORKERS ====================
    "Market Data Collector": {
        "tier": "Research Workers",
        "ai_model": "gemini-2.0-flash (Google)",
        "duties": [
            "Collect quantitative market data",
            "Verify current stock price",
            "Gather financial metrics (3-5 years)",
            "Collect valuation multiples",
            "Gather analyst consensus data"
        ],
        "skills": [
            "Data gathering and verification",
            "Financial data extraction",
            "Source triangulation"
        ],
        "tools": ["Web search", "Financial databases"],
        "inputs_from": ["Research Supervisor"],
        "outputs_to": ["Data Gate"]
    },

    "Industry Deep Dive": {
        "tier": "Research Workers",
        "ai_model": "gemini-2.0-flash (Google)",
        "duties": [
            "Analyze industry TAM/SAM/SOM",
            "Map competitive landscape",
            "Identify industry trends and drivers",
            "Assess regulatory environment"
        ],
        "skills": [
            "Industry analysis",
            "Competitive dynamics assessment",
            "Trend identification"
        ],
        "tools": ["Web search", "Industry reports"],
        "inputs_from": ["Research Supervisor"],
        "outputs_to": ["Data Gate"]
    },

    "Company Deep Dive": {
        "tier": "Research Workers",
        "ai_model": "gemini-2.0-flash (Google)",
        "duties": [
            "Analyze business model",
            "Assess competitive position and moat",
            "Evaluate management quality",
            "Identify company-specific risks"
        ],
        "skills": [
            "Business model analysis",
            "Competitive advantage assessment",
            "Management evaluation"
        ],
        "tools": ["Web search", "Company filings"],
        "inputs_from": ["Research Supervisor"],
        "outputs_to": ["Data Gate"]
    },

    # ==================== DATA QUALITY ====================
    "Data Gate": {
        "tier": "Quality Control",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Verify price accuracy from START message",
            "Validate company identity (anti-hallucination)",
            "Check data consistency across sources",
            "Block bad data from proceeding"
        ],
        "skills": [
            "Data validation and verification",
            "Hallucination detection",
            "Consistency checking"
        ],
        "tools": [],
        "inputs_from": ["Market Data Collector", "Industry Deep Dive", "Company Deep Dive"],
        "outputs_to": ["Debate Moderator", "Research Supervisor (on fail)"]
    },

    # ==================== DEBATE ====================
    "Debate Moderator": {
        "tier": "Debate",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Set up structured bull/bear debate",
            "Provide context from research",
            "Ensure verified price is used"
        ],
        "skills": [
            "Debate facilitation",
            "Context summarization"
        ],
        "tools": [],
        "inputs_from": ["Data Gate"],
        "outputs_to": ["Bull Advocate", "Bear Advocate"]
    },

    "Bull Advocate": {
        "tier": "Debate",
        "ai_model": "grok-3-fast (xAI)",
        "duties": [
            "Present strongest investment case",
            "Identify growth catalysts",
            "Quantify upside potential"
        ],
        "skills": [
            "Investment thesis construction",
            "Upside identification",
            "Evidence-based argumentation"
        ],
        "tools": [],
        "inputs_from": ["Debate Moderator"],
        "outputs_to": ["Debate Synthesizer"]
    },

    "Bear Advocate": {
        "tier": "Debate",
        "ai_model": "grok-3-fast (xAI)",
        "duties": [
            "Present strongest counter-case",
            "Identify risks and threats",
            "Quantify downside risk"
        ],
        "skills": [
            "Risk identification",
            "Downside analysis",
            "Critical thinking"
        ],
        "tools": [],
        "inputs_from": ["Debate Moderator"],
        "outputs_to": ["Debate Synthesizer"]
    },

    "Debate Synthesizer": {
        "tier": "Debate",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Synthesize bull and bear arguments",
            "Rank key points by conviction",
            "Identify key uncertainties",
            "Provide preliminary lean"
        ],
        "skills": [
            "Argument synthesis",
            "Uncertainty identification",
            "Balanced assessment"
        ],
        "tools": [],
        "inputs_from": ["Bull Advocate", "Bear Advocate"],
        "outputs_to": ["Dot Connector"]
    },

    # ==================== VALUATION ====================
    "Dot Connector": {
        "tier": "Valuation",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Bridge qualitative to quantitative",
            "Extract DCF parameters from research",
            "Provide reasoning for each parameter",
            "Avoid parameter oscillation"
        ],
        "skills": [
            "Parameter extraction",
            "Evidence-based quantification",
            "Convergence logic"
        ],
        "tools": ["Parameter history tracking"],
        "inputs_from": ["Debate Synthesizer", "Quality Gate (feedback)"],
        "outputs_to": ["Financial Modeler"]
    },

    "Financial Modeler": {
        "tier": "Valuation",
        "ai_model": "Python DCF Engine (not AI)",
        "duties": [
            "Calculate DCF across 5 scenarios",
            "Compute probability-weighted value",
            "Generate sensitivity analysis",
            "Produce valuation summary"
        ],
        "skills": [
            "DCF calculation",
            "Scenario modeling",
            "Mathematical precision"
        ],
        "tools": ["Python DCF engine", "Math calculations"],
        "inputs_from": ["Dot Connector"],
        "outputs_to": ["DCF Validator", "Comparable Validator", "Sensitivity Auditor"]
    },

    "DCF Validator": {
        "tier": "Valuation QC",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Validate reasoning behind DCF",
            "Stress-test assumptions",
            "Defend sound reasoning (not market alignment)",
            "Flag logical errors only"
        ],
        "skills": [
            "Reasoning validation",
            "Assumption stress testing",
            "Logical consistency checking"
        ],
        "tools": [],
        "inputs_from": ["Financial Modeler"],
        "outputs_to": ["Quality Gate", "Dot Connector (on error)"]
    },

    "Comparable Validator": {
        "tier": "Valuation QC",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Identify peer companies",
            "Gather peer valuation multiples",
            "Cross-check DCF vs peers",
            "Explain divergence"
        ],
        "skills": [
            "Peer identification",
            "Relative valuation",
            "Comparative analysis"
        ],
        "tools": ["Web search for peer data"],
        "inputs_from": ["Financial Modeler"],
        "outputs_to": ["Quality Gate"]
    },

    "Sensitivity Auditor": {
        "tier": "Valuation QC",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Test sensitivity to key assumptions",
            "Identify key value drivers",
            "Calculate break-even points",
            "Assess model robustness"
        ],
        "skills": [
            "Sensitivity analysis",
            "Risk quantification",
            "Scenario testing"
        ],
        "tools": [],
        "inputs_from": ["Financial Modeler"],
        "outputs_to": ["Quality Gate"]
    },

    # ==================== FINAL QUALITY ====================
    "Quality Gate": {
        "tier": "Quality Control",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Holistic quality review (bird's eye)",
            "Logic consistency verification",
            "Routing decision",
            "Loop prevention (force exit after 3)"
        ],
        "skills": [
            "Holistic assessment",
            "Logical consistency checking",
            "Decision routing"
        ],
        "tools": ["Loop counter"],
        "inputs_from": ["DCF Validator", "Comparable Validator", "Sensitivity Auditor"],
        "outputs_to": ["Synthesizer", "Data Gate", "DCF Validator", "Dot Connector"]
    },

    # ==================== SYNTHESIS ====================
    "Synthesizer": {
        "tier": "Synthesis",
        "ai_model": "gpt-4o (OpenAI)",
        "duties": [
            "Create final research report",
            "Structure all sections",
            "Ensure consistency throughout",
            "Present clear recommendation"
        ],
        "skills": [
            "Report writing",
            "Information synthesis",
            "Clear communication"
        ],
        "tools": [],
        "inputs_from": ["Quality Gate"],
        "outputs_to": ["Research Supervisor (sign-off)"]
    },
}


def print_agent_summary():
    print("=" * 100)
    print("EQUITY RESEARCH V5 - AGENT CAPABILITIES SUMMARY")
    print("=" * 100)

    # Group by tier
    tiers = {}
    for name, info in agents.items():
        tier = info["tier"]
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append((name, info))

    tier_order = ["Orchestration", "Research Workers", "Quality Control", "Debate", "Valuation", "Valuation QC", "Synthesis"]

    for tier in tier_order:
        if tier not in tiers:
            continue
        print(f"\n{'='*50}")
        print(f"TIER: {tier.upper()}")
        print(f"{'='*50}")

        for name, info in tiers[tier]:
            print(f"\n  {name}")
            print(f"  {'-'*40}")
            print(f"  AI Model: {info['ai_model']}")
            print(f"  ")
            print(f"  DUTIES:")
            for duty in info['duties']:
                print(f"    - {duty}")
            print(f"  ")
            print(f"  SKILLS:")
            for skill in info['skills']:
                print(f"    - {skill}")
            print(f"  ")
            if info['tools']:
                print(f"  TOOLS:")
                for tool in info['tools']:
                    print(f"    - {tool}")
            else:
                print(f"  TOOLS: None (reasoning only)")
            print(f"  ")
            print(f"  INPUTS FROM: {', '.join(info['inputs_from'])}")
            print(f"  OUTPUTS TO: {', '.join(info['outputs_to'])}")

    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Total Agents: {len(agents)}")

    # Count by provider
    providers = {}
    for info in agents.values():
        model = info['ai_model']
        if 'OpenAI' in model:
            providers['OpenAI'] = providers.get('OpenAI', 0) + 1
        elif 'Google' in model:
            providers['Google'] = providers.get('Google', 0) + 1
        elif 'xAI' in model:
            providers['xAI'] = providers.get('xAI', 0) + 1
        elif 'Python' in model:
            providers['Python'] = providers.get('Python', 0) + 1

    print(f"\nBy Provider:")
    for provider, count in providers.items():
        print(f"  {provider}: {count}")


if __name__ == "__main__":
    print_agent_summary()
