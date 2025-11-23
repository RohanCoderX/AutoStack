from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import logging
from dotenv import load_dotenv

from .deployers.terraform_deployer import TerraformDeployer
from .deployers.aws_manager import AWSManager
from .utils.database import DatabaseManager
from .utils.logger import setup_logger

load_dotenv()

app = FastAPI(
    title="AutoStack Deployment Service",
    description="Deploy and manage cloud infrastructure",
    version="1.0.0"
)

logger = setup_logger(__name__)
db_manager = DatabaseManager()
terraform_deployer = TerraformDeployer()
aws_manager = AWSManager()

class DeployRequest(BaseModel):
    deploymentId: str
    template: str
    templateType: str = "terraform"
    projectName: str
    awsCredentials: Optional[Dict[str, str]] = None
    region: str = "us-west-2"

class CancelRequest(BaseModel):
    deploymentId: str

class DestroyRequest(BaseModel):
    deploymentId: str
    stateUrl: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await db_manager.connect()
    logger.info("Deployment Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_manager.disconnect()
    logger.info("Deployment Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db_manager.execute("SELECT 1")
        terraform_version = terraform_deployer.get_terraform_version()
        aws_version = aws_manager.get_aws_cli_version()
        
        return {
            "status": "healthy",
            "service": "deployment",
            "terraform_version": terraform_version,
            "aws_cli_version": aws_version,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/deploy")
async def deploy_infrastructure(request: DeployRequest, background_tasks: BackgroundTasks):
    """Deploy infrastructure using Terraform"""
    try:
        logger.info(f"Starting deployment {request.deploymentId}")
        
        # Update deployment status to running
        await db_manager.execute(
            "UPDATE deployments SET status = $1 WHERE id = $2",
            "running", request.deploymentId
        )
        
        # Start deployment in background
        background_tasks.add_task(
            execute_deployment,
            request.deploymentId,
            request.template,
            request.templateType,
            request.projectName,
            request.awsCredentials,
            request.region
        )
        
        return {
            "message": "Deployment started",
            "deploymentId": request.deploymentId,
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Deployment start error: {e}")
        
        # Update status to failed
        await db_manager.execute(
            "UPDATE deployments SET status = $1, error_message = $2 WHERE id = $3",
            "failed", str(e), request.deploymentId
        )
        
        raise HTTPException(status_code=500, detail="Failed to start deployment")

@app.post("/cancel")
async def cancel_deployment(request: CancelRequest):
    """Cancel running deployment"""
    try:
        # Get deployment info
        deployment = await db_manager.fetch_one(
            "SELECT status FROM deployments WHERE id = $1",
            request.deploymentId
        )
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        if deployment["status"] not in ["pending", "running"]:
            raise HTTPException(status_code=400, detail="Cannot cancel deployment in current status")
        
        # Cancel the deployment
        success = await terraform_deployer.cancel_deployment(request.deploymentId)
        
        if success:
            await db_manager.execute(
                "UPDATE deployments SET status = $1 WHERE id = $2",
                "cancelled", request.deploymentId
            )
            return {"message": "Deployment cancelled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel deployment")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel deployment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel deployment")

@app.post("/destroy")
async def destroy_infrastructure(request: DestroyRequest, background_tasks: BackgroundTasks):
    """Destroy deployed infrastructure"""
    try:
        logger.info(f"Starting destruction of deployment {request.deploymentId}")
        
        # Update deployment status
        await db_manager.execute(
            "UPDATE deployments SET status = $1 WHERE id = $2",
            "destroying", request.deploymentId
        )
        
        # Start destruction in background
        background_tasks.add_task(
            execute_destruction,
            request.deploymentId,
            request.stateUrl
        )
        
        return {
            "message": "Infrastructure destruction started",
            "deploymentId": request.deploymentId,
            "status": "destroying"
        }
        
    except Exception as e:
        logger.error(f"Destruction start error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start destruction")

@app.get("/deployment/{deployment_id}/status")
async def get_deployment_status(deployment_id: str):
    """Get deployment status and logs"""
    try:
        deployment = await db_manager.fetch_one(
            "SELECT status, deployment_url, error_message, logs, deployed_at FROM deployments WHERE id = $1",
            deployment_id
        )
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        return {
            "deploymentId": deployment_id,
            "status": deployment["status"],
            "deploymentUrl": deployment["deployment_url"],
            "errorMessage": deployment["error_message"],
            "logs": deployment["logs"],
            "deployedAt": deployment["deployed_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get deployment status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deployment status")

@app.get("/deployment/{deployment_id}/outputs")
async def get_deployment_outputs(deployment_id: str):
    """Get Terraform outputs from deployment"""
    try:
        outputs = await terraform_deployer.get_outputs(deployment_id)
        return {"outputs": outputs}
        
    except Exception as e:
        logger.error(f"Get deployment outputs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deployment outputs")

async def execute_deployment(
    deployment_id: str,
    template: str,
    template_type: str,
    project_name: str,
    aws_credentials: Optional[Dict[str, str]],
    region: str
):
    """Background task to execute deployment"""
    try:
        logger.info(f"Executing deployment {deployment_id}")
        
        # Set up AWS credentials if provided
        if aws_credentials:
            aws_manager.set_credentials(
                aws_credentials.get("accessKeyId"),
                aws_credentials.get("secretAccessKey"),
                region
            )
        
        # Deploy using Terraform
        result = await terraform_deployer.deploy(
            deployment_id=deployment_id,
            template=template,
            project_name=project_name,
            region=region
        )
        
        if result["success"]:
            # Update deployment as completed
            await db_manager.execute("""
                UPDATE deployments 
                SET status = $1, deployment_url = $2, terraform_state_url = $3, 
                    logs = $4, deployed_at = NOW()
                WHERE id = $5
            """, "completed", result.get("deployment_url"), result.get("state_url"), 
                result.get("logs"), deployment_id)
            
            logger.info(f"Deployment {deployment_id} completed successfully")
        else:
            # Update deployment as failed
            await db_manager.execute(
                "UPDATE deployments SET status = $1, error_message = $2, logs = $3 WHERE id = $4",
                "failed", result.get("error"), result.get("logs"), deployment_id
            )
            
            logger.error(f"Deployment {deployment_id} failed: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"Deployment execution error: {e}")
        
        # Update deployment as failed
        await db_manager.execute(
            "UPDATE deployments SET status = $1, error_message = $2 WHERE id = $3",
            "failed", str(e), deployment_id
        )

async def execute_destruction(deployment_id: str, state_url: Optional[str]):
    """Background task to execute infrastructure destruction"""
    try:
        logger.info(f"Executing destruction of deployment {deployment_id}")
        
        result = await terraform_deployer.destroy(
            deployment_id=deployment_id,
            state_url=state_url
        )
        
        if result["success"]:
            await db_manager.execute(
                "UPDATE deployments SET status = $1, logs = $2 WHERE id = $3",
                "destroyed", result.get("logs"), deployment_id
            )
            logger.info(f"Deployment {deployment_id} destroyed successfully")
        else:
            await db_manager.execute(
                "UPDATE deployments SET status = $1, error_message = $2, logs = $3 WHERE id = $4",
                "destroy_failed", result.get("error"), result.get("logs"), deployment_id
            )
            logger.error(f"Destruction {deployment_id} failed: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"Destruction execution error: {e}")
        
        await db_manager.execute(
            "UPDATE deployments SET status = $1, error_message = $2 WHERE id = $3",
            "destroy_failed", str(e), deployment_id
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)