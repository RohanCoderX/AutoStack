from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import os
import logging
from dotenv import load_dotenv

from .generators.terraform_generator import TerraformGenerator
from .generators.cdk_generator import CDKGenerator
from .generators.cost_calculator import CostCalculator
from .generators.optimizer import InfrastructureOptimizer
from .utils.logger import setup_logger

load_dotenv()

app = FastAPI(
    title="AutoStack Infrastructure Generation Service",
    description="Generate optimized cloud infrastructure templates",
    version="1.0.0"
)

logger = setup_logger(__name__)
terraform_gen = TerraformGenerator()
cdk_gen = CDKGenerator()
cost_calc = CostCalculator()
optimizer = InfrastructureOptimizer()

class GenerateRequest(BaseModel):
    projectId: str
    projectName: str
    requirements: Dict[str, Any]
    templateType: str = "terraform"
    optimizationLevel: str = "balanced"
    subscriptionTier: str = "free"

class CostEstimateRequest(BaseModel):
    resources: Dict[str, Any]
    region: str = "us-west-2"

class OptimizeRequest(BaseModel):
    template: str
    resources: Dict[str, Any]
    optimizationGoals: List[str] = ["cost", "performance"]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "infrastructure-generation",
        "terraform_version": terraform_gen.get_version()
    }

@app.post("/generate")
async def generate_infrastructure(request: GenerateRequest):
    """Generate infrastructure template from requirements"""
    try:
        logger.info(f"Generating {request.templateType} template for project {request.projectId}")
        
        # Validate requirements
        if not request.requirements:
            raise HTTPException(status_code=400, detail="Requirements are required")
        
        # Apply subscription tier limitations
        filtered_requirements = _apply_tier_limits(request.requirements, request.subscriptionTier)
        
        # Generate template based on type
        if request.templateType == "terraform":
            template = await terraform_gen.generate(
                project_name=request.projectName,
                requirements=filtered_requirements,
                optimization_level=request.optimizationLevel
            )
        elif request.templateType == "cdk":
            template = await cdk_gen.generate(
                project_name=request.projectName,
                requirements=filtered_requirements,
                optimization_level=request.optimizationLevel
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported template type")
        
        # Calculate estimated cost
        estimated_cost = await cost_calc.calculate_monthly_cost(
            filtered_requirements,
            region="us-west-2"
        )
        
        # Get optimization suggestions
        optimization_suggestions = await optimizer.get_suggestions(
            filtered_requirements,
            request.optimizationLevel
        )
        
        # Extract resources for tracking
        resources = _extract_resources(filtered_requirements)
        
        return {
            "template": template,
            "estimatedCost": estimated_cost,
            "resources": resources,
            "optimizationSuggestions": optimization_suggestions
        }
        
    except Exception as e:
        logger.error(f"Template generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate template: {str(e)}")

@app.post("/estimate-cost")
async def estimate_cost(request: CostEstimateRequest):
    """Estimate infrastructure costs"""
    try:
        monthly_cost = await cost_calc.calculate_monthly_cost(
            request.resources,
            request.region
        )
        
        yearly_cost = monthly_cost * 12
        
        # Get cost breakdown
        breakdown = await cost_calc.get_cost_breakdown(
            request.resources,
            request.region
        )
        
        return {
            "monthlyCost": monthly_cost,
            "yearlyCost": yearly_cost,
            "breakdown": breakdown,
            "region": request.region
        }
        
    except Exception as e:
        logger.error(f"Cost estimation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to estimate cost")

@app.post("/optimize")
async def optimize_infrastructure(request: OptimizeRequest):
    """Optimize existing infrastructure template"""
    try:
        # Parse existing template to extract resources
        resources = _parse_template_resources(request.template)
        
        # Apply optimizations
        optimized_resources = await optimizer.optimize(
            resources,
            request.optimizationGoals
        )
        
        # Generate optimized template
        optimized_template = await terraform_gen.generate(
            project_name="optimized",
            requirements=optimized_resources,
            optimization_level="aggressive"
        )
        
        # Calculate new cost
        estimated_cost = await cost_calc.calculate_monthly_cost(
            optimized_resources,
            region="us-west-2"
        )
        
        # Get optimization suggestions
        optimization_suggestions = await optimizer.get_suggestions(
            optimized_resources,
            "aggressive"
        )
        
        return {
            "optimizedTemplate": optimized_template,
            "estimatedCost": estimated_cost,
            "optimizationSuggestions": optimization_suggestions
        }
        
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(status_code=500, detail="Failed to optimize template")

@app.get("/templates/examples")
async def get_template_examples():
    """Get example templates for different use cases"""
    return {
        "examples": [
            {
                "name": "Simple Web App",
                "description": "Basic web application with database",
                "requirements": {
                    "compute": {"type": "container", "cpu": "0.5", "memory": "1Gi"},
                    "database": {"type": "postgresql", "size": "db.t3.micro"},
                    "network": {"load_balancer": True}
                }
            },
            {
                "name": "Microservices",
                "description": "Multi-service architecture with API gateway",
                "requirements": {
                    "compute": {"type": "container", "cpu": "1", "memory": "2Gi", "replicas": 3},
                    "database": {"type": "postgresql", "size": "db.t3.small"},
                    "cache": {"type": "redis", "size": "cache.t3.micro"},
                    "network": {"api_gateway": True, "load_balancer": True}
                }
            },
            {
                "name": "Data Processing",
                "description": "Batch processing with queues and storage",
                "requirements": {
                    "compute": {"type": "lambda", "memory": "1024MB"},
                    "storage": {"type": "s3", "size": "100GB"},
                    "queue": {"type": "sqs", "visibility_timeout": 300}
                }
            }
        ]
    }

def _apply_tier_limits(requirements: Dict[str, Any], tier: str) -> Dict[str, Any]:
    """Apply subscription tier limitations to requirements"""
    limits = {
        "free": {
            "max_instances": 2,
            "max_storage": "20GB",
            "features": ["basic_monitoring"]
        },
        "starter": {
            "max_instances": 10,
            "max_storage": "100GB",
            "features": ["basic_monitoring", "auto_scaling"]
        },
        "pro": {
            "max_instances": 50,
            "max_storage": "1TB",
            "features": ["basic_monitoring", "auto_scaling", "advanced_security"]
        },
        "enterprise": {
            "max_instances": -1,  # unlimited
            "max_storage": "unlimited",
            "features": ["basic_monitoring", "auto_scaling", "advanced_security", "custom_vpc"]
        }
    }
    
    tier_limits = limits.get(tier, limits["free"])
    filtered = requirements.copy()
    
    # Apply instance limits
    if "compute" in filtered and tier_limits["max_instances"] > 0:
        if "replicas" in filtered["compute"]:
            filtered["compute"]["replicas"] = min(
                filtered["compute"]["replicas"],
                tier_limits["max_instances"]
            )
    
    return filtered

def _extract_resources(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Extract resource summary from requirements"""
    resources = {}
    
    if "compute" in requirements:
        resources["compute"] = requirements["compute"]["type"]
    
    if "database" in requirements:
        resources["database"] = requirements["database"]["type"]
    
    if "cache" in requirements:
        resources["cache"] = requirements["cache"]["type"]
    
    if "storage" in requirements:
        resources["storage"] = requirements["storage"]["type"]
    
    return resources

def _parse_template_resources(template: str) -> Dict[str, Any]:
    """Parse Terraform template to extract resources"""
    # Simplified parsing - in production, use proper HCL parser
    resources = {}
    
    if "aws_instance" in template:
        resources["compute"] = {"type": "ec2"}
    elif "aws_ecs_service" in template:
        resources["compute"] = {"type": "container"}
    
    if "aws_db_instance" in template:
        resources["database"] = {"type": "rds"}
    
    if "aws_elasticache" in template:
        resources["cache"] = {"type": "redis"}
    
    return resources

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)