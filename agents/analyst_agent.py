"""
Analyst Agent - Primary research and analysis agent
"""

from typing import Dict, Any
from .base_agent import BaseAgent, ResearchContext


class AnalystAgent(BaseAgent):
    """Primary analyst that performs comprehensive research"""

    def __init__(self, ai_provider):
        super().__init__(ai_provider, "analyst")

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
        """Perform comprehensive analysis"""
        analysis_type = kwargs.get("analysis_type", "full")

        if analysis_type == "industry":
            return await self._analyze_industry(context)
        elif analysis_type == "company":
            return await self._analyze_company(context)
        elif analysis_type == "governance":
            return await self._analyze_governance(context)
        elif analysis_type == "dcf":
            return await self._build_dcf(context)
        else:
            return await self._full_analysis(context)

    async def _analyze_industry(self, context: ResearchContext) -> str:
        prompt = f"""Analyze the industry for {context.company_name} ({context.ticker}):

Industry: {context.industry}
Sector: {context.sector}

Provide:
1. Industry Overview and Market Size (TAM/SAM/SOM)
2. Industry Growth Rate (historical and projected)
3. Key Growth Drivers
4. Competitive Landscape (major players, market share)
5. Industry Dynamics (Porter's Five Forces)
6. Regulatory Environment
7. Key Risks and Challenges
8. Industry Outlook (next 5-10 years)

Be specific with numbers and data where possible."""

        return await self.respond(prompt)

    async def _analyze_company(self, context: ResearchContext) -> str:
        prompt = f"""Analyze {context.company_name} ({context.ticker}):

Industry: {context.industry}
Sector: {context.sector}

Previous Industry Analysis:
{context.industry_analysis[:2000] if context.industry_analysis else 'Not yet available'}

Provide:
1. Business Model Overview
2. Competitive Advantages / Economic Moat
   - Brand, Network Effects, Switching Costs, Cost Advantages, Intangible Assets
3. Market Position and Share
4. Key Products/Services and Revenue Breakdown
5. Growth Strategy
6. Strengths and Weaknesses
7. Opportunities and Threats
8. Key Success Factors

Be specific and data-driven."""

        return await self.respond(prompt)

    async def _analyze_governance(self, context: ResearchContext) -> str:
        prompt = f"""Analyze corporate governance for {context.company_name} ({context.ticker}):

Provide:
1. Ownership Structure (major shareholders, insider ownership)
2. Board Composition and Independence
3. Management Quality and Track Record
4. Executive Compensation Alignment
5. Related Party Transactions
6. Accounting Quality and Audit
7. Capital Allocation History
8. ESG Considerations
9. Red Flags or Concerns
10. Overall Governance Score (1-10) with justification

Be thorough in identifying any governance risks."""

        return await self.respond(prompt)

    async def _build_dcf(self, context: ResearchContext) -> str:
        prompt = f"""Build a DCF valuation model for {context.company_name} ({context.ticker}):

Industry: {context.industry}
Company Analysis:
{context.company_analysis[:2000] if context.company_analysis else 'Not yet available'}

Requirements:
1. Estimate current financials (Revenue, EBIT, Net Income, FCF)
2. Project growth rates:
   - Years 1-5: High growth phase
   - Years 5-10: Transition phase
   - Years 10+: Terminal growth (perpetuity)

3. Build 5 scenarios with clear assumptions:
   - Super Bear (5% probability): Major disruption scenario
   - Bear (20% probability): Below expectations
   - Base (50% probability): Most likely outcome
   - Bull (20% probability): Above expectations
   - Super Bull (5% probability): Everything goes right

4. For each scenario, provide:
   - Revenue growth rates by phase
   - Margin assumptions
   - CapEx intensity
   - Working capital needs
   - Terminal growth rate
   - Key triggers/catalysts

5. Calculate intrinsic value using discount rates: 8%, 9%, 10%, 11%

Output a data table showing intrinsic value per share for each discount rate x scenario combination.

Be very diligent and conservative in your assumptions."""

        return await self.respond(prompt)

    async def _full_analysis(self, context: ResearchContext) -> str:
        """Run full analysis sequence"""
        # This would typically call the individual analyses
        prompt = f"""Provide a comprehensive equity research report for {context.company_name} ({context.ticker}):

Include:
1. Executive Summary
2. Industry Analysis
3. Company Analysis
4. Corporate Governance
5. Financial Analysis
6. DCF Valuation with Scenarios
7. Key Risks
8. Investment Recommendation

Be thorough and data-driven throughout."""

        return await self.respond(prompt)


class BullAgent(BaseAgent):
    """Agent that argues for optimistic scenarios"""

    def __init__(self, ai_provider):
        super().__init__(ai_provider, "bull")

    def _get_system_prompt(self) -> str:
        return """You are a bullish equity analyst who specializes in identifying upside potential.
Your role is to argue for optimistic scenarios and find reasons why a stock could outperform.

Guidelines:
- Identify overlooked growth opportunities
- Highlight competitive advantages the market may underappreciate
- Find catalysts that could drive positive surprises
- Challenge overly conservative assumptions
- Still be grounded in facts - optimism must be justified
- Provide specific bull case scenarios with probabilities

You are not blindly bullish - you present a well-reasoned optimistic case."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        analyst_view = kwargs.get("analyst_view", "")

        prompt = f"""Review the analyst's assessment of {context.company_name} ({context.ticker}):

{analyst_view}

As the bull case advocate:
1. What growth opportunities are being underestimated?
2. What competitive advantages deserve more credit?
3. What positive catalysts could drive upside?
4. Why might the base case be too conservative?
5. What's the realistic upside scenario and its probability?
6. What would need to happen for the super bull case?

Provide specific numbers and justifications for higher valuations."""

        return await self.respond(prompt)


class BearAgent(BaseAgent):
    """Agent that argues for pessimistic scenarios"""

    def __init__(self, ai_provider):
        super().__init__(ai_provider, "bear")

    def _get_system_prompt(self) -> str:
        return """You are a bearish equity analyst who specializes in identifying downside risks.
Your role is to argue for pessimistic scenarios and find reasons why a stock could underperform.

Guidelines:
- Identify risks the market may be ignoring
- Challenge optimistic growth assumptions
- Find threats to competitive advantages
- Highlight governance or execution concerns
- Question the durability of margins and returns
- Provide specific bear case scenarios with probabilities

You are not blindly bearish - you present well-reasoned risk analysis."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        analyst_view = kwargs.get("analyst_view", "")

        prompt = f"""Review the analyst's assessment of {context.company_name} ({context.ticker}):

{analyst_view}

As the bear case advocate:
1. What risks are being underestimated?
2. What threats to competitive advantage exist?
3. What negative catalysts could drive downside?
4. Why might the base case be too optimistic?
5. What's the realistic downside scenario and its probability?
6. What would trigger the super bear case?

Provide specific numbers and justifications for lower valuations."""

        return await self.respond(prompt)
