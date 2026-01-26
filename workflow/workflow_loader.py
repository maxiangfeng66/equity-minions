"""
Workflow Loader - Loads and validates YAML workflow configurations
Inspired by ChatDev's entity/graph_config.py architecture
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class NodeConfig:
    """Configuration for a workflow node (agent)"""
    id: str
    type: str
    config: Dict[str, Any]
    description: str = ""
    context_window: int = 0

    @property
    def provider(self) -> str:
        return self.config.get("provider", "openai")

    @property
    def model(self) -> str:
        return self.config.get("name", "gpt-4o")

    @property
    def role(self) -> str:
        return self.config.get("role", "")

    @property
    def api_key_var(self) -> str:
        """Get the API key variable name"""
        key = self.config.get("api_key", "")
        if key.startswith("${") and key.endswith("}"):
            return key[2:-1]
        return key


@dataclass
class EdgeConfig:
    """Configuration for an edge between nodes"""
    from_node: str
    to_node: str
    trigger: bool = False
    condition: Any = "true"
    carry_data: bool = True
    keep_message: bool = False
    clear_context: bool = False

    @property
    def is_conditional(self) -> bool:
        """Check if this edge has a conditional routing"""
        return isinstance(self.condition, dict)

    def evaluate_condition(self, output_text: str) -> bool:
        """Evaluate if this edge condition is met"""
        if self.condition == "true" or self.condition is True:
            return True

        if isinstance(self.condition, dict):
            cond_type = self.condition.get("type", "")
            config = self.condition.get("config", {})

            if cond_type == "keyword":
                keywords = config.get("any", [])
                case_sensitive = config.get("case_sensitive", True)

                if not case_sensitive:
                    output_text = output_text.lower()
                    keywords = [k.lower() for k in keywords]

                return any(keyword in output_text for keyword in keywords)

        return True


@dataclass
class GraphConfig:
    """Configuration for the entire workflow graph"""
    id: str
    description: str
    nodes: Dict[str, NodeConfig]
    edges: List[EdgeConfig]
    start_nodes: List[str]
    end_nodes: List[str]
    log_level: str = "DEBUG"
    is_majority_voting: bool = False
    variables: Dict[str, str] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[NodeConfig]:
        return self.nodes.get(node_id)

    def get_successors(self, node_id: str) -> List[str]:
        """Get all successor node IDs for a given node"""
        return [e.to_node for e in self.edges if e.from_node == node_id]

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get all predecessor node IDs for a given node"""
        return [e.from_node for e in self.edges if e.to_node == node_id]

    def get_outgoing_edges(self, node_id: str) -> List[EdgeConfig]:
        """Get all outgoing edges from a node"""
        return [e for e in self.edges if e.from_node == node_id]

    def get_trigger_edges(self, node_id: str) -> List[EdgeConfig]:
        """Get edges that trigger execution of a node"""
        return [e for e in self.edges if e.to_node == node_id and e.trigger]


class WorkflowLoader:
    """Loads workflow definitions from YAML files"""

    def __init__(self, workflows_dir: str = None):
        # Default to workflow/definitions/ (the actual location of YAML files)
        if workflows_dir is None:
            # Check both possible locations
            script_dir = Path(__file__).parent
            definitions_path = script_dir / "definitions"
            if definitions_path.exists():
                workflows_dir = str(definitions_path)
            else:
                # Fallback to old location
                workflows_dir = "workflows"
        self.workflows_dir = Path(workflows_dir)
        self.env_vars = self._load_env_vars()

    def _load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from config.py and .env"""
        env_vars = {}

        # Try to load from config.py
        try:
            from config import API_KEYS
            env_vars["OPENAI_API_KEY"] = API_KEYS.get("openai", "")
            env_vars["GOOGLE_API_KEY"] = API_KEYS.get("google", "")
            env_vars["XAI_API_KEY"] = API_KEYS.get("xai", "")
            env_vars["DASHSCOPE_API_KEY"] = API_KEYS.get("dashscope", "")
            env_vars["DEEPSEEK_API_KEY"] = API_KEYS.get("deepseek", "")
        except ImportError:
            pass

        # Override with environment variables if present
        for key in ["OPENAI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY"]:
            if key in os.environ:
                env_vars[key] = os.environ[key]

        return env_vars

    def _substitute_variables(self, text: str) -> str:
        """Replace ${VAR} patterns with actual values"""
        if not isinstance(text, str):
            return text

        pattern = r'\$\{([^}]+)\}'

        def replace(match):
            var_name = match.group(1)
            return self.env_vars.get(var_name, match.group(0))

        return re.sub(pattern, replace, text)

    def _process_config_values(self, config: Any) -> Any:
        """Recursively process config values to substitute variables"""
        if isinstance(config, str):
            return self._substitute_variables(config)
        elif isinstance(config, dict):
            return {k: self._process_config_values(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_config_values(item) for item in config]
        return config

    def load(self, workflow_name: str) -> GraphConfig:
        """Load a workflow by name (without .yaml extension)"""
        yaml_path = self.workflows_dir / f"{workflow_name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Workflow not found: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # Process variables
        variables = raw_config.get("vars", {})
        variables = self._process_config_values(variables)

        # Update env_vars with workflow-specific variables
        self.env_vars.update(variables)

        # Process the graph configuration
        graph_def = raw_config.get("graph", {})

        # Parse nodes
        nodes = {}
        for node_def in graph_def.get("nodes", []):
            node_id = node_def.get("id")
            node_config = self._process_config_values(node_def.get("config", {}))

            nodes[node_id] = NodeConfig(
                id=node_id,
                type=node_def.get("type", "agent"),
                config=node_config,
                description=node_def.get("description", ""),
                context_window=node_def.get("context_window", 0)
            )

        # Parse edges
        edges = []
        for edge_def in graph_def.get("edges", []):
            edges.append(EdgeConfig(
                from_node=edge_def.get("from"),
                to_node=edge_def.get("to"),
                trigger=edge_def.get("trigger", False),
                condition=edge_def.get("condition", "true"),
                carry_data=edge_def.get("carry_data", True),
                keep_message=edge_def.get("keep_message", False),
                clear_context=edge_def.get("clear_context", False)
            ))

        return GraphConfig(
            id=graph_def.get("id", workflow_name),
            description=graph_def.get("description", ""),
            nodes=nodes,
            edges=edges,
            start_nodes=graph_def.get("start", ["START"]),
            end_nodes=graph_def.get("end", []),
            log_level=graph_def.get("log_level", "DEBUG"),
            is_majority_voting=graph_def.get("is_majority_voting", False),
            variables=variables
        )

    def list_workflows(self) -> List[str]:
        """List all available workflow names"""
        if not self.workflows_dir.exists():
            return []

        return [
            f.stem for f in self.workflows_dir.glob("*.yaml")
            if not f.name.startswith("_")  # Skip private/partial workflows
        ]
