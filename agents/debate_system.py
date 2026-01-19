"""
Debate System - Orchestrates multi-agent debates for equity research
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, ResearchContext, AgentMessage
from .analyst_agent import AnalystAgent, BullAgent, BearAgent
from .critic_agent import CriticAgent, SynthesizerAgent
from .ai_providers import AIProviderManager


class DebateSystem:
    """Orchestrates multi-agent debates for thorough equity research"""

    def __init__(self, ai_manager: AIProviderManager, debate_rounds: int = 10):
        self.ai_manager = ai_manager
        self.debate_rounds = debate_rounds

        # Initialize agents with different AI providers for diversity
        providers = ai_manager.get_all_providers()

        # Assign different providers to different agents for diverse perspectives
        self.analyst = AnalystAgent(providers[0] if providers else None)
        self.bull = BullAgent(providers[1 % len(providers)] if providers else None)
        self.bear = BearAgent(providers[2 % len(providers)] if providers else None)
        self.critic = CriticAgent(providers[3 % len(providers)] if providers else None)
        self.synthesizer = SynthesizerAgent(providers[0] if providers else None)

    async def run_full_research(self, context: ResearchContext,
                                 progress_callback=None) -> ResearchContext:
        """Run complete research process with multi-agent debate"""

        # Phase 1: Initial Research
        if progress_callback:
            progress_callback(f"Phase 1: Initial research for {context.ticker}")

        await self._phase1_initial_research(context)

        # Phase 2: Multi-agent debate (10 rounds)
        if progress_callback:
            progress_callback(f"Phase 2: Running {self.debate_rounds} debate rounds")

        await self._phase2_debate(context, progress_callback)

        # Phase 3: External research comparison
        if progress_callback:
            progress_callback("Phase 3: Comparing with external research")

        await self._phase3_external_research(context)

        # Phase 4: Final synthesis
        if progress_callback:
            progress_callback("Phase 4: Final synthesis and valuation")

        await self._phase4_synthesis(context)

        return context

    async def _phase1_initial_research(self, context: ResearchContext):
        """Phase 1: Analyst performs initial research"""

        # Run industry, company, and governance analysis in parallel
        industry_task = self.analyst.analyze(context, analysis_type="industry")

        industry_result = await industry_task
        context.industry_analysis = industry_result
        context.debate_log.append(self.analyst.create_message(
            f"Industry Analysis:\n{industry_result}",
            {"phase": 1, "type": "industry"}
        ))

        # Now company analysis (depends on industry)
        company_result = await self.analyst.analyze(context, analysis_type="company")
        context.company_analysis = company_result
        context.debate_log.append(self.analyst.create_message(
            f"Company Analysis:\n{company_result}",
            {"phase": 1, "type": "company"}
        ))

        # Governance analysis
        governance_result = await self.analyst.analyze(context, analysis_type="governance")
        context.governance_analysis = governance_result
        context.debate_log.append(self.analyst.create_message(
            f"Governance Analysis:\n{governance_result}",
            {"phase": 1, "type": "governance"}
        ))

        # Initial DCF
        dcf_result = await self.analyst.analyze(context, analysis_type="dcf")
        context.debate_log.append(self.analyst.create_message(
            f"Initial DCF Valuation:\n{dcf_result}",
            {"phase": 1, "type": "dcf"}
        ))

    async def _phase2_debate(self, context: ResearchContext, progress_callback=None):
        """Phase 2: Multi-agent debate for 10 rounds"""

        for round_num in range(1, self.debate_rounds + 1):
            if progress_callback:
                progress_callback(f"  Debate round {round_num}/{self.debate_rounds}")

            # Get the latest analyst/synthesizer view
            latest_view = self._get_latest_view(context)

            # Run bull and bear challenges in parallel
            bull_task = self.bull.analyze(context, analyst_view=latest_view)
            bear_task = self.bear.analyze(context, analyst_view=latest_view)

            bull_result, bear_result = await asyncio.gather(bull_task, bear_task)

            context.debate_log.append(self.bull.create_message(
                bull_result, {"round": round_num}
            ))
            context.debate_log.append(self.bear.create_message(
                bear_result, {"round": round_num}
            ))

            # Critic evaluates the debate
            combined_view = f"Bull Case:\n{bull_result}\n\nBear Case:\n{bear_result}"
            critic_result = await self.critic.analyze(
                context,
                analysis=combined_view,
                focus="assumptions"
            )
            context.debate_log.append(self.critic.create_message(
                critic_result, {"round": round_num}
            ))

            # Every 3 rounds, synthesizer provides interim summary
            if round_num % 3 == 0:
                interim_synthesis = await self.synthesizer.analyze(context)
                context.debate_log.append(self.synthesizer.create_message(
                    f"Interim Synthesis (Round {round_num}):\n{interim_synthesis}",
                    {"round": round_num, "type": "interim"}
                ))

    async def _phase3_external_research(self, context: ResearchContext):
        """Phase 3: Compare with external research sources"""

        prompt = f"""For {context.company_name} ({context.ticker}), search for and analyze:

1. Recent analyst reports and their price targets
2. Key research from major investment banks
3. Industry reports and market analysis
4. News and recent developments

Compare these external views with our analysis:
{self._get_latest_view(context)[:2000]}

Identify:
- Key differences in assumptions
- Different methodologies used
- Unique insights from external sources
- How our view should be adjusted based on external research"""

        external_result = await self.analyst.respond(prompt)
        context.debate_log.append(self.analyst.create_message(
            f"External Research Comparison:\n{external_result}",
            {"phase": 3, "type": "external"}
        ))

    async def _phase4_synthesis(self, context: ResearchContext):
        """Phase 4: Final synthesis and valuation table"""

        # Final synthesis
        final_synthesis = await self.synthesizer.analyze(context)
        context.debate_log.append(self.synthesizer.create_message(
            f"Final Synthesis:\n{final_synthesis}",
            {"phase": 4, "type": "final"}
        ))

        # Generate final valuation table
        final_table = await self.synthesizer.create_final_table(context)
        context.scenario_analysis = final_table

        # Extract intrinsic values
        if "intrinsic_values" in final_table:
            context.intrinsic_values = final_table["intrinsic_values"]

    def _get_latest_view(self, context: ResearchContext) -> str:
        """Get the most recent comprehensive view from debate log"""
        # Look for the latest synthesizer or analyst message
        for msg in reversed(context.debate_log):
            if msg.role in ["synthesizer", "analyst"]:
                return msg.content

        # Fallback to combined initial analysis
        return f"""
Industry: {context.industry_analysis[:1000]}
Company: {context.company_analysis[:1000]}
Governance: {context.governance_analysis[:500]}
"""


class ParallelDebateRunner:
    """Runs debates for multiple equities in parallel"""

    def __init__(self, ai_manager: AIProviderManager, max_concurrent: int = 3):
        self.ai_manager = ai_manager
        self.max_concurrent = max_concurrent

    async def run_all(self, equities: Dict[str, Dict[str, str]],
                      progress_callback=None) -> Dict[str, ResearchContext]:
        """Run research for all equities with controlled concurrency"""

        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def research_with_semaphore(ticker: str, info: Dict[str, str]):
            async with semaphore:
                context = ResearchContext(
                    ticker=ticker,
                    company_name=info["name"],
                    sector=info["sector"],
                    industry=info["industry"]
                )

                debate_system = DebateSystem(self.ai_manager)

                def callback(msg):
                    if progress_callback:
                        progress_callback(f"[{ticker}] {msg}")

                return await debate_system.run_full_research(context, callback)

        # Create tasks for all equities
        tasks = [
            research_with_semaphore(ticker, info)
            for ticker, info in equities.items()
        ]

        # Run all with gather
        contexts = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results
        for (ticker, _), ctx in zip(equities.items(), contexts):
            if isinstance(ctx, Exception):
                print(f"Error researching {ticker}: {ctx}")
            else:
                results[ticker] = ctx

        return results
