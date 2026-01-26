"""
Debate Moderator Agent - Manages multi-agent debates for equity valuation

Responsibilities:
- Spawn Bull, Bear, Critic, and specialized debate agents
- Enforce debate rules and time limits
- Ensure productive discourse
- Extract consensus and disagreements
- Trigger synthesis when ready
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext, AgentMessage


class DebateModerator(SpawnableAgent):
    """
    Manages multi-agent debates for equity valuation (Tier 1).

    The DebateModerator spawns debate participants and orchestrates
    a structured debate process to arrive at a consensus valuation.

    Debate Phases:
    - Rounds 1-3: INITIAL_POSITIONS - State initial positions
    - Rounds 4-7: CROSS_EXAMINATION - Challenge and defend
    - Rounds 8-10: REFINEMENT - Refine based on critiques

    Usage:
        moderator = await supervisor.spawn_child(
            DebateModerator, "moderator_6682HK",
            config={'ticker': '6682 HK', 'rounds': 10}
        )
        synthesis = await moderator.run_full_debate(context)
    """

    # Debate phase definitions
    PHASES = {
        (1, 3): {
            'name': 'INITIAL_POSITIONS',
            'instruction': 'State your initial position with clear evidence and reasoning.'
        },
        (4, 7): {
            'name': 'CROSS_EXAMINATION',
            'instruction': 'Challenge other positions and defend your own. Be specific in critiques.'
        },
        (8, 10): {
            'name': 'REFINEMENT',
            'instruction': 'Refine your position based on valid critiques. Acknowledge strong counterarguments.'
        }
    }

    def __init__(
        self,
        ai_provider,
        parent_id: str = None,
        tier: int = 1,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role="debate_moderator",
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        # Configuration
        self.ticker = config.get('ticker', '') if config else ''
        self.debate_rounds = config.get('rounds', 10) if config else 10

        # Debate state
        self.current_round = 0
        self.debate_agents: Dict[str, str] = {}  # role -> agent_id
        self.debate_log: List[Dict] = []
        self.disagreements: List[str] = []
        self.consensus_points: List[str] = []

        # Participant configuration
        self.use_devils_advocate = config.get('use_devils_advocate', True) if config else True

    def _get_system_prompt(self) -> str:
        return """You are a Debate Moderator overseeing multi-agent equity debates.

Your role:
1. Ensure productive debate with clear, evidence-based arguments
2. Enforce time limits and round structure
3. Identify key disagreements and areas of consensus
4. Request clarification when arguments are unclear
5. Decide when synthesis should begin

Guidelines:
- Maintain fairness between bull and bear cases
- Push for specific numbers and evidence
- Challenge weak arguments from any side
- Extract actionable insights from debates
- Summarize key points between rounds

Remember: The goal is truth-seeking, not winning."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Main analysis dispatch"""
        action = kwargs.get('action', 'moderate')

        if action == 'start_debate':
            return await self.start_debate(context)
        elif action == 'run_round':
            return json.dumps(await self.run_round(context))
        elif action == 'synthesize':
            return await self.synthesize(context)
        elif action == 'get_insights':
            return await self._extract_insights_prompt()
        else:
            return await self._get_debate_status()

    # ==========================================
    # Debate Lifecycle
    # ==========================================

    async def start_debate(self, context: ResearchContext) -> str:
        """
        Initialize debate with spawned agents.

        Spawns:
        - Bull Agent (optimistic case)
        - Bear Agent (pessimistic case)
        - Critic Agent (challenges assumptions)
        - Devil's Advocate (optional, challenges consensus)

        Returns:
            Status message
        """
        from agents.workers import (
            EnhancedBullAgent,
            EnhancedBearAgent,
            EnhancedCriticAgent,
            DevilsAdvocateAgent
        )

        self.set_task(f"Starting debate for {self.ticker}")

        # Spawn core debate participants
        self.debate_agents['bull'] = (await self.spawn_child(
            EnhancedBullAgent,
            f"bull_{self.ticker.replace(' ', '_').replace('.', '_')}",
            config={'ticker': self.ticker}
        )).agent_id

        self.debate_agents['bear'] = (await self.spawn_child(
            EnhancedBearAgent,
            f"bear_{self.ticker.replace(' ', '_').replace('.', '_')}",
            config={'ticker': self.ticker}
        )).agent_id

        self.debate_agents['critic'] = (await self.spawn_child(
            EnhancedCriticAgent,
            f"critic_{self.ticker.replace(' ', '_').replace('.', '_')}",
            config={'ticker': self.ticker}
        )).agent_id

        # Optionally spawn devil's advocate
        if self.use_devils_advocate:
            self.debate_agents['devil'] = (await self.spawn_child(
                DevilsAdvocateAgent,
                f"devil_{self.ticker.replace(' ', '_').replace('.', '_')}",
                config={'ticker': self.ticker}
            )).agent_id

        self.current_round = 0

        return f"Debate started for {self.ticker} with {len(self.debate_agents)} participants"

    async def run_round(self, context: ResearchContext) -> Dict[str, str]:
        """
        Run a single debate round.

        Returns:
            Dict mapping role to their argument
        """
        self.current_round += 1
        self.heartbeat()

        # Determine phase
        phase_info = self._get_phase_info()

        self.set_task(f"{self.ticker}: Debate round {self.current_round}/{self.debate_rounds} - {phase_info['name']}")

        # Build context for this round
        round_context = self._build_round_context(context, phase_info)

        # Get responses from all agents in parallel
        tasks = []
        roles = []

        for role, agent_id in self.debate_agents.items():
            agent = self.get_child(agent_id)
            if agent:
                tasks.append(self._get_agent_argument(agent, context, round_context, role))
                roles.append(role)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        round_results = {}
        for role, result in zip(roles, results):
            if isinstance(result, str):
                round_results[role] = result
                self.debate_log.append({
                    'round': self.current_round,
                    'phase': phase_info['name'],
                    'role': role,
                    'content': result,
                    'timestamp': datetime.now().isoformat()
                })
            elif isinstance(result, Exception):
                round_results[role] = f"[Error: {str(result)}]"

        # Extract insights from this round
        await self._extract_round_insights(round_results)

        return round_results

    async def run_full_debate(self, context: ResearchContext) -> str:
        """
        Run complete debate from start to synthesis.

        Args:
            context: Research context with initial analysis

        Returns:
            Final synthesis text
        """
        # Start debate
        await self.start_debate(context)

        # Run all rounds
        for _ in range(self.debate_rounds):
            await self.run_round(context)
            self.heartbeat()

            # Small delay between rounds
            await asyncio.sleep(0.5)

        # Synthesize
        return await self.synthesize(context)

    async def synthesize(self, context: ResearchContext) -> str:
        """
        Synthesize debate into final conclusions.

        Spawns a synthesizer agent to combine all debate insights.
        """
        from agents.workers import EnhancedSynthesizerAgent

        self.set_task(f"{self.ticker}: Synthesizing debate results")

        # Spawn synthesizer with debate context
        synthesizer = await self.spawn_child(
            EnhancedSynthesizerAgent,
            f"synthesizer_{self.ticker.replace(' ', '_').replace('.', '_')}",
            config={
                'ticker': self.ticker,
                'debate_log': self.debate_log,
                'disagreements': self.disagreements,
                'consensus': self.consensus_points
            }
        )

        try:
            # Build synthesis prompt with full debate context
            synthesis_context = self._build_synthesis_context(context)
            result = await synthesizer.analyze(context, synthesis_context=synthesis_context)

            # Terminate debate agents
            for agent_id in self.debate_agents.values():
                await self.terminate_child(agent_id)

            return result

        finally:
            # Always terminate synthesizer
            await self.terminate_child(synthesizer.agent_id)

    # ==========================================
    # Helper Methods
    # ==========================================

    def _get_phase_info(self) -> Dict:
        """Get current phase based on round number"""
        for (start, end), info in self.PHASES.items():
            if start <= self.current_round <= end:
                return info
        return {'name': 'UNKNOWN', 'instruction': 'Continue the debate.'}

    def _build_round_context(self, context: ResearchContext, phase_info: Dict) -> str:
        """Build context string for debate round"""
        # Get recent debate history
        recent_history = self.debate_log[-6:] if self.debate_log else []
        history_text = "\n".join([
            f"[Round {entry['round']} - {entry['role'].upper()}]: {entry['content'][:500]}..."
            for entry in recent_history
        ])

        return f"""DEBATE ROUND {self.current_round}/{self.debate_rounds}
PHASE: {phase_info['name']}
INSTRUCTION: {phase_info['instruction']}

COMPANY: {context.company_name} ({context.ticker})
SECTOR: {context.sector} / {context.industry}

KEY POINTS FROM ANALYSIS:
- Industry: {context.industry_analysis[:300]}...
- Company: {context.company_analysis[:300]}...

RECENT DEBATE HISTORY:
{history_text}

CURRENT DISAGREEMENTS: {self.disagreements[-3:] if self.disagreements else 'None identified yet'}
CONSENSUS POINTS: {self.consensus_points[-3:] if self.consensus_points else 'None identified yet'}
"""

    async def _get_agent_argument(
        self,
        agent: SpawnableAgent,
        context: ResearchContext,
        round_context: str,
        role: str
    ) -> str:
        """Get argument from a debate agent"""
        # Build role-specific prompt
        role_prompts = {
            'bull': "Present the BULL CASE. Focus on upside potential, catalysts, and reasons for optimism.",
            'bear': "Present the BEAR CASE. Focus on risks, challenges, and reasons for caution.",
            'critic': "CRITIQUE the arguments. Find flaws in reasoning, question assumptions, demand evidence.",
            'devil': "Challenge CONSENSUS. If everyone agrees, disagree. Find the overlooked risk or opportunity."
        }

        prompt = f"""{round_context}

YOUR ROLE: {role_prompts.get(role, 'Contribute to the debate.')}

Provide your argument (500-800 words). Be specific with:
- Key thesis point
- Supporting evidence
- Response to counter-arguments
- Confidence level and key assumption"""

        return await agent.respond(prompt)

    def _build_synthesis_context(self, context: ResearchContext) -> str:
        """Build context for synthesis"""
        # Summarize all debate entries by role
        by_role = {}
        for entry in self.debate_log:
            role = entry['role']
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(entry['content'][:400])

        role_summaries = ""
        for role, entries in by_role.items():
            role_summaries += f"\n{role.upper()} ARGUMENTS ({len(entries)} entries):\n"
            for i, entry in enumerate(entries[-3:], 1):  # Last 3 from each
                role_summaries += f"  {i}. {entry}...\n"

        return f"""SYNTHESIS TASK FOR {context.ticker}

{role_summaries}

KEY DISAGREEMENTS:
{json.dumps(self.disagreements, indent=2)}

CONSENSUS POINTS:
{json.dumps(self.consensus_points, indent=2)}

SYNTHESIZE:
1. Probability-weighted target price
2. Key assumptions and scenarios
3. Main risks and catalysts
4. Confidence level
5. Where bull and bear found common ground"""

    # ==========================================
    # Insight Extraction
    # ==========================================

    async def _extract_round_insights(self, round_results: Dict[str, str]):
        """Extract disagreements and consensus from round"""
        # Use AI to analyze the round
        combined = "\n\n".join([
            f"[{role.upper()}]: {text[:600]}"
            for role, text in round_results.items()
        ])

        prompt = f"""Analyze these debate arguments from round {self.current_round}:

{combined}

Extract:
1. Key disagreements (where bull/bear clearly differ)
2. Consensus points (where multiple parties agree)
3. Unresolved questions

Format as JSON:
{{"disagreements": ["point1", "point2"], "consensus": ["point1"], "questions": ["q1"]}}"""

        try:
            response = await self.respond(prompt)
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                insights = json.loads(json_match.group())
                self.disagreements.extend(insights.get('disagreements', []))
                self.consensus_points.extend(insights.get('consensus', []))
        except (json.JSONDecodeError, Exception):
            pass  # Silently fail on parse errors

    async def _extract_insights_prompt(self) -> str:
        """Get AI-generated insights summary"""
        prompt = f"""Summarize the key insights from this debate.

Total Rounds: {len(self.debate_log)}
Participants: {list(self.debate_agents.keys())}

Disagreements Found:
{json.dumps(self.disagreements, indent=2)}

Consensus Points:
{json.dumps(self.consensus_points, indent=2)}

Provide:
1. Most important unresolved disagreements
2. Strongest consensus points
3. Quality of debate discourse
4. Recommendations for synthesis"""

        return await self.respond(prompt)

    # ==========================================
    # Status
    # ==========================================

    async def _get_debate_status(self) -> str:
        """Get debate status report"""
        return json.dumps({
            'ticker': self.ticker,
            'current_round': self.current_round,
            'total_rounds': self.debate_rounds,
            'phase': self._get_phase_info()['name'],
            'participants': list(self.debate_agents.keys()),
            'debate_entries': len(self.debate_log),
            'disagreements': len(self.disagreements),
            'consensus_points': len(self.consensus_points)
        }, indent=2)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Initialize on activation"""
        self.set_task(f"Moderating debate for {self.ticker}")

    async def _graceful_shutdown(self):
        """Graceful shutdown - terminate all debate agents"""
        for agent_id in list(self.debate_agents.values()):
            await self.terminate_child(agent_id, graceful=True)
