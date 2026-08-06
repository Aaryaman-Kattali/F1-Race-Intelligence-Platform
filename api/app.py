"""
F1 Race Intelligence Platform — FastAPI Application.

Endpoints:
    GET  /              — API status
    POST /api/predict   — Race winner prediction (rule-based + XGBoost hybrid)
    GET  /api/circuits  — List available circuits
    GET  /api/health    — Health check
    POST /api/ask       — Natural-language query agent (LangChain + Gemini)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sys
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.predictor.gp_predictor import GPPredictor

logger = logging.getLogger(__name__)

app = FastAPI(
    title="F1 Race Intelligence Platform",
    description="Data engineering + agentic AI platform for F1 race prediction and analysis",
    version="2.0.0",
)

# CORS middleware (replaces Flask-CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictor
predictor = GPPredictor()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    gp_name: str = Field(..., description="Grand Prix name, e.g. 'Hungarian Grand Prix'")


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural-language question about F1 data")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def home():
    return {"message": "F1 Race Intelligence Platform is running!"}


@app.post("/api/predict")
async def predict_race(request: PredictRequest):
    """Generate race winner prediction using the rule-based/XGBoost hybrid engine."""
    try:
        logger.info(f"🏁 API: Predicting for {request.gp_name}")
        prediction = predictor.predict_race_winner(request.gp_name)

        if "error" in prediction:
            raise HTTPException(status_code=400, detail=prediction["error"])

        return {"success": True, "data": prediction}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/circuits")
async def get_circuits():
    """List all available F1 circuits."""
    circuits = predictor.circuit_mapper.list_available_circuits()
    return circuits


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "F1 Race Intelligence Platform is running",
        "circuits_loaded": len(predictor.circuits),
        "active_drivers": len(predictor.active_drivers_2025),
    }


@app.post("/api/ask")
async def ask_question(request: AskRequest):
    """
    Natural-language query against the F1 data warehouse.

    Uses a LangChain text-to-SQL agent backed by Gemini to generate and execute
    SQL against the BigQuery warehouse (dbt-modeled tables).
    """
    try:
        from src.agent.query_agent import QueryAgent
        from src.agent.query_logger import QueryLogger

        agent = QueryAgent()
        query_logger = QueryLogger()

        result = agent.ask(request.question)
        query_logger.log(
            question=request.question,
            generated_sql=result.get("generated_sql", ""),
            response=result.get("natural_language_answer", ""),
            success="error" not in result,
            error=result.get("error"),
            estimated_bytes=result.get("estimated_bytes_scanned", 0),
        )
        return {"success": True, "data": result}
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Agent module not yet configured. Set GOOGLE_API_KEY and BigQuery credentials.",
        )
    except Exception as e:
        logger.error(f"❌ Agent Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("🏎️ Starting F1 Race Intelligence Platform...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 Docs at: http://localhost:8000/docs")
    print("🎯 Health: http://localhost:8000/api/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
