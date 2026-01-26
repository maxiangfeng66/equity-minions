"""
Consensus Validator Agent - Validates debate consensus quality

Checks:
- Sufficient debate rounds occurred
- Key disagreements were addressed
- Final synthesis reflects debate
- Minority views were considered
"""

from typing import Dict, List, Any, Optional

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class ConsensusValidatorAgent(SpawnableAgent):
    """
    Validates debate consensus quality (Tier 3).

    Ensures the debate was rigorous and the synthesis accurately
    reflects the discussion.

    Usage:
        validator = await supervisor.spawn_child(
            ConsensusValidatorAgent, "consensus_gate_6682HK",
            config={'ticker': '6682 HK', 'min_rounds': 5}
        )
        result = await validator.evaluate_gate(context)
    """

    def __init__(
        self,
        ai_provider,
        parent_id: str = None,
        tier: int = 3,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role="consensus_validator",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.ticker = config.get('ticker') if config else None
        self.min_debate_rounds = config.get('min_rounds', 5) if config else 5
        self.min_participants = config.get('min_participants', 3) if config else 3

    def _get_system_prompt(self) -> str:
        return """You are a CONSENSUS VALIDATOR for equity research debates.

Verify debate quality:
1. Sufficient debate occurred (rounds, participants)
2. Key disagreements were explicitly addressed
3. Final synthesis accurately reflects debate
4. Minority views were properly considered
5. Confidence levels match debate consensus

You are checking the PROCESS, not the conclusion.

A good debate has:
- Clear positions from multiple perspectives
- Direct engagement with counter-arguments
- Evolution of views based on challenges
- Honest acknowledgment of uncertainty
- Synthesis that represents all valid points

A bad debate has:
- Participants talking past each other
- Key challenges ignored
- Synthesis that misrepresents positions
- False consensus (everyone agreeing without engagement)"""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Run consensus validation (for compatibility)"""
        result = await self.evaluate_gate(context)
        return f"Consensus Validation: {'PASSED' if result['passed'] else 'FAILED'} (Score: {result['score']:.0%})"

    async def evaluate_gate(self, context: ResearchContext) -> Dict:
        """
        Validate consensus quality.

        Returns:
            {
                'passed': bool,
                'score': float (0-1),
                'issues': List[Dict],
                'assessment': Dict
            }
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Consensus validation")

        issues = []
        debate_log = context.debate_log

        # Structural checks
        structural_issues = self._check_structure(debate_log)
        issues.extend(structural_issues)

        # Quality assessment via AI
        quality_assessment = await self._assess_debate_quality(context)

        # Add quality issues
        if quality_assessment.get('engagement_score', 1) < 0.6:
            issues.append({
                'type': 'low_engagement',
                'severity': 'major',
                'description': 'Participants did not engage sufficiently with counter-arguments'
            })

        if quality_assessment.get('synthesis_accuracy', 1) < 0.7:
            issues.append({
                'type': 'synthesis_mismatch',
                'severity': 'major',
                'description': 'Final synthesis does not accurately reflect debate positions'
            })

        # Calculate score
        base_score = quality_assessment.get('overall_score', 0.5)

        # Deductions for structural issues
        critical = len([i for i in issues if i.get('severity') == 'critical'])
        major = len([i for i in issues if i.get('severity') == 'major'])

        adjusted_score = base_score - (critical * 0.25) - (major * 0.1)
        adjusted_score = max(0, min(1, adjusted_score))

        passed = len([i for i in issues if i['severity'] == 'critical']) == 0 and adjusted_score >= 0.6

        self.complete_task()

        return {
            'passed': passed,
            'score': adjusted_score,
            'issues': issues,
            'assessment': quality_assessment
        }

    def _check_structure(self, debate_log: List) -> List[Dict]:
        """Check structural requirements"""
        issues = []

        # Check debate rounds
        if debate_log:
            rounds = len(set(m.metadata.get('round', m.metadata.get('phase', 0)) for m in debate_log))
        else:
            rounds = 0

        if rounds < self.min_debate_rounds:
            issues.append({
                'type': 'insufficient_rounds',
                'severity': 'critical' if rounds < 3 else 'major',
                'description': f'Only {rounds} rounds, minimum {self.min_debate_rounds} required'
            })

        # Check participants
        if debate_log:
            participants = len(set(m.role for m in debate_log))
        else:
            participants = 0

        if participants < self.min_participants:
            issues.append({
                'type': 'insufficient_participants',
                'severity': 'critical' if participants < 2 else 'major',
                'description': f'Only {participants} participants, minimum {self.min_participants} required'
            })

        # Check for empty debate
        if not debate_log:
            issues.append({
                'type': 'no_debate',
                'severity': 'critical',
                'description': 'No debate log found'
            })

        return issues

    async def _assess_debate_quality(self, context: ResearchContext) -> Dict:
        """AI-assisted debate quality assessment"""
        debate_log = context.debate_log

        if not debate_log:
            return {
                'overall_score': 0,
                'engagement_score': 0,
                'synthesis_accuracy': 0,
                'reasoning': 'No debate log to assess'
            }

        # Build debate summary
        debate_summary = "\n".join([
            f"[{m.role.upper()}]: {m.content[:300]}..."
            for m in debate_log[-15:]  # Last 15 entries
        ])

        prompt = f"""Assess DEBATE QUALITY for {context.company_name} ({context.ticker}).

DEBATE LOG (recent entries):
{debate_summary}

FINAL SYNTHESIS (if present):
{[m.content[:500] for m in debate_log if m.role == 'synthesizer'][-1:]}

Assess on 0-1 scale:

1. ENGAGEMENT SCORE (0-1)
   - Did participants directly address each other's points?
   - Were challenges substantively responded to?
   - Did positions evolve based on counter-arguments?

2. ARGUMENT QUALITY (0-1)
   - Were arguments evidence-based?
   - Were claims specific and verifiable?
   - Was reasoning clear and logical?

3. COVERAGE SCORE (0-1)
   - Were all major aspects discussed?
   - Were risks and opportunities balanced?
   - Were minority views heard?

4. SYNTHESIS ACCURACY (0-1)
   - Does synthesis represent debate positions fairly?
   - Are disagreements acknowledged?
   - Is confidence level appropriate?

5. OVERALL SCORE (0-1)
   - Weighted average of above

Return JSON:
{{
    "overall_score": X.X,
    "engagement_score": X.X,
    "argument_quality": X.X,
    "coverage_score": X.X,
    "synthesis_accuracy": X.X,
    "strengths": ["..."],
    "weaknesses": ["..."],
    "reasoning": "..."
}}"""

        response = await self.respond(prompt)

        # Parse response
        import re
        import json

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, Exception):
            pass

        return {
            'overall_score': 0.5,
            'engagement_score': 0.5,
            'synthesis_accuracy': 0.5,
            'reasoning': 'Could not parse quality assessment'
        }

    async def _on_activate(self):
        self.set_task(f"Consensus validator ready for {self.ticker or 'assignment'}")
