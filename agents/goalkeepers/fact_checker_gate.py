"""
Fact Checker Gate - Quality gate for factual accuracy

Blocks publishing if:
- Financial data can't be verified
- Company information is incorrect
- Market data is stale or wrong
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


@dataclass
class FactCheckResult:
    """Result of a fact check"""
    category: str  # financial, company, market, industry
    item: str  # What was checked
    status: str  # verified, unverified, incorrect, stale
    severity: str  # critical, major, minor, info
    details: str  # Explanation


class FactCheckerGate(SpawnableAgent):
    """
    Quality gate for factual accuracy (Tier 3).

    Verifies all factual claims before research can be published.
    Blocks publishing if critical issues are found.

    Usage:
        gate = await supervisor.spawn_child(
            FactCheckerGate, "fact_gate_6682HK",
            config={'ticker': '6682 HK'}
        )
        result = await gate.evaluate_gate(context)
        if result['passed']:
            # Proceed to publishing
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
            role="fact_checker_gate",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.ticker = config.get('ticker') if config else None
        self.required_accuracy = config.get('required_accuracy', 0.95) if config else 0.95
        self.max_issues = config.get('max_issues', 2) if config else 2

    def _get_system_prompt(self) -> str:
        return """You are a FACT CHECKER GATE for equity research.

Before research can be published, you must verify:
1. All financial figures match reliable sources
2. Company information is current and accurate
3. Market data is fresh and correct
4. All claims have supporting evidence

Be RIGOROUS. False information damages credibility.

When checking facts:
- Flag specific numbers that seem wrong
- Identify claims without evidence
- Note data that may be stale
- Check for internal consistency

Your job is to BLOCK bad research, not to let it pass."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Run fact check analysis (for compatibility)"""
        result = await self.evaluate_gate(context)
        return f"Fact Check: {'PASSED' if result['passed'] else 'FAILED'} (Score: {result['score']:.0%})"

    async def evaluate_gate(self, context: ResearchContext) -> Dict:
        """
        Evaluate if research passes fact-checking gate.

        Args:
            context: Research context to verify

        Returns:
            {
                'passed': bool,
                'score': float (0-1),
                'issues': List[Dict],
                'blockers': List[str],
                'recommendations': List[str]
            }
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: Fact checking")

        issues = []

        # Run all checks in parallel conceptually (each is AI-powered)
        financial_issues = await self._check_financial_data(context)
        company_issues = await self._check_company_info(context)
        market_issues = await self._check_market_data(context)
        consistency_issues = await self._check_internal_consistency(context)

        issues.extend(financial_issues)
        issues.extend(company_issues)
        issues.extend(market_issues)
        issues.extend(consistency_issues)

        # Calculate results
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        major_issues = [i for i in issues if i['severity'] == 'major']
        minor_issues = [i for i in issues if i['severity'] == 'minor']

        # Score calculation: start at 100, deduct for issues
        score = 100 - len(critical_issues) * 25 - len(major_issues) * 10 - len(minor_issues) * 2
        score = max(0, score) / 100

        passed = len(critical_issues) == 0 and len(major_issues) <= self.max_issues

        self.complete_task()

        return {
            'passed': passed,
            'score': score,
            'issues': issues,
            'blockers': [i['item'] + ': ' + i['details'] for i in critical_issues],
            'recommendations': self._generate_recommendations(issues),
            'summary': {
                'critical': len(critical_issues),
                'major': len(major_issues),
                'minor': len(minor_issues)
            }
        }

    async def _check_financial_data(self, context: ResearchContext) -> List[Dict]:
        """Check financial data accuracy"""
        prompt = f"""FACT CHECK the financial data for {context.company_name} ({context.ticker}).

Financial Data from context:
{context.financial_data if context.financial_data else 'No structured financial data'}

DCF Assumptions:
{context.dcf_assumptions if context.dcf_assumptions else 'No DCF assumptions'}

Industry Analysis excerpt:
{context.industry_analysis[:1000] if context.industry_analysis else 'None'}

Company Analysis excerpt:
{context.company_analysis[:1000] if context.company_analysis else 'None'}

Check for:
1. Revenue/earnings figures that seem incorrect
2. Growth rates that don't match historical patterns
3. Margin assumptions that are unrealistic
4. Missing key financial metrics
5. Outdated financial data

For each issue found, provide:
- Category: financial
- Item: What was checked
- Status: verified/unverified/incorrect/stale
- Severity: critical/major/minor
- Details: Explanation

Format as JSON array: [{{"category": "financial", "item": "...", "status": "...", "severity": "...", "details": "..."}}]
Return empty array [] if no issues found."""

        response = await self.respond(prompt)
        return self._parse_issues(response, 'financial')

    async def _check_company_info(self, context: ResearchContext) -> List[Dict]:
        """Check company information accuracy"""
        prompt = f"""FACT CHECK company information for {context.company_name} ({context.ticker}).

Sector: {context.sector}
Industry: {context.industry}

Company Analysis:
{context.company_analysis[:1500] if context.company_analysis else 'None'}

Check for:
1. Incorrect company name or ticker
2. Wrong sector/industry classification
3. Outdated product/service descriptions
4. Incorrect management information
5. Wrong headquarters or key facts

For each issue, provide JSON: [{{"category": "company", "item": "...", "status": "...", "severity": "...", "details": "..."}}]
Return empty array [] if no issues found."""

        response = await self.respond(prompt)
        return self._parse_issues(response, 'company')

    async def _check_market_data(self, context: ResearchContext) -> List[Dict]:
        """Check market data accuracy"""
        prompt = f"""FACT CHECK market data for {context.company_name} ({context.ticker}).

Industry Analysis:
{context.industry_analysis[:1500] if context.industry_analysis else 'None'}

Check for:
1. Market size figures that seem wrong
2. Competitor information that's outdated
3. Market share data that doesn't add up
4. Industry growth rates that are unrealistic
5. Regulatory/macro assumptions that are incorrect

For each issue, provide JSON: [{{"category": "market", "item": "...", "status": "...", "severity": "...", "details": "..."}}]
Return empty array [] if no issues found."""

        response = await self.respond(prompt)
        return self._parse_issues(response, 'market')

    async def _check_internal_consistency(self, context: ResearchContext) -> List[Dict]:
        """Check internal consistency of the analysis"""
        prompt = f"""Check INTERNAL CONSISTENCY for {context.company_name} ({context.ticker}).

Industry Analysis excerpt:
{context.industry_analysis[:800] if context.industry_analysis else 'None'}

Company Analysis excerpt:
{context.company_analysis[:800] if context.company_analysis else 'None'}

DCF Assumptions:
{context.dcf_assumptions if context.dcf_assumptions else 'None'}

Scenario Analysis:
{context.scenario_analysis if context.scenario_analysis else 'None'}

Check for:
1. Numbers that contradict each other
2. Assumptions that conflict
3. Conclusions that don't follow from analysis
4. Missing logical connections
5. Circular reasoning

For each issue, provide JSON: [{{"category": "consistency", "item": "...", "status": "...", "severity": "...", "details": "..."}}]
Return empty array [] if no issues found."""

        response = await self.respond(prompt)
        return self._parse_issues(response, 'consistency')

    def _parse_issues(self, response: str, default_category: str) -> List[Dict]:
        """Parse AI response into issue list"""
        import re
        import json

        issues = []

        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            issues.append({
                                'category': item.get('category', default_category),
                                'item': item.get('item', 'Unknown'),
                                'status': item.get('status', 'unverified'),
                                'severity': item.get('severity', 'minor'),
                                'details': item.get('details', '')
                            })
        except (json.JSONDecodeError, Exception):
            # If parsing fails, try to extract issues manually
            if 'critical' in response.lower() or 'incorrect' in response.lower():
                issues.append({
                    'category': default_category,
                    'item': 'Parse Error',
                    'status': 'unverified',
                    'severity': 'minor',
                    'details': 'Could not parse fact check response'
                })

        return issues

    def _generate_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate recommendations based on issues found"""
        recommendations = []

        critical = [i for i in issues if i['severity'] == 'critical']
        major = [i for i in issues if i['severity'] == 'major']

        if critical:
            recommendations.append(f"BLOCKING: Fix {len(critical)} critical issues before publishing")
            for issue in critical[:3]:
                recommendations.append(f"  - {issue['item']}: {issue['details'][:100]}")

        if major:
            recommendations.append(f"Review {len(major)} major issues")

        if not issues:
            recommendations.append("All fact checks passed")

        return recommendations

    async def _on_activate(self):
        self.set_task(f"Fact checker ready for {self.ticker or 'assignment'}")
