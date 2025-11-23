from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio
import logging
from dotenv import load_dotenv

from .analyzers.code_analyzer import CodeAnalyzer
from .analyzers.amazon_q_client import AmazonQClient
from .utils.database import DatabaseManager
from .utils.logger import setup_logger

load_dotenv()

app = FastAPI(
    title="AutoStack Code Analysis Service",
    description="AI-powered code analysis using Amazon Q",
    version="1.0.0"
)

logger = setup_logger(__name__)
db_manager = DatabaseManager()
code_analyzer = CodeAnalyzer()
amazon_q = AmazonQClient()

class AnalysisRequest(BaseModel):
    projectId: str
    files: List[Dict[str, Any]]
    analysisIds: List[str]

class FileContent(BaseModel):
    filename: str
    content: str
    language: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await db_manager.connect()
    logger.info("Code Analysis Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_manager.disconnect()
    logger.info("Code Analysis Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db_manager.execute("SELECT 1")
        return {
            "status": "healthy",
            "service": "code-analysis",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/analyze")
async def analyze_code(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start code analysis for uploaded files"""
    try:
        logger.info(f"Starting analysis for project {request.projectId}")
        
        # Process each file in background
        for i, file_data in enumerate(request.files):
            analysis_id = request.analysisIds[i]
            background_tasks.add_task(
                process_file_analysis,
                analysis_id,
                file_data,
                request.projectId
            )
        
        return {
            "message": "Analysis started",
            "projectId": request.projectId,
            "filesCount": len(request.files)
        }
    except Exception as e:
        logger.error(f"Analysis start error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start analysis")

@app.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Get analysis result by ID"""
    try:
        result = await db_manager.fetch_one(
            "SELECT * FROM code_analyses WHERE id = $1",
            analysis_id
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {"analysis": dict(result)}
    except Exception as e:
        logger.error(f"Get analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")

@app.post("/analyze-content")
async def analyze_content(file: FileContent):
    """Analyze single file content directly"""
    try:
        # Detect language if not provided
        language = file.language or code_analyzer.detect_language(file.filename)
        
        # Parse code structure
        structure = await code_analyzer.parse_code(file.content, language)
        
        # Extract requirements using Amazon Q
        requirements = await amazon_q.extract_requirements(
            file.content, 
            language, 
            structure
        )
        
        return {
            "filename": file.filename,
            "language": language,
            "structure": structure,
            "requirements": requirements
        }
    except Exception as e:
        logger.error(f"Content analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze content")

async def process_file_analysis(analysis_id: str, file_data: Dict, project_id: str):
    """Background task to process individual file analysis"""
    try:
        # Update status to running
        await db_manager.execute(
            "UPDATE code_analyses SET status = $1 WHERE id = $2",
            "running", analysis_id
        )
        
        filename = file_data.get("filename", "")
        content = file_data.get("content", "")
        
        # Detect programming language
        language = code_analyzer.detect_language(filename)
        
        # Parse code structure
        structure = await code_analyzer.parse_code(content, language)
        
        # Extract framework information
        framework = code_analyzer.detect_framework(content, language)
        
        # Get dependencies
        dependencies = code_analyzer.extract_dependencies(content, language)
        
        # Use Amazon Q to extract infrastructure requirements
        requirements = await amazon_q.extract_requirements(
            content, language, structure, dependencies
        )
        
        # Get security analysis
        security_analysis = await amazon_q.analyze_security(content, language)
        
        # Combine analysis results
        analysis_results = {
            "structure": structure,
            "security": security_analysis,
            "complexity": code_analyzer.calculate_complexity(content, language),
            "patterns": code_analyzer.identify_patterns(content, language)
        }
        
        # Update database with results
        await db_manager.execute("""
            UPDATE code_analyses 
            SET language = $1, framework = $2, dependencies = $3, 
                requirements = $4, analysis_results = $5, status = $6
            WHERE id = $7
        """, language, framework, dependencies, requirements, analysis_results, "completed", analysis_id)
        
        logger.info(f"Analysis completed for {filename}")
        
    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {e}")
        
        # Update status to failed
        await db_manager.execute(
            "UPDATE code_analyses SET status = $1, analysis_results = $2 WHERE id = $3",
            "failed", {"error": str(e)}, analysis_id
        )

@app.get("/project/{project_id}/summary")
async def get_project_analysis_summary(project_id: str):
    """Get aggregated analysis summary for a project"""
    try:
        # Get all completed analyses for the project
        analyses = await db_manager.fetch_all(
            "SELECT * FROM code_analyses WHERE project_id = $1 AND status = 'completed'",
            project_id
        )
        
        if not analyses:
            return {"message": "No completed analyses found"}
        
        # Aggregate requirements
        aggregated_requirements = {}
        languages = set()
        frameworks = set()
        total_complexity = 0
        
        for analysis in analyses:
            if analysis['language']:
                languages.add(analysis['language'])
            if analysis['framework']:
                frameworks.add(analysis['framework'])
            
            # Merge requirements
            if analysis['requirements']:
                for key, value in analysis['requirements'].items():
                    if key not in aggregated_requirements:
                        aggregated_requirements[key] = set()
                    if isinstance(value, list):
                        aggregated_requirements[key].update(value)
                    else:
                        aggregated_requirements[key].add(value)
            
            # Sum complexity
            if analysis['analysis_results'] and 'complexity' in analysis['analysis_results']:
                total_complexity += analysis['analysis_results']['complexity']
        
        # Convert sets to lists for JSON serialization
        for key in aggregated_requirements:
            aggregated_requirements[key] = list(aggregated_requirements[key])
        
        return {
            "projectId": project_id,
            "totalFiles": len(analyses),
            "languages": list(languages),
            "frameworks": list(frameworks),
            "totalComplexity": total_complexity,
            "aggregatedRequirements": aggregated_requirements
        }
        
    except Exception as e:
        logger.error(f"Project summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate project summary")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)