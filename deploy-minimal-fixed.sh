#!/bin/bash
# AutoStack Minimal Deployment Script - FIXED VERSION

set -e

echo "🚀 Deploying AutoStack for 10 users (Ultra-low cost)"

# Check prerequisites
command -v aws >/dev/null 2>&1 || { echo "AWS CLI required but not installed. Aborting." >&2; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "Terraform required but not installed. Aborting." >&2; exit 1; }

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 Using AWS Account: $AWS_ACCOUNT_ID"

# Create unique S3 bucket name
BUCKET_NAME="autostack-state-$AWS_ACCOUNT_ID-$(date +%s)"
echo "📦 Creating S3 bucket: $BUCKET_NAME"

# Create S3 bucket for Terraform state
aws s3 mb s3://$BUCKET_NAME --region ap-south-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

echo "🏗️ Preparing infrastructure..."
cd infrastructure

# Clean up any existing terraform state
rm -rf .terraform .terraform.lock.hcl terraform.tfstate*

# Create a clean main.tf from minimal.tf
cat > main.tf << 'EOF'
# AutoStack Minimal Infrastructure for 10 Users
# Monthly Cost: ~$8.20 (Mumbai region)

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Will be configured dynamically
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "minimal"
}

# Single EC2 instance running all services
resource "aws_instance" "autostack" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  
  vpc_security_group_ids = [aws_security_group.autostack.id]
  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    docker_compose = base64encode(file("${path.module}/../docker-compose.lite.yml"))
    env_file = base64encode(templatefile("${path.module}/app.env", {
      jwt_secret = random_password.jwt_secret.result
    }))
  }))

  tags = {
    Name        = "autostack-server"
    Environment = var.environment
  }
}

# Get latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group
resource "aws_security_group" "autostack" {
  name_prefix = "autostack"
  description = "AutoStack security group"

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # API Gateway
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH (for debugging)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "autostack-sg"
    Environment = var.environment
  }
}

# S3 bucket for Terraform state (minimal cost)
resource "aws_s3_bucket" "terraform_state" {
  bucket = "autostack-state-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "autostack-terraform-state"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Random resources
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

# Outputs
output "instance_ip" {
  description = "Public IP of AutoStack instance"
  value       = aws_instance.autostack.public_ip
}

output "api_url" {
  description = "AutoStack API URL"
  value       = "http://${aws_instance.autostack.public_ip}:3000"
}

output "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = "ssh -i your-key.pem ec2-user@${aws_instance.autostack.public_ip}"
}
EOF

# Initialize Terraform with backend config
terraform init -backend-config="bucket=$BUCKET_NAME" -backend-config="key=minimal/terraform.tfstate" -backend-config="region=ap-south-1"

# Plan deployment
terraform plan

# Apply deployment
terraform apply -auto-approve

# Get outputs
INSTANCE_IP=$(terraform output -raw instance_ip)
API_URL=$(terraform output -raw api_url)

echo ""
echo "✅ Deployment completed!"
echo "🌐 Instance IP: $INSTANCE_IP"
echo "🔗 API URL: $API_URL"
echo "💰 Estimated monthly cost: $8.20 (Mumbai region)"
echo ""
echo "⏳ Services are starting up... This may take 5-10 minutes."
echo "🔍 Check status: curl $API_URL/health"
echo ""
echo "📊 Capacity: 10 users, 50 projects, 10MB uploads"
echo "📈 Scale up when ready: ./scale-up.sh"