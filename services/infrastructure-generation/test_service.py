#!/usr/bin/env python3
"""
Test script for Infrastructure Generation Service
"""
import asyncio
import aiohttp
import json

async def test_infrastructure_service():
    """Test the infrastructure generation service endpoints"""
    base_url = "http://localhost:8001"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Infrastructure Generation Service...\n")
        
        # Test health endpoint
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Health check:", data)
                else:
                    print("❌ Health check failed:", response.status)
        except Exception as e:
            print("❌ Health check error:", str(e))
        
        # Test template generation
        sample_requirements = {
            "compute": {
                "type": "container",
                "cpu": "0.5",
                "memory": "1Gi",
                "replicas": 2
            },
            "database": {
                "type": "postgresql",
                "size": "db.t3.micro",
                "storage": "20GB"
            },
            "network": {
                "load_balancer": True,
                "ssl": True
            }
        }
        
        try:
            payload = {
                "projectId": "test-project-123",
                "projectName": "Test Web App",
                "requirements": sample_requirements,
                "templateType": "terraform",
                "optimizationLevel": "balanced"
            }
            
            async with session.post(f"{base_url}/generate", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Template generation:")
                    print(f"   Estimated cost: ${data.get('estimatedCost', 0):.2f}/month")
                    print(f"   Resources: {list(data.get('resources', {}).keys())}")
                    print(f"   Template length: {len(data.get('template', ''))} characters")
                    print(f"   Optimization suggestions: {len(data.get('optimizationSuggestions', []))}")
                else:
                    print("❌ Template generation failed:", response.status)
                    error = await response.text()
                    print("   Error:", error)
        except Exception as e:
            print("❌ Template generation error:", str(e))
        
        # Test cost estimation
        try:
            payload = {
                "resources": sample_requirements,
                "region": "us-west-2"
            }
            
            async with session.post(f"{base_url}/estimate-cost", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Cost estimation:")
                    print(f"   Monthly cost: ${data.get('monthlyCost', 0):.2f}")
                    print(f"   Yearly cost: ${data.get('yearlyCost', 0):.2f}")
                    print(f"   Breakdown: {list(data.get('breakdown', {}).keys())}")
                else:
                    print("❌ Cost estimation failed:", response.status)
        except Exception as e:
            print("❌ Cost estimation error:", str(e))
        
        # Test template examples
        try:
            async with session.get(f"{base_url}/templates/examples") as response:
                if response.status == 200:
                    data = await response.json()
                    examples = data.get('examples', [])
                    print(f"✅ Template examples: {len(examples)} available")
                    for example in examples:
                        print(f"   - {example.get('name')}: {example.get('description')}")
                else:
                    print("❌ Template examples failed:", response.status)
        except Exception as e:
            print("❌ Template examples error:", str(e))
        
        print("\n🎉 Infrastructure Generation Service tests completed!")

if __name__ == "__main__":
    asyncio.run(test_infrastructure_service())