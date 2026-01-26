"""
Logic Auditor Agent - Quality gate for logical consistency

Blocks publishing if:
- DCF assumptions contradict thesis
- Scenario probabilities don't sum to 100%
- Recommendation contradicts analysis
- Circular reasoning detected
"""

from typing import Dict, List, Any, Optional

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class LogicAuditorAgent(SpawnableAgent):
    """
    Quality gate for logical consistency (Tier 3).

    Verifies that the analysis is internally consistent and
    conclusions follow logically from the evidence.

    Usage:
        auditor = await supervisor.spawn_child(
            LogicAuditorAgent, "logic_gate_6682HK",
            config={'ticker': '6682 HK'}
        )
        result = await auditor.evaluate_gate(context)
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
            role="logic_auditor",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        return """You are a LOGIC AUDITOR for equity research.

Verify logical consistency:
1. Assumptions must align with stated thesis
2. Projections must be internally consistent
3. Scenarios must be properly structured (probabilities sum to 100%)
4. Recommendations must follow from analysis
5. No circular reasoning or contradictions

You are looking for LOGICAL FLAWS, not factual errors.

Examples of issues to catch:
- "Company will grow 30%" but DCF assumes 10% growth
- Bull case probability + Bear case probability = 150%
- "Strong Buy" recommendation despite listing many risks
- Using conclusion to prove premise (circular)

Be precise about what's wrong and why."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Run logic audit (for compatibility)"""
        result = await self.evaluate_gate(context)
        return f"Logic Audit: {'PASSED' if result['passed'] else 'FAILED'} (Score: {result['score']:.0%})"

    async def evaluate_gate(self, context: ResearchContext) -> Dict:
        """
        Evaluate logical consistency.

        Returns:
            {
                'passed': bool,
                'score': float (0-1),
                'issues': List[Dict],
                'blockers': List[str]
            }
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Logic audit")

        issues = []

        # Run logic checks
        dcf_issues = await self._check_dcf_consistency(context)
        scenario_issues = await self._check_scenario_logic(context)
        thesis_issues = await self._check_thesis_alignment(context)
        reasoning_issues = await self._check_reasoning_quality(context)

        issues.extend(dcf_issues)
        issues.extend(scenario_issues)
        issues.extend(thesis_issues)
        issues.extend(reasoning_issues)

        # Calculate score
        critical = [i for i in issues if i.get('severity') == 'critical']
        major = [i for i in issues if i.get('severity') == 'major']

        score = 100 - len(critical) * 25 - len(major) * 10
        score = max(0, score) / 100

        passed = len(critical) == 0

        self.complete_task()

        return {
            'passed': passed,
            'score': score,
            'issues': issues,
            'blockers': [f"{i['type']}: {i['description']}" for i in critical]
        }

    async def _check_dcf_consistency(self, context: ResearchContext) -> List[Dict]:
        """Check DCF model consistency"""
        prompt = f"""Check DCF CONSISTENCY for {context.company_name} ({context.ticker}).

DCF Assumptions:
{context.dcf_assumptions if context.dcf_assumptions else 'Not available'}

Company Analysis:
{context.company_analysis[:1000] if context.company_analysis else 'Not available'}

Scenario Analysis:
{context.scenario_analysis if context.scenario_analysis else 'Not available'}

Check for:
1. Growth assumptions that contradict thesis
2. Margin assumptions inconsistent with competitive analysis
3. Terminal value assumptions unrealistic
4. Discount rate inappropriate for risk profile
5. CapEx assumptions that don't match business model

For each issue found, provide JSON:
[{{"type": "dcf_inconsistency", "severity": "critical/major/minor", "description": "..."}}]
Return [] if no issues."""

        response = await self.respond(prompt)
        return self._parse_issues(response)

    async def _check_scenario_logic(self, context: ResearchContext) -> List[Dict]:
        """Check scenario analysis logic"""
        prompt = f"""Check SCENARIO LOGIC for {context.company_name} ({context.ticker}).

Scenario Analysis:
{context.scenario_analysis if context.scenario_analysis else 'Not available'}

Check for:
1. Probabilities don't sum to 100% (critical)
2. Scenarios overlap or have unclear boundaries
3. Super Bull more likely than Bull (illogical)
4. Base case isn't between Bull and Bear
5. Scenario drivers not clearly defined

For each issue found, provide JSON:
[{{"type": "scenario_logic", "severity": "critical/major/minor", "description": "..."}}]
Return [] if no issues."""

        response = await self.respond(prompt)
        return self._parse_issues(response)

    async def _check_thesis_alignment(self, context: ResearchContext) -> List[Dict]:
        """Check if conclusion aligns with analysis"""
        prompt = f"""Check THESIS ALIGNMENT for {context.company_name} ({context.ticker}).

Industry Analysis:
{context.industry_analysis[:800] if context.industry_analysis else 'Not available'}

Company Analysis:
{context.company_analysis[:800] if context.company_analysis else 'Not available'}

Debate Log (last entries):
{[{'role': m.role, 'content': m.content[:200]} for m in context.debate_log[-5:]] if context.debate_log else 'Not available'}

Check for:
1. Recommendation contradicts identified risks
2. Bull/Bear conclusions not reflected in final view
3. Key concerns from debate ignored in synthesis
4. Price target doesn't match scenario analysis

For each issue found, provide JSON:
[{{"type": "thesis_misalignment", "severity": "critical/major/minor", "description": "..."}}]
Return [] if no issues."""

        response = await self.respond(prompt)
        return self._parse_issues(response)

    async def _check_reasoning_quality(self, context: ResearchContext) -> List[Dict]:
        """Check for reasoning flaws"""
        prompt = f"""Check REASONING QUALITY for {context.company_name} ({context.ticker}).

Full Analysis Context:
- Industry: {context.industry_analysis[:500] if context.industry_analysis else 'N/A'}
- Company: {context.company_analysis[:500] if context.company_analysis else 'N/A'}
- Governance: {context.governance_analysis[:300] if context.governance_analysis else 'N/A'}

Check for:
1. Circular reasoning (using conclusion to prove premise)
2. Non-sequiturs (conclusions that don't follow)
3. False dichotomies
4. Cherry-picking evidence
5. Assuming causation from correlation

For each issue found, provide JSON:
[{{"type": "reasoning_flaw", "severity": "critical/major/minor", "description": "..."}}]
Return [] if no issues."""

        response = await self.respond(prompt)
        return self._parse_issues(response)

    def _parse_issues(self, response: str) -> List[Dict]:
        """Parse AI response into issue list"""
        import re
        import json

        issues = []

        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            issues.append({
                                'type': item.get('type', 'unknown'),
                                'severity': item.get('severity', 'minor'),
                                'description': item.get('description', '')
                            })
        except (json.JSONDecodeError, Exception):
            pass

        return issues

    async def _on_activate(self):
        self.set_task(f"Logic auditor ready for {self.ticker or 'assignment'}")
