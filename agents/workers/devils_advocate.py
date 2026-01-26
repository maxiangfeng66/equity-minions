"""
Devil's Advocate Agent - Challenges ALL positions regardless of bull/bear stance

The Devil's Advocate is specifically designed to:
- Find flaws in consensus thinking
- Question assumptions everyone takes for granted
- Present unlikely but plausible scenarios
- Force rigorous justification
"""

from typing import Dict, Any, Optional
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class DevilsAdvocateAgent(SpawnableAgent):
    """
    Challenges ALL positions regardless of bull/bear stance (Tier 2).

    Unlike the Critic who evaluates arguments, the Devil's Advocate
    specifically looks for contrarian angles and challenges consensus.

    Usage:
        devil = await moderator.spawn_child(
            DevilsAdvocateAgent, "devil_6682HK",
            config={'ticker': '6682 HK'}
        )
        challenge = await devil.analyze(context,
            debate_summary="...",
            consensus=["point1", "point2"]
        )
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
            role="devil_advocate",
            parent_id=parent_id,
            tier=tier,
            config=config
        )
        self.ticker = config.get('ticker') if config else None
        # How contrarian to be (0-1)
        self.contrarian_bias = config.get('contrarian_bias', 0.8) if config else 0.8

    def _get_system_prompt(self) -> str:
        return """You are the DEVIL'S ADVOCATE in equity research debates.

Your role is to challenge EVERY position:
- When others agree, find reasons to disagree
- When bull/bear debate, question BOTH sides
- Challenge assumptions everyone accepts
- Present unlikely but plausible scenarios
- Force others to justify their reasoning

You are NOT pessimistic or optimistic - you are CONTRARIAN.
If everyone thinks something is obvious, question it.
If there's consensus, find the overlooked angle.

Your goal is to STRESS-TEST the thesis to destruction.

Guidelines:
- The more confident everyone is, the harder you push back
- Look for "black swan" scenarios
- Question the base rate and priors
- Find historical analogies that contradict the consensus
- Be provocative but grounded - challenges must be addressable

Remember: If your challenge can't be answered, it's valuable.
If it can be answered well, you've strengthened the thesis."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """
        Challenge the current analysis.

        Args:
            context: Research context
            debate_summary: Summary of debate so far
            consensus: List of consensus points
            bull_view: Bull's current position
            bear_view: Bear's current position

        Returns:
            Contrarian challenges
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Devil's advocacy")

        debate_summary = kwargs.get('debate_summary', '')
        consensus_points = kwargs.get('consensus', [])
        bull_view = kwargs.get('bull_view', '')
        bear_view = kwargs.get('bear_view', '')

        prompt = f"""Challenge the analysis for {context.company_name} ({context.ticker}).

CURRENT DEBATE STATE:
{debate_summary[:1500] if debate_summary else 'No summary provided'}

BULL VIEW:
{bull_view[:500] if bull_view else 'Not provided'}

BEAR VIEW:
{bear_view[:500] if bear_view else 'Not provided'}

CONSENSUS POINTS (everyone agrees on these):
{json.dumps(consensus_points, indent=2) if consensus_points else 'None identified'}

Industry: {context.industry}
Sector: {context.sector}

AS THE DEVIL'S ADVOCATE:

1. CHALLENGE EACH CONSENSUS POINT
   For each point everyone agrees on, explain why they might ALL be wrong.

2. FIND THE BLIND SPOTS
   What is NO ONE considering? What's the elephant in the room?

3. PRESENT A CONTRARIAN SCENARIO
   What's the unlikely outcome everyone is ignoring?
   - What probability would you assign?
   - What would have to happen?
   - Why is the market missing it?

4. QUESTION THE MOST CONFIDENT ASSUMPTION
   The more confident both sides are, the more scrutiny it deserves.
   Which "obvious truth" might not be true?

5. HISTORICAL PARALLEL
   Find a historical example that contradicts the consensus.
   What can we learn from companies/situations that looked similar but turned out differently?

Be provocative but substantive. Your challenges must be addressable with evidence."""

        result = await self.respond(prompt)
        self.complete_task()
        return result

    async def challenge_specific(self, context: ResearchContext, target: str, claim: str) -> str:
        """
        Challenge a specific claim from a specific side.

        Args:
            context: Research context
            target: Who made the claim (bull/bear/analyst)
            claim: The specific claim to challenge

        Returns:
            Targeted challenge
        """
        self.heartbeat()

        prompt = f"""As Devil's Advocate, challenge this specific claim.

COMPANY: {context.company_name} ({context.ticker})
CLAIM BY: {target.upper()}
CLAIM: {claim}

Challenge this claim by:
1. Finding the weakest link in the reasoning
2. Identifying what evidence would disprove it
3. Presenting an alternative explanation
4. Quantifying how wrong it could be

Be specific and constructive."""

        return await self.respond(prompt)

    async def find_black_swan(self, context: ResearchContext) -> str:
        """
        Identify potential black swan scenarios.

        Args:
            context: Research context

        Returns:
            Black swan analysis
        """
        self.heartbeat()

        prompt = f"""Identify potential BLACK SWAN scenarios for {context.company_name} ({context.ticker}).

Industry: {context.industry}
Sector: {context.sector}

A black swan is:
- Highly improbable (but not impossible)
- Extremely high impact
- Often rationalized after the fact

For this company, identify:

1. NEGATIVE BLACK SWANS (3-5)
   Events that could devastate the investment:
   - What could happen?
   - Probability estimate (even if very low)
   - Impact magnitude
   - Early warning signs

2. POSITIVE BLACK SWANS (2-3)
   Events that could create extraordinary upside:
   - What could happen?
   - Probability estimate
   - Impact magnitude
   - What would need to align

3. INDUSTRY DISRUPTION SCENARIOS
   What could fundamentally change the industry?
   - Technology disruption
   - Regulatory change
   - Competitive entry
   - Consumer behavior shift

4. RECOMMENDED HEDGES
   If you had to protect against these scenarios, how would you?

Think creatively. The goal is to identify what we're NOT thinking about."""

        return await self.respond(prompt)

    async def stress_test_valuation(self, context: ResearchContext, valuation: Dict) -> str:
        """
        Stress test a valuation model.

        Args:
            context: Research context
            valuation: Valuation assumptions and outputs

        Returns:
            Stress test results
        """
        self.heartbeat()

        prompt = f"""STRESS TEST this valuation for {context.company_name} ({context.ticker}).

VALUATION MODEL:
{json.dumps(valuation, indent=2) if valuation else 'Not provided'}

DCF Assumptions (from context):
{json.dumps(context.dcf_assumptions, indent=2) if context.dcf_assumptions else 'Not available'}

STRESS TEST:

1. MOST SENSITIVE ASSUMPTIONS
   Which 3 assumptions, if wrong, would most affect the valuation?
   - For each: What's the impact of being 20% wrong?

2. CORRELATION RISK
   Are assumptions correlated in ways not modeled?
   - What if growth AND margins are both wrong?
   - What if best-case scenarios cluster together?

3. HISTORICAL COMPARISON
   Has this valuation methodology worked for similar companies?
   - Examples where it worked
   - Examples where it failed
   - Why might this be different?

4. MARKET DISAGREEMENT
   If the market price differs significantly from model:
   - What is the market seeing that the model misses?
   - What is the model seeing that the market misses?
   - Who is more likely right?

5. VALUATION FLOOR
   What's the absolute worst case? At what price is it definitely wrong to sell?

Be quantitative where possible."""

        return await self.respond(prompt)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Log activation"""
        self.set_task(f"Devil's Advocate ready for {self.ticker or 'assignment'}")
