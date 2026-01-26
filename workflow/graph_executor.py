"""
Graph Executor - Executes complete workflow graphs
Inspired by ChatDev's workflow/graph.py architecture

Key features:
- DAG-based execution with parallel node processing
- Cycle detection and handling for feedback loops
- Conditional edge routing
- Quality review feedback loops
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from .workflow_loader import WorkflowLoader, GraphConfig, NodeConfig, EdgeConfig
from .node_executor import NodeExecutor, PassthroughExecutor, PythonValuationExecutor, Message, get_executor


@dataclass
class NodeState:
    """Tracks the state of a node during execution"""
    id: str
    config: NodeConfig
    inputs: List[Message] = field(default_factory=list)
    outputs: List[Message] = field(default_factory=list)
    triggered: bool = False
    executed: bool = False
    execution_count: int = 0

    def reset_triggers(self):
        self.triggered = False

    def add_input(self, message: Message):
        self.inputs.append(message)

    def add_output(self, message: Message):
        self.outputs.append(message)

    def get_last_output(self) -> Optional[Message]:
        return self.outputs[-1] if self.outputs else None


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    success: bool
    final_output: Optional[Message]
    node_outputs: Dict[str, List[Message]]
    execution_log: List[Dict[str, Any]]
    total_tokens: Dict[str, int] = field(default_factory=dict)
    execution_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "final_output": self.final_output.to_dict() if self.final_output else None,
            "node_outputs": {
                k: [m.to_dict() for m in v] for k, v in self.node_outputs.items()
            },
            "execution_log": self.execution_log,
            "total_tokens": self.total_tokens,
            "execution_time": self.execution_time,
            "error": self.error
        }


class GraphExecutor:
    """Executes a workflow graph with support for parallel execution and feedback loops"""

    MAX_ITERATIONS = 36  # Maximum feedback loop iterations (increased for complex workflows with feedback loops)

    def __init__(
        self,
        graph_config: GraphConfig,
        api_keys: Dict[str, str],
        output_dir: str = "context",
        context: Dict[str, Any] = None
    ):
        self.config = graph_config
        self.api_keys = api_keys
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.context = context or {}  # Context for valuation nodes (ticker, market_data, etc.)

        # Initialize node states
        self.node_states: Dict[str, NodeState] = {}
        for node_id, node_config in graph_config.nodes.items():
            self.node_states[node_id] = NodeState(id=node_id, config=node_config)

        # Build execution layers (topological sort)
        self.layers = self._build_execution_layers()

        # Execution tracking
        self.execution_log: List[Dict[str, Any]] = []
        self.iteration_count = 0

    def _build_execution_layers(self) -> List[List[str]]:
        """Build execution layers using topological sort"""
        # Calculate in-degree for each node
        in_degree = defaultdict(int)
        for edge in self.config.edges:
            if edge.trigger:  # Only count trigger edges
                in_degree[edge.to_node] += 1

        # Start with nodes that have no trigger dependencies
        layers = []
        remaining = set(self.config.nodes.keys())
        processed = set()

        while remaining:
            # Find nodes with all dependencies satisfied
            layer = []
            for node_id in remaining:
                deps_satisfied = True
                for edge in self.config.get_trigger_edges(node_id):
                    if edge.from_node not in processed:
                        deps_satisfied = False
                        break
                if deps_satisfied:
                    layer.append(node_id)

            if not layer:
                # Cycle detected - just add remaining nodes
                layer = list(remaining)

            layers.append(layer)
            processed.update(layer)
            remaining -= set(layer)

        return layers

    def log(self, event: str, node_id: str = "", details: Dict[str, Any] = None):
        """Log an execution event"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "node_id": node_id,
            "iteration": self.iteration_count,
            "details": details or {}
        }
        self.execution_log.append(entry)
        print(f"[{entry['timestamp']}] {event}: {node_id} - {details}")

    async def execute(self, task_prompt: str) -> WorkflowResult:
        """Execute the complete workflow"""
        start_time = datetime.now()

        try:
            self.log("workflow_start", details={"task": task_prompt[:100]})

            # Initialize start nodes with task prompt
            initial_message = Message(
                role="user",
                content=task_prompt,
                source="TASK"
            )

            for start_node in self.config.start_nodes:
                if start_node in self.node_states:
                    self.node_states[start_node].add_input(initial_message)
                    self.node_states[start_node].triggered = True

            # Execute the graph
            await self._execute_graph()

            # Get final output
            final_output = self._get_final_output()

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Collect all outputs
            node_outputs = {
                node_id: state.outputs
                for node_id, state in self.node_states.items()
                if state.outputs
            }

            self.log("workflow_complete", details={
                "execution_time": execution_time,
                "nodes_executed": len([s for s in self.node_states.values() if s.executed])
            })

            return WorkflowResult(
                success=True,
                final_output=final_output,
                node_outputs=node_outputs,
                execution_log=self.execution_log,
                execution_time=execution_time
            )

        except Exception as e:
            self.log("workflow_error", details={"error": str(e)})
            return WorkflowResult(
                success=False,
                final_output=None,
                node_outputs={},
                execution_log=self.execution_log,
                error=str(e)
            )

    async def _execute_graph(self):
        """Execute the graph with support for cycles"""
        while self.iteration_count < self.MAX_ITERATIONS:
            self.iteration_count += 1
            self.log("iteration_start", details={"iteration": self.iteration_count})

            # Find all triggered nodes
            triggered_nodes = [
                node_id for node_id, state in self.node_states.items()
                if state.triggered and state.inputs
            ]

            if not triggered_nodes:
                self.log("no_triggered_nodes", details={"iteration": self.iteration_count})
                break

            # Execute triggered nodes in parallel batches
            await self._execute_nodes_parallel(triggered_nodes)

            # Check if we've reached end nodes with no more routing
            if self._is_complete():
                break

        self.log("execution_complete", details={"iterations": self.iteration_count})

    async def _execute_nodes_parallel(self, node_ids: List[str]):
        """Execute multiple nodes in parallel"""
        tasks = []
        for node_id in node_ids:
            tasks.append(self._execute_single_node(node_id))

        await asyncio.gather(*tasks)

    def _get_prior_outputs(self) -> Dict[str, str]:
        """Collect outputs from all executed nodes for valuation context"""
        prior_outputs = {}
        for nid, state in self.node_states.items():
            if state.outputs:
                # Use the most recent output
                last_output = state.outputs[-1]
                prior_outputs[nid] = last_output.content
                # Also map by node description if available (for more flexible matching)
                if state.config.description and state.config.description != nid:
                    prior_outputs[state.config.description] = last_output.content
        return prior_outputs

    async def _execute_single_node(self, node_id: str):
        """Execute a single node"""
        state = self.node_states[node_id]
        node_config = state.config

        self.log("node_start", node_id, details={
            "type": node_config.type,
            "input_count": len(state.inputs)
        })

        # Reset trigger for next iteration
        state.reset_triggers()

        try:
            # Use factory function to get appropriate executor
            # This handles Python valuation nodes, passthrough, and AI nodes
            executor = get_executor(node_config, self.api_keys, self.context)

            # Execute the node
            # For valuation nodes, pass prior outputs for context extraction
            if isinstance(executor, PythonValuationExecutor):
                prior_outputs = self._get_prior_outputs()
                result = await executor.execute(state.inputs, prior_outputs)
            else:
                result = await executor.execute(state.inputs)

            # Record output
            state.add_output(result)
            state.executed = True
            state.execution_count += 1

            # Include output preview for visualizer (first 2000 chars)
            output_preview = result.content[:2000] if result.content else ""
            self.log("node_complete", node_id, details={
                "output_length": len(result.content),
                "execution_count": state.execution_count,
                "output_preview": output_preview,
                "provider": result.metadata.get("provider", "unknown")
            })

            # Process outgoing edges
            await self._process_edges(node_id, result)

            # Clear inputs after processing (unless context window is -1)
            if node_config.context_window != -1:
                state.inputs = []

        except Exception as e:
            self.log("node_error", node_id, details={"error": str(e)})
            raise

    def _is_error_output(self, output: Message) -> bool:
        """Check if the output message is an error message"""
        # Check metadata flag
        if output.metadata.get("is_error"):
            return True

        # Check for error patterns in content
        error_patterns = [
            "Error executing",
            "API error:",
            "rate_limit_exceeded",
            "Error code: 4",  # 400, 401, 403, 429, etc.
            "Error code: 5",  # 500, 502, 503, etc.
        ]

        content = output.content[:500]  # Only check first 500 chars
        return any(pattern in content for pattern in error_patterns)

    async def _process_edges(self, from_node: str, output: Message):
        """Process all outgoing edges from a node"""
        edges = self.config.get_outgoing_edges(from_node)

        # Check if the output is an error - if so, don't propagate to downstream nodes
        is_error = self._is_error_output(output)
        if is_error:
            self.log("error_output_detected", from_node, details={
                "error_content": output.content[:200],
                "blocking_downstream": True
            })
            # Don't trigger downstream nodes with error content
            # This prevents cascading failures
            return

        # Debug: log all edges being processed
        self.log("processing_edges", from_node, details={
            "edge_count": len(edges),
            "targets": [e.to_node for e in edges]
        })

        for edge in edges:
            # Evaluate edge condition
            if not edge.evaluate_condition(output.content):
                self.log("edge_condition_failed", details={
                    "from": from_node,
                    "to": edge.to_node,
                    "condition": str(edge.condition)
                })
                continue

            # Get target node state
            target_state = self.node_states.get(edge.to_node)
            if not target_state:
                continue

            # Carry data to target node
            if edge.carry_data:
                # Clone the message for the target
                target_message = Message(
                    role=output.role,
                    content=output.content,
                    source=from_node,
                    metadata={**output.metadata, "from_edge": f"{from_node}->{edge.to_node}"}
                )
                target_state.add_input(target_message)

            # Set trigger if this is a trigger edge
            if edge.trigger:
                target_state.triggered = True
                self.log("node_triggered", edge.to_node, details={
                    "from": from_node,
                    "trigger": True
                })

    def _is_complete(self) -> bool:
        """Check if workflow execution is complete"""
        # Check if end nodes have been executed
        for end_node in self.config.end_nodes:
            if end_node in self.node_states:
                state = self.node_states[end_node]
                if state.executed and state.outputs:
                    return True

        # Check if no nodes are triggered
        triggered = any(s.triggered for s in self.node_states.values())
        return not triggered

    def _get_final_output(self) -> Optional[Message]:
        """Get the final output from end nodes"""
        # Try configured end nodes first
        for end_node in self.config.end_nodes:
            if end_node in self.node_states:
                state = self.node_states[end_node]
                if state.outputs:
                    return state.outputs[-1]

        # Fallback: find sink nodes (nodes with no outgoing edges)
        sink_nodes = []
        for node_id in self.config.nodes:
            outgoing = self.config.get_outgoing_edges(node_id)
            if not outgoing:
                sink_nodes.append(node_id)

        for sink in sink_nodes:
            if sink in self.node_states:
                state = self.node_states[sink]
                if state.outputs:
                    return state.outputs[-1]

        return None

    def save_results(self, ticker: str) -> str:
        """Save execution results to context file"""
        output_file = self.output_dir / f"{ticker.replace(' ', '_')}_workflow_result.json"

        # Extract verified price from context - THIS IS THE AUTHORITATIVE SOURCE
        verified_price = None
        currency = self.context.get("currency", "USD")
        if self.context.get("market_data"):
            verified_price = self.context["market_data"].get("current_price")
            currency = self.context["market_data"].get("currency", currency)

        # Collect all node outputs
        results = {
            "ticker": ticker,
            "workflow_id": self.config.id,
            "executed_at": datetime.now().isoformat(),
            "iterations": self.iteration_count,
            # CRITICAL: Save verified price so report generator uses it
            "verified_price": verified_price,
            "currency": currency,
            "context": {
                "company_name": self.context.get("company_name"),
                "sector": self.context.get("sector"),
                "industry": self.context.get("industry"),
            },
            "node_outputs": {},
            "execution_log": self.execution_log
        }

        for node_id, state in self.node_states.items():
            if state.outputs:
                results["node_outputs"][node_id] = [m.to_dict() for m in state.outputs]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return str(output_file)


async def run_workflow(
    workflow_name: str,
    task_prompt: str,
    api_keys: Optional[Dict[str, str]] = None,
    output_dir: str = "context",
    context: Dict[str, Any] = None
) -> WorkflowResult:
    """
    Convenience function to run a workflow.

    Args:
        workflow_name: Name of the workflow YAML file (without extension)
        task_prompt: Initial prompt/task description
        api_keys: API keys for AI providers
        output_dir: Directory for output files
        context: Additional context (ticker, market_data, etc.) for Python nodes

    Returns:
        WorkflowResult with execution details
    """
    # Load workflow
    loader = WorkflowLoader()
    config = loader.load(workflow_name)

    # Use provided API keys or load from config
    if api_keys is None:
        try:
            from config import API_KEYS
            api_keys = {
                "OPENAI_API_KEY": API_KEYS.get("openai", ""),
                "GOOGLE_API_KEY": API_KEYS.get("google", ""),
                "XAI_API_KEY": API_KEYS.get("xai", ""),
                "DASHSCOPE_API_KEY": API_KEYS.get("dashscope", ""),
                "DEEPSEEK_API_KEY": API_KEYS.get("deepseek", "")
            }
        except ImportError:
            api_keys = {}

    # Create executor and run with context for valuation nodes
    executor = GraphExecutor(config, api_keys, output_dir, context)
    return await executor.execute(task_prompt)
