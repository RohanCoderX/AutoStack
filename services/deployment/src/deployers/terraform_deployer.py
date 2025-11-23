import os
import subprocess
import tempfile
import shutil
import json
from typing import Dict, Any, Optional
import logging
import asyncio
from python_terraform import Terraform

logger = logging.getLogger(__name__)

class TerraformDeployer:
    """Deploy infrastructure using Terraform"""
    
    def __init__(self):
        self.workspace_dir = "/tmp/terraform_workspaces"
        self.state_bucket = os.getenv("TERRAFORM_STATE_BUCKET", "autostack-terraform-state")
        self.running_deployments = {}
        
        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    def get_terraform_version(self) -> str:
        """Get Terraform version"""
        try:
            result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
            return result.stdout.split('\n')[0] if result.returncode == 0 else "unknown"
        except:
            return "not_installed"
    
    async def deploy(self, deployment_id: str, template: str, project_name: str, region: str) -> Dict[str, Any]:
        """Deploy infrastructure using Terraform"""
        workspace_path = None
        try:
            # Create workspace directory
            workspace_path = os.path.join(self.workspace_dir, deployment_id)
            os.makedirs(workspace_path, exist_ok=True)
            
            # Write Terraform template to file
            template_path = os.path.join(workspace_path, "main.tf")
            with open(template_path, 'w') as f:
                f.write(template)
            
            # Add backend configuration for state management
            backend_config = self._generate_backend_config(deployment_id, region)
            backend_path = os.path.join(workspace_path, "backend.tf")
            with open(backend_path, 'w') as f:
                f.write(backend_config)
            
            # Create terraform.tfvars file
            tfvars_content = f'''
project_name = "{project_name}"
aws_region = "{region}"
deployment_id = "{deployment_id}"
'''
            tfvars_path = os.path.join(workspace_path, "terraform.tfvars")
            with open(tfvars_path, 'w') as f:
                f.write(tfvars_content)
            
            # Initialize Terraform
            tf = Terraform(working_dir=workspace_path)
            
            logger.info(f"Initializing Terraform for deployment {deployment_id}")
            return_code, stdout, stderr = tf.init(capture_output=True)
            
            if return_code != 0:
                return {
                    "success": False,
                    "error": f"Terraform init failed: {stderr}",
                    "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
                }
            
            # Plan deployment
            logger.info(f"Planning deployment {deployment_id}")
            return_code, stdout, stderr = tf.plan(capture_output=True)
            
            if return_code != 0:
                return {
                    "success": False,
                    "error": f"Terraform plan failed: {stderr}",
                    "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
                }
            
            # Apply deployment
            logger.info(f"Applying deployment {deployment_id}")
            self.running_deployments[deployment_id] = tf
            
            return_code, stdout, stderr = tf.apply(
                skip_plan=True,
                capture_output=True,
                auto_approve=True
            )
            
            # Remove from running deployments
            self.running_deployments.pop(deployment_id, None)
            
            if return_code != 0:
                return {
                    "success": False,
                    "error": f"Terraform apply failed: {stderr}",
                    "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
                }
            
            # Get outputs
            outputs = self._get_terraform_outputs(tf)
            deployment_url = self._extract_deployment_url(outputs)
            
            return {
                "success": True,
                "deployment_url": deployment_url,
                "state_url": f"s3://{self.state_bucket}/{deployment_id}/terraform.tfstate",
                "outputs": outputs,
                "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
            }
            
        except Exception as e:
            logger.error(f"Terraform deployment error: {e}")
            return {
                "success": False,
                "error": str(e),
                "logs": f"Exception: {str(e)}"
            }
        
        finally:
            # Cleanup workspace
            if workspace_path and os.path.exists(workspace_path):
                try:
                    shutil.rmtree(workspace_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup workspace {workspace_path}: {e}")
    
    async def destroy(self, deployment_id: str, state_url: Optional[str] = None) -> Dict[str, Any]:
        """Destroy infrastructure using Terraform"""
        workspace_path = None
        try:
            # Create workspace directory
            workspace_path = os.path.join(self.workspace_dir, f"{deployment_id}_destroy")
            os.makedirs(workspace_path, exist_ok=True)
            
            # If we have state URL, we need to recreate the configuration
            if state_url:
                # Create minimal configuration for destroy
                destroy_config = self._generate_destroy_config(deployment_id)
                config_path = os.path.join(workspace_path, "main.tf")
                with open(config_path, 'w') as f:
                    f.write(destroy_config)
                
                # Add backend configuration
                backend_config = self._generate_backend_config(deployment_id, "us-west-2")
                backend_path = os.path.join(workspace_path, "backend.tf")
                with open(backend_path, 'w') as f:
                    f.write(backend_config)
            
            # Initialize Terraform
            tf = Terraform(working_dir=workspace_path)
            
            logger.info(f"Initializing Terraform for destruction {deployment_id}")
            return_code, stdout, stderr = tf.init(capture_output=True)
            
            if return_code != 0:
                return {
                    "success": False,
                    "error": f"Terraform init failed: {stderr}",
                    "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
                }
            
            # Destroy infrastructure
            logger.info(f"Destroying deployment {deployment_id}")
            return_code, stdout, stderr = tf.destroy(
                capture_output=True,
                auto_approve=True
            )
            
            if return_code != 0:
                return {
                    "success": False,
                    "error": f"Terraform destroy failed: {stderr}",
                    "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
                }
            
            return {
                "success": True,
                "logs": f"STDOUT: {stdout}\nSTDERR: {stderr}"
            }
            
        except Exception as e:
            logger.error(f"Terraform destruction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "logs": f"Exception: {str(e)}"
            }
        
        finally:
            # Cleanup workspace
            if workspace_path and os.path.exists(workspace_path):
                try:
                    shutil.rmtree(workspace_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup workspace {workspace_path}: {e}")
    
    async def cancel_deployment(self, deployment_id: str) -> bool:
        """Cancel running deployment"""
        try:
            if deployment_id in self.running_deployments:
                # This is a simplified cancellation - in production, you'd need more sophisticated process management
                logger.info(f"Cancelling deployment {deployment_id}")
                self.running_deployments.pop(deployment_id, None)
                return True
            return False
        except Exception as e:
            logger.error(f"Cancel deployment error: {e}")
            return False
    
    async def get_outputs(self, deployment_id: str) -> Dict[str, Any]:
        """Get Terraform outputs for a deployment"""
        try:
            workspace_path = os.path.join(self.workspace_dir, deployment_id)
            if not os.path.exists(workspace_path):
                return {}
            
            tf = Terraform(working_dir=workspace_path)
            return self._get_terraform_outputs(tf)
            
        except Exception as e:
            logger.error(f"Get outputs error: {e}")
            return {}
    
    def _generate_backend_config(self, deployment_id: str, region: str) -> str:
        """Generate Terraform backend configuration"""
        return f'''
terraform {{
  backend "s3" {{
    bucket = "{self.state_bucket}"
    key    = "{deployment_id}/terraform.tfstate"
    region = "{region}"
    
    # Enable state locking
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }}
}}
'''
    
    def _generate_destroy_config(self, deployment_id: str) -> str:
        """Generate minimal configuration for destroy operation"""
        return f'''
# Minimal configuration for destroy operation
# This allows Terraform to read the state and destroy resources

terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}}

variable "project_name" {{
  description = "Project name"
  type        = string
  default     = "autostack-{deployment_id}"
}}

variable "deployment_id" {{
  description = "Deployment ID"
  type        = string
  default     = "{deployment_id}"
}}
'''
    
    def _get_terraform_outputs(self, tf: Terraform) -> Dict[str, Any]:
        """Get Terraform outputs"""
        try:
            return_code, stdout, stderr = tf.output(json=True, capture_output=True)
            if return_code == 0 and stdout:
                return json.loads(stdout)
            return {}
        except Exception as e:
            logger.warning(f"Failed to get Terraform outputs: {e}")
            return {}
    
    def _extract_deployment_url(self, outputs: Dict[str, Any]) -> Optional[str]:
        """Extract deployment URL from Terraform outputs"""
        try:
            # Look for common output names that might contain URLs
            url_keys = ["load_balancer_dns", "alb_dns_name", "website_url", "endpoint_url"]
            
            for key in url_keys:
                if key in outputs and "value" in outputs[key]:
                    return f"http://{outputs[key]['value']}"
            
            # If no URL found, return None
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract deployment URL: {e}")
            return None