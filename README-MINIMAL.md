# AutoStack - Minimal Deployment (10 Users)

**Ultra-low cost AI-powered infrastructure generator**

## 💰 Cost: $9.42/month (After Free Tier)

### What You Get
- **10 Users** with full AutoStack features
- **AI Code Analysis** powered by Amazon Q
- **Infrastructure Generation** (Terraform/CDK)
- **One-Click AWS Deployment**
- **SQLite Database** (no external DB costs)
- **Single EC2 Instance** (t3.micro)

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Install Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip && sudo mv terraform /usr/local/bin/

# Configure AWS
aws configure
```

### 2. Deploy AutoStack
```bash
git clone https://github.com/yourusername/autostack.git
cd autostack
./deploy-minimal.sh
```

### 3. Access Your Platform
```bash
# Get your instance IP (from deployment output)
curl http://YOUR_INSTANCE_IP:3000/health

# Create first user
curl -X POST http://YOUR_INSTANCE_IP:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"secure123","name":"Admin"}'
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           AWS EC2 t3.micro              │
│         (Free Tier Eligible)            │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ API Gateway │  │ Code Analysis   │   │
│  │   :3000     │  │     :8000       │   │
│  └─────────────┘  └─────────────────┘   │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │Infrastructure│  │ Deployment      │   │
│  │ Gen :8001   │  │     :8002       │   │
│  └─────────────┘  └─────────────────┘   │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │        SQLite Database              │ │
│  │     /opt/autostack/data/            │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## 📊 Capacity & Limits

### User Limits
- **Maximum Users:** 10
- **Projects per User:** 5
- **File Upload Size:** 10MB
- **API Rate Limit:** 50 requests/15min

### Performance
- **Concurrent Users:** 5-8
- **Code Analysis:** 30-60 seconds
- **Infrastructure Generation:** 5-10 seconds
- **AWS Deployment:** 5-15 minutes

## 💡 Features

### ✅ Included
- AI-powered code analysis (Amazon Q)
- Terraform template generation
- AWS CDK template generation
- Cost estimation and optimization
- Infrastructure deployment
- User authentication (JWT)
- Project management
- SQLite database
- Docker containerization

### ❌ Not Included (Cost Savings)
- PostgreSQL RDS ($15/month saved)
- Redis ElastiCache ($12/month saved)
- Multi-AZ deployment ($135/month saved)
- Load balancer ($23/month saved)
- Auto-scaling groups

## 🔧 Management

### Monitor Your Instance
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@YOUR_INSTANCE_IP

# Check service status
docker ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```

### Backup Database
```bash
# Manual backup
scp -i your-key.pem ec2-user@YOUR_INSTANCE_IP:/opt/autostack/data/autostack.db ./backup.db

# Automated daily backup (on instance)
echo "0 2 * * * cp /opt/autostack/data/autostack.db /opt/autostack/backups/autostack-\$(date +\%Y\%m\%d).db" | crontab -
```

## 📈 Scaling Path

### When to Scale Up
- **CPU > 80%** consistently
- **Users approaching 10**
- **Response time > 2 seconds**
- **Need high availability**

### Scaling Options
```bash
# Option 1: Upgrade instance type
terraform apply -var="instance_type=t3.small"  # +$9/month

# Option 2: Add RDS database
# Uncomment RDS resources in main.tf  # +$15/month

# Option 3: Full microservices
./deploy-production.sh  # $260/month
```

## 🔒 Security

### Basic Security (Included)
- Security groups (minimal ports)
- SQLite (no network exposure)
- JWT authentication
- HTTPS ready (manual SSL setup)

### Enhanced Security (Manual)
```bash
# Install Let's Encrypt SSL
sudo yum install -y certbot
sudo certbot --nginx -d yourdomain.com

# Enable firewall
sudo ufw enable
sudo ufw allow 22,80,443,3000/tcp
```

## 🚨 Troubleshooting

### Common Issues
```bash
# Services not starting
docker-compose down && docker-compose up -d

# Database locked
sudo systemctl restart autostack

# Out of disk space
df -h  # Check usage
docker system prune -f  # Clean up

# High CPU usage
htop  # Check processes
docker stats  # Check container usage
```

### Health Checks
```bash
# API Gateway
curl http://localhost:3000/health

# Code Analysis
curl http://localhost:8000/health

# Infrastructure Generation
curl http://localhost:8001/health

# Deployment Service
curl http://localhost:8002/health
```

## 💰 Cost Optimization

### Free Tier Benefits (First Year)
- **EC2 t3.micro:** 750 hours/month FREE
- **S3:** 5GB storage FREE
- **Data Transfer:** 1GB/month FREE
- **Total First Year:** ~$1/month

### After Free Tier
- **EC2 t3.micro:** $8.50/month
- **S3 Storage:** $0.02/month
- **Data Transfer:** $0.90/month
- **Total:** $9.42/month

### Additional Savings
- **Reserved Instance:** 30% off ($6/month)
- **Spot Instance:** 70% off ($2.50/month)
- **Scheduled Scaling:** Turn off nights/weekends

## 🎯 Perfect For

- **MVP Development**
- **Small Teams (2-10 people)**
- **Proof of Concept**
- **Learning & Experimentation**
- **Budget-Conscious Projects**
- **Hackathon Demos**

---

**Start with minimal, scale when needed. Perfect for getting AutoStack running without breaking the bank!** 💪