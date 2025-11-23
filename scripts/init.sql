-- AutoStack Database Schema
-- This script initializes the PostgreSQL database with all required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    subscription_tier VARCHAR(50) DEFAULT 'free',
    github_id VARCHAR(100),
    google_id VARCHAR(100),
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_url VARCHAR(500),
    language VARCHAR(50),
    framework VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Code analyses table
CREATE TABLE code_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    file_path VARCHAR(500),
    language VARCHAR(50),
    framework VARCHAR(100),
    dependencies JSONB DEFAULT '{}',
    requirements JSONB DEFAULT '{}',
    analysis_results JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Infrastructure templates table
CREATE TABLE infrastructure_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    template_type VARCHAR(50) NOT NULL, -- terraform, cdk
    template_content TEXT NOT NULL,
    estimated_cost DECIMAL(10,2),
    resources JSONB DEFAULT '{}',
    optimization_suggestions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deployments table
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES infrastructure_templates(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    deployment_url VARCHAR(500),
    terraform_state_url VARCHAR(500),
    logs TEXT,
    error_message TEXT,
    deployed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking table
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- analyze, generate, deploy
    resource_type VARCHAR(50),
    cost DECIMAL(8,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_code_analyses_project_id ON code_analyses(project_id);
CREATE INDEX idx_infrastructure_templates_project_id ON infrastructure_templates(project_id);
CREATE INDEX idx_deployments_template_id ON deployments(template_id);
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);

-- Insert sample data for development
INSERT INTO users (email, name, subscription_tier, api_key) VALUES 
('demo@autostack.dev', 'Demo User', 'pro', 'as_demo_key_123456789'),
('test@autostack.dev', 'Test User', 'free', 'as_test_key_987654321');

-- Sample project
INSERT INTO projects (user_id, name, description, language, framework) VALUES 
((SELECT id FROM users WHERE email = 'demo@autostack.dev'), 
 'Sample Node.js API', 
 'A REST API with PostgreSQL database', 
 'javascript', 
 'express');