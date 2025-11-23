import os
import subprocess
import boto3
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AWSManager:
    """Manage AWS credentials and operations"""
    
    def __init__(self):
        self.session = None
        self.current_region = None
    
    def get_aws_cli_version(self) -> str:
        """Get AWS CLI version"""
        try:
            result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "not_installed"
    
    def set_credentials(self, access_key_id: str, secret_access_key: str, region: str):
        """Set AWS credentials for deployment"""
        try:
            # Set environment variables for this session
            os.environ["AWS_ACCESS_KEY_ID"] = access_key_id
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key
            os.environ["AWS_DEFAULT_REGION"] = region
            
            # Create boto3 session
            self.session = boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region
            )
            self.current_region = region
            
            logger.info(f"AWS credentials set for region {region}")
            
        except Exception as e:
            logger.error(f"Failed to set AWS credentials: {e}")
            raise
    
    def validate_credentials(self) -> Dict[str, Any]:
        """Validate AWS credentials"""
        try:
            if not self.session:
                return {"valid": False, "error": "No credentials set"}
            
            # Try to get caller identity
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            return {
                "valid": True,
                "account_id": identity.get("Account"),
                "user_arn": identity.get("Arn"),
                "region": self.current_region
            }
            
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    def check_permissions(self, required_permissions: list) -> Dict[str, Any]:
        """Check if current credentials have required permissions"""
        try:
            if not self.session:
                return {"has_permissions": False, "error": "No credentials set"}
            
            iam = self.session.client('iam')
            
            # This is a simplified permission check
            # In production, you'd use IAM policy simulator or actual resource access tests
            missing_permissions = []
            
            for permission in required_permissions:
                try:
                    # Try to simulate the permission (simplified)
                    if permission.startswith("ec2:"):
                        ec2 = self.session.client('ec2')
                        ec2.describe_regions()
                    elif permission.startswith("rds:"):
                        rds = self.session.client('rds')
                        rds.describe_db_instances()
                    elif permission.startswith("s3:"):
                        s3 = self.session.client('s3')
                        s3.list_buckets()
                except Exception:
                    missing_permissions.append(permission)
            
            return {
                "has_permissions": len(missing_permissions) == 0,
                "missing_permissions": missing_permissions
            }
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return {"has_permissions": False, "error": str(e)}
    
    def create_state_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Create S3 bucket for Terraform state"""
        try:
            if not self.session:
                return {"success": False, "error": "No credentials set"}
            
            s3 = self.session.client('s3')
            
            # Check if bucket already exists
            try:
                s3.head_bucket(Bucket=bucket_name)
                return {"success": True, "message": "Bucket already exists"}
            except:
                pass
            
            # Create bucket
            if self.current_region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.current_region}
                )
            
            # Enable versioning
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Enable encryption
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            
            # Block public access
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            return {"success": True, "message": f"Bucket {bucket_name} created successfully"}
            
        except Exception as e:
            logger.error(f"Failed to create state bucket: {e}")
            return {"success": False, "error": str(e)}
    
    def create_dynamodb_lock_table(self, table_name: str = "terraform-state-lock") -> Dict[str, Any]:
        """Create DynamoDB table for Terraform state locking"""
        try:
            if not self.session:
                return {"success": False, "error": "No credentials set"}
            
            dynamodb = self.session.client('dynamodb')
            
            # Check if table already exists
            try:
                dynamodb.describe_table(TableName=table_name)
                return {"success": True, "message": "Table already exists"}
            except dynamodb.exceptions.ResourceNotFoundException:
                pass
            
            # Create table
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'LockID',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'LockID',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {
                        'Key': 'Purpose',
                        'Value': 'TerraformStateLock'
                    },
                    {
                        'Key': 'ManagedBy',
                        'Value': 'AutoStack'
                    }
                ]
            )
            
            return {"success": True, "message": f"DynamoDB table {table_name} created successfully"}
            
        except Exception as e:
            logger.error(f"Failed to create DynamoDB lock table: {e}")
            return {"success": False, "error": str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get AWS account information"""
        try:
            if not self.session:
                return {"error": "No credentials set"}
            
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            # Get account alias if available
            try:
                iam = self.session.client('iam')
                aliases = iam.list_account_aliases()
                account_alias = aliases['AccountAliases'][0] if aliases['AccountAliases'] else None
            except:
                account_alias = None
            
            return {
                "account_id": identity.get("Account"),
                "account_alias": account_alias,
                "user_arn": identity.get("Arn"),
                "user_id": identity.get("UserId"),
                "region": self.current_region
            }
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {"error": str(e)}
    
    def estimate_costs(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for resources (simplified)"""
        try:
            # This is a simplified cost estimation
            # In production, you'd use AWS Cost Explorer API or Pricing API
            
            total_monthly_cost = 0.0
            cost_breakdown = {}
            
            # EC2 instances
            if "compute" in resources:
                compute = resources["compute"]
                if compute.get("type") == "ec2":
                    instance_type = compute.get("size", "t3.micro")
                    instance_count = compute.get("replicas", 1)
                    
                    # Simplified pricing (per hour)
                    ec2_pricing = {
                        "t3.nano": 0.0052,
                        "t3.micro": 0.0104,
                        "t3.small": 0.0208,
                        "t3.medium": 0.0416
                    }
                    
                    hourly_cost = ec2_pricing.get(instance_type, 0.0104)
                    monthly_cost = hourly_cost * 24 * 30 * instance_count
                    
                    cost_breakdown["ec2"] = monthly_cost
                    total_monthly_cost += monthly_cost
            
            # RDS databases
            if "database" in resources:
                db = resources["database"]
                instance_type = db.get("size", "db.t3.micro")
                
                # Simplified RDS pricing
                rds_pricing = {
                    "db.t3.micro": 0.017,
                    "db.t3.small": 0.034,
                    "db.t3.medium": 0.068
                }
                
                hourly_cost = rds_pricing.get(instance_type, 0.017)
                monthly_cost = hourly_cost * 24 * 30
                
                cost_breakdown["rds"] = monthly_cost
                total_monthly_cost += monthly_cost
            
            return {
                "total_monthly_cost": round(total_monthly_cost, 2),
                "cost_breakdown": cost_breakdown,
                "currency": "USD",
                "region": self.current_region
            }
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return {"error": str(e)}