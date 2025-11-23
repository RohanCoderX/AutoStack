const express = require('express');
const { Pool } = require('pg');
const axios = require('axios');
const { checkSubscription } = require('../middleware/auth');

const router = express.Router();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Get all deployments for user
router.get('/', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.*, it.template_type, p.name as project_name
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE p.user_id = $1
      ORDER BY d.created_at DESC
    `, [req.user.id]);

    res.json({ deployments: result.rows });
  } catch (error) {
    console.error('Get deployments error:', error);
    res.status(500).json({ error: 'Failed to fetch deployments' });
  }
});

// Get deployments for specific project
router.get('/project/:projectId', async (req, res) => {
  try {
    const { projectId } = req.params;

    // Verify project ownership
    const projectResult = await pool.query(
      'SELECT id FROM projects WHERE id = $1 AND user_id = $2',
      [projectId, req.user.id]
    );

    if (projectResult.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    const result = await pool.query(`
      SELECT d.*, it.template_type
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      WHERE it.project_id = $1
      ORDER BY d.created_at DESC
    `, [projectId]);

    res.json({ deployments: result.rows });
  } catch (error) {
    console.error('Get project deployments error:', error);
    res.status(500).json({ error: 'Failed to fetch project deployments' });
  }
});

// Get specific deployment
router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.*, it.template_type, it.template_content, p.name as project_name, p.user_id
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE d.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deployment not found' });
    }

    res.json({ deployment: result.rows[0] });
  } catch (error) {
    console.error('Get deployment error:', error);
    res.status(500).json({ error: 'Failed to fetch deployment' });
  }
});

// Deploy infrastructure
router.post('/deploy', checkSubscription('starter'), async (req, res) => {
  try {
    const { templateId, awsCredentials, region = 'us-west-2' } = req.body;

    if (!templateId) {
      return res.status(400).json({ error: 'Template ID required' });
    }

    // Verify template ownership
    const templateResult = await pool.query(`
      SELECT it.*, p.user_id, p.name as project_name
      FROM infrastructure_templates it
      JOIN projects p ON it.project_id = p.id
      WHERE it.id = $1 AND p.user_id = $2
    `, [templateId, req.user.id]);

    if (templateResult.rows.length === 0) {
      return res.status(404).json({ error: 'Template not found' });
    }

    const template = templateResult.rows[0];

    // Create deployment record
    const deploymentResult = await pool.query(
      'INSERT INTO deployments (template_id, status) VALUES ($1, $2) RETURNING *',
      [templateId, 'pending']
    );

    const deployment = deploymentResult.rows[0];

    // Call deployment service
    try {
      await axios.post(`${process.env.DEPLOYMENT_SERVICE_URL || 'http://deployment-service:8002'}/deploy`, {
        deploymentId: deployment.id,
        template: template.template_content,
        templateType: template.template_type,
        projectName: template.project_name,
        awsCredentials,
        region
      });

      res.json({
        message: 'Deployment started',
        deployment: {
          id: deployment.id,
          status: 'pending',
          created_at: deployment.created_at
        }
      });
    } catch (serviceError) {
      console.error('Deployment service error:', serviceError.message);
      
      // Update deployment status to failed
      await pool.query(
        'UPDATE deployments SET status = $1, error_message = $2 WHERE id = $3',
        ['failed', 'Deployment service unavailable', deployment.id]
      );

      return res.status(503).json({ error: 'Deployment service unavailable' });
    }
  } catch (error) {
    console.error('Deploy error:', error);
    res.status(500).json({ error: 'Failed to start deployment' });
  }
});

// Get deployment status
router.get('/:id/status', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.id, d.status, d.deployment_url, d.error_message, d.deployed_at, d.created_at, p.user_id
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE d.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deployment not found' });
    }

    res.json({ deployment: result.rows[0] });
  } catch (error) {
    console.error('Get deployment status error:', error);
    res.status(500).json({ error: 'Failed to fetch deployment status' });
  }
});

// Get deployment logs
router.get('/:id/logs', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.logs, p.user_id
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE d.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deployment not found' });
    }

    res.json({ logs: result.rows[0].logs || 'No logs available' });
  } catch (error) {
    console.error('Get deployment logs error:', error);
    res.status(500).json({ error: 'Failed to fetch deployment logs' });
  }
});

// Cancel deployment
router.post('/:id/cancel', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.id, d.status, p.user_id
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE d.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deployment not found' });
    }

    const deployment = result.rows[0];

    if (deployment.status !== 'pending' && deployment.status !== 'running') {
      return res.status(400).json({ error: 'Cannot cancel deployment in current status' });
    }

    // Call deployment service to cancel
    try {
      await axios.post(`${process.env.DEPLOYMENT_SERVICE_URL || 'http://deployment-service:8002'}/cancel`, {
        deploymentId: deployment.id
      });

      // Update status
      await pool.query(
        'UPDATE deployments SET status = $1 WHERE id = $2',
        ['cancelled', deployment.id]
      );

      res.json({ message: 'Deployment cancelled successfully' });
    } catch (serviceError) {
      console.error('Cancel deployment service error:', serviceError.message);
      return res.status(503).json({ error: 'Failed to cancel deployment' });
    }
  } catch (error) {
    console.error('Cancel deployment error:', error);
    res.status(500).json({ error: 'Failed to cancel deployment' });
  }
});

// Destroy infrastructure
router.post('/:id/destroy', checkSubscription('starter'), async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT d.id, d.status, d.terraform_state_url, p.user_id
      FROM deployments d
      JOIN infrastructure_templates it ON d.template_id = it.id
      JOIN projects p ON it.project_id = p.id
      WHERE d.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deployment not found' });
    }

    const deployment = result.rows[0];

    if (deployment.status !== 'completed') {
      return res.status(400).json({ error: 'Can only destroy completed deployments' });
    }

    // Call deployment service to destroy
    try {
      await axios.post(`${process.env.DEPLOYMENT_SERVICE_URL || 'http://deployment-service:8002'}/destroy`, {
        deploymentId: deployment.id,
        stateUrl: deployment.terraform_state_url
      });

      // Update status
      await pool.query(
        'UPDATE deployments SET status = $1 WHERE id = $2',
        ['destroying', deployment.id]
      );

      res.json({ message: 'Infrastructure destruction started' });
    } catch (serviceError) {
      console.error('Destroy deployment service error:', serviceError.message);
      return res.status(503).json({ error: 'Failed to start destruction' });
    }
  } catch (error) {
    console.error('Destroy deployment error:', error);
    res.status(500).json({ error: 'Failed to destroy infrastructure' });
  }
});

module.exports = router;