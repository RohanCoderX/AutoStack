#!/bin/bash
# AutoStack Deployment Status Checker

IP="44.246.130.102"
PORT="3000"

echo "🔍 Checking AutoStack deployment status..."
echo "📍 Instance: $IP"
echo "🚀 Launched: 2025-11-23T18:17:15+00:00"
echo ""

# Check how long it's been running
LAUNCH_TIME=$(date -d "2025-11-23T18:17:15+00:00" +%s)
CURRENT_TIME=$(date +%s)
RUNNING_TIME=$((CURRENT_TIME - LAUNCH_TIME))
MINUTES=$((RUNNING_TIME / 60))

echo "⏱️  Running for: ${MINUTES} minutes (${RUNNING_TIME} seconds)"
echo ""

# Check basic connectivity
echo "🌐 Testing connectivity..."
if timeout 3 bash -c "</dev/tcp/$IP/22" 2>/dev/null; then
    echo "✅ SSH (port 22): Accessible"
else
    echo "❌ SSH (port 22): Not accessible"
fi

if timeout 3 bash -c "</dev/tcp/$IP/$PORT" 2>/dev/null; then
    echo "✅ API (port $PORT): Accessible"
    
    # Test API health endpoint
    echo ""
    echo "🏥 Testing API health..."
    RESPONSE=$(curl -s -m 5 http://$IP:$PORT/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ Health endpoint: $RESPONSE"
    else
        echo "⚠️  Health endpoint: No response yet"
    fi
else
    echo "❌ API (port $PORT): Not accessible yet"
fi

echo ""
if [ $MINUTES -lt 5 ]; then
    echo "⏳ Services typically take 5-10 minutes to fully start"
    echo "🔄 Try again in a few minutes"
elif [ $MINUTES -lt 10 ]; then
    echo "⏳ Still within normal startup time (5-10 minutes)"
    echo "🔄 Should be ready soon"
else
    echo "⚠️  Taking longer than expected (>10 minutes)"
    echo "🔧 May need troubleshooting"
fi

echo ""
echo "🔗 Once ready, test with:"
echo "   curl http://$IP:$PORT/health"