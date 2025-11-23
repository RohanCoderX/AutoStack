const express = require('express');
const { Pool } = require('pg');
const axios = require('axios');

const router = express.Router();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Get analysis results for a project
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
      'SELECT id, file_path, language, framework, dependencies, requirements, analysis_results, status, created_at FROM code_analyses WHERE project_id = $1 ORDER BY created_at DESC',
      [projectId]
    );

    res.json({ analyses: result.rows });
  } catch (error) {
    console.error('Get analysis error:', error);
    res.status(500).json({ error: 'Failed to fetch analysis results' });
  }
});

// Get specific analysis result
router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT ca.*, p.user_id 
      FROM code_analyses ca 
      JOIN projects p ON ca.project_id = p.id 
      WHERE ca.id = $1 AND p.user_id = $2
    `, [req.params.id, req.user.id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Analysis not found' });
    }

    res.json({ analysis: result.rows[0] });
  } catch (error) {
    console.error('Get analysis error:', error);
    res.status(500).json({ error: 'Failed to fetch analysis' });
  }
});

// Trigger code analysis
router.post('/analyze', async (req, res) => {
  try {
    const { projectId, files } = req.body;

    if (!projectId || !files || files.length === 0) {
      return res.status(400).json({ error: 'Project ID and files required' });
    }

    // Verify project ownership
    const projectResult = await pool.query(
      'SELECT id FROM projects WHERE id = $1 AND user_id = $2',
      [projectId, req.user.id]
    );

    if (projectResult.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    // Create analysis records
    const analysisIds = [];
    for (const file of files) {
      const result = await pool.query(
        'INSERT INTO code_analyses (project_id, file_path, status) VALUES ($1, $2, $3) RETURNING id',
        [projectId, file.filename, 'pending']
      );
      analysisIds.push(result.rows[0].id);
    }

    // Send to code analysis service (mock for now)
    try {
      await axios.post(`${process.env.CODE_ANALYSIS_SERVICE_URL || 'http://code-analysis:8000'}/analyze`, {
        projectId,
        files,
        analysisIds
      });
    } catch (serviceError) {
      console.error('Code analysis service error:', serviceError.message);
      // Update status to failed
      await pool.query(
        'UPDATE code_analyses SET status = $1 WHERE id = ANY($2)',
        ['failed', analysisIds]
      );
      return res.status(503).json({ error: 'Analysis service unavailable' });
    }

    res.json({
      message: 'Analysis started',
      analysisIds
    });
  } catch (error) {
    console.error('Analyze error:', error);
    res.status(500).json({ error: 'Failed to start analysis' });
  }
});

// Get analysis summary for project
router.get('/project/:projectId/summary', async (req, res) => {
  try {
    const { projectId } = req.params;

    // Verify project ownership
    const projectResult = await pool.query(
      'SELECT id, name FROM projects WHERE id = $1 AND user_id = $2',
      [projectId, req.user.id]
    );

    if (projectResult.rows.length === 0) {
      return res.status(404).json({ error: 'Project not found' });
    }

    // Get analysis summary
    const summaryResult = await pool.query(`
      SELECT 
        COUNT(*) as total_files,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
        array_agg(DISTINCT language) FILTER (WHERE language IS NOT NULL) as languages,
        array_agg(DISTINCT framework) FILTER (WHERE framework IS NOT NULL) as frameworks
      FROM code_analyses 
      WHERE project_id = $1
    `, [projectId]);

    const summary = summaryResult.rows[0];

    // Get infrastructure requirements
    const requirementsResult = await pool.query(`
      SELECT 
        jsonb_object_agg(key, value) as aggregated_requirements
      FROM (
        SELECT key, jsonb_agg(DISTINCT value) as value
        FROM code_analyses ca,
        jsonb_each(ca.requirements) 
        WHERE ca.project_id = $1 AND ca.status = 'completed'
        GROUP BY key
      ) subq
    `, [projectId]);

    res.json({
      project: projectResult.rows[0],
      summary: {
        totalFiles: parseInt(summary.total_files),
        completed: parseInt(summary.completed),
        pending: parseInt(summary.pending),
        failed: parseInt(summary.failed),
        languages: summary.languages || [],
        frameworks: summary.frameworks || []
      },
      requirements: requirementsResult.rows[0]?.aggregated_requirements || {}
    });
  } catch (error) {
    console.error('Get summary error:', error);
    res.status(500).json({ error: 'Failed to fetch analysis summary' });
  }
});

module.exports = router;