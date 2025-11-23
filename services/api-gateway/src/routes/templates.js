const express = require('express');
const { Pool } = require('pg');
const axios = require('axios');
const { checkSubscription } = require('../middleware/auth');

const router = express.Router();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Get all templates for a project
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

    const result = await pool.query(
      'SELECT id, template_type, estimated_cost, resources, optimization_suggestions, created_at FROM infrastructure_templates WHERE project_id = $1 ORDER BY created_at DESC',
      [projectId]
    );

    res.json({ templates: result.rows });
  } catch (error) {
    console.error('Get templates error:', error);
    res.status(500).json({ error: 'Failed to fetch templates' });
  }
});

// Get specific template
router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT it.*, p.user_id 
      FROM infrastructure_templates it 
      JOIN projects p ON it.project_id = p.id 
      WHERE it.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Template not found' });
    }

    res.json({ template: result.rows[0] });
  } catch (error) {
    console.error('Get template error:', error);
    res.status(500).json({ error: 'Failed to fetch template' });
  }
});

// Generate infrastructure template
router.post('/generate', async (req, res) => {
  try {
    const { projectId, templateType = 'terraform', optimizationLevel = 'balanced' } = req.body;

    if (!projectId) {
      return res.status(400).json({ error: 'Project ID required' });
    }

    // Verify project ownership
    const projectResult = await pool.query(
      'SELECT id, name FROM projects WHERE id = $1 AND user_id = $2',
      [projectId, req.user.id]
    );

    if (projectResult.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    // Check if analysis is completed
    const analysisResult = await pool.query(
      'SELECT COUNT(*) as total, COUNT(CASE WHEN status = \'completed\' THEN 1 END) as completed FROM code_analyses WHERE project_id = $1',
      [projectId]
    );

    const { total, completed } = analysisResult.rows[0];
    if (total === 0) {
      return res.status(400).json({ error: 'No code analysis found. Please upload and analyze code first.' });
    }

    if (completed === 0) {
      return res.status(400).json({ error: 'Code analysis not completed yet. Please wait for analysis to finish.' });
    }

    // Get analysis results
    const requirementsResult = await pool.query(`
      SELECT 
        jsonb_object_agg(key, value) as requirements
      FROM (
        SELECT key, jsonb_agg(DISTINCT value) as value
        FROM code_analyses ca,
        jsonb_each(ca.requirements) 
        WHERE ca.project_id = $1 AND ca.status = 'completed'
        GROUP BY key
      ) subq
    `, [projectId]);

    const requirements = requirementsResult.rows[0]?.requirements || {};

    // Call infrastructure generation service
    try {
      const response = await axios.post(`${process.env.INFRASTRUCTURE_SERVICE_URL || 'http://infrastructure-service:8001'}/generate`, {
        projectId,
        projectName: projectResult.rows[0].name,
        requirements,
        templateType,
        optimizationLevel,
        subscriptionTier: req.user.subscription_tier
      });

      const { template, estimatedCost, resources, optimizationSuggestions } = response.data;

      // Save template to database
      const templateResult = await pool.query(
        'INSERT INTO infrastructure_templates (project_id, template_type, template_content, estimated_cost, resources, optimization_suggestions) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
        [projectId, templateType, template, estimatedCost, JSON.stringify(resources), JSON.stringify(optimizationSuggestions)]
      );

      res.json({
        message: 'Template generated successfully',
        template: templateResult.rows[0]
      });
    } catch (serviceError) {
      console.error('Infrastructure service error:', serviceError.message);
      return res.status(503).json({ error: 'Infrastructure generation service unavailable' });
    }
  } catch (error) {
    console.error('Generate template error:', error);
    res.status(500).json({ error: 'Failed to generate template' });
  }
});

// Download template file
router.get('/:id/download', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT it.template_content, it.template_type, p.name as project_name, p.user_id 
      FROM infrastructure_templates it 
      JOIN projects p ON it.project_id = p.id 
      WHERE it.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Template not found' });
    }

    const { template_content, template_type, project_name } = result.rows[0];
    const extension = template_type === 'terraform' ? 'tf' : 'ts';
    const filename = `${project_name.replace(/[^a-zA-Z0-9]/g, '_')}_infrastructure.${extension}`;

    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.send(template_content);
  } catch (error) {
    console.error('Download template error:', error);
    res.status(500).json({ error: 'Failed to download template' });
  }
});

// Get cost estimation
router.post('/estimate-cost', checkSubscription('starter'), async (req, res) => {
  try {
    const { resources, region = 'us-west-2' } = req.body;

    if (!resources) {
      return res.status(400).json({ error: 'Resources configuration required' });
    }

    // Call cost calculation service
    try {
      const response = await axios.post(`${process.env.COST_SERVICE_URL || 'http://infrastructure-service:8001'}/estimate-cost`, {
        resources,
        region
      });

      res.json(response.data);
    } catch (serviceError) {
      console.error('Cost service error:', serviceError.message);
      return res.status(503).json({ error: 'Cost estimation service unavailable' });
    }
  } catch (error) {
    console.error('Cost estimation error:', error);
    res.status(500).json({ error: 'Failed to estimate cost' });
  }
});

// Optimize template
router.post('/:id/optimize', checkSubscription('pro'), async (req, res) => {
  try {
    const { optimizationGoals = ['cost', 'performance'] } = req.body;

    const result = await pool.query(`
      SELECT it.*, p.user_id 
      FROM infrastructure_templates it 
      JOIN projects p ON it.project_id = p.id 
      WHERE it.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Template not found' });
    }

    const template = result.rows[0];

    // Call optimization service
    try {
      const response = await axios.post(`${process.env.INFRASTRUCTURE_SERVICE_URL || 'http://infrastructure-service:8001'}/optimize`, {
        template: template.template_content,
        resources: template.resources,
        optimizationGoals
      });

      const { optimizedTemplate, estimatedCost, optimizationSuggestions } = response.data;

      // Create new optimized template
      const optimizedResult = await pool.query(
        'INSERT INTO infrastructure_templates (project_id, template_type, template_content, estimated_cost, resources, optimization_suggestions) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
        [template.project_id, template.template_type, optimizedTemplate, estimatedCost, template.resources, JSON.stringify(optimizationSuggestions)]
      );

      res.json({
        message: 'Template optimized successfully',
        originalCost: template.estimated_cost,
        optimizedCost: estimatedCost,
        savings: template.estimated_cost - estimatedCost,
        template: optimizedResult.rows[0]
      });
    } catch (serviceError) {
      console.error('Optimization service error:', serviceError.message);
      return res.status(503).json({ error: 'Optimization service unavailable' });
    }
  } catch (error) {
    console.error('Optimize template error:', error);
    res.status(500).json({ error: 'Failed to optimize template' });
  }
});

module.exports = router;