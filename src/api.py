"""
FastAPI application for SQL Sage.
Serves the frontend and exposes the SQL analysis API.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from .analyzer import analyze_query

app = FastAPI(
    title="SQL Sage API",
    description="AI SQL explainer and optimizer with dialect detection and performance analysis",
    version="1.0.0"
)

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


class AnalyzeRequest(BaseModel):
    query: str
    dialect: str = "auto"

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("SQL query must be at least 10 characters")
        return v.strip()


class Inefficiency(BaseModel):
    issue: str
    description: str
    impact: str
    fix_hint: str


class EdgeCase(BaseModel):
    scenario: str
    risk: str
    mitigation: str


class AnalyzeResponse(BaseModel):
    dialect: str
    query_type: str
    complexity: str
    estimated_complexity: str
    plain_english_explanation: str
    step_by_step: list[str]
    inefficiencies: list[Inefficiency]
    optimized_query: str
    optimization_notes: list[str]
    edge_cases: list[EdgeCase]
    index_suggestions: list[str]
    overall_score: float


@app.get("/")
async def serve_frontend():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "SQL Sage API running. Frontend not found."}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_sql(request: AnalyzeRequest):
    """
    Analyze a SQL query for explanation, performance, and optimization.
    Auto-detects dialect if not specified.
    """
    try:
        result = analyze_query(request.query, request.dialect)
        return AnalyzeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sql-sage"}
