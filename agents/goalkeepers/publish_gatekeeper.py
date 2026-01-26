"""
Publish Gatekeeper Agent - Final gate before publishing

Coordinates all other gates and makes final publish decision.
Only allows publication if ALL gates pass.

NEW: Includes Due Diligence gate for high-conviction calls
(upside >= 40% or downside <= -20%)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class PublishGatekeeperAgent(SpawnableAgent):
    """
    Final quality gate before publishing (Tier 3).

    Coordinates all quality gates and makes the final publish decision.
    This is the last checkpoint before research is published.

    Gates:
    1. Fact Checker Gate - verifies accuracy
    2. Logic Auditor - ensures consistency
    3. Consensus Validator - confirms debate quality
    4. Due Diligence (conditional) - deep verification for high-conviction calls

    Usage:
        gatekeeper = await supervisor.spawn_child(
            PublishGatekeeperAgent, "gatekeeper_6682HK",
            config={
                'ticker': '6682 HK',
                'current_price': 61.60,
                'target_price': 100.00
            }
        )
        result = await gatekeeper.run_all_gates(context)
        if result['approved']:
            # Safe to publish
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
            role="publish_gatekeeper",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.ticker = config.get('ticker') if config else None
        self.current_price = config.get('current_price', 0) if config else 0
        self.target_price = config.get('target_price', 0) if config else 0
        self.gate_results: Dict[str, Dict] = {}

    def _get_system_prompt(self) -> str:
        return """You are the PUBLISH GATEKEEPER - the final quality control.

You coordinate all quality gates:
1. Fact Checker Gate - verifies accuracy
2. Logic Auditor - ensures consistency
3. Consensus Validator - confirms debate quality
4. Due Diligence Gate (conditional) - deep verification for high-conviction calls

Due Diligence is REQUIRED when:
- Upside >= 40% (bullish conviction)
- Downside <= -20% (bearish conviction)

Only approve publication when ALL required gates pass.

Your decision is final. If you approve:
- The research will be published
- It will influence investment decisions
- Your credibility is on the line

If you reject:
- Research goes back for revision
- Specific issues must be fixed
- You must provide clear guidance

Be thorough but fair. Don't block good research unnecessarily,
but never let bad research through."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Run all gates (for compatibility)"""
        result = await self.run_all_gates(context)
        return f"Publish Decision: {'APPROVED' if result['approved'] else 'REJECTED'}"

    async def run_all_gates(self, context: ResearchContext) -> Dict:
        """
        Run all quality gates in parallel.

        Spawns each gate agent, runs evaluation, aggregates results.
        Includes Due Diligence gate for high-conviction calls.

        Args:
            context: Research context to evaluate

        Returns:
            {
                'approved': bool,
                'gates': {
                    'fact_check': {...},
                    'logic_audit': {...},
                    'consensus': {...},
                    'due_diligence': {...} (if triggered)
                },
                'timestamp': str,
                'recommendation': str,
                'overall_score': float,
                'blockers': List[str],
                'suggestions': List[str],
                'due_diligence_triggered': bool,
                'conviction_level': str (if due diligence triggered)
            }
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Running all quality gates")

        from .fact_checker_gate import FactCheckerGate
        from .logic_auditor import LogicAuditorAgent
        from .consensus_validator import ConsensusValidatorAgent
        from .due_diligence_agent import DueDiligenceAgent

        ticker_safe = self.ticker.replace(' ', '_').replace('.', '_') if self.ticker else 'temp'

        # Spawn core gate agents
        fact_gate = await self.spawn_child(
            FactCheckerGate,
            f"fact_gate_{ticker_safe}",
            config={'ticker': self.ticker}
        )

        logic_gate = await self.spawn_child(
            LogicAuditorAgent,
            f"logic_gate_{ticker_safe}",
            config={'ticker': self.ticker}
        )

        consensus_gate = await self.spawn_child(
            ConsensusValidatorAgent,
            f"consensus_gate_{ticker_safe}",
            config={'ticker': self.ticker}
        )

        # Check if due diligence is needed
        dd_gate = None
        dd_triggered = False
        if self.current_price and self.target_price and self.current_price > 0:
            upside_pct = (self.target_price - self.current_price) / self.current_price
            if upside_pct >= 0.40 or upside_pct <= -0.20:
                dd_triggered = True
                dd_gate = await self.spawn_child(
                    DueDiligenceAgent,
                    f"dd_gate_{ticker_safe}",
                    config={
                        'ticker': self.ticker,
                        'current_price': self.current_price,
                        'target_price': self.target_price
                    }
                )

        try:
            # Run core gates in parallel
            core_results = await asyncio.gather(
                fact_gate.evaluate_gate(context),
                logic_gate.evaluate_gate(context),
                consensus_gate.evaluate_gate(context),
                return_exceptions=True
            )

            # Process core results
            self.gate_results = {
                'fact_check': self._process_gate_result(core_results[0], 'fact_check'),
                'logic_audit': self._process_gate_result(core_results[1], 'logic_audit'),
                'consensus': self._process_gate_result(core_results[2], 'consensus')
            }

            # Run due diligence if triggered
            dd_result = None
            if dd_gate:
                self.set_task(f"{self.ticker}: Running due diligence (high conviction)")
                dd_result = await dd_gate.run_due_diligence(context)
                self.gate_results['due_diligence'] = {
                    'passed': dd_result.get('passed', False),
                    'score': dd_result.get('conviction_level', 'None') in ['High', 'Very High'],
                    'conviction_level': dd_result.get('conviction_level', 'None'),
                    'trigger_reason': dd_result.get('trigger_reason', ''),
                    'key_differences': dd_result.get('key_differences', []),
                    'blockers': [] if dd_result.get('passed', False) else [
                        f"Due diligence failed: {dd_result.get('recommendation', 'REVISE')}"
                    ]
                }

        finally:
            # Always terminate gate agents
            await self.terminate_child(fact_gate.agent_id)
            await self.terminate_child(logic_gate.agent_id)
            await self.terminate_child(consensus_gate.agent_id)
            if dd_gate:
                await self.terminate_child(dd_gate.agent_id)

        # Make final decision
        all_passed = all(
            g.get('passed', False) for g in self.gate_results.values()
        )

        # Calculate overall score
        scores = [g.get('score', 0) for g in self.gate_results.values() if isinstance(g.get('score'), (int, float))]
        overall_score = sum(scores) / len(scores) if scores else 0

        # Collect all blockers
        blockers = []
        for gate_name, result in self.gate_results.items():
            if result.get('blockers'):
                blockers.extend([f"[{gate_name}] {b}" for b in result['blockers']])

        # Generate suggestions
        suggestions = await self._generate_suggestions(context, self.gate_results)

        self.complete_task()

        result = {
            'approved': all_passed,
            'gates': self.gate_results,
            'timestamp': datetime.now().isoformat(),
            'recommendation': 'PUBLISH' if all_passed else 'REVISE',
            'overall_score': overall_score,
            'blockers': blockers,
            'suggestions': suggestions,
            'due_diligence_triggered': dd_triggered
        }

        # Add conviction level if due diligence was run
        if dd_triggered and dd_result:
            result['conviction_level'] = dd_result.get('conviction_level', 'None')

        return result

    def _process_gate_result(self, result: Any, gate_name: str) -> Dict:
        """Process individual gate result"""
        if isinstance(result, Exception):
            return {
                'passed': False,
                'score': 0,
                'error': str(result),
                'blockers': [f'{gate_name} failed to run: {str(result)}']
            }
        elif isinstance(result, dict):
            return result
        else:
            return {
                'passed': False,
                'score': 0,
                'error': 'Invalid result type',
                'blockers': [f'{gate_name} returned invalid result']
            }

    async def _generate_suggestions(self, context: ResearchContext, gate_results: Dict) -> List[str]:
        """Generate actionable suggestions for improvement"""
        suggestions = []

        # Collect all issues
        all_issues = []
        for gate_name, result in gate_results.items():
            issues = result.get('issues', [])
            for issue in issues:
                all_issues.append({
                    'gate': gate_name,
                    **issue
                })

        if not all_issues:
            return ["All quality checks passed. Ready for publication."]

        # Critical issues first
        critical = [i for i in all_issues if i.get('severity') == 'critical']
        if critical:
            suggestions.append("CRITICAL ISSUES (must fix):")
            for issue in critical[:5]:
                desc = issue.get('description') or issue.get('details', 'No details')
                suggestions.append(f"  - [{issue['gate']}] {desc[:100]}")

        # Major issues
        major = [i for i in all_issues if i.get('severity') == 'major']
        if major:
            suggestions.append("MAJOR ISSUES (should fix):")
            for issue in major[:3]:
                desc = issue.get('description') or issue.get('details', 'No details')
                suggestions.append(f"  - [{issue['gate']}] {desc[:100]}")

        # General recommendations
        prompt = f"""Based on these quality gate results for {context.ticker}:

{json.dumps(gate_results, indent=2, default=str)[:2000]}

Provide 2-3 specific, actionable recommendations to improve the research.
Focus on the most impactful changes."""

        try:
            ai_suggestions = await self.respond(prompt)
            suggestions.append("AI RECOMMENDATIONS:")
            suggestions.append(ai_suggestions[:500])
        except:
            pass

        return suggestions

    async def quick_check(self, context: ResearchContext) -> Dict:
        """
        Quick preliminary check without full gate evaluation.

        Useful for early feedback during research process.

        Returns:
            {
                'ready_for_full_check': bool,
                'issues': List[str]
            }
        """
        self.heartbeat()

        issues = []

        # Check minimum requirements
        if not context.industry_analysis:
            issues.append("Missing industry analysis")
        elif len(context.industry_analysis) < 500:
            issues.append("Industry analysis too short")

        if not context.company_analysis:
            issues.append("Missing company analysis")
        elif len(context.company_analysis) < 500:
            issues.append("Company analysis too short")

        if not context.debate_log:
            issues.append("No debate log")
        elif len(context.debate_log) < 10:
            issues.append("Debate log has too few entries")

        if not context.dcf_assumptions:
            issues.append("Missing DCF assumptions")

        if not context.scenario_analysis:
            issues.append("Missing scenario analysis")

        return {
            'ready_for_full_check': len(issues) == 0,
            'issues': issues
        }

    async def _on_activate(self):
        self.set_task(f"Gatekeeper ready for {self.ticker or 'assignment'}")
