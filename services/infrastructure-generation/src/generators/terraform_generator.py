import os
import subprocess
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
import logging

logger = logging.getLogger(__name__)

class TerraformGenerator:
    """Generate Terraform templates from requirements"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "terraform")
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))
    
    def get_version(self) -> str:
        """Get Terraform version"""
        try:
            result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
            return result.stdout.split('\n')[0] if result.returncode == 0 else "unknown"
        except:
            return "not_installed"
    
    async def generate(self, project_name: str, requirements: Dict[str, Any], optimization_level: str = "balanced") -> str:
        """Generate Terraform template"""
        try:
            # Prepare template variables
            template_vars = {
                "project_name": self._sanitize_name(project_name),
                "requirements": requirements,
                "optimization_level": optimization_level,
                "region": "us-west-2",
                "availability_zones": ["us-west-2a", "us-west-2b", "us-west-2c"]
            }
            
            # Generate main template
            main_template = self.jinja_env.get_template("main.tf.j2")
            terraform_code = main_template.render(**template_vars)
            
            # Add variables file
            variables_template = self.jinja_env.get_template("variables.tf.j2")
            variables_code = variables_template.render(**template_vars)
            
            # Add outputs file
            outputs_template = self.jinja_env.get_template("outputs.tf.j2")
            outputs_code = outputs_template.render(**template_vars)
            
            # Combine all files
            full_template = f"""# AutoStack Generated Terraform Template
# Project: {project_name}
# Generated: {self._get_timestamp()}

{terraform_code}

{variables_code}

{outputs_code}
"""
            
            return full_template
            
        except Exception as e:
            logger.error(f"Terraform generation error: {e}")
            return self._generate_fallback_template(project_name, requirements)
    
    def _generate_fallback_template(self, project_name: str, requirements: Dict[str, Any]) -> str:
        """Generate basic Terraform template as fallback"""
        project_name = self._sanitize_name(project_name)
        
        template = f'''# AutoStack Generated Terraform Template
# Project: {project_name}

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

# Variables
variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}}

variable "project_name" {{
  description = "Project name"
  type        = string
  default     = "{project_name}"
}}

# VPC
resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {{
    Name = "${{var.project_name}}-vpc"
  }}
}}

# Internet Gateway
resource "aws_internet_gateway" "main" {{
  vpc_id = aws_vpc.main.id

  tags = {{
    Name = "${{var.project_name}}-igw"
  }}
}}

# Public Subnets
resource "aws_subnet" "public" {{
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${{count.index + 1}}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {{
    Name = "${{var.project_name}}-public-${{count.index + 1}}"
  }}
}}

# Private Subnets
resource "aws_subnet" "private" {{
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${{count.index + 10}}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {{
    Name = "${{var.project_name}}-private-${{count.index + 1}}"
  }}
}}

# Route Table
resource "aws_route_table" "public" {{
  vpc_id = aws_vpc.main.id

  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }}

  tags = {{
    Name = "${{var.project_name}}-public-rt"
  }}
}}

resource "aws_route_table_association" "public" {{
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}}

# Security Group
resource "aws_security_group" "web" {{
  name_prefix = "${{var.project_name}}-web"
  vpc_id      = aws_vpc.main.id

  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  ingress {{
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{
    Name = "${{var.project_name}}-web-sg"
  }}
}}

# Data sources
data "aws_availability_zones" "available" {{
  state = "available"
}}
'''

        # Add compute resources based on requirements
        if requirements.get("compute"):
            compute = requirements["compute"]
            if compute.get("type") == "container":
                template += self._add_ecs_resources(project_name, compute)
            elif compute.get("type") == "ec2":
                template += self._add_ec2_resources(project_name, compute)
            elif compute.get("type") == "lambda":
                template += self._add_lambda_resources(project_name, compute)
        
        # Add database resources
        if requirements.get("database"):
            template += self._add_database_resources(project_name, requirements["database"])
        
        # Add cache resources
        if requirements.get("cache"):
            template += self._add_cache_resources(project_name, requirements["cache"])
        
        # Add storage resources
        if requirements.get("storage"):
            template += self._add_storage_resources(project_name, requirements["storage"])
        
        # Add outputs
        template += f'''
# Outputs
output "vpc_id" {{
  description = "VPC ID"
  value       = aws_vpc.main.id
}}

output "public_subnet_ids" {{
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}}

output "private_subnet_ids" {{
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}}
'''
        
        return template
    
    def _add_ecs_resources(self, project_name: str, compute: Dict[str, Any]) -> str:
        """Add ECS resources to template"""
        return f'''
# ECS Cluster
resource "aws_ecs_cluster" "main" {{
  name = "${{var.project_name}}-cluster"

  tags = {{
    Name = "${{var.project_name}}-cluster"
  }}
}}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {{
  family                   = "${{var.project_name}}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "{compute.get('cpu', '256')}"
  memory                   = "{compute.get('memory', '512')}"

  container_definitions = jsonencode([
    {{
      name  = "${{var.project_name}}-app"
      image = "nginx:latest"
      
      portMappings = [
        {{
          containerPort = 80
          protocol      = "tcp"
        }}
      ]
      
      logConfiguration = {{
        logDriver = "awslogs"
        options = {{
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }}
      }}
    }}
  ])

  tags = {{
    Name = "${{var.project_name}}-task"
  }}
}}

# ECS Service
resource "aws_ecs_service" "app" {{
  name            = "${{var.project_name}}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = {compute.get('replicas', 1)}
  launch_type     = "FARGATE"

  network_configuration {{
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.web.id]
  }}

  tags = {{
    Name = "${{var.project_name}}-service"
  }}
}}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {{
  name              = "/ecs/${{var.project_name}}"
  retention_in_days = 7

  tags = {{
    Name = "${{var.project_name}}-logs"
  }}
}}
'''
    
    def _add_database_resources(self, project_name: str, database: Dict[str, Any]) -> str:
        """Add database resources to template"""
        db_type = database.get("type", "postgresql")
        instance_class = database.get("size", "db.t3.micro")
        
        return f'''
# Database Subnet Group
resource "aws_db_subnet_group" "main" {{
  name       = "${{var.project_name}}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {{
    Name = "${{var.project_name}}-db-subnet-group"
  }}
}}

# Database Security Group
resource "aws_security_group" "database" {{
  name_prefix = "${{var.project_name}}-db"
  vpc_id      = aws_vpc.main.id

  ingress {{
    from_port       = {self._get_db_port(db_type)}
    to_port         = {self._get_db_port(db_type)}
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }}

  tags = {{
    Name = "${{var.project_name}}-db-sg"
  }}
}}

# RDS Instance
resource "aws_db_instance" "main" {{
  identifier = "${{var.project_name}}-db"

  engine         = "{self._get_db_engine(db_type)}"
  engine_version = "{self._get_db_version(db_type)}"
  instance_class = "{instance_class}"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = "appdb"
  username = "admin"
  password = "changeme123!"  # Use AWS Secrets Manager in production

  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = true
  deletion_protection = false

  tags = {{
    Name = "${{var.project_name}}-db"
  }}
}}
'''
    
    def _add_cache_resources(self, project_name: str, cache: Dict[str, Any]) -> str:
        """Add cache resources to template"""
        return f'''
# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {{
  name       = "${{var.project_name}}-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}}

# ElastiCache Security Group
resource "aws_security_group" "cache" {{
  name_prefix = "${{var.project_name}}-cache"
  vpc_id      = aws_vpc.main.id

  ingress {{
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }}

  tags = {{
    Name = "${{var.project_name}}-cache-sg"
  }}
}}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "main" {{
  replication_group_id       = "${{var.project_name}}-cache"
  description                = "Redis cache for ${{var.project_name}}"
  
  node_type                  = "{cache.get('size', 'cache.t3.micro')}"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  
  num_cache_clusters         = 1
  
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.cache.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = {{
    Name = "${{var.project_name}}-cache"
  }}
}}
'''
    
    def _add_storage_resources(self, project_name: str, storage: Dict[str, Any]) -> str:
        """Add storage resources to template"""
        return f'''
# S3 Bucket
resource "aws_s3_bucket" "main" {{
  bucket = "${{var.project_name}}-storage-${{random_id.bucket_suffix.hex}}"

  tags = {{
    Name = "${{var.project_name}}-storage"
  }}
}}

resource "aws_s3_bucket_versioning" "main" {{
  bucket = aws_s3_bucket.main.id
  versioning_configuration {{
    status = "Enabled"
  }}
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {{
  bucket = aws_s3_bucket.main.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}

resource "random_id" "bucket_suffix" {{
  byte_length = 4
}}
'''
    
    def _add_lambda_resources(self, project_name: str, compute: Dict[str, Any]) -> str:
        """Add Lambda resources to template"""
        return f'''
# Lambda Function
resource "aws_lambda_function" "main" {{
  filename         = "lambda.zip"
  function_name    = "${{var.project_name}}-function"
  role            = aws_iam_role.lambda.arn
  handler         = "index.handler"
  runtime         = "python3.9"
  memory_size     = {compute.get('memory', '128')}
  timeout         = {compute.get('timeout', '30')}

  tags = {{
    Name = "${{var.project_name}}-lambda"
  }}
}}

# Lambda IAM Role
resource "aws_iam_role" "lambda" {{
  name = "${{var.project_name}}-lambda-role"

  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {{
          Service = "lambda.amazonaws.com"
        }}
      }}
    ]
  }})
}}

resource "aws_iam_role_policy_attachment" "lambda_basic" {{
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda.name
}}
'''
    
    def _get_db_port(self, db_type: str) -> int:
        """Get database port by type"""
        ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "mariadb": 3306,
            "oracle": 1521,
            "sqlserver": 1433
        }
        return ports.get(db_type, 5432)
    
    def _get_db_engine(self, db_type: str) -> str:
        """Get database engine name"""
        engines = {
            "postgresql": "postgres",
            "mysql": "mysql",
            "mariadb": "mariadb",
            "oracle": "oracle-ee",
            "sqlserver": "sqlserver-ex"
        }
        return engines.get(db_type, "postgres")
    
    def _get_db_version(self, db_type: str) -> str:
        """Get database version"""
        versions = {
            "postgresql": "14.9",
            "mysql": "8.0",
            "mariadb": "10.6",
            "oracle": "19.0.0.0.ru-2023-04.rur-2023-04.r1",
            "sqlserver": "15.00"
        }
        return versions.get(db_type, "14.9")
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for AWS resources"""
        import re
        # Replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower())
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Limit length
        return sanitized[:50]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")