#!/usr/bin/env python3
"""
Test script for Code Analysis Service
"""
import asyncio
import aiohttp
import json

async def test_code_analysis_service():
    """Test the code analysis service endpoints"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Code Analysis Service...\n")
        
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
        
        # Test content analysis
        sample_code = '''
def calculate_fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class DatabaseManager:
    def __init__(self, connection_string):
        self.connection = connection_string
    
    def connect(self):
        # Connect to database
        pass
'''
        
        try:
            payload = {
                "filename": "test.py",
                "content": sample_code,
                "language": "python"
            }
            
            async with session.post(f"{base_url}/analyze-content", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Content analysis:")
                    print(f"   Language: {data.get('language')}")
                    print(f"   Functions: {len(data.get('structure', {}).get('functions', []))}")
                    print(f"   Classes: {len(data.get('structure', {}).get('classes', []))}")
                    print(f"   Requirements: {list(data.get('requirements', {}).keys())}")
                else:
                    print("❌ Content analysis failed:", response.status)
                    error = await response.text()
                    print("   Error:", error)
        except Exception as e:
            print("❌ Content analysis error:", str(e))
        
        print("\n🎉 Code Analysis Service tests completed!")

if __name__ == "__main__":
    asyncio.run(test_code_analysis_service())