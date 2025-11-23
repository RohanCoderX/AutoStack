#!/bin/bash
# Quick Start AutoStack API Gateway (No Docker)

set -e

echo "🚀 Starting AutoStack API Gateway directly..."

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
    sudo yum install -y nodejs
fi

# Go to API Gateway directory
cd /opt/autostack/services/api-gateway

# Install dependencies
echo "📦 Installing dependencies..."
npm install --production

# Create data directory
mkdir -p /opt/autostack/data

# Set environment variables
export NODE_ENV=production
export JWT_SECRET="autostack-jwt-secret-$(date +%s)"
export DATABASE_URL="sqlite:///opt/autostack/data/autostack.db"
export PORT=3000

# Start the API Gateway
echo "🌐 Starting API Gateway on port 3000..."
nohup node src/index.js > /opt/autostack/api-gateway.log 2>&1 &

echo "✅ AutoStack API Gateway started!"
echo "🔗 API URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"
echo "📋 Check logs: tail -f /opt/autostack/api-gateway.log"