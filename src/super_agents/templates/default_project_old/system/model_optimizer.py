#!/usr/bin/env python3
"""
AET Model Optimizer
Implements model-specific agent optimization for Phase 1.7
- Model selection based on task complexity
- Fallback chains for availability
- Performance monitoring
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

class ModelTier(Enum):
    """Model tiers for different use cases"""
    HAIKU = "claude-3-5-haiku-20241022"  # Fast, lightweight
    SONNET = "claude-3-5-sonnet-20241022"  # Balanced
    OPUS = "claude-3-opus-20240229"  # Complex reasoning
    
    # Future models (placeholders)
    OPUS_4_1 = "claude-opus-4-1-20250805"  # When available
    SONNET_4 = "claude-sonnet-4-20250514"  # When available

class TaskComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = 1    # Simple yes/no, lookups
    SIMPLE = 2     # Basic operations, file edits
    MODERATE = 3   # Standard development tasks
    COMPLEX = 4    # Architecture, complex logic
    CRITICAL = 5   # Security, contracts, data migration

class ModelOptimizer:
    """Optimizes model selection for agents based on task requirements"""
    
    # Agent to model mapping based on requirements
    AGENT_MODEL_MAP = {
        # Fast response agents (Haiku)
        "filesystem-guardian": {
            "primary": ModelTier.HAIKU,
            "complexity_threshold": TaskComplexity.SIMPLE,
            "reason": "Path validation needs speed, not complex reasoning"
        },
        "incident-response-agent": {
            "primary": ModelTier.HAIKU,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Fast response critical for incident handling"
        },
        "verifier-agent": {
            "primary": ModelTier.HAIKU,
            "complexity_threshold": TaskComplexity.SIMPLE,
            "reason": "Quick consistency checks"
        },
        
        # Balanced performance agents (Sonnet)
        "developer-agent": {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Balance between speed and code quality"
        },
        "reviewer-agent": {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Code review needs understanding but not deep reasoning"
        },
        "test-executor": {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Test analysis requires moderate complexity"
        },
        "documentation-agent": {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.SIMPLE,
            "reason": "Documentation generation is straightforward"
        },
        "frontend-agent": {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "UI implementation needs balance"
        },
        
        # Complex reasoning agents (Opus)
        "architect-agent": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.COMPLEX,
            "reason": "System design requires deep reasoning"
        },
        "contract-guardian": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.CRITICAL,
            "reason": "API contracts are critical - need highest accuracy"
        },
        "security-agent": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.CRITICAL,
            "reason": "Security analysis requires thorough reasoning"
        },
        "data-migration-agent": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.CRITICAL,
            "reason": "Data integrity is critical"
        },
        "database-agent": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.COMPLEX,
            "reason": "Schema design needs careful planning"
        },
        "pm-agent": {
            "primary": ModelTier.OPUS,
            "complexity_threshold": TaskComplexity.COMPLEX,
            "reason": "Project planning requires strategic thinking"
        }
    }
    
    # Fallback chains for each model
    FALLBACK_CHAINS = {
        ModelTier.OPUS: [ModelTier.OPUS, ModelTier.SONNET, ModelTier.HAIKU],
        ModelTier.SONNET: [ModelTier.SONNET, ModelTier.OPUS, ModelTier.HAIKU],
        ModelTier.HAIKU: [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]
    }
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.metrics_dir = self.claude_dir / "metrics"
        self.config_dir = self.claude_dir / "config"
        
        # Ensure directories exist
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self.model_config = self._load_model_config()
        self.performance_metrics = self._load_metrics()
        
        # Setup logging
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup model optimizer logger"""
        logger = logging.getLogger("AET_ModelOptimizer")
        logger.setLevel(logging.INFO)
        
        logs_dir = self.claude_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(logs_dir / "model_optimizer.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration"""
        config_file = self.config_dir / "model_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        # Default configuration
        default_config = {
            "available_models": {
                ModelTier.HAIKU.value: {
                    "available": True,
                    "rate_limit": 5000,  # requests per minute
                    "cost_per_1k": 0.00025,  # input tokens
                    "latency_ms": 200
                },
                ModelTier.SONNET.value: {
                    "available": True,
                    "rate_limit": 1000,
                    "cost_per_1k": 0.003,
                    "latency_ms": 500
                },
                ModelTier.OPUS.value: {
                    "available": True,
                    "rate_limit": 100,
                    "cost_per_1k": 0.015,
                    "latency_ms": 2000
                }
            },
            "rate_limit_buffer": 0.8,  # Use 80% of rate limit
            "max_retries": 3,
            "retry_delay": 1.0
        }
        
        # Save default config
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        return default_config
        
    def _load_metrics(self) -> Dict[str, Any]:
        """Load performance metrics"""
        metrics_file = self.metrics_dir / "model_metrics.json"
        
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        return {
            "agents": {},
            "models": {},
            "fallbacks": []
        }
        
    def select_model(self, agent_name: str, task_description: str,
                    complexity: TaskComplexity = None) -> Tuple[str, str]:
        """Select optimal model for agent and task"""
        
        # Get agent configuration
        agent_config = self.AGENT_MODEL_MAP.get(agent_name, {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Default configuration"
        })
        
        # Assess task complexity if not provided
        if complexity is None:
            complexity = self._assess_complexity(task_description)
            
        # Determine model based on complexity
        primary_model = agent_config["primary"]
        threshold = agent_config["complexity_threshold"]
        
        # Upgrade model if task is more complex than agent's threshold
        if complexity.value > threshold.value:
            # Upgrade to Opus for critical tasks
            if complexity == TaskComplexity.CRITICAL:
                selected_model = ModelTier.OPUS
            # Otherwise upgrade one tier
            elif primary_model == ModelTier.HAIKU:
                selected_model = ModelTier.SONNET
            else:
                selected_model = ModelTier.OPUS
        else:
            selected_model = primary_model
            
        # Check availability and get fallback if needed
        final_model = self._get_available_model(selected_model)
        
        # Log selection
        self.logger.info(
            f"Model selection: Agent={agent_name}, "
            f"Complexity={complexity.name}, "
            f"Selected={final_model.value}, "
            f"Reason={agent_config['reason']}"
        )
        
        # Record metrics
        self._record_selection(agent_name, final_model, complexity)
        
        return final_model.value, agent_config['reason']
        
    def _assess_complexity(self, task_description: str) -> TaskComplexity:
        """Assess task complexity from description"""
        
        # Keywords indicating complexity levels
        critical_keywords = [
            'security', 'authentication', 'encryption', 'contract',
            'breaking change', 'data migration', 'schema change',
            'production', 'critical', 'compliance'
        ]
        
        complex_keywords = [
            'architecture', 'design', 'refactor', 'optimize',
            'performance', 'scale', 'integration', 'algorithm'
        ]
        
        moderate_keywords = [
            'implement', 'feature', 'bug', 'test', 'update',
            'modify', 'enhance', 'improve'
        ]
        
        simple_keywords = [
            'fix', 'typo', 'rename', 'move', 'copy',
            'format', 'comment', 'log'
        ]
        
        task_lower = task_description.lower()
        
        # Check keywords in order of priority
        if any(kw in task_lower for kw in critical_keywords):
            return TaskComplexity.CRITICAL
        elif any(kw in task_lower for kw in complex_keywords):
            return TaskComplexity.COMPLEX
        elif any(kw in task_lower for kw in moderate_keywords):
            return TaskComplexity.MODERATE
        elif any(kw in task_lower for kw in simple_keywords):
            return TaskComplexity.SIMPLE
        else:
            # Default to moderate
            return TaskComplexity.MODERATE
            
    def _get_available_model(self, preferred: ModelTier) -> ModelTier:
        """Get available model using fallback chain"""
        
        fallback_chain = self.FALLBACK_CHAINS[preferred]
        
        for model in fallback_chain:
            model_info = self.model_config["available_models"].get(model.value, {})
            if model_info.get("available", False):
                # Check rate limits
                if self._check_rate_limit(model):
                    return model
                    
        # If nothing available, return Haiku as last resort
        self.logger.warning("No models available, defaulting to Haiku")
        return ModelTier.HAIKU
        
    def _check_rate_limit(self, model: ModelTier) -> bool:
        """Check if model is within rate limits"""
        
        model_metrics = self.performance_metrics.get("models", {}).get(model.value, {})
        current_rpm = model_metrics.get("requests_per_minute", 0)
        
        model_info = self.model_config["available_models"].get(model.value, {})
        rate_limit = model_info.get("rate_limit", 1000)
        buffer = self.model_config.get("rate_limit_buffer", 0.8)
        
        return current_rpm < (rate_limit * buffer)
        
    def _record_selection(self, agent: str, model: ModelTier, 
                         complexity: TaskComplexity):
        """Record model selection metrics"""
        
        # Update agent metrics
        if agent not in self.performance_metrics["agents"]:
            self.performance_metrics["agents"][agent] = {
                "selections": [],
                "model_usage": {}
            }
            
        agent_metrics = self.performance_metrics["agents"][agent]
        
        # Record selection
        agent_metrics["selections"].append({
            "timestamp": datetime.now().isoformat(),
            "model": model.value,
            "complexity": complexity.name
        })
        
        # Update model usage count
        if model.value not in agent_metrics["model_usage"]:
            agent_metrics["model_usage"][model.value] = 0
        agent_metrics["model_usage"][model.value] += 1
        
        # Keep only last 1000 selections
        if len(agent_metrics["selections"]) > 1000:
            agent_metrics["selections"] = agent_metrics["selections"][-1000:]
            
        # Save metrics
        self._save_metrics()
        
    def _save_metrics(self):
        """Save performance metrics"""
        metrics_file = self.metrics_dir / "model_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.performance_metrics, f, indent=2)
            
    def get_model_recommendation(self, agent: str) -> Dict[str, Any]:
        """Get model recommendation with explanation"""
        
        agent_config = self.AGENT_MODEL_MAP.get(agent, {
            "primary": ModelTier.SONNET,
            "complexity_threshold": TaskComplexity.MODERATE,
            "reason": "Default configuration"
        })
        
        return {
            "agent": agent,
            "recommended_model": agent_config["primary"].value,
            "complexity_threshold": agent_config["complexity_threshold"].name,
            "reason": agent_config["reason"],
            "fallback_chain": [m.value for m in self.FALLBACK_CHAINS[agent_config["primary"]]],
            "metrics": self.performance_metrics.get("agents", {}).get(agent, {})
        }
        
    def generate_selection_matrix(self) -> Dict[str, Dict[str, str]]:
        """Generate complete model selection matrix"""
        
        matrix = {}
        
        for agent, config in self.AGENT_MODEL_MAP.items():
            matrix[agent] = {
                "trivial": ModelTier.HAIKU.value,
                "simple": ModelTier.HAIKU.value if config["complexity_threshold"].value <= 2 
                         else config["primary"].value,
                "moderate": config["primary"].value,
                "complex": ModelTier.OPUS.value if config["primary"] != ModelTier.OPUS 
                          else config["primary"].value,
                "critical": ModelTier.OPUS.value
            }
            
        return matrix
        
    def optimize_for_cost(self, monthly_budget: float) -> Dict[str, Any]:
        """Optimize model selection for cost constraints"""
        
        # Calculate current monthly cost
        current_cost = 0
        recommendations = {}
        
        for agent, metrics in self.performance_metrics.get("agents", {}).items():
            agent_cost = 0
            for model, count in metrics.get("model_usage", {}).items():
                model_info = self.model_config["available_models"].get(model, {})
                cost_per_1k = model_info.get("cost_per_1k", 0.003)
                # Estimate tokens per request (rough average)
                estimated_tokens = 2000
                agent_cost += (count * estimated_tokens / 1000) * cost_per_1k
                
            current_cost += agent_cost
            
            # Recommend downgrades if over budget
            if current_cost > monthly_budget:
                agent_config = self.AGENT_MODEL_MAP.get(agent, {})
                if agent_config.get("primary") == ModelTier.OPUS:
                    recommendations[agent] = "Consider downgrading to Sonnet for non-critical tasks"
                elif agent_config.get("primary") == ModelTier.SONNET:
                    recommendations[agent] = "Consider using Haiku for simple tasks"
                    
        return {
            "current_monthly_cost": current_cost,
            "budget": monthly_budget,
            "within_budget": current_cost <= monthly_budget,
            "recommendations": recommendations
        }


def main():
    """CLI interface for model optimizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Model Optimizer")
    parser.add_argument('--select', metavar='AGENT:TASK',
                       help='Select model for agent and task')
    parser.add_argument('--recommend', metavar='AGENT',
                       help='Get model recommendation for agent')
    parser.add_argument('--matrix', action='store_true',
                       help='Generate selection matrix')
    parser.add_argument('--optimize-cost', metavar='BUDGET',
                       type=float, help='Optimize for monthly budget')
    parser.add_argument('--metrics', action='store_true',
                       help='Show performance metrics')
    
    args = parser.parse_args()
    
    optimizer = ModelOptimizer()
    
    if args.select:
        parts = args.select.split(':', 1)
        if len(parts) == 2:
            agent, task = parts
            model, reason = optimizer.select_model(agent, task)
            print(f"Selected Model: {model}")
            print(f"Reason: {reason}")
            
    elif args.recommend:
        rec = optimizer.get_model_recommendation(args.recommend)
        print(f"Agent: {rec['agent']}")
        print(f"Recommended Model: {rec['recommended_model']}")
        print(f"Complexity Threshold: {rec['complexity_threshold']}")
        print(f"Reason: {rec['reason']}")
        print(f"Fallback Chain: {' → '.join(rec['fallback_chain'])}")
        
    elif args.matrix:
        matrix = optimizer.generate_selection_matrix()
        print("Model Selection Matrix:")
        print("-" * 80)
        print(f"{'Agent':<30} {'Trivial':<10} {'Simple':<10} {'Moderate':<10} {'Complex':<10} {'Critical':<10}")
        print("-" * 80)
        for agent, models in sorted(matrix.items()):
            print(f"{agent:<30} {models['trivial']:<10} {models['simple']:<10} "
                  f"{models['moderate']:<10} {models['complex']:<10} {models['critical']:<10}")
            
    elif args.optimize_cost:
        result = optimizer.optimize_for_cost(args.optimize_cost)
        print(f"Current Monthly Cost: ${result['current_monthly_cost']:.2f}")
        print(f"Budget: ${result['budget']:.2f}")
        print(f"Within Budget: {result['within_budget']}")
        if result['recommendations']:
            print("\nRecommendations:")
            for agent, rec in result['recommendations'].items():
                print(f"  • {agent}: {rec}")
                
    elif args.metrics:
        metrics = optimizer.performance_metrics
        print("Model Performance Metrics:")
        for agent, data in metrics.get("agents", {}).items():
            print(f"\n{agent}:")
            for model, count in data.get("model_usage", {}).items():
                print(f"  {model}: {count} requests")
                
    else:
        parser.print_help()


if __name__ == "__main__":
    main()