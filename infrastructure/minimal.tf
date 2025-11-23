# AutoStack Minimal Infrastructure for 10 Users
# Monthly Cost: ~$15

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "minimal"
}

# Single EC2 instance running all services
resource "aws_instance" "autostack" {
  ami           = "ami-0c02fb55956c7d316" # Amazon Linux 2023
  instance_type = "t3.micro"              # Free tier eligible
  
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