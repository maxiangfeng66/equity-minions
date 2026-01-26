"""
Enhanced Worker Agents - SpawnableAgent versions of core research agents

These wrap the original agent functionality with:
- Lifecycle management
- Dynamic spawning capability
- Health monitoring
- Task tracking
"""

from typing import Dict, Any, Optional
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class EnhancedAnalystAgent(SpawnableAgent):
    """
    Primary analyst agent with spawning capabilities (Tier 2).

    Can spawn Specialist agents for domain-specific deep dives.

    Usage:
        analyst = await supervisor.spawn_child(
            EnhancedAnalystAgent, "analyst_6682HK",
            config={'ticker': '6682 HK'}
        )
        industry = await analyst.analyze(context, analysis_type="industry")
    """

    def __init__(
        self,
        ai_provider,
        parent_id: str = None,
        tier: int = 2,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role="analyst",
            parent_id=parent_id,
            tier=tier,
            config=config
        )
        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        return """You are a senior equity research analyst with 20+ years of experience.

Your role is to provide thorough, unbiased analysis of companies and industries.

Key responsibilities:
1. Industry Analysis: Assess market size, growth drivers, competitive dynamics, and risks
2. Company Analysis: Evaluate competitive advantages, moat, management quality, and execution
3. Financial Analysis: Analyze historical financials and project future cash flows
4. Valuation: Build DCF models with clear assumptions and scenario analysis

Guidelines:
- Be objective and balanced - present both bull and bear cases
- Support all claims with data and logic
- Clearly state assumptions and their sensitivity
- Acknowledge uncertainties and risks
- Use conservative estimates as base case
- Provide specific numbers, not vague ranges when possible

Output format: Structured analysis with clear sections and data tables."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """
        Perform analysis, spawning specialists as needed.

        Args:
            context: Research context
            analysis_type: Type of analysis (industry, company, governance, dcf, full)
            specialist_insight: Pre-fetched specialist insight (optional)

        Returns:
            Analysis text
        """
        analysis_type = kwargs.get('analysis_type', 'full')
        self.heartbeat()
        self.set_task(f"{self.ticker}: {analysis_type} analysis")

        # Check if specialist is needed for industry analysis
        if analysis_type == 'industry' and context.industry:
            from .specialist import SpecialistAgent
            specialist_type = SpecialistAgent.detect_specialization(
                context.industry, context.sector
            )
            if specialist_type != 'general':
                # Spawn specialist for enhanced analysis
                specialist = await self.spawn_child(
                    SpecialistAgent,
                    f"specialist_{specialist_type}",
                    config={'specialization': specialist_type, 'ticker': self.ticker}
                )
                try:
                    specialist_insight = await specialist.analyze(context)
                    kwargs['specialist_insight'] = specialist_insight
                finally:
                    await self.terminate_child(specialist.agent_id)

        # Dispatch to specific analysis method
        if analysis_type == "industry":
            result = await self._analyze_industry(context, **kwargs)
        elif analysis_type == "company":
            result = await self._analyze_company(context, **kwargs)
        elif analysis_type == "governance":
            result = await self._analyze_governance(context, **kwargs)
        elif analysis_type == "dcf":
            result = await self._analyze_dcf(context, **kwargs)
        else:
            result = await self._full_analysis(context, **kwargs)

        self.complete_task()
        return result

    async def _analyze_industry(self, context: ResearchContext, **kwargs) -> str:
        """Perform industry analysis"""
        specialist_insight = kwargs.get('specialist_insight', '')

        prompt = f"""Perform a comprehensive industry analysis for:
Company: {context.company_name} ({context.ticker})
Sector: {context.sector}
Industry: {context.industry}

{f"SPECIALIST INSIGHT:{chr(10)}{specialist_insight}{chr(10)}" if specialist_insight else ""}

Analyze:
1. Market Size and Growth
   - Total addressable market (TAM)
   - Growth rate and drivers
   - Key trends

2. Competitive Landscape
   - Major players and market share
   - Barriers to entry
   - Competitive intensity

3. Industry Dynamics
   - Porter's Five Forces assessment
   - Regulatory environment
   - Technology disruption risk

4. Key Success Factors
   - What separates winners from losers
   - Critical capabilities needed

Provide specific data points and cite sources where possible."""

        return await self.respond(prompt)

    async def _analyze_company(self, context: ResearchContext, **kwargs) -> str:
        """Perform company analysis"""
        prompt = f"""Perform comprehensive company analysis for:
Company: {context.company_name} ({context.ticker})
Sector: {context.sector}
Industry: {context.industry}

Industry Context (already analyzed):
{context.industry_analysis[:1500] if context.industry_analysis else 'Not yet analyzed'}

Analyze:
1. Business Model
   - Revenue streams and mix
   - Key products/services
   - Customer base and concentration

2. Competitive Position
   - Market share and trends
   - Competitive moat (source and durability)
   - Unique advantages

3. Management & Execution
   - Track record
   - Strategic vision
   - Capital allocation history

4. Growth Drivers
   - Organic growth levers
   - M&A strategy
   - Geographic expansion

5. Key Risks
   - Business-specific risks
   - Competitive threats
   - Execution risks

Be specific with numbers and comparisons to peers."""

        return await self.respond(prompt)

    async def _analyze_governance(self, context: ResearchContext, **kwargs) -> str:
        """Perform governance analysis"""
        prompt = f"""Perform corporate governance analysis for:
Company: {context.company_name} ({context.ticker})

Analyze:
1. Board Composition
   - Independence
   - Expertise diversity
   - Tenure and refreshment

2. Executive Compensation
   - Alignment with shareholders
   - Performance metrics
   - Comparison to peers

3. Ownership Structure
   - Major shareholders
   - Insider ownership
   - Institutional holdings

4. Governance Practices
   - Related party transactions
   - Minority shareholder protection
   - Disclosure quality

5. ESG Considerations
   - Environmental practices
   - Social responsibility
   - Governance score

Flag any red flags or concerns."""

        return await self.respond(prompt)

    async def _analyze_dcf(self, context: ResearchContext, **kwargs) -> str:
        """Perform DCF valuation analysis"""
        prompt = f"""Build a DCF valuation model for:
Company: {context.company_name} ({context.ticker})
Sector: {context.sector}

Company Analysis:
{context.company_analysis[:1500] if context.company_analysis else 'See above'}

Build DCF with:

1. Revenue Projections (5-10 years)
   - Growth assumptions by segment
   - Market share assumptions
   - Pricing trends

2. Margin Assumptions
   - Gross margin trajectory
   - Operating leverage
   - Terminal margins

3. Capital Requirements
   - CapEx as % of revenue
   - Working capital needs
   - D&A assumptions

4. Discount Rate
   - Risk-free rate
   - Equity risk premium
   - Company-specific beta
   - WACC calculation

5. Terminal Value
   - Growth rate assumption
   - Exit multiple alternative

6. Scenario Analysis
   - Base case (50% probability)
   - Bull case (20% probability)
   - Bear case (20% probability)
   - Super Bull (5% probability)
   - Super Bear (5% probability)

Provide specific numbers for all assumptions.
Calculate implied price for each scenario.
Calculate probability-weighted target price."""

        return await self.respond(prompt)

    async def _full_analysis(self, context: ResearchContext, **kwargs) -> str:
        """Perform full analysis (all components)"""
        # Run each analysis sequentially
        industry = await self._analyze_industry(context, **kwargs)
        context.industry_analysis = industry

        company = await self._analyze_company(context, **kwargs)
        context.company_analysis = company

        governance = await self._analyze_governance(context, **kwargs)
        context.governance_analysis = governance

        dcf = await self._analyze_dcf(context, **kwargs)

        return f"""# FULL ANALYSIS: {context.company_name} ({context.ticker})

## INDUSTRY ANALYSIS
{industry}

## COMPANY ANALYSIS
{company}

## GOVERNANCE ANALYSIS
{governance}

## DCF VALUATION
{dcf}
"""

    async def _on_activate(self):
        """Log activation"""
        self.set_task(f"Analyst ready for {self.ticker or 'assignment'}")


class EnhancedBullAgent(SpawnableAgent):
    """Bull case advocate with lifecycle management (Tier 2)"""

    def __init__(self, ai_provider, parent_id: str = None, tier: int = 2, config: Optional[Dict] = None):
        super().__init__(ai_provider, "bull", parent_id, tier, config)
        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        return """You are the BULL advocate in an equity research debate.

Your role is to present the OPTIMISTIC case for the investment:
1. Identify upside catalysts and opportunities
2. Highlight competitive advantages and moat
3. Find reasons the market may be undervaluing the stock
4. Project best-case scenario outcomes

Guidelines:
- Be specific with numbers and targets
- Acknowledge but rebut bear arguments
- Focus on probability-weighted upside
- Support claims with evidence
- Be aggressive but not delusional

Your goal is not to be right, but to ensure all bullish arguments are heard."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        self.heartbeat()
        analyst_view = kwargs.get('analyst_view', '')
        debate_context = kwargs.get('debate_context', '')

        prompt = f"""Present the BULL CASE for {context.company_name} ({context.ticker}).

{f"Current Analysis:{chr(10)}{analyst_view[:1000]}" if analyst_view else ""}
{f"Debate Context:{chr(10)}{debate_context[:1000]}" if debate_context else ""}

Industry: {context.industry}
Sector: {context.sector}

Provide:
1. Key bull thesis (1-2 sentences)
2. Top 3 catalysts with timing
3. Upside scenario and target price
4. Why bears are wrong
5. Confidence level (1-10) and key assumption"""

        result = await self.respond(prompt)
        self.complete_task()
        return result


class EnhancedBearAgent(SpawnableAgent):
    """Bear case advocate with lifecycle management (Tier 2)"""

    def __init__(self, ai_provider, parent_id: str = None, tier: int = 2, config: Optional[Dict] = None):
        super().__init__(ai_provider, "bear", parent_id, tier, config)
        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        return """You are the BEAR advocate in an equity research debate.

Your role is to present the PESSIMISTIC case for the investment:
1. Identify key risks and threats
2. Find weaknesses in the business model
3. Challenge bullish assumptions
4. Project downside scenarios

Guidelines:
- Be specific about what could go wrong
- Quantify potential downside
- Focus on probability-weighted risks
- Don't be blindly negative - be realistic
- Acknowledge but rebut bull arguments

Your goal is not to be right, but to ensure all risks are surfaced."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        self.heartbeat()
        analyst_view = kwargs.get('analyst_view', '')
        debate_context = kwargs.get('debate_context', '')

        prompt = f"""Present the BEAR CASE for {context.company_name} ({context.ticker}).

{f"Current Analysis:{chr(10)}{analyst_view[:1000]}" if analyst_view else ""}
{f"Debate Context:{chr(10)}{debate_context[:1000]}" if debate_context else ""}

Industry: {context.industry}
Sector: {context.sector}

Provide:
1. Key bear thesis (1-2 sentences)
2. Top 3 risks with probability
3. Downside scenario and target price
4. Why bulls are wrong
5. Confidence level (1-10) and key concern"""

        result = await self.respond(prompt)
        self.complete_task()
        return result


class EnhancedCriticAgent(SpawnableAgent):
    """Critic that challenges all assumptions (Tier 2)"""

    def __init__(self, ai_provider, parent_id: str = None, tier: int = 2, config: Optional[Dict] = None):
        super().__init__(ai_provider, "critic", parent_id, tier, config)
        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        return """You are a CRITIC in an equity research debate.

Your role is to challenge ALL arguments - both bull and bear:
1. Find logical flaws in reasoning
2. Question unsupported assumptions
3. Demand evidence for claims
4. Identify missing considerations

Guidelines:
- Be constructive, not destructive
- Ask probing questions
- Point out circular reasoning
- Challenge consensus views
- Demand specificity over vagueness

Your goal is to strengthen the analysis through rigorous critique."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        self.heartbeat()
        bull_result = kwargs.get('bull_result', '')
        bear_result = kwargs.get('bear_result', '')
        debate_context = kwargs.get('debate_context', '')

        prompt = f"""CRITIQUE the debate arguments for {context.company_name} ({context.ticker}).

Bull Argument:
{bull_result[:800] if bull_result else 'Not provided'}

Bear Argument:
{bear_result[:800] if bear_result else 'Not provided'}

{f"Debate Context:{chr(10)}{debate_context[:500]}" if debate_context else ""}

Provide:
1. Strongest point from BULL case
2. Weakest point from BULL case (and why)
3. Strongest point from BEAR case
4. Weakest point from BEAR case (and why)
5. Key question neither side addressed
6. What evidence would settle the debate"""

        result = await self.respond(prompt)
        self.complete_task()
        return result


class EnhancedSynthesizerAgent(SpawnableAgent):
    """Synthesizes debate into conclusions (Tier 2)"""

    def __init__(self, ai_provider, parent_id: str = None, tier: int = 2, config: Optional[Dict] = None):
        super().__init__(ai_provider, "synthesizer", parent_id, tier, config)
        self.ticker = config.get('ticker') if config else None
        self.debate_log = config.get('debate_log', []) if config else []
        self.disagreements = config.get('disagreements', []) if config else []
        self.consensus = config.get('consensus', []) if config else []

    def _get_system_prompt(self) -> str:
        return """You are the SYNTHESIZER in an equity research debate.

Your role is to:
1. Reconcile bull and bear arguments
2. Assign probabilities to scenarios
3. Calculate probability-weighted target price
4. Provide final recommendation

Guidelines:
- Be balanced and objective
- Weight arguments by evidence quality
- Acknowledge uncertainty appropriately
- Provide clear, actionable conclusion
- State confidence level explicitly

Your output should be the definitive research conclusion."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        self.heartbeat()
        synthesis_context = kwargs.get('synthesis_context', '')

        prompt = f"""SYNTHESIZE the debate for {context.company_name} ({context.ticker}).

{synthesis_context if synthesis_context else f'''
Debate Summary:
- Entries: {len(self.debate_log)}
- Key Disagreements: {json.dumps(self.disagreements[:5], indent=2)}
- Consensus Points: {json.dumps(self.consensus[:5], indent=2)}
'''}

Industry Analysis:
{context.industry_analysis[:500] if context.industry_analysis else 'Not available'}

Company Analysis:
{context.company_analysis[:500] if context.company_analysis else 'Not available'}

Provide:
1. INVESTMENT THESIS (2-3 sentences)

2. SCENARIO ANALYSIS
   | Scenario | Probability | Target Price | Key Driver |
   | Super Bear | X% | $XX | reason |
   | Bear | X% | $XX | reason |
   | Base | X% | $XX | reason |
   | Bull | X% | $XX | reason |
   | Super Bull | X% | $XX | reason |

3. PROBABILITY-WEIGHTED TARGET: $XX

4. KEY RISKS (top 3)

5. KEY CATALYSTS (top 3)

6. RECOMMENDATION: [Strong Buy / Buy / Hold / Sell / Strong Sell]
   Confidence: [High / Medium / Low]

7. POSITION SIZING SUGGESTION"""

        result = await self.respond(prompt)
        self.complete_task()
        return result
