"""
Cross-Equity Analyst Agent

Analyzes relationships and relative value across multiple equities
in a portfolio, providing comparative insights and portfolio recommendations.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class RelativeValue(Enum):
    CHEAP = "cheap"
    FAIR = "fair"
    EXPENSIVE = "expensive"


@dataclass
class EquityMetrics:
    """Key metrics for an equity"""
    ticker: str
    company: str
    sector: str
    current_price: float
    fair_value: float
    upside_pct: float
    rating: str
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ps_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    moat_strength: Optional[str] = None  # Wide, Narrow, None
    risk_score: Optional[float] = None  # 1-10


@dataclass
class CrossEquityAnalysis:
    """Result of cross-equity analysis"""
    equities: List[EquityMetrics]
    rankings: Dict[str, List[str]]
    correlation_analysis: Dict
    portfolio_recommendations: Dict
    key_insights: List[str]


class CrossEquityAnalyst:
    """
    Analyzes relationships across portfolio equities.

    Responsibilities:
    - Compare valuations across equities
    - Identify relative value opportunities
    - Assess risk correlation and diversification
    - Recommend portfolio weights
    """

    def __init__(self):
        self.equities: Dict[str, EquityMetrics] = {}
        self.analysis: Optional[CrossEquityAnalysis] = None

    def add_equity(self, ticker: str, context: Dict):
        """
        Add an equity to the analysis.

        Args:
            ticker: Equity ticker
            context: Research context with metrics
        """
        # Extract metrics from context
        metrics = self._extract_metrics(ticker, context)
        self.equities[ticker] = metrics

    def _extract_metrics(self, ticker: str, context: Dict) -> EquityMetrics:
        """Extract key metrics from research context"""
        # Helper to safely get numeric values
        def get_num(d: Dict, *keys, default=None):
            for key in keys:
                val = d.get(key)
                if val is not None:
                    try:
                        # Clean string values
                        if isinstance(val, str):
                            val = val.replace('$', '').replace('%', '').replace(',', '')
                            val = val.replace('HKD', '').replace('USD', '').replace('CNY', '').strip()
                        return float(val)
                    except (ValueError, TypeError):
                        continue
            return default

        # Get basic info
        company = context.get('company', context.get('company_name', ticker))
        sector = context.get('sector', 'Unknown')

        # Get prices
        current_price = get_num(context, 'current_price', 'price', default=0)
        fair_value = get_num(context, 'fair_value', 'pwv', 'probability_weighted_value', default=0)

        # Calculate upside
        upside_pct = get_num(context, 'upside_pct', 'upside', 'implied_upside', default=0)
        if upside_pct == 0 and current_price > 0 and fair_value > 0:
            upside_pct = ((fair_value - current_price) / current_price) * 100

        # Get rating
        rating = context.get('rating', context.get('recommendation', 'HOLD'))
        if isinstance(rating, dict):
            rating = rating.get('rating', 'HOLD')

        # Get valuation multiples
        valuation = context.get('valuation_metrics', context.get('financial_data', {}))
        pe_ratio = get_num(valuation, 'pe_ratio', 'p_e', 'pe')
        ev_ebitda = get_num(valuation, 'ev_ebitda', 'ev/ebitda')
        ps_ratio = get_num(valuation, 'ps_ratio', 'p_s', 'ps')
        pb_ratio = get_num(valuation, 'pb_ratio', 'p_b', 'pb')

        # Get growth
        financials = context.get('financial_data', {})
        revenue_growth = get_num(financials, 'revenue_growth', 'growth_rate')

        # Get moat
        company_analysis = context.get('company_analysis', {})
        moat = company_analysis.get('moat', company_analysis.get('competitive_moat', 'Narrow'))
        if isinstance(moat, dict):
            moat = moat.get('rating', 'Narrow')

        return EquityMetrics(
            ticker=ticker,
            company=company,
            sector=sector,
            current_price=current_price,
            fair_value=fair_value,
            upside_pct=upside_pct,
            rating=rating,
            pe_ratio=pe_ratio,
            ev_ebitda=ev_ebitda,
            ps_ratio=ps_ratio,
            pb_ratio=pb_ratio,
            revenue_growth=revenue_growth,
            moat_strength=moat
        )

    def analyze(self) -> CrossEquityAnalysis:
        """
        Perform cross-equity analysis.

        Returns:
            CrossEquityAnalysis with rankings, correlations, and recommendations
        """
        equities = list(self.equities.values())

        if len(equities) < 2:
            return self._create_empty_analysis()

        # Generate rankings
        rankings = self._generate_rankings(equities)

        # Analyze correlation
        correlation = self._analyze_correlation(equities)

        # Generate recommendations
        recommendations = self._generate_recommendations(equities, rankings, correlation)

        # Generate insights
        insights = self._generate_insights(equities, rankings, correlation)

        self.analysis = CrossEquityAnalysis(
            equities=equities,
            rankings=rankings,
            correlation_analysis=correlation,
            portfolio_recommendations=recommendations,
            key_insights=insights
        )

        return self.analysis

    def _generate_rankings(self, equities: List[EquityMetrics]) -> Dict[str, List[str]]:
        """Generate rankings by various criteria"""
        rankings = {}

        # By upside (highest first)
        by_upside = sorted(equities, key=lambda x: x.upside_pct or 0, reverse=True)
        rankings['by_upside'] = [e.ticker for e in by_upside]

        # By valuation (lowest P/E first = cheapest)
        equities_with_pe = [e for e in equities if e.pe_ratio and e.pe_ratio > 0]
        if equities_with_pe:
            by_pe = sorted(equities_with_pe, key=lambda x: x.pe_ratio)
            rankings['by_pe_valuation'] = [e.ticker for e in by_pe]

        # By growth (highest first)
        equities_with_growth = [e for e in equities if e.revenue_growth is not None]
        if equities_with_growth:
            by_growth = sorted(equities_with_growth, key=lambda x: x.revenue_growth or 0, reverse=True)
            rankings['by_growth'] = [e.ticker for e in by_growth]

        # By moat strength
        moat_order = {'Wide': 3, 'Narrow': 2, 'None': 1, None: 0}
        by_moat = sorted(equities, key=lambda x: moat_order.get(x.moat_strength, 0), reverse=True)
        rankings['by_moat'] = [e.ticker for e in by_moat]

        # Composite ranking (average rank across dimensions)
        ticker_ranks = {}
        for ticker in [e.ticker for e in equities]:
            ranks = []
            for ranking_list in rankings.values():
                if ticker in ranking_list:
                    ranks.append(ranking_list.index(ticker) + 1)
            if ranks:
                ticker_ranks[ticker] = sum(ranks) / len(ranks)

        composite = sorted(ticker_ranks.keys(), key=lambda x: ticker_ranks[x])
        rankings['composite'] = composite

        return rankings

    def _analyze_correlation(self, equities: List[EquityMetrics]) -> Dict:
        """Analyze risk correlation between equities"""
        sectors = [e.sector for e in equities]
        unique_sectors = set(sectors)

        # Sector concentration
        sector_concentration = len(sectors) - len(unique_sectors)

        # Geographic concentration (HK vs US)
        hk_count = sum(1 for e in equities if 'HK' in e.ticker)
        us_count = sum(1 for e in equities if 'US' in e.ticker)
        geo_diversified = hk_count > 0 and us_count > 0

        # Determine correlation level
        if sector_concentration >= 2:
            correlation_level = "high"
        elif sector_concentration == 1 or not geo_diversified:
            correlation_level = "medium"
        else:
            correlation_level = "low"

        # Common risk factors
        common_factors = []
        if hk_count >= 2:
            common_factors.append("China macro/regulatory risk")
        if any(e.sector == "Healthcare" for e in equities):
            common_factors.append("FDA/regulatory approval risk")
        if any(e.sector == "Technology" for e in equities):
            common_factors.append("Technology disruption risk")

        return {
            "risk_correlation": correlation_level,
            "sector_concentration": sector_concentration,
            "unique_sectors": list(unique_sectors),
            "geographic_mix": {
                "HK": hk_count,
                "US": us_count,
                "other": len(equities) - hk_count - us_count
            },
            "diversification_benefit": "high" if correlation_level == "low" else "medium" if correlation_level == "medium" else "low",
            "common_risk_factors": common_factors
        }

    def _generate_recommendations(self, equities: List[EquityMetrics],
                                   rankings: Dict, correlation: Dict) -> Dict:
        """Generate portfolio recommendations"""
        n = len(equities)

        # Base weights - equal weight starting point
        weights = {e.ticker: 1.0 / n for e in equities}

        # Adjust weights based on conviction (upside)
        total_upside = sum(max(e.upside_pct, 0) for e in equities)
        if total_upside > 0:
            for e in equities:
                upside_weight = max(e.upside_pct, 0) / total_upside
                # Blend equal weight with upside weight
                weights[e.ticker] = 0.5 * weights[e.ticker] + 0.5 * upside_weight

        # Normalize
        total = sum(weights.values())
        weights = {k: round(v / total, 2) for k, v in weights.items()}

        # Determine priority order
        priority_order = rankings.get('composite', [e.ticker for e in equities])

        # Entry recommendations
        entry_recs = {}
        for e in equities:
            if e.upside_pct >= 30:
                entry_recs[e.ticker] = "Accumulate aggressively"
            elif e.upside_pct >= 15:
                entry_recs[e.ticker] = "Build position gradually"
            elif e.upside_pct >= 0:
                entry_recs[e.ticker] = "Small position, wait for pullback"
            else:
                entry_recs[e.ticker] = "Avoid or trim"

        return {
            "optimal_weights": weights,
            "priority_order": priority_order,
            "entry_recommendations": entry_recs,
            "rebalancing_triggers": [
                "Any position moves +/- 10% from target weight",
                "Rating change by any provider",
                "Material news or earnings event",
                "Target price reached"
            ],
            "rationale": self._generate_weight_rationale(equities, weights)
        }

    def _generate_weight_rationale(self, equities: List[EquityMetrics], weights: Dict) -> str:
        """Generate rationale for portfolio weights"""
        parts = []

        # Find highest conviction
        highest = max(equities, key=lambda e: e.upside_pct or 0)
        if highest.upside_pct and highest.upside_pct > 20:
            parts.append(f"{highest.ticker} gets highest weight ({weights.get(highest.ticker, 0):.0%}) due to {highest.upside_pct:.0f}% upside potential")

        # Find best quality
        moat_order = {'Wide': 3, 'Narrow': 2, 'None': 1, None: 0}
        by_moat = sorted(equities, key=lambda x: moat_order.get(x.moat_strength, 0), reverse=True)
        best_quality = by_moat[0]
        if best_quality.moat_strength == 'Wide':
            parts.append(f"{best_quality.ticker} has widest moat, supporting long-term hold")

        if not parts:
            parts.append("Equal weighting used due to similar conviction levels")

        return ". ".join(parts)

    def _generate_insights(self, equities: List[EquityMetrics],
                           rankings: Dict, correlation: Dict) -> List[str]:
        """Generate key insights from the analysis"""
        insights = []

        # Upside spread insight
        upsides = [e.upside_pct for e in equities if e.upside_pct is not None]
        if upsides:
            max_up = max(upsides)
            min_up = min(upsides)
            spread = max_up - min_up
            if spread > 30:
                high_ticker = next(e.ticker for e in equities if e.upside_pct == max_up)
                low_ticker = next(e.ticker for e in equities if e.upside_pct == min_up)
                insights.append(f"Wide upside spread: {high_ticker} ({max_up:.0f}%) vs {low_ticker} ({min_up:.0f}%) suggests differentiated views")

        # Sector insight
        unique_sectors = correlation.get('unique_sectors', [])
        if len(unique_sectors) == len(equities):
            insights.append("Portfolio spans different sectors, providing good diversification")
        elif len(unique_sectors) == 1:
            insights.append(f"Portfolio concentrated in {unique_sectors[0]} - consider diversification")

        # Geographic insight
        geo = correlation.get('geographic_mix', {})
        if geo.get('HK', 0) > 0 and geo.get('US', 0) > 0:
            insights.append("Mix of HK and US exposure provides geographic diversification")

        # Rating insight
        ratings = [e.rating.upper() if e.rating else 'HOLD' for e in equities]
        if all('BUY' in r for r in ratings):
            insights.append("All equities have BUY ratings - high conviction portfolio")
        elif any('SELL' in r or 'AVOID' in r for r in ratings):
            insights.append("Consider trimming or avoiding equities with SELL ratings")

        # Composite ranking insight
        if 'composite' in rankings and rankings['composite']:
            top = rankings['composite'][0]
            insights.append(f"{top} ranks highest on composite score (upside + valuation + quality)")

        return insights

    def _create_empty_analysis(self) -> CrossEquityAnalysis:
        """Create empty analysis when insufficient data"""
        return CrossEquityAnalysis(
            equities=[],
            rankings={},
            correlation_analysis={},
            portfolio_recommendations={},
            key_insights=["Insufficient equities for cross-analysis"]
        )

    def to_json(self) -> str:
        """Export analysis as JSON"""
        if not self.analysis:
            return "{}"

        return json.dumps({
            "relative_rankings": self.analysis.rankings,
            "valuation_comparison": {
                e.ticker: {
                    "P/E": e.pe_ratio,
                    "EV/EBITDA": e.ev_ebitda,
                    "P/S": e.ps_ratio,
                    "P/B": e.pb_ratio,
                    "upside": f"{e.upside_pct:.1f}%" if e.upside_pct else "N/A",
                    "relative": self._get_relative_value(e)
                }
                for e in self.analysis.equities
            },
            "correlation_analysis": self.analysis.correlation_analysis,
            "portfolio_recommendations": self.analysis.portfolio_recommendations,
            "key_insights": self.analysis.key_insights
        }, indent=2)

    def _get_relative_value(self, e: EquityMetrics) -> str:
        """Determine relative value label"""
        if e.upside_pct is None:
            return "unknown"
        if e.upside_pct >= 25:
            return "cheap"
        elif e.upside_pct >= 0:
            return "fair"
        else:
            return "expensive"
