"""
Agent Executor - Bridges YAML workflow nodes to real Agent classes.

This module enables the hybrid approach:
- YAML defines workflow structure (what runs, in what order)
- Agent classes handle execution (with spawning, lifecycle, specialists)

Benefits:
- Leverages existing SpawnableAgent infrastructure
- Dynamic specialist spawning based on context
- Lifecycle management and health monitoring
- Error recovery and retry logic
"""

import asyncio
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from datetime import datetime

from .node_executor import Message, NodeConfig

# Import AI providers
try:
    from agents.ai_providers import (
        OpenAIProvider, GeminiProvider, GrokProvider, QwenProvider
    )
    AI_PROVIDERS_AVAILABLE = True
except ImportError as e:
    AI_PROVIDERS_AVAILABLE = False
    OpenAIProvider = None
    GeminiProvider = None
    GrokProvider = None
    QwenProvider = None
    print(f"[WARNING] AI providers not available: {e}")

# Import agent classes
try:
    from agents.core.spawnable_agent import SpawnableAgent
    from agents.core.agent_registry import AgentRegistry

    # Import ResearchContext from base_agent (it's a dataclass, not deprecated)
    from agents.base_agent import ResearchContext, AgentMessage

    # Workers
    from agents.workers.enhanced_workers import (
        EnhancedAnalystAgent,
        EnhancedBullAgent,
        EnhancedBearAgent,
        EnhancedCriticAgent,
        EnhancedSynthesizerAgent
    )
    from agents.workers.devils_advocate import DevilsAdvocateAgent
    from agents.workers.specialist import SpecialistAgent

    # Supervisors
    from agents.supervisors.research_supervisor import ResearchSupervisor
    from agents.supervisors.debate_moderator import DebateModerator

    # Goalkeepers
    from agents.goalkeepers.fact_checker_gate import FactCheckerGate
    from agents.goalkeepers.logic_auditor import LogicAuditorAgent
    from agents.goalkeepers.consensus_validator import ConsensusValidatorAgent

    # Specialized
    from agents.specialized.market_data_agent import MarketDataAgent
    from agents.specialized.validation_agent import ValidationAgent
    from agents.specialized.dcf_agent import DCFModelingAgent

    # Oversight
    from agents.oversight.dcf_quality_controller import DCFQualityController

    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    # Placeholders when not available
    SpawnableAgent = None
    AgentRegistry = None
    ResearchContext = None
    AgentMessage = None
    EnhancedAnalystAgent = None
    EnhancedBullAgent = None
    EnhancedBearAgent = None
    EnhancedCriticAgent = None
    EnhancedSynthesizerAgent = None
    DevilsAdvocateAgent = None
    SpecialistAgent = None
    ResearchSupervisor = None
    DebateModerator = None
    FactCheckerGate = None
    LogicAuditorAgent = None
    ConsensusValidatorAgent = None
    MarketDataAgent = None
    ValidationAgent = None
    DCFModelingAgent = None
    DCFQualityController = None
    print(f"[WARNING] Agent classes not fully available: {e}")


@dataclass
class AgentMapping:
    """Maps a YAML node to an agent class with configuration"""
    agent_class: Optional[Type]  # Type of SpawnableAgent when available
    tier: int
    config: Dict[str, Any]
    analysis_type: Optional[str] = None  # For analyst agents
    provider_preference: str = "openai"  # Preferred AI provider


# Node ID to Agent Class mapping
NODE_TO_AGENT: Dict[str, AgentMapping] = {
    # === SUPERVISORS (Tier 1) ===
    "Research Supervisor": AgentMapping(
        agent_class=ResearchSupervisor if AGENTS_AVAILABLE else None,
        tier=1,
        config={"role": "supervisor"},
        provider_preference="openai"
    ),
    "Research Supervisor Final Sign-off": AgentMapping(
        agent_class=ResearchSupervisor if AGENTS_AVAILABLE else None,
        tier=1,
        config={"role": "final_reviewer"},
        provider_preference="openai"
    ),
    "Debate Moderator": AgentMapping(
        agent_class=DebateModerator if AGENTS_AVAILABLE else None,
        tier=1,
        config={"role": "moderator"},
        provider_preference="openai"
    ),

    # === RESEARCH WORKERS (Tier 2) ===
    # Note: MarketDataAgent has a different interface, use NodeExecutor instead
    # "Market Data Collector" - fallback to NodeExecutor (not in mapping)
    "Industry Deep Dive": AgentMapping(
        agent_class=EnhancedAnalystAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "analyst"},
        analysis_type="industry",
        provider_preference="openai"
    ),
    "Company Deep Dive": AgentMapping(
        agent_class=EnhancedAnalystAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "analyst"},
        analysis_type="company",
        provider_preference="qwen"
    ),
    # Note: ValidationAgent is abstract, use NodeExecutor instead
    # "Data Verifier" - fallback to NodeExecutor (not in mapping)

    # === DEBATE WORKERS (Tier 2) ===
    "Bull Advocate R1": AgentMapping(
        agent_class=EnhancedBullAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "bull", "round": 1},
        provider_preference="grok"  # xAI for optimistic view
    ),
    "Bull Advocate R2": AgentMapping(
        agent_class=EnhancedBullAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "bull", "round": 2},
        provider_preference="grok"
    ),
    "Bear Advocate R1": AgentMapping(
        agent_class=EnhancedBearAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "bear", "round": 1},
        provider_preference="qwen"  # Qwen for risk-focused
    ),
    "Bear Advocate R2": AgentMapping(
        agent_class=EnhancedBearAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "bear", "round": 2},
        provider_preference="qwen"
    ),
    "Devils Advocate": AgentMapping(
        agent_class=DevilsAdvocateAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "devils_advocate"},
        provider_preference="openai"
    ),
    "Debate Critic": AgentMapping(
        agent_class=EnhancedCriticAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "critic"},
        provider_preference="openai"
    ),

    # === VALUATION WORKERS (Tier 2) ===
    "Dot Connector": AgentMapping(
        agent_class=EnhancedAnalystAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "dot_connector"},
        analysis_type="dcf",
        provider_preference="openai"
    ),

    # === GOALKEEPERS (Tier 3) ===
    "Data Checkpoint": AgentMapping(
        agent_class=FactCheckerGate if AGENTS_AVAILABLE else None,
        tier=3,
        config={"role": "data_gate"},
        provider_preference="openai"
    ),
    # Note: Pre-Model Validator uses abstract class, use NodeExecutor instead
    # "Pre-Model Validator" - fallback to NodeExecutor (not in mapping)
    "DCF Validator": AgentMapping(
        agent_class=DCFQualityController if AGENTS_AVAILABLE else None,
        tier=3,
        config={"role": "dcf_validator"},
        provider_preference="openai"
    ),
    "Data Verification Gate": AgentMapping(
        agent_class=FactCheckerGate if AGENTS_AVAILABLE else None,
        tier=3,
        config={"role": "data_verification"},
        provider_preference="openai"
    ),
    "Logic Verification Gate": AgentMapping(
        agent_class=LogicAuditorAgent if AGENTS_AVAILABLE else None,
        tier=3,
        config={"role": "logic_verification"},
        provider_preference="openai"
    ),
    "Quality Supervisor": AgentMapping(
        agent_class=ConsensusValidatorAgent if AGENTS_AVAILABLE else None,
        tier=3,
        config={"role": "quality_supervisor"},
        provider_preference="openai"
    ),

    # === SYNTHESIS (Tier 2) ===
    "Synthesizer": AgentMapping(
        agent_class=EnhancedSynthesizerAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "synthesizer"},
        provider_preference="openai"
    ),
    "Birds Eye Reviewer": AgentMapping(
        agent_class=EnhancedCriticAgent if AGENTS_AVAILABLE else None,
        tier=2,
        config={"role": "birds_eye"},
        provider_preference="openai"
    ),
}


def get_ai_provider(provider_name: str, api_keys: Dict[str, str]):
    """Get AI provider instance by name"""
    if not AI_PROVIDERS_AVAILABLE:
        return None

    provider_map = {
        "openai": ("OpenAI", "OPENAI_API_KEY", OpenAIProvider),
        "gpt": ("OpenAI", "OPENAI_API_KEY", OpenAIProvider),
        "gemini": ("Gemini", "GOOGLE_API_KEY", GeminiProvider),
        "google": ("Gemini", "GOOGLE_API_KEY", GeminiProvider),
        "grok": ("Grok", "XAI_API_KEY", GrokProvider),
        "xai": ("Grok", "XAI_API_KEY", GrokProvider),
        "qwen": ("Qwen", "DASHSCOPE_API_KEY", QwenProvider),
        "dashscope": ("Qwen", "DASHSCOPE_API_KEY", QwenProvider),
    }

    provider_name = provider_name.lower()
    if provider_name not in provider_map:
        provider_name = "openai"  # Default

    name, key_name, provider_class = provider_map[provider_name]
    api_key = api_keys.get(key_name) or api_keys.get(key_name.lower())

    if not api_key:
        print(f"[WARNING] No API key for {name}, falling back to OpenAI")
        api_key = api_keys.get("OPENAI_API_KEY") or api_keys.get("openai")
        provider_class = OpenAIProvider

    return provider_class(api_key) if api_key else None


class AgentExecutor:
    """
    Executes YAML workflow nodes using real Agent classes.

    This enables:
    - Dynamic specialist spawning (e.g., biotech specialist for biotech companies)
    - Agent lifecycle management
    - Parent-child hierarchies within a node's execution
    - Health monitoring and error recovery
    """

    def __init__(
        self,
        node_config: NodeConfig,
        api_keys: Dict[str, str],
        context: Dict[str, Any] = None
    ):
        self.node_config = node_config
        self.api_keys = api_keys
        self.context = context or {}

        # Get agent mapping
        self.mapping = NODE_TO_AGENT.get(node_config.id)

        # Track spawned agents for cleanup
        self.spawned_agents: List[SpawnableAgent] = []

        # Get or create registry (AgentRegistry is a singleton)
        self.registry = AgentRegistry() if AGENTS_AVAILABLE else None

        # Initialize visualizer for spawned agents
        self._init_visualizer()

    def _init_visualizer(self):
        """Initialize visualizer so spawned agents appear in UI"""
        try:
            from visualizer.visualizer_bridge import VisualizerBridge
            from agents.core.spawnable_agent import set_global_visualizer
            visualizer = VisualizerBridge.get_instance()
            set_global_visualizer(visualizer)
        except ImportError:
            pass  # Visualizer not available

    @classmethod
    def can_handle_node(cls, node_id: str) -> bool:
        """Check if this node can be handled by agent execution"""
        return node_id in NODE_TO_AGENT and NODE_TO_AGENT[node_id].agent_class is not None

    def _build_research_context(self, input_messages: List[Message]) -> ResearchContext:
        """Build ResearchContext from workflow context and input messages"""
        # Get basic info from context
        ticker = self.context.get("ticker", "UNKNOWN")
        company_name = self.context.get("company_name", ticker)
        sector = self.context.get("sector", "Unknown")
        industry = self.context.get("industry", "Unknown")

        # Create context
        research_ctx = ResearchContext(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            industry=industry
        )

        # Add financial data if available
        if self.context.get("market_data"):
            research_ctx.financial_data = self.context["market_data"]

        # Parse input messages to populate context
        for msg in input_messages:
            content = msg.content
            source = msg.source.lower() if msg.source else ""

            # Route content to appropriate context field
            if "industry" in source or "industry deep dive" in source.lower():
                research_ctx.industry_analysis = content
            elif "company" in source or "company deep dive" in source.lower():
                research_ctx.company_analysis = content
            elif "governance" in source:
                research_ctx.governance_analysis = content
            elif "bull" in source or "bear" in source or "critic" in source:
                # Add to debate log
                research_ctx.debate_log.append(AgentMessage(
                    role=source,
                    content=content,
                    metadata=msg.metadata
                ))

        return research_ctx

    async def execute(self, input_messages: List[Message]) -> Message:
        """
        Execute interface for GraphExecutor compatibility.
        Delegates to run_agent for actual execution.
        """
        return await self.run_agent(input_messages)

    async def run_agent(self, input_messages: List[Message]) -> Message:
        """
        Execute the node using the mapped agent class.

        This creates a real agent, runs it, and cleans up.
        The agent may spawn children (e.g., specialists) during execution.
        """
        if not AGENTS_AVAILABLE or not self.mapping or not self.mapping.agent_class:
            return Message(
                role="assistant",
                content=f"[ERROR] Agent class not available for node: {self.node_config.id}",
                source=self.node_config.id,
                metadata={"error": "agent_not_available", "is_error": True}
            )

        try:
            # Get AI provider
            provider = get_ai_provider(self.mapping.provider_preference, self.api_keys)
            if not provider:
                return Message(
                    role="assistant",
                    content=f"[ERROR] No AI provider available for node: {self.node_config.id}",
                    source=self.node_config.id,
                    metadata={"error": "provider_not_available", "is_error": True}
                )

            # Build research context
            research_ctx = self._build_research_context(input_messages)

            # Create agent config
            agent_config = {
                **self.mapping.config,
                "ticker": self.context.get("ticker"),
                "node_id": self.node_config.id,
            }

            # Create agent instance
            agent = self.mapping.agent_class(
                ai_provider=provider,
                tier=self.mapping.tier,
                config=agent_config
            )
            self.spawned_agents.append(agent)

            # Activate agent
            await agent.activate()

            print(f"  [AgentExecutor] Spawned {agent.agent_id} for node '{self.node_config.id}'")

            # Execute based on agent type
            if self.mapping.analysis_type:
                # Analyst-type agent with specific analysis
                result = await agent.analyze(
                    research_ctx,
                    analysis_type=self.mapping.analysis_type
                )
            elif hasattr(agent, 'analyze'):
                # Generic analyze method
                result = await agent.analyze(research_ctx)
            elif hasattr(agent, 'run_gate'):
                # Goalkeeper agent
                gate_result = await agent.run_gate(research_ctx)
                result = self._format_gate_result(gate_result)
            else:
                # Fallback to respond
                prompt = self._build_prompt_from_messages(input_messages)
                result = await agent.respond(prompt)

            # Check for child agents spawned during execution
            children_spawned = len(agent.children_ids)
            if children_spawned > 0:
                print(f"  [AgentExecutor] Agent {agent.agent_id} spawned {children_spawned} children")

            # Terminate agent
            await agent.terminate()
            print(f"  [AgentExecutor] Terminated {agent.agent_id}")

            return Message(
                role="assistant",
                content=result,
                source=self.node_config.id,
                metadata={
                    "provider": self.mapping.provider_preference,
                    "agent_id": agent.agent_id,
                    "agent_class": self.mapping.agent_class.__name__,
                    "children_spawned": children_spawned,
                    "executed_via": "AgentExecutor"
                }
            )

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"  [AgentExecutor] Error in {self.node_config.id}: {e}")

            # Cleanup any spawned agents
            await self._cleanup_agents()

            return Message(
                role="assistant",
                content=f"[AGENT ERROR] {self.node_config.id}: {str(e)}\n\n{error_trace}",
                source=self.node_config.id,
                metadata={"error": str(e), "is_error": True}
            )

    def _build_prompt_from_messages(self, messages: List[Message]) -> str:
        """Build a prompt string from input messages"""
        parts = []
        for msg in messages:
            source = msg.source or msg.role
            parts.append(f"[{source.upper()}]\n{msg.content}\n")
        return "\n".join(parts)

    def _format_gate_result(self, gate_result: Dict[str, Any]) -> str:
        """Format a goalkeeper gate result to string"""
        lines = []

        passed = gate_result.get("passed", False)
        score = gate_result.get("score", 0)

        lines.append(f"GATE RESULT: {'PASSED' if passed else 'FAILED'}")
        lines.append(f"Score: {score:.2f}")

        if gate_result.get("issues"):
            lines.append("\nIssues Found:")
            for issue in gate_result["issues"]:
                severity = issue.get("severity", "unknown")
                desc = issue.get("description", str(issue))
                lines.append(f"  [{severity.upper()}] {desc}")

        if gate_result.get("recommendations"):
            lines.append("\nRecommendations:")
            for rec in gate_result["recommendations"]:
                lines.append(f"  - {rec}")

        return "\n".join(lines)

    async def _cleanup_agents(self):
        """Cleanup all spawned agents"""
        for agent in self.spawned_agents:
            try:
                if hasattr(agent, 'terminate'):
                    await agent.terminate()
            except Exception:
                pass
        self.spawned_agents.clear()


def create_agent_executor_if_applicable(
    node_config: NodeConfig,
    api_keys: Dict[str, str],
    context: Dict[str, Any] = None
) -> Optional[AgentExecutor]:
    """
    Factory function to create AgentExecutor if the node should use agent execution.

    Returns None if the node should use the default NodeExecutor.
    """
    # Temporarily disabled - hybrid approach needs agent class interface alignment
    # if AgentExecutor.can_handle_node(node_config.id):
    #     return AgentExecutor(node_config, api_keys, context)
    return None  # Fall back to standard NodeExecutor for all nodes