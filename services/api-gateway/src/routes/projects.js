const express = require('express');
const { Pool } = require('pg');
const multer = require('multer');
const { checkSubscription } = require('../middleware/auth');

const router = express.Router();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Configure multer for file uploads
const upload = multer({
  limits: { fileSize: 100 * 1024 * 1024 }, // 100MB limit
  fileFilter: (req, file, cb) => {
    // Allow common code files
    const allowedTypes = /\.(js|ts|py|java|go|rb|php|cs|cpp|c|h|json|yaml|yml|dockerfile|tf|hcl)$/i;
    if (allowedTypes.test(file.originalname)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  }
});

// Get all projects for user
router.get('/', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT id, name, description, repository_url, language, framework, status, created_at FROM projects WHERE user_id = $1 ORDER BY created_at DESC',
      [req.user.id]
    );

    res.json({ projects: result.rows });
  } catch (error) {
    console.error('Get projects error:', error);
    res.status(500).json({ error: 'Failed to fetch projects' });
  }
});

// Create new project
router.post('/', async (req, res) => {
  try {
    const { name, description, repository_url, language, framework } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Project name required' });
    }

    // Check project limits based on subscription
    const projectCount = await pool.query('SELECT COUNT(*) FROM projects WHERE user_id = $1', [req.user.id]);
    const limits = { free: 5, starter: 20, pro: Infinity, enterprise: Infinity };
    
    if (projectCount.rows[0].count >= limits[req.user.subscription_tier]) {
      return res.status(403).json({ error: 'Project limit reached for your subscription tier' });
    }

    const result = await pool.query(
      'INSERT INTO projects (user_id, name, description, repository_url, language, framework) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
      [req.user.id, name, description, repository_url, language, framework]
    );

    res.status(201).json({ project: result.rows[0] });
  } catch (error) {
    console.error('Create project error:', error);
    res.status(500).json({ error: 'Failed to create project' });
  }
});

// Get specific project
router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM projects WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.json({ project: result.rows[0] });
  } catch (error) {
    console.error('Get project error:', error);
    res.status(500).json({ error: 'Failed to fetch project' });
  }
});

// Update project
router.put('/:id', async (req, res) => {
  try {
    const { name, description, repository_url, language, framework } = req.body;

    const result = await pool.query(
      'UPDATE projects SET name = COALESCE($1, name), description = COALESCE($2, description), repository_url = COALESCE($3, repository_url), language = COALESCE($4, language), framework = COALESCE($5, framework), updated_at = NOW() WHERE id = $6 AND user_id = $7 RETURNING *',
      [name, description, repository_url, language, framework, req.params.id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.json({ project: result.rows[0] });
  } catch (error) {
    console.error('Update project error:', error);
    res.status(500).json({ error: 'Failed to update project' });
  }
});

// Delete project
router.delete('/:id', async (req, res) => {
  try {
    const result = await pool.query(
      'DELETE FROM projects WHERE id = $1 AND user_id = $2 RETURNING id',
      [req.params.id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.json({ message: 'Project deleted successfully' });
  } catch (error) {
    console.error('Delete project error:', error);
    res.status(500).json({ error: 'Failed to delete project' });
  }
});

// Upload code files to project
router.post('/:id/upload', upload.array('files', 50), async (req, res) => {
  try {
    const projectId = req.params.id;

    // Verify project ownership
    const projectResult = await pool.query(
      'SELECT id FROM projects WHERE id = $1 AND user_id = $2',
      [projectId, req.user.id]
    );

    if (projectResult.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    // Store file information and trigger analysis
    const uploadedFiles = [];
    for (const file of req.files) {
      const analysisResult = await pool.query(
        'INSERT INTO code_analyses (project_id, file_path, status) VALUES ($1, $2, $3) RETURNING id',
        [projectId, file.originalname, 'pending']
      );

      uploadedFiles.push({
        id: analysisResult.rows[0].id,
        filename: file.originalname,
        size: file.size,
        content: file.buffer.toString('utf8')
      });
    }

    res.json({
      message: 'Files uploaded successfully',
      files: uploadedFiles.map(f => ({ id: f.id, filename: f.filename, size: f.size }))
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload files' });
  }
});

module.exports = router;