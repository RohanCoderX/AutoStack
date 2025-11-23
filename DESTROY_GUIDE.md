# 🗑️ AutoStack Destruction Guide

## Quick Destroy (Stop All Costs)

```bash
./destroy-autostack.sh
```

**What it destroys:**
- ✅ EC2 instance (stops $6.50/month)
- ✅ S3 buckets (stops $0.70/month) 
- ✅ Security groups
- ✅ All Terraform state files
- ✅ **Total savings: $8.20/month → $0.00/month**

## Manual Verification

After running the script, verify everything is gone:

```bash
# Check no EC2 instances
aws ec2 describe-instances --region ap-south-1 --query "Reservations[*].Instances[?Tags[?Key=='Name' && contains(Value, 'autostack')]]"

# Check no S3 buckets
aws s3 ls | grep autostack

# Check no security groups
aws ec2 describe-security-groups --region ap-south-1 --query "SecurityGroups[?contains(GroupName, 'autostack')]"
```

## Emergency Stop (If script fails)

```bash
# 1. Destroy via Terraform
cd infrastructure
terraform destroy -auto-approve

# 2. Delete S3 buckets manually
aws s3 rm s3://your-bucket-name --recursive
aws s3api delete-bucket --bucket your-bucket-name --region ap-south-1

# 3. Terminate EC2 instances manually
aws ec2 terminate-instances --instance-ids i-xxxxxxxxx --region ap-south-1
```

## Cost Verification

After destruction, check your AWS billing:
- Go to AWS Console → Billing → Bills
- Verify no charges for AutoStack resources
- All costs should stop within 24 hours

**⚠️ Important: Run the destroy script BEFORE the end of your billing cycle to avoid charges!**