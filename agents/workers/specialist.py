"""
Specialist Agent - Domain-specific expertise for industry deep dives

Dynamically spawned by analysts when domain expertise is needed.
Auto-detects appropriate specialization from sector/industry.
"""

from typing import Dict, Any, Optional
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class SpecialistAgent(SpawnableAgent):
    """
    Domain-specific specialist agent (Tier 2+).

    Can be specialized for:
    - Biotech/Pharma (clinical trials, FDA)
    - Technology (TAM/SAM, network effects)
    - Financials (banking regulations, capital ratios)
    - Real Estate (cap rates, occupancy)
    - Energy (commodity cycles, ESG)

    Usage:
        specialist = await analyst.spawn_child(
            SpecialistAgent, "specialist_biotech",
            config={'specialization': 'biotech', 'ticker': 'LEGN US'}
        )
        insight = await specialist.analyze(context)
    """

    # Specialization configurations
    SPECIALIZATIONS = {
        'biotech': {
            'prompt': """You are a BIOTECH equity specialist with deep knowledge of:
- Clinical trial phases, endpoints, and success rates
- FDA approval processes, timelines, and precedents
- Drug pricing, market access, and reimbursement
- Pipeline valuation methodologies (rNPV)
- Competitive landscape in therapeutics
- Patent cliffs and IP considerations
- Manufacturing and supply chain for biologics

You understand that biotech valuations are highly binary and
dependent on clinical data. You know how to interpret trial
results and regulatory signals.""",
            'keywords': ['pharma', 'biotech', 'drug', 'clinical', 'fda', 'therapeutic', 'biopharma', 'medicine']
        },
        'technology': {
            'prompt': """You are a TECHNOLOGY equity specialist with expertise in:
- TAM/SAM/SOM analysis and market sizing
- Network effects and platform economics
- Unit economics: CAC, LTV, payback period
- Technology adoption curves (S-curve, chasm)
- Competitive moats in software and hardware
- SaaS metrics: ARR, churn, expansion revenue
- Cloud economics and infrastructure scaling
- AI/ML capabilities and differentiation

You understand that tech valuations depend on growth trajectories
and the durability of competitive advantages.""",
            'keywords': ['tech', 'software', 'ai', 'cloud', 'platform', 'saas', 'internet', 'semiconductor', 'digital']
        },
        'financials': {
            'prompt': """You are a FINANCIALS sector specialist with expertise in:
- Bank capital adequacy (Basel III/IV requirements)
- Net interest margin analysis and interest rate sensitivity
- Credit quality assessment and provisioning
- Insurance reserve adequacy and combined ratios
- Asset management fee structures and AUM dynamics
- Regulatory capital requirements and stress testing
- Fee income diversification
- Cost efficiency and operating leverage

You understand that financial company valuations depend heavily
on credit cycles, interest rates, and regulatory environment.""",
            'keywords': ['bank', 'insurance', 'financial', 'lending', 'asset management', 'fintech', 'exchange']
        },
        'energy': {
            'prompt': """You are an ENERGY sector specialist with expertise in:
- Commodity price cycles and hedging strategies
- Renewable vs. fossil fuel transition dynamics
- ESG considerations and carbon credits
- Capital intensity and returns on invested capital
- Regulatory and subsidy impacts
- Reserve replacement and decline curves (O&G)
- Power purchase agreements (renewables)
- Grid economics and energy storage

You understand that energy valuations are highly cyclical and
dependent on commodity prices and energy transition dynamics.""",
            'keywords': ['energy', 'power', 'utility', 'solar', 'wind', 'nuclear', 'oil', 'gas', 'hydro', 'renewable']
        },
        'real_estate': {
            'prompt': """You are a REAL ESTATE specialist with expertise in:
- Cap rate analysis and property valuation
- NOI projections and same-store growth
- Occupancy trends and lease structures
- Development pipeline and construction costs
- Interest rate sensitivity for REITs
- Property type dynamics (office, retail, industrial, residential)
- Geographic concentration risks
- Debt maturity profiles and refinancing risk

You understand that real estate valuations depend on location,
property type cycles, and interest rate environment.""",
            'keywords': ['real estate', 'reit', 'property', 'landlord', 'development', 'housing']
        },
        'consumer': {
            'prompt': """You are a CONSUMER sector specialist with expertise in:
- Brand equity valuation and consumer loyalty
- Retail economics: same-store sales, inventory turns
- E-commerce vs. brick-and-mortar dynamics
- Consumer spending trends and demographics
- Private label threat and pricing power
- Channel strategy and distribution
- Marketing efficiency and brand building
- Seasonality and cyclicality

You understand that consumer company valuations depend on
brand strength, distribution, and consumer behavior trends.""",
            'keywords': ['consumer', 'retail', 'restaurant', 'food', 'beverage', 'apparel', 'luxury', 'e-commerce']
        },
        'healthcare': {
            'prompt': """You are a HEALTHCARE sector specialist with expertise in:
- Healthcare delivery economics
- Payer mix and reimbursement trends
- Hospital capacity and utilization
- Medical device adoption cycles
- Healthcare IT and interoperability
- Regulatory environment (CMS, state regulations)
- Value-based care transition
- Labor costs and staffing challenges

You understand that healthcare valuations depend on
reimbursement rates, regulatory environment, and demographic trends.""",
            'keywords': ['healthcare', 'hospital', 'medical', 'health', 'diagnostic', 'equipment']
        },
        'telecom': {
            'prompt': """You are a TELECOM sector specialist with expertise in:
- Spectrum valuation and licensing
- Network economics and CapEx cycles
- ARPU trends and churn analysis
- 5G deployment and monetization
- Competitive dynamics and pricing pressure
- Tower economics and infrastructure sharing
- Content and bundling strategies
- Regulatory environment

You understand that telecom valuations depend on
spectrum assets, network quality, and competitive intensity.""",
            'keywords': ['telecom', 'wireless', 'mobile', 'carrier', 'tower', '5g', 'broadband']
        }
    }

    def __init__(
        self,
        ai_provider,
        parent_id: str = None,
        tier: int = 3,  # Spawned by tier 2 workers
        config: Optional[Dict] = None
    ):
        specialization = config.get('specialization', 'general') if config else 'general'

        super().__init__(
            ai_provider=ai_provider,
            role=f"specialist_{specialization}",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        self.specialization = specialization
        self.spec_config = self.SPECIALIZATIONS.get(specialization, {})
        self.ticker = config.get('ticker') if config else None

    def _get_system_prompt(self) -> str:
        base = self.spec_config.get('prompt', 'You are a domain specialist providing sector expertise.')
        return base + """

Apply your specialized knowledge to:
1. Identify sector-specific risks others might miss
2. Challenge assumptions using domain expertise
3. Provide industry-specific valuation considerations
4. Reference relevant precedents and comparables
5. Highlight key metrics unique to this industry

Be specific and quantitative. Your expertise should add unique value
that a generalist analyst would miss."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """
        Provide specialized analysis.

        Args:
            context: Research context

        Returns:
            Domain-specific analysis
        """
        self.heartbeat()
        self.set_task(f"{self.ticker}: {self.specialization} specialist analysis")

        prompt = f"""Provide SPECIALIST ANALYSIS for {context.company_name} ({context.ticker}).

Industry: {context.industry}
Sector: {context.sector}

Your specialization: {self.specialization.upper()}

Industry analysis (if available):
{context.industry_analysis[:1000] if context.industry_analysis else 'Not yet analyzed'}

Company analysis (if available):
{context.company_analysis[:1000] if context.company_analysis else 'Not yet analyzed'}

As a {self.specialization} specialist, provide:

1. SECTOR-SPECIFIC FACTORS
   What industry-specific factors are critical for this company?
   What might generalist analysts miss?

2. KEY METRICS
   What are the most important metrics for this industry?
   How does this company compare on these metrics?

3. COMPARABLE ANALYSIS
   What are the best comparables?
   How should this company trade relative to peers?

4. SECTOR-SPECIFIC RISKS
   What risks are unique to this industry?
   How exposed is this company?

5. VALUATION METHODOLOGY
   What's the right way to value companies in this sector?
   Any adjustments needed for this specific company?

6. INDUSTRY OUTLOOK
   Where is this industry headed?
   How does that affect this company's positioning?

Be specific and quantitative. Provide numbers where possible."""

        result = await self.respond(prompt)
        self.complete_task()
        return result

    async def analyze_specific_metric(self, context: ResearchContext, metric: str) -> str:
        """
        Deep dive on a specific industry metric.

        Args:
            context: Research context
            metric: Specific metric to analyze

        Returns:
            Detailed metric analysis
        """
        self.heartbeat()

        prompt = f"""Analyze the metric "{metric}" for {context.company_name} ({context.ticker}).

Your specialization: {self.specialization.upper()}

Provide:
1. Definition and importance in this industry
2. How to calculate/measure it
3. Industry benchmarks
4. This company's performance
5. Trend and outlook
6. Red flags to watch for"""

        return await self.respond(prompt)

    @classmethod
    def detect_specialization(cls, industry: str, sector: str) -> str:
        """
        Auto-detect appropriate specialization based on sector/industry.

        Args:
            industry: Industry classification
            sector: Sector classification

        Returns:
            Specialization key (e.g., 'biotech', 'technology', 'general')
        """
        combined = f"{industry} {sector}".lower()

        for spec_name, spec_config in cls.SPECIALIZATIONS.items():
            keywords = spec_config.get('keywords', [])
            if any(kw in combined for kw in keywords):
                return spec_name

        return 'general'

    @classmethod
    def get_available_specializations(cls) -> list:
        """Get list of available specializations"""
        return list(cls.SPECIALIZATIONS.keys())

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Log activation"""
        self.set_task(f"{self.specialization} specialist ready for {self.ticker or 'assignment'}")
