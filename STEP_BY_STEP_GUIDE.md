# 🚀 AutoStack Step-by-Step User Guide

## What is AutoStack?
AutoStack is an AI-powered infrastructure generator that analyzes your application code and automatically creates AWS infrastructure using Terraform. Upload your code, get production-ready AWS architecture!

---

## 📋 Prerequisites
- AWS CLI installed and configured
- Terraform installed
- Git installed

---

## 🚀 STEP 1: Deploy AutoStack

### 1.1 Clone Repository
```bash
git clone https://github.com/RohanCoderX/AutoStack.git
cd AutoStack
```

### 1.2 Deploy Infrastructure
```bash
./deploy-minimal-fixed.sh
```

**Expected Output:**
```
✅ Deployment completed!
🌐 Instance IP: 35.90.1.153
🔗 API URL: http://35.90.1.153:3000
💰 Estimated monthly cost: $8.20 (Mumbai region)
```

### 1.3 Wait for Services (5-10 minutes)
```bash
# Check when ready
curl http://35.90.1.153:3000/health
```

---

## 👤 STEP 2: Create User Account

### 2.1 Register New User
```bash
curl -X POST http://35.90.1.153:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "mypassword123"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
  "userId": 1
}
```

### 2.2 Login to Get Token
```bash
curl -X POST http://35.90.1.153:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "mypassword123"
  }'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

### 2.3 Save Your Token
```bash
export JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 📁 STEP 3: Create Project

### 3.1 Create New Project
```bash
curl -X POST http://35.90.1.153:3000/api/projects \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-commerce Website",
    "description": "Node.js e-commerce app with MongoDB and Redis"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "E-commerce Website",
  "description": "Node.js e-commerce app with MongoDB and Redis",
  "status": "created",
  "createdAt": "2025-11-23T18:30:00Z"
}
```

---

## 💻 STEP 4: Demo - E-commerce App Analysis

### 4.1 Create Sample E-commerce App
```bash
mkdir ecommerce-demo && cd ecommerce-demo

# Create package.json
cat > package.json << 'EOF'
{
  "name": "ecommerce-app",
  "version": "1.0.0",
  "description": "Full-stack e-commerce application",
  "main": "server.js",
  "dependencies": {
    "express": "^4.18.0",
    "mongoose": "^7.0.0",
    "redis": "^4.6.0",
    "stripe": "^12.0.0",
    "jsonwebtoken": "^9.0.0",
    "bcryptjs": "^2.4.3",
    "multer": "^1.4.5",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "express-rate-limit": "^6.7.0"
  },
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  }
}
EOF

# Create main server file
cat > server.js << 'EOF'
const express = require('express');
const mongoose = require('mongoose');
const redis = require('redis');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const multer = require('multer');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Database connections
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/ecommerce', {
  useNewUrlParser: true,
  useUnifiedTopology: true
});

const redisClient = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379'
});

// File upload configuration
const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

// User Schema
const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { type: String, enum: ['customer', 'admin'], default: 'customer' }
});

const User = mongoose.model('User', userSchema);

// Product Schema
const productSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  price: { type: Number, required: true },
  category: String,
  inventory: { type: Number, default: 0 },
  images: [String],
  createdAt: { type: Date, default: Date.now }
});

const Product = mongoose.model('Product', productSchema);

// Order Schema
const orderSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  items: [{
    productId: { type: mongoose.Schema.Types.ObjectId, ref: 'Product' },
    quantity: Number,
    price: Number
  }],
  total: { type: Number, required: true },
  status: { type: String, enum: ['pending', 'processing', 'shipped', 'delivered'], default: 'pending' },
  paymentId: String,
  createdAt: { type: Date, default: Date.now }
});

const Order = mongoose.model('Order', orderSchema);

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'E-commerce API is running!' });
});

// Authentication routes
app.post('/api/auth/register', async (req, res) => {
  // User registration logic
  res.json({ message: 'User registered successfully' });
});

app.post('/api/auth/login', async (req, res) => {
  // User login logic
  res.json({ token: 'jwt_token_here' });
});

// Product routes
app.get('/api/products', async (req, res) => {
  // Get all products with caching
  const cachedProducts = await redisClient.get('products');
  if (cachedProducts) {
    return res.json(JSON.parse(cachedProducts));
  }
  
  const products = await Product.find();
  await redisClient.setex('products', 300, JSON.stringify(products)); // Cache for 5 minutes
  res.json(products);
});

app.post('/api/products', upload.array('images', 5), async (req, res) => {
  // Create new product with image upload
  res.json({ message: 'Product created successfully' });
});

// Order routes
app.post('/api/orders', async (req, res) => {
  // Create new order with Stripe payment
  res.json({ message: 'Order created successfully' });
});

app.get('/api/orders/:userId', async (req, res) => {
  // Get user orders
  res.json({ orders: [] });
});

// Payment webhook
app.post('/api/webhooks/stripe', express.raw({type: 'application/json'}), (req, res) => {
  // Handle Stripe webhooks
  res.json({ received: true });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    database: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
    redis: redisClient.isOpen ? 'connected' : 'disconnected'
  });
});

app.listen(port, () => {
  console.log(`E-commerce server running on port ${port}`);
});
EOF

# Create Docker configuration
cat > Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
EOF

# Create environment file
cat > .env.example << 'EOF'
NODE_ENV=production
PORT=3000
MONGODB_URI=mongodb://mongodb:27017/ecommerce
REDIS_URL=redis://redis:6379
JWT_SECRET=your_jwt_secret_here
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
EOF

# Zip the application
zip -r ecommerce-app.zip . -x "*.git*" "node_modules/*"
```

### 4.2 Upload and Analyze Code
```bash
curl -X POST http://35.90.1.153:3000/api/analysis/upload \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "file=@ecommerce-app.zip" \
  -F "projectId=1"
```

**Response:**
```json
{
  "analysisId": 1,
  "message": "Code uploaded and analysis started",
  "status": "processing"
}
```

### 4.3 Get Analysis Results
```bash
curl -X GET http://35.90.1.153:3000/api/analysis/1 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Analysis Response:**
```json
{
  "id": 1,
  "projectId": 1,
  "status": "completed",
  "analysis": {
    "framework": "Express.js",
    "language": "Node.js",
    "database": "MongoDB",
    "cache": "Redis",
    "fileUpload": "Multer",
    "payment": "Stripe",
    "authentication": "JWT",
    "dependencies": [
      "express", "mongoose", "redis", "stripe", 
      "jsonwebtoken", "bcryptjs", "multer", "cors", "helmet"
    ],
    "recommendations": {
      "compute": "ECS Fargate (2 vCPU, 4GB RAM)",
      "database": "DocumentDB (MongoDB-compatible)",
      "cache": "ElastiCache Redis",
      "storage": "S3 for file uploads",
      "loadBalancer": "Application Load Balancer",
      "cdn": "CloudFront for static assets",
      "security": "WAF + Security Groups"
    },
    "scalingNeeds": {
      "expectedUsers": "1000-5000",
      "trafficPattern": "E-commerce (peak during sales)",
      "dataGrowth": "High (user data + product catalog)"
    }
  },
  "costEstimate": {
    "monthly": 245.80,
    "breakdown": {
      "compute": 120.00,
      "database": 85.00,
      "cache": 25.00,
      "storage": 10.00,
      "loadBalancer": 18.00,
      "dataTransfer": 12.80
    }
  }
}
```

---

## 🏗️ STEP 5: Generate Infrastructure

### 5.1 Generate Terraform Template
```bash
curl -X POST http://35.90.1.153:3000/api/templates/generate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "projectId": 1,
    "analysisId": 1,
    "templateType": "terraform",
    "environment": "production"
  }'
```

**Response:**
```json
{
  "templateId": 1,
  "message": "Infrastructure template generated successfully",
  "status": "completed"
}
```

### 5.2 Download Generated Template
```bash
curl -X GET http://35.90.1.153:3000/api/templates/1 \
  -H "Authorization: Bearer $JWT_TOKEN" \
  > ecommerce-infrastructure.tf
```

**Generated Terraform includes:**
- ECS Fargate cluster
- DocumentDB cluster
- ElastiCache Redis
- Application Load Balancer
- S3 bucket for uploads
- CloudFront distribution
- VPC with public/private subnets
- Security groups
- IAM roles

---

## 🚀 STEP 6: Deploy Infrastructure

### 6.1 Deploy to AWS
```bash
curl -X POST http://35.90.1.153:3000/api/deployments \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "projectId": 1,
    "templateId": 1,
    "environment": "production"
  }'
```

**Response:**
```json
{
  "deploymentId": 1,
  "message": "Deployment started",
  "status": "in_progress",
  "estimatedTime": "15-20 minutes"
}
```

### 6.2 Monitor Deployment Status
```bash
curl -X GET http://35.90.1.153:3000/api/deployments/1/status \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response:**
```json
{
  "deploymentId": 1,
  "status": "completed",
  "resources": {
    "loadBalancerUrl": "https://ecommerce-lb-123456789.us-west-2.elb.amazonaws.com",
    "databaseEndpoint": "ecommerce-docdb.cluster-xyz.us-west-2.docdb.amazonaws.com",
    "redisEndpoint": "ecommerce-redis.abc123.cache.amazonaws.com",
    "s3Bucket": "ecommerce-uploads-bucket-xyz"
  },
  "totalCost": "$245.80/month",
  "deploymentTime": "18 minutes"
}
```

---

## 🗑️ STEP 7: Clean Up (Stop Costs)

### 7.1 Destroy Application Infrastructure
```bash
curl -X DELETE http://35.90.1.153:3000/api/deployments/1 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 7.2 Destroy AutoStack Infrastructure
```bash
./destroy-autostack.sh
```

**Type `yes` when prompted to confirm destruction.**

---

## 📊 Demo Results Summary

### **What AutoStack Detected:**
- **Framework**: Express.js with Node.js
- **Database**: MongoDB (recommended DocumentDB)
- **Cache**: Redis (recommended ElastiCache)
- **Features**: File uploads, payments, authentication
- **Scale**: 1000-5000 users

### **Generated Infrastructure:**
- **Compute**: ECS Fargate cluster
- **Database**: DocumentDB cluster
- **Cache**: ElastiCache Redis
- **Storage**: S3 + CloudFront
- **Network**: VPC + Load Balancer
- **Security**: WAF + Security Groups

### **Cost**: $245.80/month for production e-commerce platform

---

## 🎯 Key Benefits

1. **AI-Powered Analysis**: Automatically detects frameworks, databases, scaling needs
2. **Production-Ready**: Generates secure, scalable AWS infrastructure
3. **Cost Optimization**: Right-sized resources based on actual needs
4. **Best Practices**: Follows AWS Well-Architected Framework
5. **Time Saving**: Minutes instead of days to create infrastructure

---

## 🔗 API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | User login |
| `/api/projects` | POST | Create project |
| `/api/analysis/upload` | POST | Upload code for analysis |
| `/api/analysis/:id` | GET | Get analysis results |
| `/api/templates/generate` | POST | Generate infrastructure template |
| `/api/templates/:id` | GET | Download template |
| `/api/deployments` | POST | Deploy infrastructure |
| `/api/deployments/:id/status` | GET | Check deployment status |

---

**🚀 That's it! You've successfully used AutoStack to analyze code and generate AWS infrastructure!**