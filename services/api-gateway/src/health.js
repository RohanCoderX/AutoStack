const { Pool } = require('pg');

// Health check script for Docker
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function healthCheck() {
  try {
    // Check database connection
    await pool.query('SELECT 1');
    console.log('Health check passed');
    process.exit(0);
  } catch (error) {
    console.error('Health check failed:', error.message);
    process.exit(1);
  }
}

healthCheck();