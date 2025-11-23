#!/bin/bash
# AutoStack Minimal Deployment Script for 10 Users

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
aws s3 mb s3://$BUCKET_NAME --region us-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Create minimal tfvars
cat > infrastructure/minimal.auto.tfvars << EOF
aws_region = "us-west-2"
environment = "minimal"
terraform_state_bucket = "$BUCKET_NAME"
EOF

# Update backend configuration
cat > infrastructure/backend.tf << EOF
terraform {
  backend "s3" {
    bucket = "$BUCKET_NAME"
    key    = "minimal/terraform.tfstate"
    region = "us-west-2"
  }
}
EOF

echo "🏗️ Deploying infrastructure..."
cd infrastructure

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="minimal.auto.tfvars"

# Apply deployment
terraform apply -var-file="minimal.auto.tfvars" -auto-approve

# Get outputs
INSTANCE_IP=$(terraform output -raw instance_ip)
API_URL=$(terraform output -raw api_url)

echo ""
echo "✅ Deployment completed!"
echo "🌐 Instance IP: $INSTANCE_IP"
echo "🔗 API URL: $API_URL"
echo "💰 Estimated monthly cost: $9.42 (after free tier)"
echo ""
echo "⏳ Services are starting up... This may take 5-10 minutes."
echo "🔍 Check status: curl $API_URL/health"
echo "🔑 SSH access: ssh -i your-key.pem ec2-user@$INSTANCE_IP"
echo ""
echo "📊 Capacity: 10 users, 50 projects, 10MB uploads"
echo "📈 Scale up when ready: ./scale-up.sh"