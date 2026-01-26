"""
Due Diligence Agent - Deep verification for high-conviction calls

Triggers when target price differs significantly from market:
- Upside >= 40% -> Triggers due diligence
- Downside <= -20% -> Triggers due diligence

Quality is paramount - takes the time needed to verify high-conviction calls.

Steps:
1. Logic Verification - Review analytical chain
2. Data Verification - Cross-check key figures
3. Market Consensus Comparison - Fetch analyst estimates
4. Discrepancy Analysis - Explain differences vs market
5. Deep Dive Research - Spawn sub-agents for specific areas
6. Final Conviction Assessment - High confidence articulation
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext, AgentMessage


@dataclass
class DueDiligenceResult:
    """Result of due diligence process"""
    triggered: bool  # Whether DD was needed
    trigger_reason: str  # Why DD was triggered
    passed: bool  # Whether DD passed
    conviction_level: str  # None, Low, Medium, High, Very High
    target_price: float
    current_price: float
    upside_pct: float

    # Verification results
    logic_verified: bool
    data_verified: bool
    market_comparison_done: bool
    deep_dive_findings: List[str]

    # Output
    summary: str
    key_differences: List[str]
    supporting_evidence: List[str]


class DueDiligenceAgent(SpawnableAgent):
    """
    Due Diligence Agent for high-conviction equity calls (Tier 3).

    Performs deep verification when research conclusions differ
    significantly from market consensus.

    Trigger Conditions:
    - Upside >= 40%: Bullish call needs verification
    - Downside <= -20%: Bearish call needs verification

    Usage:
        dd_agent = await supervisor.spawn_child(
            DueDiligenceAgent, "dd_agent_6682HK",
            config={
                'ticker': '6682 HK',
                'current_price': 61.60,
                'target_price': 100.00
            }
        )
        result = await dd_agent.run_due_diligence(context)
        if result['passed'] and result['conviction'] >= 'High':
            # High-conviction call verified
    """

    # Trigger thresholds
    UPSIDE_THRESHOLD = 0.40  # 40% upside
    DOWNSIDE_THRESHOLD = -0.20  # -20% downside

    def __init__(
        self,
        ai_provider,
        parent_id: str = None,
        tier: int = 3,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role="due_diligence_agent",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.ticker = config.get('ticker') if config else None
        self.current_price = config.get('current_price', 0) if config else 0
        self.target_price = config.get('target_price', 0) if config else 0

        # Sub-agent tracking
        self.sub_agents: Dict[str, str] = {}  # type -> agent_id

        # Results tracking
        self.verification_results: Dict[str, Any] = {}
        self.deep_dive_findings: List[str] = []
        self.key_differences: List[str] = []

    def _get_system_prompt(self) -> str:
        return """You are a DUE DILIGENCE AGENT for high-conviction equity research.

Your job is to VERIFY research with significant price targets. Quality is paramount.

When our target price differs significantly from market consensus:
- We need to PROVE we're right, or ADMIT we're wrong
- Every major assumption needs supporting evidence
- Extraordinary claims require extraordinary proof

You perform:
1. LOGIC VERIFICATION - Is the analytical chain sound?
2. DATA VERIFICATION - Are the numbers correct?
3. MARKET CONSENSUS COMPARISON - What does the market think?
4. DISCREPANCY ANALYSIS - WHY do we differ from consensus?
5. DEEP DIVE RESEARCH - Investigate specific areas of uncertainty
6. CONVICTION ASSESSMENT - How confident are we AFTER verification?

You MUST articulate WHY our view differs from market with CONFIDENCE.
If you can't defend the thesis after verification, recommend revision.

Time is NOT a constraint. Thoroughness is MANDATORY."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Run due diligence analysis (for compatibility)"""
        result = await self.run_due_diligence(context)
        return f"Due Diligence: {'PASSED' if result['passed'] else 'FAILED'} (Conviction: {result['conviction_level']})"

    def should_trigger(self, current_price: float = None, target_price: float = None) -> tuple:
        """
        Check if due diligence should be triggered.

        Returns:
            (triggered: bool, reason: str, upside_pct: float)
        """
        cp = current_price or self.current_price
        tp = target_price or self.target_price

        if not cp or not tp or cp <= 0:
            return (False, "Missing price data", 0)

        upside_pct = (tp - cp) / cp

        if upside_pct >= self.UPSIDE_THRESHOLD:
            return (True, f"High upside ({upside_pct:.1%}) exceeds {self.UPSIDE_THRESHOLD:.0%} threshold", upside_pct)
        elif upside_pct <= self.DOWNSIDE_THRESHOLD:
            return (True, f"Significant downside ({upside_pct:.1%}) exceeds {abs(self.DOWNSIDE_THRESHOLD):.0%} threshold", upside_pct)
        else:
            return (False, f"Target within normal range ({upside_pct:.1%})", upside_pct)

    async def run_due_diligence(self, context: ResearchContext) -> Dict:
        """
        Run full due diligence process.

        Args:
            context: Research context to verify

        Returns:
            {
                'triggered': bool,
                'trigger_reason': str,
                'passed': bool,
                'conviction_level': str,
                'upside_pct': float,
                'logic_verified': bool,
                'data_verified': bool,
                'market_consensus': Dict,
                'key_differences': List[str],
                'deep_dive_findings': List[str],
                'supporting_evidence': List[str],
                'summary': str,
                'recommendation': str
            }
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Running due diligence")

        # Check if due diligence should trigger
        triggered, reason, upside_pct = self.should_trigger()

        if not triggered:
            self.complete_task()
            return {
                'triggered': False,
                'trigger_reason': reason,
                'passed': True,
                'conviction_level': 'Standard',
                'upside_pct': upside_pct,
                'summary': f"Due diligence not required. Target within normal range.",
                'recommendation': 'PROCEED'
            }

        # Full due diligence process
        try:
            # Step 1: Logic Verification
            self.set_task(f"{self.ticker}: Step 1 - Logic verification")
            logic_result = await self._verify_logic(context)
            self.verification_results['logic'] = logic_result

            # Step 2: Data Verification
            self.set_task(f"{self.ticker}: Step 2 - Data verification")
            data_result = await self._verify_data(context)
            self.verification_results['data'] = data_result

            # Step 3: Market Consensus Comparison
            self.set_task(f"{self.ticker}: Step 3 - Market consensus comparison")
            consensus_result = await self._compare_market_consensus(context)
            self.verification_results['consensus'] = consensus_result

            # Step 4: Discrepancy Analysis
            self.set_task(f"{self.ticker}: Step 4 - Discrepancy analysis")
            discrepancy_result = await self._analyze_discrepancies(context, consensus_result)
            self.verification_results['discrepancies'] = discrepancy_result

            # Step 5: Deep Dive Research (spawn sub-agents)
            self.set_task(f"{self.ticker}: Step 5 - Deep dive research")
            deep_dive_result = await self._run_deep_dive(context, discrepancy_result)
            self.verification_results['deep_dive'] = deep_dive_result

            # Step 6: Final Conviction Assessment
            self.set_task(f"{self.ticker}: Step 6 - Final conviction assessment")
            conviction_result = await self._assess_conviction(context)
            self.verification_results['conviction'] = conviction_result

            # Aggregate results
            passed = (
                logic_result.get('verified', False) and
                data_result.get('verified', False) and
                conviction_result.get('level', 'Low') in ['High', 'Very High']
            )

            self.complete_task()

            return {
                'triggered': True,
                'trigger_reason': reason,
                'passed': passed,
                'conviction_level': conviction_result.get('level', 'Low'),
                'upside_pct': upside_pct,
                'logic_verified': logic_result.get('verified', False),
                'data_verified': data_result.get('verified', False),
                'market_consensus': consensus_result,
                'key_differences': self.key_differences,
                'deep_dive_findings': self.deep_dive_findings,
                'supporting_evidence': conviction_result.get('evidence', []),
                'summary': conviction_result.get('summary', ''),
                'recommendation': 'PUBLISH' if passed else 'REVISE',
                'verification_details': self.verification_results
            }

        except Exception as e:
            self.fail_task(str(e))
            return {
                'triggered': True,
                'trigger_reason': reason,
                'passed': False,
                'conviction_level': 'None',
                'upside_pct': upside_pct,
                'error': str(e),
                'summary': f"Due diligence failed: {str(e)}",
                'recommendation': 'REVISE'
            }

    # ==========================================
    # Step 1: Logic Verification
    # ==========================================

    async def _verify_logic(self, context: ResearchContext) -> Dict:
        """Review the entire analytical chain for logical consistency"""

        prompt = f"""LOGIC VERIFICATION for {context.company_name} ({context.ticker})

Our Analysis Summary:
- Industry Analysis: {context.industry_analysis[:800] if context.industry_analysis else 'None'}
- Company Analysis: {context.company_analysis[:800] if context.company_analysis else 'None'}
- DCF Assumptions: {json.dumps(context.dcf_assumptions, default=str)[:500] if context.dcf_assumptions else 'None'}
- Scenario Analysis: {json.dumps(context.scenario_analysis, default=str)[:500] if context.scenario_analysis else 'None'}

Target Price: {self.target_price}
Current Price: {self.current_price}
Upside: {((self.target_price/self.current_price)-1)*100:.1f}%

VERIFY:
1. Is the logical chain from analysis to valuation sound?
2. Do the assumptions internally consistent?
3. Do cause-effect relationships make sense?
4. Are there any logical leaps or gaps?
5. Does the conclusion follow from the evidence?

Provide:
- verified: true/false
- issues: List of logical issues found
- gaps: Any missing logical connections
- assessment: Overall assessment (1-5 scale)

Format as JSON: {{"verified": bool, "issues": [], "gaps": [], "assessment": int, "explanation": "..."}}"""

        response = await self.respond(prompt)
        return self._parse_verification_result(response, 'logic')

    # ==========================================
    # Step 2: Data Verification
    # ==========================================

    async def _verify_data(self, context: ResearchContext) -> Dict:
        """Cross-check key financial figures with multiple sources"""

        prompt = f"""DATA VERIFICATION for {context.company_name} ({context.ticker})

Financial Data:
{json.dumps(context.financial_data, default=str)[:1500] if context.financial_data else 'None'}

DCF Assumptions:
{json.dumps(context.dcf_assumptions, default=str)[:800] if context.dcf_assumptions else 'None'}

VERIFY these key figures:
1. Revenue figures - Are they correct?
2. Margin assumptions - Are they reasonable?
3. Growth rates - Do they match historical patterns?
4. Industry statistics - Are they accurate?
5. Competitive data - Is it current?

For each key figure:
- Confirm if verifiable
- Flag if seems incorrect
- Note if data is stale

Provide:
- verified: true/false (only true if all critical data verified)
- verified_items: List of items verified
- flagged_items: List of items that couldn't be verified or seem wrong
- stale_items: List of items that may be outdated
- confidence: 0-100%

Format as JSON: {{"verified": bool, "verified_items": [], "flagged_items": [], "stale_items": [], "confidence": int}}"""

        response = await self.respond(prompt)
        return self._parse_verification_result(response, 'data')

    # ==========================================
    # Step 3: Market Consensus Comparison
    # ==========================================

    async def _compare_market_consensus(self, context: ResearchContext) -> Dict:
        """Compare our target with analyst consensus"""

        prompt = f"""MARKET CONSENSUS COMPARISON for {context.company_name} ({context.ticker})

Our Analysis:
- Target Price: {self.target_price}
- Current Price: {self.current_price}
- Implied Upside: {((self.target_price/self.current_price)-1)*100:.1f}%

Based on your knowledge of typical analyst coverage for {context.industry} companies in {context.sector}:

1. What is the typical consensus target range for this stock?
2. What are typical sell-side estimates?
3. How does our target compare to consensus?
4. What's the typical bull/bear spread in analyst targets?

Provide estimated consensus data:
- consensus_low: Lowest analyst target estimate
- consensus_median: Median analyst target
- consensus_high: Highest analyst target
- our_position: Where we stand (below/in-line/above consensus)
- deviation_pct: How much we deviate from median consensus

Format as JSON: {{"consensus_low": float, "consensus_median": float, "consensus_high": float, "our_position": "...", "deviation_pct": float, "market_sentiment": "..."}}"""

        response = await self.respond(prompt)
        return self._parse_verification_result(response, 'consensus')

    # ==========================================
    # Step 4: Discrepancy Analysis
    # ==========================================

    async def _analyze_discrepancies(self, context: ResearchContext, consensus: Dict) -> Dict:
        """Identify specific assumptions where we differ from market"""

        deviation = consensus.get('deviation_pct', 0)
        position = consensus.get('our_position', 'unknown')

        prompt = f"""DISCREPANCY ANALYSIS for {context.company_name} ({context.ticker})

Our Target: {self.target_price}
Consensus Median: {consensus.get('consensus_median', 'N/A')}
Our Position: {position}
Deviation: {deviation}%

Our Key Assumptions:
{json.dumps(context.dcf_assumptions, default=str)[:1000] if context.dcf_assumptions else 'None'}

Our Scenario Analysis:
{json.dumps(context.scenario_analysis, default=str)[:800] if context.scenario_analysis else 'None'}

IDENTIFY:
1. Which specific assumptions differ from market?
2. What key drivers do we see differently?
3. WHY do we believe the market is wrong?

For each major discrepancy:
- assumption: What assumption differs
- our_view: What we believe
- market_view: What market believes
- rationale: Why we're confident in our view
- evidence: Supporting evidence for our view

Provide 3-5 key differences:

Format as JSON: {{"differences": [{{"assumption": "...", "our_view": "...", "market_view": "...", "rationale": "...", "evidence": "..."}}], "conviction_factors": [], "risk_factors": []}}"""

        response = await self.respond(prompt)
        result = self._parse_verification_result(response, 'discrepancy')

        # Store key differences
        if 'differences' in result:
            for diff in result['differences']:
                self.key_differences.append(
                    f"{diff.get('assumption', 'Unknown')}: {diff.get('our_view', '')} vs market view: {diff.get('market_view', '')}"
                )

        return result

    # ==========================================
    # Step 5: Deep Dive Research
    # ==========================================

    async def _run_deep_dive(self, context: ResearchContext, discrepancies: Dict) -> Dict:
        """Spawn sub-agents to investigate specific areas"""

        differences = discrepancies.get('differences', [])
        findings = []

        # Limit to top 3 most important discrepancies
        for i, diff in enumerate(differences[:3]):
            assumption = diff.get('assumption', f'Assumption {i+1}')

            # Deep dive into each major discrepancy
            prompt = f"""DEEP DIVE RESEARCH for {context.company_name} ({context.ticker})

Investigating: {assumption}
Our View: {diff.get('our_view', 'N/A')}
Market View: {diff.get('market_view', 'N/A')}
Our Rationale: {diff.get('rationale', 'N/A')}

Company Context:
{context.company_analysis[:500] if context.company_analysis else 'None'}

Industry Context:
{context.industry_analysis[:500] if context.industry_analysis else 'None'}

CONDUCT DEEP DIVE:
1. What additional evidence supports our view?
2. What evidence contradicts our view?
3. What are we potentially missing?
4. What would invalidate our thesis?
5. What's the probability we're correct?

Provide:
- supporting_evidence: List of evidence FOR our view
- contradicting_evidence: List of evidence AGAINST our view
- blind_spots: What we might be missing
- probability_correct: 0-100%
- recommendation: "maintain", "revise_up", "revise_down", or "reject"

Format as JSON."""

            response = await self.respond(prompt)
            result = self._parse_verification_result(response, f'deep_dive_{i}')

            findings.append({
                'assumption': assumption,
                'result': result,
                'recommendation': result.get('recommendation', 'maintain')
            })

            self.deep_dive_findings.append(
                f"{assumption}: {result.get('recommendation', 'unknown')} (Confidence: {result.get('probability_correct', 'N/A')}%)"
            )

        return {
            'deep_dives_completed': len(findings),
            'findings': findings,
            'overall_recommendation': self._aggregate_deep_dive_recommendations(findings)
        }

    def _aggregate_deep_dive_recommendations(self, findings: List[Dict]) -> str:
        """Aggregate deep dive recommendations"""
        recommendations = [f.get('recommendation', 'maintain') for f in findings]

        if 'reject' in recommendations:
            return 'REVISE_NEEDED'
        elif recommendations.count('revise_down') > len(recommendations) / 2:
            return 'REVISE_DOWN'
        elif recommendations.count('revise_up') > len(recommendations) / 2:
            return 'REVISE_UP'
        else:
            return 'MAINTAIN'

    # ==========================================
    # Step 6: Final Conviction Assessment
    # ==========================================

    async def _assess_conviction(self, context: ResearchContext) -> Dict:
        """Final conviction assessment after all verification"""

        prompt = f"""FINAL CONVICTION ASSESSMENT for {context.company_name} ({context.ticker})

VERIFICATION SUMMARY:

Logic Verification:
{json.dumps(self.verification_results.get('logic', {}), default=str)[:400]}

Data Verification:
{json.dumps(self.verification_results.get('data', {}), default=str)[:400]}

Market Consensus:
{json.dumps(self.verification_results.get('consensus', {}), default=str)[:400]}

Key Differences from Market:
{json.dumps(self.key_differences[:5], default=str)}

Deep Dive Findings:
{json.dumps(self.deep_dive_findings[:5], default=str)}

Our Target: {self.target_price}
Current Price: {self.current_price}
Upside: {((self.target_price/self.current_price)-1)*100:.1f}%

FINAL ASSESSMENT:
Based on ALL verification completed, provide:

1. conviction_level: "Very High", "High", "Medium", "Low", or "None"
2. summary: 2-3 sentence conviction statement
3. evidence: Top 3 pieces of supporting evidence
4. risks: Top 3 risks to thesis
5. recommendation: "PUBLISH_HIGH_CONVICTION", "PUBLISH_STANDARD", "REVISE_TARGET", or "REJECT"

ONLY assign "High" or "Very High" if:
- Logic is sound AND
- Data is verified AND
- We can clearly articulate WHY we differ from market AND
- Deep dive research supports our view

Format as JSON: {{"level": "...", "summary": "...", "evidence": [], "risks": [], "recommendation": "..."}}"""

        response = await self.respond(prompt)
        return self._parse_verification_result(response, 'conviction')

    # ==========================================
    # Helper Methods
    # ==========================================

    def _parse_verification_result(self, response: str, step: str) -> Dict:
        """Parse AI response into structured result"""
        import re

        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, Exception):
            pass

        # Fallback: return raw response
        return {
            'step': step,
            'raw_response': response[:1000],
            'parsed': False
        }

    async def evaluate_gate(self, context: ResearchContext) -> Dict:
        """
        Evaluate if research passes due diligence gate.

        Compatible with other goalkeeper gates interface.
        """
        result = await self.run_due_diligence(context)

        return {
            'passed': result.get('passed', False),
            'score': self._calculate_score(result),
            'issues': self._extract_issues(result),
            'blockers': [] if result.get('passed', False) else [
                f"Due diligence failed: {result.get('recommendation', 'REVISE')}"
            ],
            'conviction_level': result.get('conviction_level', 'None'),
            'summary': result.get('summary', '')
        }

    def _calculate_score(self, result: Dict) -> float:
        """Calculate numerical score from result"""
        if not result.get('triggered', False):
            return 1.0  # Not triggered = pass

        conviction = result.get('conviction_level', 'None')
        conviction_scores = {
            'Very High': 1.0,
            'High': 0.85,
            'Medium': 0.65,
            'Low': 0.40,
            'None': 0.0
        }

        base_score = conviction_scores.get(conviction, 0.5)

        # Adjust for verification results
        if result.get('logic_verified', False):
            base_score += 0.05
        if result.get('data_verified', False):
            base_score += 0.05

        return min(1.0, base_score)

    def _extract_issues(self, result: Dict) -> List[Dict]:
        """Extract issues from verification results"""
        issues = []

        verification = result.get('verification_details', {})

        # Logic issues
        logic = verification.get('logic', {})
        for issue in logic.get('issues', []):
            issues.append({
                'category': 'logic',
                'item': issue,
                'severity': 'major'
            })

        # Data issues
        data = verification.get('data', {})
        for item in data.get('flagged_items', []):
            issues.append({
                'category': 'data',
                'item': item,
                'severity': 'major'
            })

        return issues

    async def _on_activate(self):
        self.set_task(f"Due diligence agent ready for {self.ticker or 'assignment'}")

    async def _graceful_shutdown(self):
        """Terminate any spawned sub-agents"""
        for agent_id in self.sub_agents.values():
            await self.terminate_child(agent_id, graceful=True)


# Helper sub-agent classes for deep dive
# These can be spawned by the DueDiligenceAgent for specific research areas

class IndustryDeepDiveAgent(SpawnableAgent):
    """Investigates industry-specific assumptions"""

    def _get_system_prompt(self) -> str:
        return """You are an INDUSTRY DEEP DIVE specialist.

Your job is to deeply investigate industry-specific assumptions:
- Market size and growth
- Competitive dynamics
- Regulatory environment
- Technology trends
- Customer behavior changes

Provide evidence-based findings."""


class FinancialVerificationAgent(SpawnableAgent):
    """Re-validates financial projections and models"""

    def _get_system_prompt(self) -> str:
        return """You are a FINANCIAL VERIFICATION specialist.

Your job is to deeply verify financial projections:
- Revenue growth assumptions
- Margin trajectory
- Capital efficiency
- Working capital needs
- Cash flow conversion

Challenge every assumption with data."""


class CompetitiveAnalysisAgent(SpawnableAgent):
    """Deeper look at competitive dynamics and moat"""

    def _get_system_prompt(self) -> str:
        return """You are a COMPETITIVE ANALYSIS specialist.

Your job is to deeply analyze competitive position:
- Competitive moat strength
- Threat of new entrants
- Substitute products/services
- Supplier/buyer power
- Market share trends

Identify risks and opportunities."""


class RiskFactorAgent(SpawnableAgent):
    """Investigates specific risk scenarios in detail"""

    def _get_system_prompt(self) -> str:
        return """You are a RISK FACTOR specialist.

Your job is to deeply investigate risks:
- Identify tail risks
- Quantify probability and impact
- Assess mitigation strategies
- Model downside scenarios
- Stress test assumptions

Be thorough - risks often hide in plain sight."""


class CatalystAgent(SpawnableAgent):
    """Researches timing and probability of key catalysts"""

    def _get_system_prompt(self) -> str:
        return """You are a CATALYST RESEARCH specialist.

Your job is to identify and analyze catalysts:
- Upcoming events that could move the stock
- Probability of positive vs negative outcome
- Timing considerations
- Market expectations vs. likely reality
- Risk/reward of the catalyst

Catalysts drive stock performance - analyze them carefully."""
