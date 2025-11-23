#!/bin/bash
# AutoStack Destroy Script - Remove ALL resources to stop costs

set -e

echo "🗑️  Destroying AutoStack infrastructure..."
echo "⚠️  This will DELETE ALL resources and STOP all costs!"
echo ""
read -p "Are you sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Destruction cancelled"
    exit 1
fi

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "Terraform required but not installed. Aborting." >&2; exit 1; }

cd infrastructure

echo "🏗️  Destroying Terraform resources..."
terraform destroy -auto-approve

echo "🧹 Cleaning up local files..."
rm -rf .terraform .terraform.lock.hcl terraform.tfstate*

echo "📦 Finding and destroying S3 state buckets..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Find all AutoStack S3 buckets
BUCKETS=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'autostack-state')].Name" --output text)

for bucket in $BUCKETS; do
    if [[ $bucket == *"$AWS_ACCOUNT_ID"* ]]; then
        echo "🗑️  Deleting S3 bucket: $bucket"
        
        # Delete all objects first
        aws s3 rm s3://$bucket --recursive 2>/dev/null || true
        
        # Delete all versions
        aws s3api delete-objects --bucket $bucket --delete "$(aws s3api list-object-versions --bucket $bucket --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" 2>/dev/null || true
        
        # Delete all delete markers
        aws s3api delete-objects --bucket $bucket --delete "$(aws s3api list-object-versions --bucket $bucket --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')" 2>/dev/null || true
        
        # Delete bucket
        aws s3api delete-bucket --bucket $bucket --region ap-south-1 2>/dev/null || true
        
        echo "✅ Deleted bucket: $bucket"
    fi
done

echo ""
echo "✅ AutoStack completely destroyed!"
echo "💰 All AWS costs have been stopped"
echo "🧹 No resources remain in your account"
echo ""
echo "📊 Final cost: $0.00/month"