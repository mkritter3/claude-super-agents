#!/usr/bin/env python3
"""
AET Agent Dependency Graph - Smart parallel execution orchestration
Part of Phase 1.1: Determines which agents can run in parallel
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
import matplotlib.pyplot as plt
import logging

class AgentRelationType(Enum):
    """Types of relationships between agents"""
    DEPENDS_ON = "depends_on"          # A must complete before B
    BLOCKS = "blocks"                  # A blocks B from running
    TRIGGERS = "triggers"              # A triggers B to run
    PARALLEL = "parallel"              # A and B can run together
    MUTEX = "mutex"                    # A and B cannot run together
    OPTIONAL = "optional"              # A optionally enhances B

@dataclass
class AgentNode:
    """Represents an agent in the dependency graph"""
    name: str
    category: str
    priority: int = 3  # 1=critical, 2=high, 3=normal, 4=low
    cpu_bound: bool = False
    io_bound: bool = True
    estimated_duration: float = 60.0  # seconds
    max_parallel: int = 1  # How many instances can run in parallel
    dependencies: Set[str] = field(default_factory=set)
    triggers: Set[str] = field(default_factory=set)
    blocks: Set[str] = field(default_factory=set)
    mutex_with: Set[str] = field(default_factory=set)

class AgentDependencyGraph:
    """Manages agent dependencies and determines parallel execution strategies"""
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        
        # Create directed graph
        self.graph = nx.DiGraph()
        
        # Agent metadata
        self.agents: Dict[str, AgentNode] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Initialize graph with known agents
        self._initialize_agents()
        self._build_graph()
        
    def _setup_logging(self):
        """Setup dependency graph logger"""
        log_dir = self.claude_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("AgentDependencyGraph")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / "dependency_graph.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
    def _initialize_agents(self):
        """Initialize known agents with their properties"""
        
        # Critical path agents (blocking)
        self.agents["contract-guardian"] = AgentNode(
            name="contract-guardian",
            category="critical",
            priority=1,
            cpu_bound=True,
            estimated_duration=30.0,
            blocks={"developer-agent", "integrator-agent"}
        )
        
        self.agents["security-agent"] = AgentNode(
            name="security-agent",
            category="critical",
            priority=1,
            cpu_bound=True,
            estimated_duration=45.0,
            blocks={"integrator-agent", "devops-agent"}
        )
        
        # High priority agents
        self.agents["test-executor"] = AgentNode(
            name="test-executor",
            category="operational",
            priority=2,
            cpu_bound=True,
            estimated_duration=120.0,
            dependencies={"developer-agent"},
            blocks={"integrator-agent"}
        )
        
        self.agents["incident-response-agent"] = AgentNode(
            name="incident-response-agent",
            category="operational",
            priority=1,
            io_bound=True,
            estimated_duration=15.0,
            mutex_with={"performance-optimizer-agent"}
        )
        
        # Core development agents
        self.agents["architect-agent"] = AgentNode(
            name="architect-agent",
            category="engineering",
            priority=2,
            cpu_bound=True,
            estimated_duration=90.0,
            triggers={"developer-agent"}
        )
        
        self.agents["developer-agent"] = AgentNode(
            name="developer-agent",
            category="engineering",
            priority=2,
            cpu_bound=True,
            estimated_duration=180.0,
            dependencies={"architect-agent"},
            triggers={"test-executor", "reviewer-agent"}
        )
        
        self.agents["reviewer-agent"] = AgentNode(
            name="reviewer-agent",
            category="engineering",
            priority=3,
            cpu_bound=True,
            estimated_duration=60.0,
            dependencies={"developer-agent"}
        )
        
        self.agents["integrator-agent"] = AgentNode(
            name="integrator-agent",
            category="engineering",
            priority=3,
            io_bound=True,
            estimated_duration=30.0,
            dependencies={"test-executor", "reviewer-agent", "contract-guardian"}
        )
        
        # Background agents (can run in parallel)
        self.agents["documentation-agent"] = AgentNode(
            name="documentation-agent",
            category="operational",
            priority=4,
            io_bound=True,
            estimated_duration=90.0,
            dependencies={"developer-agent"},
            max_parallel=3
        )
        
        self.agents["performance-optimizer-agent"] = AgentNode(
            name="performance-optimizer-agent",
            category="operational",
            priority=4,
            cpu_bound=True,
            estimated_duration=120.0,
            mutex_with={"incident-response-agent"}
        )
        
        self.agents["monitoring-agent"] = AgentNode(
            name="monitoring-agent",
            category="operational",
            priority=3,
            io_bound=True,
            estimated_duration=30.0,
            max_parallel=5
        )
        
        # Infrastructure agents
        self.agents["devops-agent"] = AgentNode(
            name="devops-agent",
            category="infrastructure",
            priority=3,
            io_bound=True,
            estimated_duration=60.0,
            dependencies={"security-agent"}
        )
        
        self.agents["database-agent"] = AgentNode(
            name="database-agent",
            category="infrastructure",
            priority=3,
            cpu_bound=True,
            estimated_duration=45.0,
            blocks={"developer-agent"}
        )
        
        self.agents["data-migration-agent"] = AgentNode(
            name="data-migration-agent",
            category="infrastructure",
            priority=2,
            cpu_bound=True,
            estimated_duration=180.0,
            dependencies={"database-agent"},
            blocks={"developer-agent", "test-executor"}
        )
        
        # UI/UX agents
        self.agents["frontend-agent"] = AgentNode(
            name="frontend-agent",
            category="frontend",
            priority=3,
            cpu_bound=True,
            estimated_duration=120.0,
            triggers={"ux-agent"}
        )
        
        self.agents["ux-agent"] = AgentNode(
            name="ux-agent",
            category="frontend",
            priority=3,
            io_bound=True,
            estimated_duration=60.0,
            dependencies={"frontend-agent"}
        )
        
        # Product agents
        self.agents["product-agent"] = AgentNode(
            name="product-agent",
            category="product",
            priority=3,
            io_bound=True,
            estimated_duration=45.0,
            triggers={"architect-agent"}
        )
        
        self.agents["pm-agent"] = AgentNode(
            name="pm-agent",
            category="product",
            priority=2,
            io_bound=True,
            estimated_duration=30.0,
            triggers={"architect-agent", "product-agent"}
        )
        
        self.logger.info(f"Initialized {len(self.agents)} agents")
        
    def _build_graph(self):
        """Build the dependency graph from agent definitions"""
        
        # Add nodes
        for agent_name, agent in self.agents.items():
            self.graph.add_node(
                agent_name,
                category=agent.category,
                priority=agent.priority,
                cpu_bound=agent.cpu_bound,
                duration=agent.estimated_duration
            )
            
        # Add edges for dependencies
        for agent_name, agent in self.agents.items():
            # Dependencies (must complete before)
            for dep in agent.dependencies:
                if dep in self.agents:
                    self.graph.add_edge(dep, agent_name, 
                                      relation=AgentRelationType.DEPENDS_ON)
                    
            # Triggers (causes to run)
            for trigger in agent.triggers:
                if trigger in self.agents:
                    self.graph.add_edge(agent_name, trigger,
                                      relation=AgentRelationType.TRIGGERS)
                    
            # Blocks (prevents from running)
            for blocked in agent.blocks:
                if blocked in self.agents:
                    self.graph.add_edge(agent_name, blocked,
                                      relation=AgentRelationType.BLOCKS)
                    
        self.logger.info(f"Built graph with {self.graph.number_of_nodes()} nodes "
                        f"and {self.graph.number_of_edges()} edges")
                        
    def get_parallel_groups(self, agents: List[str]) -> List[Set[str]]:
        """Determine which agents can run in parallel"""
        
        # Filter to requested agents
        requested = set(agents) & set(self.agents.keys())
        
        # Build subgraph for analysis
        subgraph = self.graph.subgraph(requested)
        
        # Find strongly connected components (must run sequentially)
        sequential_groups = list(nx.strongly_connected_components(subgraph))
        
        # Find agents that can run in parallel
        parallel_groups = []
        processed = set()
        
        for agent in requested:
            if agent in processed:
                continue
                
            # Find agents that have no dependencies with this one
            parallel_set = {agent}
            
            for other in requested:
                if other == agent or other in processed:
                    continue
                    
                # Check if they can run in parallel
                if self._can_run_parallel(agent, other):
                    parallel_set.add(other)
                    
            parallel_groups.append(parallel_set)
            processed.update(parallel_set)
            
        return parallel_groups
        
    def _can_run_parallel(self, agent1: str, agent2: str) -> bool:
        """Check if two agents can run in parallel"""
        
        node1 = self.agents.get(agent1)
        node2 = self.agents.get(agent2)
        
        if not node1 or not node2:
            return False
            
        # Check mutex relationship
        if agent2 in node1.mutex_with or agent1 in node2.mutex_with:
            return False
            
        # Check dependencies
        if agent2 in node1.dependencies or agent1 in node2.dependencies:
            return False
            
        # Check blocks
        if agent2 in node1.blocks or agent1 in node2.blocks:
            return False
            
        # Check if there's a path between them (dependency chain)
        if nx.has_path(self.graph, agent1, agent2) or nx.has_path(self.graph, agent2, agent1):
            return False
            
        return True
        
    def get_execution_order(self, agents: List[str]) -> List[List[str]]:
        """Get optimal execution order considering dependencies"""
        
        # Filter to requested agents
        requested = set(agents) & set(self.agents.keys())
        
        # Build subgraph
        subgraph = self.graph.subgraph(requested)
        
        # Topological sort for execution order
        try:
            topo_order = list(nx.topological_sort(subgraph))
        except nx.NetworkXError:
            # Graph has cycles, use priority-based ordering
            topo_order = sorted(requested, 
                              key=lambda x: (self.agents[x].priority, x))
            
        # Group by levels (can run in parallel)
        levels = []
        processed = set()
        
        for agent in topo_order:
            if agent in processed:
                continue
                
            # Find all agents at this level (no dependencies on unprocessed)
            level = [agent]
            
            for other in topo_order:
                if other == agent or other in processed:
                    continue
                    
                # Check if all dependencies are processed
                deps = self.agents[other].dependencies & requested
                if deps.issubset(processed | {agent}):
                    if self._can_run_parallel(agent, other):
                        level.append(other)
                        
            levels.append(level)
            processed.update(level)
            
        return levels
        
    def estimate_execution_time(self, agents: List[str], 
                               parallel_workers: int = 4) -> float:
        """Estimate total execution time with parallel processing"""
        
        execution_order = self.get_execution_order(agents)
        total_time = 0.0
        
        for level in execution_order:
            # Time for this level is max of parallel execution groups
            level_times = []
            
            # Group by CPU vs I/O bound
            cpu_tasks = [a for a in level if self.agents[a].cpu_bound]
            io_tasks = [a for a in level if not self.agents[a].cpu_bound]
            
            # CPU tasks limited by worker count
            if cpu_tasks:
                cpu_time = sum(self.agents[a].estimated_duration for a in cpu_tasks)
                cpu_time = cpu_time / min(parallel_workers, len(cpu_tasks))
                level_times.append(cpu_time)
                
            # I/O tasks can run more in parallel
            if io_tasks:
                io_time = max(self.agents[a].estimated_duration for a in io_tasks)
                level_times.append(io_time)
                
            total_time += max(level_times) if level_times else 0
            
        return total_time
        
    def visualize_graph(self, output_file: Path = None, agents: List[str] = None):
        """Visualize the dependency graph"""
        
        if output_file is None:
            output_file = self.claude_dir / "graphs" / "agent_dependencies.png"
            
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use subset if specified
        if agents:
            graph = self.graph.subgraph(agents)
        else:
            graph = self.graph
            
        # Create layout
        pos = nx.spring_layout(graph, k=2, iterations=50)
        
        # Setup plot
        plt.figure(figsize=(16, 12))
        
        # Color by category
        categories = set(self.agents[n].category for n in graph.nodes())
        colors = plt.cm.Set3(range(len(categories)))
        category_colors = dict(zip(categories, colors))
        
        node_colors = [category_colors[self.agents[n].category] 
                      for n in graph.nodes()]
        
        # Draw nodes
        nx.draw_networkx_nodes(graph, pos, node_color=node_colors,
                             node_size=3000, alpha=0.8)
        
        # Draw edges by type
        edge_types = {
            AgentRelationType.DEPENDS_ON: ('solid', 'blue'),
            AgentRelationType.TRIGGERS: ('dashed', 'green'),
            AgentRelationType.BLOCKS: ('dotted', 'red')
        }
        
        for edge_type, (style, color) in edge_types.items():
            edges = [(u, v) for u, v, d in graph.edges(data=True)
                    if d.get('relation') == edge_type]
            if edges:
                nx.draw_networkx_edges(graph, pos, edgelist=edges,
                                      style=style, edge_color=color,
                                      arrows=True, arrowsize=20)
                                      
        # Draw labels
        nx.draw_networkx_labels(graph, pos, font_size=8)
        
        # Add legend
        legend_elements = []
        for cat, color in category_colors.items():
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w',
                                            markerfacecolor=color, markersize=10,
                                            label=cat))
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title("Agent Dependency Graph")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        plt.close()
        
        self.logger.info(f"Saved graph visualization to {output_file}")
        
    def suggest_optimizations(self) -> List[Dict]:
        """Suggest optimizations for parallel execution"""
        
        suggestions = []
        
        # Find bottlenecks (high degree centrality)
        centrality = nx.degree_centrality(self.graph)
        bottlenecks = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for agent, score in bottlenecks:
            if score > 0.3:  # Significant bottleneck
                suggestions.append({
                    "type": "bottleneck",
                    "agent": agent,
                    "impact": "high",
                    "suggestion": f"Consider breaking {agent} into smaller parallel tasks"
                })
                
        # Find long sequential chains
        longest_path = []
        try:
            longest_path = nx.dag_longest_path(self.graph)
        except:
            pass
            
        if len(longest_path) > 5:
            suggestions.append({
                "type": "sequential_chain",
                "agents": longest_path,
                "impact": "medium",
                "suggestion": "Long sequential chain detected, consider parallelization"
            })
            
        # Find mutex conflicts
        for agent_name, agent in self.agents.items():
            if len(agent.mutex_with) > 2:
                suggestions.append({
                    "type": "mutex_conflict",
                    "agent": agent_name,
                    "conflicts": list(agent.mutex_with),
                    "impact": "low",
                    "suggestion": f"Many mutex conflicts for {agent_name}, review necessity"
                })
                
        return suggestions


def main():
    """CLI interface for dependency graph"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Dependency Graph")
    parser.add_argument('--analyze', nargs='+',
                       help='Analyze dependencies for specific agents')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate graph visualization')
    parser.add_argument('--optimize', action='store_true',
                       help='Suggest optimizations')
    parser.add_argument('--estimate', nargs='+',
                       help='Estimate execution time for agents')
    
    args = parser.parse_args()
    
    graph = AgentDependencyGraph()
    
    if args.analyze:
        print(f"\nAnalyzing agents: {args.analyze}")
        
        # Get parallel groups
        groups = graph.get_parallel_groups(args.analyze)
        print("\nParallel execution groups:")
        for i, group in enumerate(groups, 1):
            print(f"  Group {i}: {', '.join(group)}")
            
        # Get execution order
        order = graph.get_execution_order(args.analyze)
        print("\nOptimal execution order:")
        for i, level in enumerate(order, 1):
            print(f"  Level {i}: {', '.join(level)}")
            
    elif args.visualize:
        output = Path.cwd() / "agent_dependencies.png"
        graph.visualize_graph(output)
        print(f"Graph saved to {output}")
        
    elif args.optimize:
        suggestions = graph.suggest_optimizations()
        
        print("\n=== Optimization Suggestions ===")
        for suggestion in suggestions:
            print(f"\n[{suggestion['impact'].upper()}] {suggestion['type']}")
            print(f"  {suggestion['suggestion']}")
            if 'agent' in suggestion:
                print(f"  Agent: {suggestion['agent']}")
            if 'agents' in suggestion:
                print(f"  Agents: {' -> '.join(suggestion['agents'])}")
                
    elif args.estimate:
        time_est = graph.estimate_execution_time(args.estimate)
        
        print(f"\nEstimated execution time for {len(args.estimate)} agents:")
        print(f"  Sequential: {sum(graph.agents[a].estimated_duration for a in args.estimate if a in graph.agents):.1f} seconds")
        print(f"  Parallel (4 workers): {time_est:.1f} seconds")
        print(f"  Speedup: {sum(graph.agents[a].estimated_duration for a in args.estimate if a in graph.agents) / time_est:.1f}x")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()