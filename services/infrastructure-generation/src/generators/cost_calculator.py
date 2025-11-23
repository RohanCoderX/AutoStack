import boto3
import json
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class CostCalculator:
    """Calculate AWS infrastructure costs"""
    
    def __init__(self):
        # AWS Pricing data (simplified - in production, use AWS Pricing API)
        self.pricing = {
            "us-west-2": {
                "ec2": {
                    "t3.nano": 0.0052,
                    "t3.micro": 0.0104,
                    "t3.small": 0.0208,
                    "t3.medium": 0.0416,
                    "t3.large": 0.0832,
                    "t3.xlarge": 0.1664
                },
                "rds": {
                    "db.t3.micro": 0.017,
                    "db.t3.small": 0.034,
                    "db.t3.medium": 0.068,
                    "db.t3.large": 0.136
                },
                "elasticache": {
                    "cache.t3.micro": 0.017,
                    "cache.t3.small": 0.034,
                    "cache.t3.medium": 0.068
                },
                "fargate": {
                    "cpu_per_vcpu": 0.04048,  # per vCPU per hour
                    "memory_per_gb": 0.004445  # per GB per hour
                },
                "lambda": {
                    "requests": 0.0000002,  # per request
                    "duration": 0.0000166667  # per GB-second
                },
                "s3": {
                    "standard": 0.023,  # per GB per month
                    "requests_put": 0.0005,  # per 1000 requests
                    "requests_get": 0.0004   # per 1000 requests
                },
                "alb": 0.0225,  # per hour
                "nat_gateway": 0.045,  # per hour
                "data_transfer": 0.09  # per GB
            }
        }
    
    async def calculate_monthly_cost(self, requirements: Dict[str, Any], region: str = "us-west-2") -> float:
        """Calculate total monthly cost for infrastructure"""
        try:
            total_cost = 0.0
            region_pricing = self.pricing.get(region, self.pricing["us-west-2"])
            
            # Compute costs
            if "compute" in requirements:
                compute_cost = await self._calculate_compute_cost(requirements["compute"], region_pricing)
                total_cost += compute_cost
            
            # Database costs
            if "database" in requirements:
                db_cost = await self._calculate_database_cost(requirements["database"], region_pricing)
                total_cost += db_cost
            
            # Cache costs
            if "cache" in requirements:
                cache_cost = await self._calculate_cache_cost(requirements["cache"], region_pricing)
                total_cost += cache_cost
            
            # Storage costs
            if "storage" in requirements:
                storage_cost = await self._calculate_storage_cost(requirements["storage"], region_pricing)
                total_cost += storage_cost
            
            # Network costs
            if "network" in requirements:
                network_cost = await self._calculate_network_cost(requirements["network"], region_pricing)
                total_cost += network_cost
            
            # Queue costs (minimal for SQS)
            if "queue" in requirements:
                total_cost += 1.0  # Approximate SQS cost
            
            return round(total_cost, 2)
            
        except Exception as e:
            logger.error(f"Cost calculation error: {e}")
            return 0.0
    
    async def _calculate_compute_cost(self, compute: Dict[str, Any], pricing: Dict) -> float:
        """Calculate compute costs"""
        compute_type = compute.get("type", "container")
        
        if compute_type == "ec2":
            instance_type = compute.get("size", "t3.micro")
            instance_count = compute.get("replicas", 1)
            hourly_cost = pricing["ec2"].get(instance_type, 0.0104)
            return hourly_cost * 24 * 30 * instance_count
        
        elif compute_type == "container":
            # Fargate pricing
            cpu = float(compute.get("cpu", "0.25"))
            memory_gb = self._parse_memory(compute.get("memory", "512Mi"))
            replicas = compute.get("replicas", 1)
            
            cpu_cost = cpu * pricing["fargate"]["cpu_per_vcpu"] * 24 * 30
            memory_cost = memory_gb * pricing["fargate"]["memory_per_gb"] * 24 * 30
            
            return (cpu_cost + memory_cost) * replicas
        
        elif compute_type == "lambda":
            # Simplified Lambda cost calculation
            memory_mb = compute.get("memory", 128)
            monthly_invocations = compute.get("monthly_invocations", 1000)
            avg_duration_ms = compute.get("avg_duration_ms", 1000)
            
            gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * monthly_invocations
            
            request_cost = monthly_invocations * pricing["lambda"]["requests"]
            duration_cost = gb_seconds * pricing["lambda"]["duration"]
            
            return request_cost + duration_cost
        
        return 0.0
    
    async def _calculate_database_cost(self, database: Dict[str, Any], pricing: Dict) -> float:
        """Calculate database costs"""
        instance_type = database.get("size", "db.t3.micro")
        hourly_cost = pricing["rds"].get(instance_type, 0.017)
        
        # Storage cost (20GB default)
        storage_gb = int(database.get("storage", "20GB").replace("GB", ""))
        storage_cost = storage_gb * 0.115  # GP2 storage cost per GB per month
        
        return (hourly_cost * 24 * 30) + storage_cost
    
    async def _calculate_cache_cost(self, cache: Dict[str, Any], pricing: Dict) -> float:
        """Calculate cache costs"""
        instance_type = cache.get("size", "cache.t3.micro")
        hourly_cost = pricing["elasticache"].get(instance_type, 0.017)
        
        return hourly_cost * 24 * 30
    
    async def _calculate_storage_cost(self, storage: Dict[str, Any], pricing: Dict) -> float:
        """Calculate storage costs"""
        storage_type = storage.get("type", "s3")
        
        if storage_type == "s3":
            size_gb = self._parse_storage_size(storage.get("size", "10GB"))
            monthly_requests = storage.get("monthly_requests", 1000)
            
            storage_cost = size_gb * pricing["s3"]["standard"]
            request_cost = (monthly_requests / 1000) * pricing["s3"]["requests_get"]
            
            return storage_cost + request_cost
        
        return 0.0
    
    async def _calculate_network_cost(self, network: Dict[str, Any], pricing: Dict) -> float:
        """Calculate network costs"""
        cost = 0.0
        
        # Load balancer
        if network.get("load_balancer"):
            cost += pricing["alb"] * 24 * 30
        
        # NAT Gateway (if private subnets)
        if network.get("nat_gateway", True):
            cost += pricing["nat_gateway"] * 24 * 30
        
        # Data transfer (estimate 100GB/month)
        data_transfer_gb = network.get("data_transfer_gb", 100)
        if data_transfer_gb > 1:  # First 1GB free
            cost += (data_transfer_gb - 1) * pricing["data_transfer"]
        
        return cost
    
    async def get_cost_breakdown(self, requirements: Dict[str, Any], region: str = "us-west-2") -> Dict[str, float]:
        """Get detailed cost breakdown"""
        breakdown = {}
        region_pricing = self.pricing.get(region, self.pricing["us-west-2"])
        
        if "compute" in requirements:
            breakdown["compute"] = await self._calculate_compute_cost(requirements["compute"], region_pricing)
        
        if "database" in requirements:
            breakdown["database"] = await self._calculate_database_cost(requirements["database"], region_pricing)
        
        if "cache" in requirements:
            breakdown["cache"] = await self._calculate_cache_cost(requirements["cache"], region_pricing)
        
        if "storage" in requirements:
            breakdown["storage"] = await self._calculate_storage_cost(requirements["storage"], region_pricing)
        
        if "network" in requirements:
            breakdown["network"] = await self._calculate_network_cost(requirements["network"], region_pricing)
        
        return breakdown
    
    def _parse_memory(self, memory_str: str) -> float:
        """Parse memory string to GB"""
        if memory_str.endswith("Mi"):
            return float(memory_str[:-2]) / 1024
        elif memory_str.endswith("Gi"):
            return float(memory_str[:-2])
        elif memory_str.endswith("MB"):
            return float(memory_str[:-2]) / 1024
        elif memory_str.endswith("GB"):
            return float(memory_str[:-2])
        else:
            # Assume MB
            return float(memory_str) / 1024
    
    def _parse_storage_size(self, size_str: str) -> float:
        """Parse storage size string to GB"""
        if size_str.endswith("GB"):
            return float(size_str[:-2])
        elif size_str.endswith("TB"):
            return float(size_str[:-2]) * 1024
        else:
            # Assume GB
            return float(size_str)
    
    async def get_cost_optimization_suggestions(self, requirements: Dict[str, Any], current_cost: float) -> List[Dict[str, Any]]:
        """Get cost optimization suggestions"""
        suggestions = []
        
        # Compute optimizations
        if "compute" in requirements:
            compute = requirements["compute"]
            if compute.get("type") == "ec2":
                suggestions.append({
                    "type": "compute",
                    "suggestion": "Consider using Fargate containers instead of EC2 for better cost efficiency",
                    "potential_savings": current_cost * 0.2
                })
            
            if compute.get("replicas", 1) > 1:
                suggestions.append({
                    "type": "compute",
                    "suggestion": "Implement auto-scaling to reduce costs during low traffic periods",
                    "potential_savings": current_cost * 0.15
                })
        
        # Database optimizations
        if "database" in requirements:
            db = requirements["database"]
            if db.get("size", "").startswith("db.t3."):
                suggestions.append({
                    "type": "database",
                    "suggestion": "Consider using Aurora Serverless for variable workloads",
                    "potential_savings": current_cost * 0.3
                })
        
        # Storage optimizations
        if "storage" in requirements:
            suggestions.append({
                "type": "storage",
                "suggestion": "Use S3 Intelligent Tiering to automatically optimize storage costs",
                "potential_savings": current_cost * 0.1
            })
        
        return suggestions