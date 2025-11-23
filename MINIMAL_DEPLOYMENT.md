# AutoStack Minimal Deployment (10 Users)

## 💰 Ultra-Low Cost Architecture

### Monthly Cost Breakdown
```
Service                    Monthly Cost
─────────────────────────────────────
EC2 t3.micro (Free Tier)   $0 (first year)
EC2 t3.micro (After)       $8.50
S3 Storage (1GB)           $0.02
Data Transfer (10GB)       $0.90
─────────────────────────────────────
Total (First Year):        $0.92/month
Total (After First Year):  $9.42/month
```

### Architecture
```
┌─────────────────────────────────────────┐
│           Single EC2 Instance           │
│              (t3.micro)                 │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ API Gateway │  │ Code Analysis   │   │
│  │ (Port 3000) │  │ (Port 8000)     │   │
│  └─────────────┘  └─────────────────┘   │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │Infrastructure│  │ Deployment      │   │
│  │ Gen (8001)  │  │ (Port 8002)     │   │
│  └─────────────┘  └─────────────────┘   │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │        SQLite Database              │ │
│  │        (File-based)                 │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## 🚀 Quick Deployment

### 1. Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS
aws configure
```

### 2. Deploy Infrastructure
```bash
cd infrastructure
terraform init
terraform apply -var-file="minimal.tfvars"
```

### 3. Access AutoStack
```bash
# Get instance IP
INSTANCE_IP=$(terraform output -raw instance_ip)

# Access API
curl http://$INSTANCE_IP:3000/health

# Web interface (if built)
open http://$INSTANCE_IP:3000
```

## 🔧 Configuration for 10 Users

### Resource Limits
```yaml
Users: 10 maximum
Projects per user: 5
File upload size: 10MB
Concurrent deployments: 2
API rate limit: 50 requests/15min
```

### Database Schema (SQLite)
```sql
-- Optimized for 10 users
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    subscription_tier TEXT DEFAULT 'free',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Simplified tables for minimal deployment
CREATE TABLE code_analyses (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    status TEXT DEFAULT 'pending',
    results TEXT, -- JSON stored as text
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 📊 Scaling Path

### Growth Stages
```
Stage 1: 1-10 users     → Single EC2 (t3.micro)     → $9/month
Stage 2: 10-50 users    → EC2 (t3.small) + RDS      → $35/month  
Stage 3: 50-200 users   → ECS + RDS + Redis         → $120/month
Stage 4: 200+ users     → Full microservices        → $260/month
```

### Migration Triggers
- **CPU > 80%** for 5+ minutes → Upgrade instance
- **Disk > 80%** → Add EBS volume or migrate to RDS
- **Response time > 2s** → Add caching layer
- **Users > 50** → Split into microservices

## 🔒 Security (Minimal)

### Basic Security
- **Security Group**: Only necessary ports (22, 80, 443, 3000)
- **SQLite**: File-based, no network exposure
- **JWT**: Secure token authentication
- **HTTPS**: Let's Encrypt SSL (manual setup)

### Monitoring
- **CloudWatch**: Basic EC2 metrics
- **Health Check**: Simple curl-based monitoring
- **Logs**: Docker container logs

## 🛠️ Maintenance

### Backup Strategy
```bash
# Daily SQLite backup
0 2 * * * cp /opt/autostack/data/autostack.db /opt/autostack/backups/autostack-$(date +\%Y\%m\%d).db

# Weekly S3 backup
0 3 * * 0 aws s3 cp /opt/autostack/data/autostack.db s3://your-backup-bucket/
```

### Updates
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@INSTANCE_IP

# Update services
cd /opt/autostack
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

## 📈 Performance Expectations

### Capacity
- **Concurrent Users**: 5-8
- **API Requests**: 1000/hour
- **Code Analyses**: 50/day
- **Infrastructure Deployments**: 10/day

### Response Times
- **API Endpoints**: <500ms
- **Code Analysis**: 30-60 seconds
- **Template Generation**: 5-10 seconds
- **Infrastructure Deployment**: 5-15 minutes

## 🚨 Limitations

### Technical Constraints
- **Single Point of Failure**: One EC2 instance
- **No Auto-scaling**: Manual intervention needed
- **Limited Concurrency**: SQLite write locks
- **No Load Balancing**: Direct instance access

### Recommended Limits
- **Max Users**: 10
- **Max Projects**: 50 total
- **Max File Size**: 10MB
- **Max Concurrent Deployments**: 2

## 💡 Cost Optimization Tips

### Free Tier Benefits
- **EC2**: 750 hours/month free (t3.micro)
- **S3**: 5GB storage free
- **Data Transfer**: 1GB/month free

### Additional Savings
- **Spot Instances**: 70% savings (for non-critical workloads)
- **Reserved Instances**: 30% savings (1-year commitment)
- **S3 Intelligent Tiering**: Automatic cost optimization

---

**Perfect for MVP, demos, and small teams! Scale up as you grow.** 🚀