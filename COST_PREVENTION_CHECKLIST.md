# 💰 AutoStack Cost Prevention Checklist

## ⚠️ CRITICAL: Always Destroy After Testing!

### 🚨 Potential Monthly Costs If Not Destroyed:
- **Demo E-commerce Infrastructure**: $245.80/month
- **AutoStack Platform**: $8.20/month
- **TOTAL**: $254.00/month

### ✅ After Proper Destruction: $0.00/month

---

## 📋 Pre-Testing Checklist

Before starting the demo:

- [ ] Set a phone reminder for 2 hours to destroy resources
- [ ] Add calendar event: "Destroy AutoStack Demo"
- [ ] Bookmark this checklist
- [ ] Have AWS billing alerts enabled

---

## 🗑️ Destruction Checklist (MANDATORY)

### Step 1: Destroy Demo Infrastructure
```bash
curl -X DELETE http://YOUR_IP:3000/api/deployments/1 \
  -H "Authorization: Bearer $JWT_TOKEN"
```
- [ ] Command executed successfully
- [ ] Received "destroying" status response
- [ ] Waited for "destroyed" status (10-15 minutes)

### Step 2: Destroy AutoStack Platform
```bash
./destroy-autostack.sh
```
- [ ] Typed "yes" to confirm
- [ ] Saw "AutoStack completely destroyed!" message
- [ ] Received "$0.00/month" confirmation

### Step 3: Verify Zero Costs
```bash
# Check no running instances
aws ec2 describe-instances --region us-west-2 --query "Reservations[*].Instances[?State.Name=='running']"

# Check no AutoStack S3 buckets
aws s3 ls | grep autostack
```
- [ ] No running EC2 instances found
- [ ] No AutoStack S3 buckets found
- [ ] AWS billing shows $0.00 for AutoStack resources

---

## 🚨 Emergency Destruction (If Scripts Fail)

### Manual Cleanup Commands:
```bash
# Terminate all AutoStack instances
aws ec2 describe-instances --region us-west-2 \
  --filters "Name=tag:Name,Values=*autostack*" \
  --query "Reservations[*].Instances[*].InstanceId" --output text | \
  xargs -r aws ec2 terminate-instances --region us-west-2 --instance-ids

# Delete all AutoStack S3 buckets
aws s3 ls | grep autostack | awk '{print $3}' | \
  xargs -I {} sh -c 'aws s3 rm s3://{} --recursive && aws s3 rb s3://{}'

# Delete AutoStack security groups
aws ec2 describe-security-groups --region us-west-2 \
  --filters "Name=group-name,Values=autostack*" \
  --query "SecurityGroups[*].GroupId" --output text | \
  xargs -r aws ec2 delete-security-group --region us-west-2 --group-id
```

---

## 📊 Cost Monitoring

### AWS Billing Verification:
1. **AWS Console** → **Billing** → **Bills**
2. **Check for $0.00 charges on:**
   - EC2 instances
   - S3 storage
   - Data transfer
   - Load balancers
   - RDS/DocumentDB
   - ElastiCache

### Set Up Billing Alerts:
```bash
# Create billing alarm for $1
aws cloudwatch put-metric-alarm \
  --alarm-name "AutoStack-Cost-Alert" \
  --alarm-description "Alert when AutoStack costs exceed $1" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1
```

---

## ✅ Final Verification

After destruction, confirm:

- [ ] **EC2 Dashboard**: No running instances
- [ ] **S3 Dashboard**: No AutoStack buckets
- [ ] **Billing Dashboard**: $0.00 ongoing costs
- [ ] **CloudWatch**: No active alarms
- [ ] **VPC Dashboard**: No AutoStack security groups

---

## 🎯 Quick Destroy (2 Commands)

```bash
# 1. Destroy demo infrastructure
curl -X DELETE http://YOUR_IP:3000/api/deployments/1 -H "Authorization: Bearer $JWT_TOKEN"

# 2. Destroy AutoStack platform
./destroy-autostack.sh
```

**Result**: $254.00/month → $0.00/month ✅

---

## 📞 Support

If you encounter issues destroying resources:

1. **Check AWS Console** manually
2. **Use emergency cleanup commands** above
3. **Contact AWS Support** if charges continue
4. **File billing dispute** if unexpected charges occur

**Remember**: AWS charges by the hour, so destroy resources immediately after testing!