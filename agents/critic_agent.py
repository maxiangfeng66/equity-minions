"""
Critic Agent - Challenges assumptions and finds logical flaws
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, ResearchContext, AgentMessage


class CriticAgent(BaseAgent):
    """Agent that challenges all assumptions and finds logical flaws"""

    def __init__(self, ai_provider):
        super().__init__(ai_provider, "critic")

    def _get_system_prompt(self) -> str:
        return """You are a rigorous critic and devil's advocate for equity research.
Your role is to challenge assumptions, find logical flaws, and stress-test analysis.

Guidelines:
- Question every assumption - why is this number reasonable?
- Look for internal inconsistencies in the analysis
- Challenge the data sources and methodology
- Identify circular reasoning or confirmation bias
- Point out missing considerations or blind spots
- Suggest alternative interpretations of the same data
- Rate the confidence level of different assumptions
- Push for more rigorous justifications

You are not negative - you are rigorous. Your goal is to make the analysis stronger."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Critique the current analysis"""
        analysis_to_critique = kwargs.get("analysis", "")
        focus_area = kwargs.get("focus", "general")

        prompt = f"""Critique this analysis of {context.company_name} ({context.ticker}):

{analysis_to_critique}

Focus on challenging:
1. Key Assumptions - Are the growth rates justified? What's the evidence?
2. Logic Flow - Are there logical inconsistencies or gaps?
3. Data Quality - How reliable are the data sources?
4. Missing Factors - What important considerations are overlooked?
5. Bias Detection - Is there confirmation bias or over-optimism/pessimism?
6. Scenario Probabilities - Are the scenario weights reasonable?
7. Discount Rate - Is the chosen rate appropriate for this company's risk?
8. Terminal Value - Is the terminal growth rate sustainable?

For each critique, provide:
- The specific issue
- Why it matters
- Suggested improvement or alternative

Be thorough and rigorous."""

        return await self.respond(prompt)

    async def challenge_assumptions(self, assumptions: Dict[str, Any], context: ResearchContext) -> str:
        """Specifically challenge DCF assumptions"""
        prompt = f"""Challenge these DCF assumptions for {context.company_name} ({context.ticker}):

{assumptions}

For each assumption:
1. Is it reasonable given historical data?
2. Is it consistent with industry norms?
3. What could make this assumption wrong?
4. What's the sensitivity if this assumption is off by 20%?
5. Suggested alternative range

Provide specific counterarguments and alternative assumptions."""

        return await self.respond(prompt)

    async def evaluate_debate(self, debate_log: List[AgentMessage]) -> str:
        """Evaluate the quality of the debate so far"""
        debate_summary = "\n\n".join([
            f"**{msg.role.upper()}**: {msg.content[:500]}..."
            for msg in debate_log[-6:]  # Last 6 messages
        ])

        prompt = f"""Evaluate this equity research debate:

{debate_summary}

Assess:
1. Quality of Arguments - Are both sides making strong, evidence-based points?
2. Key Disagreements - What are the main points of contention?
3. Unresolved Issues - What questions remain unanswered?
4. Consensus Areas - Where do the agents agree?
5. Missing Perspectives - What viewpoints are underrepresented?
6. Recommendation - What additional analysis would strengthen the conclusions?

Provide a balanced assessment."""

        return await self.respond(prompt)


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes debate into final conclusions"""

    def __init__(self, ai_provider):
        super().__init__(ai_provider, "synthesizer")

    def _get_system_prompt(self) -> str:
        return """You are a senior investment committee member who synthesizes research debates.
Your role is to weigh different perspectives and form a balanced, final view.

Guidelines:
- Weigh the strength of arguments from all sides
- Identify the most credible assumptions and projections
- Synthesize conflicting views into a coherent narrative
- Assign appropriate probabilities to scenarios based on debate quality
- Produce a clear, actionable conclusion
- Acknowledge remaining uncertainties
- Provide a probability-weighted target price

Your output should reflect the best thinking from all agents."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Synthesize debate into final conclusions"""
        debate_log = context.debate_log

        debate_summary = "\n\n".join([
            f"**{msg.role.upper()}**: {msg.content[:800]}..."
            for msg in debate_log
        ])

        prompt = f"""Synthesize this equity research debate for {context.company_name} ({context.ticker}):

{debate_summary}

Produce:
1. **Key Findings Summary**
   - Most important insights from the debate
   - Areas of consensus and disagreement

2. **Final Scenario Assumptions**
   Based on the debate, refine the scenarios:
   - Super Bear: probability, key assumptions
   - Bear: probability, key assumptions
   - Base: probability, key assumptions
   - Bull: probability, key assumptions
   - Super Bull: probability, key assumptions

3. **Final Valuation Table**
   Intrinsic value per share for each discount rate (8%, 9%, 10%, 11%) × scenario

4. **Probability-Weighted Target Price**
   Calculate the expected value using scenario probabilities

5. **Confidence Assessment**
   - High confidence conclusions
   - Medium confidence conclusions
   - Low confidence / high uncertainty areas

6. **Key Risks and Catalysts**
   - Main risks to monitor
   - Potential positive catalysts

7. **Investment Recommendation**
   - Buy / Hold / Sell with price target
   - Key factors that would change the view

Be balanced and reflect the full debate."""

        return await self.respond(prompt)

    async def create_final_table(self, context: ResearchContext) -> Dict[str, Any]:
        """Create the final valuation data table"""
        prompt = f"""Based on the research for {context.company_name} ({context.ticker}), create a final valuation table.

Context:
{context.to_dict()}

Output a JSON object with this exact structure:
{{
    "scenarios": {{
        "super_bear": {{"probability": 0.05, "description": "...", "growth_assumptions": {{...}}}},
        "bear": {{"probability": 0.20, "description": "...", "growth_assumptions": {{...}}}},
        "base": {{"probability": 0.50, "description": "...", "growth_assumptions": {{...}}}},
        "bull": {{"probability": 0.20, "description": "...", "growth_assumptions": {{...}}}},
        "super_bull": {{"probability": 0.05, "description": "...", "growth_assumptions": {{...}}}}
    }},
    "intrinsic_values": {{
        "8%": {{"super_bear": X, "bear": X, "base": X, "bull": X, "super_bull": X}},
        "9%": {{"super_bear": X, "bear": X, "base": X, "bull": X, "super_bull": X}},
        "10%": {{"super_bear": X, "bear": X, "base": X, "bull": X, "super_bull": X}},
        "11%": {{"super_bear": X, "bear": X, "base": X, "bull": X, "super_bull": X}}
    }},
    "probability_weighted_value": {{
        "8%": X,
        "9%": X,
        "10%": X,
        "11%": X
    }},
    "recommended_fair_value": X,
    "current_price": X,
    "upside_downside": "X%"
}}

Replace X with actual numbers. Provide only the JSON, no other text."""

        response = await self.respond(prompt)

        # Try to parse the JSON from the response
        import json
        import re

        # Find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                return {"raw_response": response}

        return {"raw_response": response}
