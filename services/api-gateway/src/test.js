const request = require('supertest');
const app = require('./index');

// Simple test to verify the API Gateway is working
async function runTests() {
  console.log('🧪 Testing AutoStack API Gateway...\n');

  try {
    // Test health endpoint
    const healthResponse = await request(app).get('/health');
    console.log('✅ Health check:', healthResponse.body);

    // Test auth registration (will fail without DB, but route should exist)
    const registerResponse = await request(app)
      .post('/api/auth/register')
      .send({ email: 'test@example.com', password: 'password123' });
    
    console.log('📝 Register endpoint status:', registerResponse.status);

    // Test protected route without auth (should return 401)
    const protectedResponse = await request(app).get('/api/projects');
    console.log('🔒 Protected route without auth:', protectedResponse.status === 401 ? '✅ Properly protected' : '❌ Not protected');

    // Test 404 handling
    const notFoundResponse = await request(app).get('/api/nonexistent');
    console.log('🔍 404 handling:', notFoundResponse.status === 404 ? '✅ Working' : '❌ Not working');

    console.log('\n🎉 API Gateway tests completed!');
  } catch (error) {
    console.error('❌ Test error:', error.message);
  }
}

if (require.main === module) {
  runTests();
}

module.exports = { runTests };