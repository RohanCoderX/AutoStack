from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class InfrastructureOptimizer:
    """Optimize infrastructure configurations for cost and performance"""
    
    def __init__(self):
        self.optimization_rules = {
            "cost": [
                "use_spot_instances",
                "right_size_instances",
                "use_reserved_instances",
                "optimize_storage_tiers",
                "reduce_data_transfer"
            ],
            "performance": [
                "use_ssd_storage",
                "enable_auto_scaling",
                "use_cdn",
                "optimize_database",
                "enable_caching"
            ],
            "security": [
                "enable_encryption",
                "use_private_subnets",
                "enable_vpc_flow_logs",
                "use_secrets_manager",
                "enable_cloudtrail"
            ],
            "reliability": [
                "multi_az_deployment",
                "enable_backups",
                "use_health_checks",
                "implement_circuit_breakers",
                "enable_monitoring"
            ]
        }
    
    async def optimize(self, requirements: Dict[str, Any], optimization_goals: List[str]) -> Dict[str, Any]:
        """Optimize infrastructure requirements based on goals"""
        try:
            optimized = requirements.copy()
            
            for goal in optimization_goals:
                if goal in self.optimization_rules:
                    optimized = await self._apply_optimization_rules(
                        optimized, 
                        self.optimization_rules[goal]
                    )
            
            return optimized
            
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return requirements
    
    async def get_suggestions(self, requirements: Dict[str, Any], optimization_level: str = "balanced") -> List[Dict[str, Any]]:
        """Get optimization suggestions based on requirements"""
        suggestions = []
        
        # Compute optimizations
        if "compute" in requirements:
            compute_suggestions = await self._get_compute_suggestions(
                requirements["compute"], 
                optimization_level
            )
            suggestions.extend(compute_suggestions)
        
        # Database optimizations
        if "database" in requirements:
            db_suggestions = await self._get_database_suggestions(
                requirements["database"], 
                optimization_level
            )
            suggestions.extend(db_suggestions)
        
        # Storage optimizations
        if "storage" in requirements:
            storage_suggestions = await self._get_storage_suggestions(
                requirements["storage"], 
                optimization_level
            )
            suggestions.extend(storage_suggestions)
        
        # Network optimizations
        if "network" in requirements:
            network_suggestions = await self._get_network_suggestions(
                requirements["network"], 
                optimization_level
            )
            suggestions.extend(network_suggestions)
        
        return suggestions
    
    async def _apply_optimization_rules(self, requirements: Dict[str, Any], rules: List[str]) -> Dict[str, Any]:
        """Apply specific optimization rules"""
        optimized = requirements.copy()
        
        for rule in rules:
            if rule == "use_spot_instances":
                optimized = self._optimize_spot_instances(optimized)
            elif rule == "right_size_instances":
                optimized = self._right_size_instances(optimized)
            elif rule == "optimize_storage_tiers":
                optimized = self._optimize_storage_tiers(optimized)
            elif rule == "enable_auto_scaling":
                optimized = self._enable_auto_scaling(optimized)
            elif rule == "enable_encryption":
                optimized = self._enable_encryption(optimized)
            elif rule == "multi_az_deployment":
                optimized = self._enable_multi_az(optimized)
        
        return optimized
    
    def _optimize_spot_instances(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize for spot instances where appropriate"""
        if "compute" in requirements:
            compute = requirements["compute"]
            if compute.get("type") == "ec2" and not compute.get("critical", False):
                compute["spot_instances"] = True
                compute["spot_max_price"] = "0.05"  # Max price per hour
        
        return requirements
    
    def _right_size_instances(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Right-size instances based on usage patterns"""
        if "compute" in requirements:
            compute = requirements["compute"]
            
            # Suggest smaller instances for low-traffic applications
            if compute.get("type") == "container":
                current_cpu = float(compute.get("cpu", "0.25"))
                current_memory = compute.get("memory", "512Mi")
                
                if current_cpu > 1.0:
                    compute["cpu"] = "0.5"
                    compute["suggested_reason"] = "Reduced CPU allocation for cost optimization"
                
                if "Gi" in current_memory and float(current_memory.replace("Gi", "")) > 2:
                    compute["memory"] = "1Gi"
                    compute["suggested_reason"] = "Reduced memory allocation for cost optimization"
        
        return requirements
    
    def _optimize_storage_tiers(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize storage tiers"""
        if "storage" in requirements:
            storage = requirements["storage"]
            if storage.get("type") == "s3":
                storage["intelligent_tiering"] = True
                storage["lifecycle_policy"] = {
                    "transition_to_ia": 30,  # days
                    "transition_to_glacier": 90  # days
                }
        
        return requirements
    
    def _enable_auto_scaling(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Enable auto-scaling for compute resources"""
        if "compute" in requirements:
            compute = requirements["compute"]
            if not compute.get("auto_scaling"):
                compute["auto_scaling"] = {
                    "min_capacity": 1,
                    "max_capacity": compute.get("replicas", 1) * 3,
                    "target_cpu_utilization": 70,
                    "scale_out_cooldown": 300,
                    "scale_in_cooldown": 300
                }
        
        return requirements
    
    def _enable_encryption(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Enable encryption for all resources"""
        # Database encryption
        if "database" in requirements:
            requirements["database"]["encryption_at_rest"] = True
            requirements["database"]["encryption_in_transit"] = True
        
        # Storage encryption
        if "storage" in requirements:
            requirements["storage"]["encryption"] = "AES256"
        
        # Cache encryption
        if "cache" in requirements:
            requirements["cache"]["encryption_at_rest"] = True
            requirements["cache"]["encryption_in_transit"] = True
        
        return requirements
    
    def _enable_multi_az(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Enable multi-AZ deployment for high availability"""
        if "database" in requirements:
            requirements["database"]["multi_az"] = True
        
        if "compute" in requirements:
            compute = requirements["compute"]
            if not compute.get("availability_zones"):
                compute["availability_zones"] = ["us-west-2a", "us-west-2b", "us-west-2c"]
        
        return requirements
    
    async def _get_compute_suggestions(self, compute: Dict[str, Any], level: str) -> List[Dict[str, Any]]:
        """Get compute optimization suggestions"""
        suggestions = []
        
        if compute.get("type") == "ec2":
            suggestions.append({
                "category": "compute",
                "type": "cost_optimization",
                "title": "Consider Fargate over EC2",
                "description": "Fargate can be more cost-effective for containerized workloads",
                "impact": "medium",
                "effort": "low",
                "estimated_savings": "20-30%"
            })
        
        if not compute.get("auto_scaling"):
            suggestions.append({
                "category": "compute",
                "type": "performance",
                "title": "Enable Auto Scaling",
                "description": "Automatically scale based on demand to optimize costs and performance",
                "impact": "high",
                "effort": "medium",
                "estimated_savings": "15-25%"
            })
        
        if level in ["aggressive", "cost"] and not compute.get("spot_instances"):
            suggestions.append({
                "category": "compute",
                "type": "cost_optimization",
                "title": "Use Spot Instances",
                "description": "Use spot instances for non-critical workloads to save up to 90%",
                "impact": "high",
                "effort": "medium",
                "estimated_savings": "60-90%"
            })
        
        return suggestions
    
    async def _get_database_suggestions(self, database: Dict[str, Any], level: str) -> List[Dict[str, Any]]:
        """Get database optimization suggestions"""
        suggestions = []
        
        if not database.get("multi_az"):
            suggestions.append({
                "category": "database",
                "type": "reliability",
                "title": "Enable Multi-AZ Deployment",
                "description": "Improve availability and durability with multi-AZ deployment",
                "impact": "high",
                "effort": "low",
                "estimated_cost_increase": "100%"
            })
        
        if database.get("type") == "postgresql" and level in ["performance", "balanced"]:
            suggestions.append({
                "category": "database",
                "type": "performance",
                "title": "Consider Aurora PostgreSQL",
                "description": "Aurora provides better performance and automatic scaling",
                "impact": "high",
                "effort": "medium",
                "estimated_performance_gain": "3-5x"
            })
        
        if not database.get("read_replicas") and level == "performance":
            suggestions.append({
                "category": "database",
                "type": "performance",
                "title": "Add Read Replicas",
                "description": "Improve read performance with read replicas",
                "impact": "medium",
                "effort": "low",
                "estimated_performance_gain": "2-3x"
            })
        
        return suggestions
    
    async def _get_storage_suggestions(self, storage: Dict[str, Any], level: str) -> List[Dict[str, Any]]:
        """Get storage optimization suggestions"""
        suggestions = []
        
        if storage.get("type") == "s3" and not storage.get("intelligent_tiering"):
            suggestions.append({
                "category": "storage",
                "type": "cost_optimization",
                "title": "Enable S3 Intelligent Tiering",
                "description": "Automatically optimize storage costs based on access patterns",
                "impact": "medium",
                "effort": "low",
                "estimated_savings": "20-40%"
            })
        
        if not storage.get("lifecycle_policy"):
            suggestions.append({
                "category": "storage",
                "type": "cost_optimization",
                "title": "Implement Lifecycle Policies",
                "description": "Automatically transition objects to cheaper storage classes",
                "impact": "medium",
                "effort": "low",
                "estimated_savings": "30-50%"
            })
        
        return suggestions
    
    async def _get_network_suggestions(self, network: Dict[str, Any], level: str) -> List[Dict[str, Any]]:
        """Get network optimization suggestions"""
        suggestions = []
        
        if not network.get("cdn"):
            suggestions.append({
                "category": "network",
                "type": "performance",
                "title": "Add CloudFront CDN",
                "description": "Improve performance and reduce data transfer costs",
                "impact": "high",
                "effort": "low",
                "estimated_performance_gain": "50-80%",
                "estimated_savings": "10-20%"
            })
        
        if network.get("load_balancer") and level == "cost":
            suggestions.append({
                "category": "network",
                "type": "cost_optimization",
                "title": "Consider Network Load Balancer",
                "description": "NLB can be more cost-effective for simple load balancing",
                "impact": "low",
                "effort": "medium",
                "estimated_savings": "25%"
            })
        
        return suggestions