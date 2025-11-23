# AutoStack Deployment Guide

## 🚀 Deployment Architecture

### AWS Account Strategy

#### Development/Demo
- **Your Personal AWS Account**: Used for testing and development
- **Estimated Cost**: $130/month for 1K users
- **Account ID**: Your personal AWS account ID

#### Production
- **User-Provided Credentials**: Each user provides their own AWS credentials
- **Cross-Account Roles**: For enterprise customers
- **Multi-Tenant**: Isolated resources per user

### CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
Trigger: Push to main branch
Steps:
  1. Run Tests (Unit + Integration)
  2. Build Docker Images
  3. Push to ECR
  4. Deploy Infrastructure (Terraform)
  5. Update ECS Services
  6. Health Checks
```

#### Pipeline Components
- **ECR Repositories**: Store Docker images
- **ECS Cluster**: Run microservices
- **RDS PostgreSQL**: Database
- **ElastiCache Redis**: Caching
- **Application Load Balancer**: Traffic routing

## 🏗️ Infrastructure Components

### Core Services
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Code Analysis   │────│ Infrastructure  │
│   (Port 3000)   │    │   (Port 8000)    │    │  Gen (8001)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │   Deployment      │
                        │   (Port 8002)     │
                        └────────────────────┘
```

### AWS Resources
- **VPC**: 10.0.0.0/16 with public/private subnets
- **ECS Fargate**: Serverless containers
- **RDS**: PostgreSQL 14.9 (db.t3.micro)
- **ElastiCache**: Redis 7 (cache.t3.micro)
- **ALB**: Application Load Balancer
- **S3**: Terraform state storage

## 🔧 Setup Instructions

### 1. Prerequisites
```bash
# Required tools
- AWS CLI v2
- Terraform >= 1.6.0
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
```

### 2. AWS Account Setup
```bash
# Configure AWS CLI
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-west-2
# Default output format: json

# Create S3 bucket for Terraform state
aws s3 mb s3://autostack-terraform-state-YOUR-ACCOUNT-ID

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
DATABASE_URL=postgresql://postgres:password@localhost:5432/autostack
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-super-secret-jwt-key-here
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AMAZON_Q_API_KEY=your-amazon-q-api-key
```

### 4. Local Development
```bash
# Start all services
docker-compose up -d

# Check service health
curl http://localhost:3000/health    # API Gateway
curl http://localhost:8000/health    # Code Analysis
curl http://localhost:8001/health    # Infrastructure Generation
curl http://localhost:8002/health    # Deployment Service

# View logs
docker-compose logs -f
```

### 5. Production Deployment

#### Option A: GitHub Actions (Recommended)
```bash
# 1. Fork the repository
# 2. Set GitHub Secrets:
#    - AWS_ACCESS_KEY_ID
#    - AWS_SECRET_ACCESS_KEY
# 3. Push to main branch
git push origin main
```

#### Option B: Manual Deployment
```bash
# Deploy infrastructure
cd infrastructure
terraform init
terraform plan
terraform apply

# Build and push images
docker build -t autostack-api-gateway services/api-gateway/
docker build -t autostack-code-analysis services/code-analysis/
docker build -t autostack-infrastructure-generation services/infrastructure-generation/
docker build -t autostack-deployment services/deployment/

# Tag and push to ECR (replace ACCOUNT_ID)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com

docker tag autostack-api-gateway:latest ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/autostack-api-gateway:latest
docker push ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/autostack-api-gateway:latest
```

## 💰 Cost Breakdown

### Development Environment
```
Service                    Monthly Cost
─────────────────────────────────────
ECS Fargate (4 services)   $60
RDS db.t3.micro            $15
ElastiCache t3.micro       $12
Application Load Balancer  $23
NAT Gateway (3 AZs)        $135
Data Transfer              $10
S3 Storage                 $5
─────────────────────────────────────
Total:                     $260/month
```

### Production Scaling
```
Users     Monthly Cost    Revenue Potential
─────────────────────────────────────────
1K        $260           $3,200
5K        $450           $16,000
10K       $750           $32,000
50K       $2,500         $160,000
```

## 🔒 Security Considerations

### Infrastructure Security
- **VPC**: Private subnets for databases
- **Security Groups**: Minimal port access
- **Encryption**: At-rest and in-transit
- **IAM Roles**: Least privilege access
- **Secrets Manager**: For sensitive data

### Application Security
- **JWT Authentication**: Secure API access
- **Rate Limiting**: Prevent abuse
- **Input Validation**: Prevent injection attacks
- **HTTPS Only**: TLS 1.3 encryption
- **CORS**: Proper origin restrictions

### User Data Security
- **Credential Isolation**: Each user's AWS credentials are isolated
- **State Encryption**: Terraform state encrypted in S3
- **Audit Logging**: All deployments logged
- **Access Control**: Role-based permissions

## 📊 Monitoring & Observability

### CloudWatch Metrics
- **ECS Service Health**: CPU, memory, task count
- **Database Performance**: Connections, queries, latency
- **Load Balancer**: Request count, response time, errors
- **Custom Metrics**: User signups, deployments, costs

### Logging
- **Application Logs**: Structured JSON logs
- **Access Logs**: ALB request logs
- **Audit Logs**: Deployment activities
- **Error Tracking**: Centralized error monitoring

### Alerting
- **Service Health**: ECS task failures
- **Database**: High CPU, connection limits
- **Cost**: Budget alerts for unexpected charges
- **Security**: Failed authentication attempts

## 🚨 Disaster Recovery

### Backup Strategy
- **Database**: Automated daily backups (7-day retention)
- **Code**: Git repository with multiple remotes
- **Infrastructure**: Terraform state versioning
- **User Data**: Cross-region replication

### Recovery Procedures
- **RTO**: 4 hours (Recovery Time Objective)
- **RPO**: 1 hour (Recovery Point Objective)
- **Failover**: Automated ECS service recovery
- **Data Recovery**: Point-in-time database restore

## 📈 Scaling Strategy

### Horizontal Scaling
- **ECS Auto Scaling**: Based on CPU/memory
- **Database Read Replicas**: For read-heavy workloads
- **Multi-Region**: Deploy to multiple AWS regions
- **CDN**: CloudFront for static assets

### Performance Optimization
- **Connection Pooling**: Database connections
- **Caching**: Redis for frequent queries
- **Async Processing**: Background job queues
- **Code Optimization**: Profiling and optimization

## 🎯 Success Metrics

### Technical KPIs
- **Uptime**: 99.9% availability
- **Response Time**: <500ms p95
- **Error Rate**: <1%
- **Deployment Success**: >95%

### Business KPIs
- **User Growth**: 100 users/month
- **Conversion Rate**: 15% free to paid
- **Revenue Growth**: $3K+ MRR
- **Customer Satisfaction**: 4.5+ stars

---

**AutoStack is now ready for production deployment with enterprise-grade security, scalability, and monitoring!**