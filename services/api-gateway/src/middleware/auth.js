const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const authenticateToken = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Verify user still exists
    const result = await pool.query('SELECT id, email, subscription_tier FROM users WHERE id = $1', [decoded.userId]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid token' });
    }

    req.user = result.rows[0];
    next();
  } catch (error) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
};

const authenticateApiKey = async (req, res, next) => {
  const apiKey = req.headers['x-api-key'];

  if (!apiKey) {
    return res.status(401).json({ error: 'API key required' });
  }

  try {
    const result = await pool.query('SELECT id, email, subscription_tier FROM users WHERE api_key = $1', [apiKey]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    req.user = result.rows[0];
    next();
  } catch (error) {
    return res.status(500).json({ error: 'Authentication error' });
  }
};

const checkSubscription = (requiredTier) => {
  const tierLevels = { free: 0, starter: 1, pro: 2, enterprise: 3 };
  
  return (req, res, next) => {
    const userTier = req.user.subscription_tier;
    
    if (tierLevels[userTier] < tierLevels[requiredTier]) {
      return res.status(403).json({ 
        error: 'Subscription upgrade required',
        required: requiredTier,
        current: userTier
      });
    }
    
    next();
  };
};

module.exports = {
  authenticateToken,
  authenticateApiKey,
  checkSubscription
};