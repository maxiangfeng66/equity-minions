"""
Portfolio Orchestrator Agent

Coordinates multiple equity research workflows, assigns tickers to slots,
and identifies cross-equity synergies for enhanced analysis.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from config import EQUITIES


@dataclass
class WorkflowSlot:
    """Represents a workflow execution slot"""
    slot_id: str
    ticker: Optional[str] = None
    company: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    priority: int = 0
    status: str = "pending"  # pending, running, complete, error
    synergies: List[str] = field(default_factory=list)
    research_focus: List[str] = field(default_factory=list)


@dataclass
class PortfolioAssignment:
    """Complete portfolio assignment with all slots"""
    slots: Dict[str, WorkflowSlot]
    synergies_matrix: Dict[str, List[str]]
    cross_analysis_hints: List[str]
    total_equities: int
    sectors_covered: List[str]


class PortfolioOrchestrator:
    """
    Orchestrates parallel equity research workflows.

    Responsibilities:
    - Assigns tickers to workflow slots
    - Identifies sector synergies
    - Prioritizes research order
    - Coordinates cross-equity analysis preparation
    """

    def __init__(self, max_parallel: int = 3):
        self.max_parallel = max_parallel
        self.slots: Dict[str, WorkflowSlot] = {}
        self.assignment: Optional[PortfolioAssignment] = None

    def assign_portfolio(self, tickers: List[str]) -> PortfolioAssignment:
        """
        Assign tickers to workflow slots.

        Args:
            tickers: List of tickers to research (max 3)

        Returns:
            PortfolioAssignment with slot assignments and synergies
        """
        if len(tickers) > self.max_parallel:
            tickers = tickers[:self.max_parallel]

        # Create workflow slots
        self.slots = {}
        sectors_covered = set()

        for i, ticker in enumerate(tickers):
            slot_id = f"slot_{i + 1}"

            # Get company info from config
            company_info = EQUITIES.get(ticker, {})
            company = company_info.get("name", ticker)
            sector = company_info.get("sector", "Unknown")
            industry = company_info.get("industry", "Unknown")

            # Calculate priority (lower = higher priority)
            # Prioritize by: 1) data availability, 2) sector complexity
            priority = i + 1  # Simple sequential for now

            # Identify research focus areas based on sector
            research_focus = self._get_research_focus(sector, industry)

            self.slots[slot_id] = WorkflowSlot(
                slot_id=slot_id,
                ticker=ticker,
                company=company,
                sector=sector,
                industry=industry,
                priority=priority,
                status="pending",
                research_focus=research_focus
            )

            sectors_covered.add(sector)

        # Identify synergies between slots
        synergies_matrix = self._identify_synergies()

        # Generate cross-analysis hints
        cross_analysis_hints = self._generate_cross_analysis_hints()

        # Create assignment
        self.assignment = PortfolioAssignment(
            slots=self.slots,
            synergies_matrix=synergies_matrix,
            cross_analysis_hints=cross_analysis_hints,
            total_equities=len(tickers),
            sectors_covered=list(sectors_covered)
        )

        return self.assignment

    def _get_research_focus(self, sector: str, industry: str) -> List[str]:
        """Get research focus areas based on sector/industry"""
        focus_by_sector = {
            "Healthcare": [
                "Pipeline analysis and clinical trials",
                "FDA approval probabilities",
                "Patent expiration and competition",
                "Reimbursement and pricing power"
            ],
            "Technology": [
                "TAM expansion and market share",
                "R&D productivity and innovation",
                "Customer acquisition costs",
                "Competitive moat sustainability"
            ],
            "Utilities": [
                "Regulatory environment",
                "Capacity expansion plans",
                "Fuel cost sensitivity",
                "ESG and renewable transition"
            ],
            "Communication Services": [
                "Subscriber growth and ARPU",
                "Network capex requirements",
                "Competitive intensity",
                "5G/technology transition"
            ],
            "Real Estate": [
                "Occupancy rates and rent growth",
                "Geographic concentration",
                "Development pipeline",
                "Interest rate sensitivity"
            ]
        }

        return focus_by_sector.get(sector, [
            "Business model analysis",
            "Competitive positioning",
            "Financial health",
            "Growth drivers"
        ])

    def _identify_synergies(self) -> Dict[str, List[str]]:
        """Identify synergies between portfolio slots"""
        synergies = {}

        slot_list = list(self.slots.values())

        for i, slot1 in enumerate(slot_list):
            slot1_synergies = []

            for j, slot2 in enumerate(slot_list):
                if i == j:
                    continue

                # Same sector synergy
                if slot1.sector == slot2.sector:
                    slot1_synergies.append(f"{slot2.ticker} (same sector: {slot1.sector})")
                    slot1.synergies.append(slot2.ticker)

                # Same industry synergy (stronger)
                if slot1.industry == slot2.industry:
                    slot1_synergies.append(f"{slot2.ticker} (same industry: {slot1.industry})")
                    if slot2.ticker not in slot1.synergies:
                        slot1.synergies.append(slot2.ticker)

                # Geographic synergy (China exposure)
                if "HK" in slot1.ticker and "HK" in slot2.ticker:
                    slot1_synergies.append(f"{slot2.ticker} (China/HK exposure)")

            synergies[slot1.slot_id] = slot1_synergies

        return synergies

    def _generate_cross_analysis_hints(self) -> List[str]:
        """Generate hints for cross-equity analysis"""
        hints = []

        slot_list = list(self.slots.values())
        sectors = [s.sector for s in slot_list]

        # Sector-specific hints
        if "Healthcare" in sectors:
            healthcare_tickers = [s.ticker for s in slot_list if s.sector == "Healthcare"]
            if len(healthcare_tickers) > 1:
                hints.append(f"Compare biotech valuations and pipeline strength across {', '.join(healthcare_tickers)}")
            hints.append("Assess FDA/regulatory risk correlation across healthcare holdings")

        if "Technology" in sectors:
            tech_tickers = [s.ticker for s in slot_list if s.sector == "Technology"]
            hints.append(f"Compare technology moats and R&D efficiency")

        # China exposure hints
        hk_tickers = [s.ticker for s in slot_list if "HK" in s.ticker]
        if len(hk_tickers) > 1:
            hints.append(f"Assess China regulatory and macro risk correlation across {', '.join(hk_tickers)}")

        # US vs HK hints
        us_tickers = [s.ticker for s in slot_list if "US" in s.ticker]
        if us_tickers and hk_tickers:
            hints.append(f"Compare US ({', '.join(us_tickers)}) vs HK ({', '.join(hk_tickers)}) market dynamics")

        # General hints
        hints.append("Rank all 3 equities by risk-adjusted expected return")
        hints.append("Identify optimal portfolio weights based on correlation and conviction")

        return hints

    def get_slot(self, slot_id: str) -> Optional[WorkflowSlot]:
        """Get a specific workflow slot"""
        return self.slots.get(slot_id)

    def update_slot_status(self, slot_id: str, status: str):
        """Update the status of a workflow slot"""
        if slot_id in self.slots:
            self.slots[slot_id].status = status

    def all_complete(self) -> bool:
        """Check if all workflows are complete"""
        return all(slot.status == "complete" for slot in self.slots.values())

    def to_json(self) -> str:
        """Export assignment as JSON"""
        if not self.assignment:
            return "{}"

        return json.dumps({
            "portfolio_analysis": {
                "total_equities": self.assignment.total_equities,
                "sectors_covered": self.assignment.sectors_covered,
                "synergies_identified": list(self.assignment.synergies_matrix.values())
            },
            "workflow_assignments": {
                slot_id: {
                    "ticker": slot.ticker,
                    "company": slot.company,
                    "sector": slot.sector,
                    "industry": slot.industry,
                    "priority": slot.priority,
                    "status": slot.status,
                    "research_focus": slot.research_focus,
                    "synergies_with": slot.synergies
                }
                for slot_id, slot in self.slots.items()
            },
            "cross_analysis_hints": self.assignment.cross_analysis_hints,
            "resource_allocation": {
                "parallel_execution": True,
                "max_concurrent": self.max_parallel,
                "estimated_api_calls_per_workflow": 50,
                "recommended_rate_limit_delay": 0.5
            }
        }, indent=2)
