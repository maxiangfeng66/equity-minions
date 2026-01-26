"""
Quality Reviewer - Implements iterative quality control with feedback loops
Inspired by ChatDev's Quality Reviewer pattern

This module provides a quality gate that can:
1. Review research output for completeness and accuracy
2. Route back to revision if issues are found
3. Approve and forward to synthesis when quality is met
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re


class QualityVerdict(Enum):
    """Possible quality review verdicts"""
    APPROVED = "APPROVED"
    REVISION_NEEDED = "REVISION_NEEDED"
    MAJOR_REVISION = "MAJOR_REVISION"


@dataclass
class QualityIssue:
    """Represents a quality issue found during review"""
    category: str  # structural, factual, analytical, balance
    severity: str  # low, medium, high
    description: str
    recommendation: str


@dataclass
class QualityReport:
    """Complete quality review report"""
    verdict: QualityVerdict
    score: float  # 0-100
    issues: List[QualityIssue]
    strengths: List[str]
    routing: str  # "Synthesizer" or "Revision Needed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "description": i.description,
                    "recommendation": i.recommendation
                }
                for i in self.issues
            ],
            "strengths": self.strengths,
            "routing": self.routing
        }


class QualityReviewer:
    """
    Implements quality control for equity research output.

    Quality Dimensions:
    1. Structural Integrity - All required sections present
    2. Factual Accuracy - Claims supported by evidence
    3. Analytical Depth - Sufficient analysis, not just data
    4. Balance - Fair treatment of bull/bear cases
    """

    REQUIRED_SECTIONS = [
        "industry_analysis",
        "company_analysis",
        "financial_analysis",
        "valuation",
        "bull_case",
        "bear_case",
        "risk_assessment",
        "recommendation"
    ]

    QUALITY_THRESHOLDS = {
        "structural": 0.8,   # 80% of sections required
        "factual": 0.7,      # 70% of claims should have evidence
        "analytical": 0.6,   # 60% should show analysis
        "balance": 0.6       # 60% balance between bull/bear
    }

    def __init__(self, max_revisions: int = 3):
        self.max_revisions = max_revisions
        self.revision_count = 0

    def review(self, research_content: Dict[str, Any]) -> QualityReport:
        """
        Perform comprehensive quality review of research content.

        Args:
            research_content: Dict containing research output from various agents

        Returns:
            QualityReport with verdict and routing decision
        """
        issues = []
        strengths = []
        scores = {}

        # 1. Structural Integrity Check
        structural_score, structural_issues = self._check_structural_integrity(research_content)
        scores["structural"] = structural_score
        issues.extend(structural_issues)

        # 2. Factual Accuracy Check
        factual_score, factual_issues = self._check_factual_accuracy(research_content)
        scores["factual"] = factual_score
        issues.extend(factual_issues)

        # 3. Analytical Depth Check
        analytical_score, analytical_issues = self._check_analytical_depth(research_content)
        scores["analytical"] = analytical_score
        issues.extend(analytical_issues)

        # 4. Balance Check
        balance_score, balance_issues = self._check_balance(research_content)
        scores["balance"] = balance_score
        issues.extend(balance_issues)

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) * 100

        # Identify strengths
        if structural_score >= 0.9:
            strengths.append("Comprehensive coverage of all required sections")
        if factual_score >= 0.8:
            strengths.append("Well-supported factual claims")
        if analytical_score >= 0.7:
            strengths.append("Strong analytical depth")
        if balance_score >= 0.7:
            strengths.append("Balanced bull/bear treatment")

        # Determine verdict
        high_severity_issues = [i for i in issues if i.severity == "high"]

        if len(high_severity_issues) > 2:
            verdict = QualityVerdict.MAJOR_REVISION
            routing = "ROUTE: Revision Needed"
        elif overall_score < 60 or len(high_severity_issues) > 0:
            verdict = QualityVerdict.REVISION_NEEDED
            routing = "ROUTE: Revision Needed"
        else:
            verdict = QualityVerdict.APPROVED
            routing = "ROUTE: Synthesizer"

        # Check revision limit
        self.revision_count += 1
        if self.revision_count >= self.max_revisions and verdict != QualityVerdict.APPROVED:
            # Force approval after max revisions
            verdict = QualityVerdict.APPROVED
            routing = "ROUTE: Synthesizer"
            strengths.append(f"Max revisions ({self.max_revisions}) reached - proceeding with current quality")

        return QualityReport(
            verdict=verdict,
            score=overall_score,
            issues=issues,
            strengths=strengths,
            routing=routing
        )

    def _check_structural_integrity(self, content: Dict[str, Any]) -> tuple:
        """Check if all required sections are present"""
        issues = []
        present_sections = 0

        for section in self.REQUIRED_SECTIONS:
            # Check various possible locations
            found = False
            for key in content.keys():
                if section.lower() in key.lower():
                    found = True
                    break

            if found:
                present_sections += 1
            else:
                issues.append(QualityIssue(
                    category="structural",
                    severity="medium",
                    description=f"Missing section: {section}",
                    recommendation=f"Add {section} section to complete the analysis"
                ))

        score = present_sections / len(self.REQUIRED_SECTIONS)
        return score, issues

    def _check_factual_accuracy(self, content: Dict[str, Any]) -> tuple:
        """Check if factual claims have supporting evidence"""
        issues = []
        claims_with_evidence = 0
        total_claims = 0

        # Convert content to text for analysis
        text_content = self._extract_text(content)

        # Look for claims (sentences with numbers or strong assertions)
        claim_patterns = [
            r'\d+%',  # Percentage claims
            r'\$[\d,]+',  # Dollar amounts
            r'billion|million|trillion',  # Scale claims
            r'will|should|must|definitely',  # Strong assertions
        ]

        for pattern in claim_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            total_claims += len(matches)

        # Check for evidence markers
        evidence_patterns = [
            r'according to',
            r'source:',
            r'data shows',
            r'research indicates',
            r'based on',
            r'\[\d+\]',  # Citation markers
        ]

        for pattern in evidence_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            claims_with_evidence += len(matches)

        if total_claims > 0:
            score = min(1.0, claims_with_evidence / max(1, total_claims * 0.5))
        else:
            score = 0.5  # Neutral if no claims detected

        if score < self.QUALITY_THRESHOLDS["factual"]:
            issues.append(QualityIssue(
                category="factual",
                severity="high" if score < 0.4 else "medium",
                description=f"Insufficient evidence for factual claims (score: {score:.0%})",
                recommendation="Add sources and citations to support key claims"
            ))

        return score, issues

    def _check_analytical_depth(self, content: Dict[str, Any]) -> tuple:
        """Check if content shows real analysis vs just data reporting"""
        issues = []

        text_content = self._extract_text(content)

        # Analysis markers
        analysis_markers = [
            r'this suggests',
            r'this indicates',
            r'therefore',
            r'consequently',
            r'as a result',
            r'we believe',
            r'the implication',
            r'compared to',
            r'relative to peers',
            r'outperform|underperform',
        ]

        analysis_count = 0
        for pattern in analysis_markers:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            analysis_count += len(matches)

        # Word count as baseline
        word_count = len(text_content.split())

        # Expect roughly 1 analysis marker per 200 words
        expected_markers = max(5, word_count / 200)
        score = min(1.0, analysis_count / expected_markers)

        if score < self.QUALITY_THRESHOLDS["analytical"]:
            issues.append(QualityIssue(
                category="analytical",
                severity="medium",
                description=f"Insufficient analytical depth (score: {score:.0%})",
                recommendation="Add more interpretive analysis, comparisons, and implications"
            ))

        return score, issues

    def _check_balance(self, content: Dict[str, Any]) -> tuple:
        """Check if bull/bear cases are balanced"""
        issues = []

        text_content = self._extract_text(content)

        # Count bull vs bear arguments
        bull_markers = ['bull', 'upside', 'opportunity', 'growth', 'positive', 'outperform']
        bear_markers = ['bear', 'downside', 'risk', 'decline', 'negative', 'underperform']

        bull_count = sum(text_content.lower().count(m) for m in bull_markers)
        bear_count = sum(text_content.lower().count(m) for m in bear_markers)

        total = bull_count + bear_count
        if total > 0:
            balance_ratio = min(bull_count, bear_count) / max(bull_count, bear_count)
        else:
            balance_ratio = 0.5

        score = balance_ratio

        if score < self.QUALITY_THRESHOLDS["balance"]:
            dominant = "bullish" if bull_count > bear_count else "bearish"
            issues.append(QualityIssue(
                category="balance",
                severity="medium",
                description=f"Analysis appears too {dominant} (balance: {score:.0%})",
                recommendation=f"Add more {'bear' if dominant == 'bullish' else 'bull'} case arguments"
            ))

        return score, issues

    def _extract_text(self, content: Any) -> str:
        """Recursively extract all text from content"""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            return " ".join(self._extract_text(v) for v in content.values())
        elif isinstance(content, list):
            return " ".join(self._extract_text(item) for item in content)
        else:
            return str(content) if content else ""


def create_quality_review_prompt(research_content: str) -> str:
    """Create a prompt for AI-based quality review"""
    return f"""
You are a Quality Control Analyst reviewing equity research.

Review the following research for:
1. STRUCTURAL INTEGRITY - Are all required sections present?
2. FACTUAL ACCURACY - Are claims supported by evidence?
3. ANALYTICAL DEPTH - Is there real analysis, not just data?
4. BALANCE - Is the bull/bear debate fair?

Required sections:
- Industry Analysis
- Company Analysis
- Financial Analysis
- Valuation/DCF
- Bull Case
- Bear Case
- Risk Assessment
- Recommendation

RESEARCH TO REVIEW:
{research_content}

PROVIDE YOUR VERDICT:
If there are significant issues, respond with:
ROUTE: Revision Needed
<list specific issues to fix>

If the research meets quality standards, respond with:
ROUTE: Synthesizer
<brief summary of strengths>
"""
