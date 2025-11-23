const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

class SQLiteManager {
  constructor() {
    // Ensure data directory exists
    const dataDir = path.join(__dirname, '../../../data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    
    const dbPath = process.env.DATABASE_URL?.includes('sqlite') 
      ? process.env.DATABASE_URL.replace('sqlite:///', '')
      : path.join(dataDir, 'autostack.db');
    
    this.db = new Database(dbPath);
    this.initTables();
  }

  initTables() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        name TEXT,
        subscription_tier TEXT DEFAULT 'free',
        api_key TEXT UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        name TEXT NOT NULL,
        description TEXT,
        repository_url TEXT,
        language TEXT,
        framework TEXT,
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS code_analyses (
        id TEXT PRIMARY KEY,
        project_id TEXT REFERENCES projects(id),
        file_path TEXT,
        language TEXT,
        framework TEXT,
        dependencies TEXT, -- JSON as text
        requirements TEXT, -- JSON as text
        analysis_results TEXT, -- JSON as text
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS infrastructure_templates (
        id TEXT PRIMARY KEY,
        project_id TEXT REFERENCES projects(id),
        template_type TEXT NOT NULL,
        template_content TEXT NOT NULL,
        estimated_cost REAL,
        resources TEXT, -- JSON as text
        optimization_suggestions TEXT, -- JSON as text
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS deployments (
        id TEXT PRIMARY KEY,
        template_id TEXT REFERENCES infrastructure_templates(id),
        status TEXT DEFAULT 'pending',
        deployment_url TEXT,
        terraform_state_url TEXT,
        logs TEXT,
        error_message TEXT,
        deployed_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS usage_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        action TEXT NOT NULL,
        resource_type TEXT,
        cost REAL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  }

  query(sql, params = []) {
    try {
      if (sql.trim().toUpperCase().startsWith('SELECT')) {
        return this.db.prepare(sql).all(params);
      } else if (sql.trim().toUpperCase().startsWith('INSERT')) {
        const result = this.db.prepare(sql).run(params);
        return { lastInsertRowid: result.lastInsertRowid, changes: result.changes };
      } else {
        return this.db.prepare(sql).run(params);
      }
    } catch (error) {
      console.error('Database query error:', error);
      throw error;
    }
  }

  queryOne(sql, params = []) {
    try {
      return this.db.prepare(sql).get(params);
    } catch (error) {
      console.error('Database query error:', error);
      throw error;
    }
  }

  close() {
    this.db.close();
  }
}

module.exports = new SQLiteManager();