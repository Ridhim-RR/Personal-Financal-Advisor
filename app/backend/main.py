import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.backend.routes import api_router
from app.backend.database.connection import get_db_manager
from app.backend.services.ollama_service import ollama_service

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Investment Research Copilot", description="Backend API for AI Investment Research Copilot", version="0.1.0")

# Initialize database tables
from app.backend.database import models  # noqa: F401
get_db_manager()

# 🌍 UPDATED CORS CONFIGURATION FOR PRODUCTION
# We allow your local development links AND catch your upcoming live production frontend URL
allowed_origins = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    os.environ.get("FRONTEND_URL", "*") # Falls back to wildcard if frontend isn't live yet
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Checking Ollama availability...")
        status = await ollama_service.check_ollama_status()

        if status["installed"]:
            if status["running"]:
                logger.info(f"✓ Ollama is installed and running at {status['server_url']}")
                if status["available_models"]:
                    logger.info(f"✓ Available models: {', '.join(status['available_models'])}")
                else:
                    logger.info("ℹ No models are currently downloaded")
            else:
                logger.info("ℹ Ollama is installed but not running")
        else:
            logger.info("ℹ Ollama is not installed. Defaulting to Cloud API providers (Groq/OpenAI) if configured.")

    except Exception as e:
        logger.warning(f"Could not check Ollama status: {e}")
        logger.info("ℹ Server starting without local Ollama connection.")


# 🚀 NEW: THE PRODUCTION ENTRY GATEWAY FOR RENDER
if __name__ == "__main__":
    # Pull the port dynamically from Render's server environment, default to 8000 locally
    production_port = int(os.environ.get("PORT", 8000))
    
    # Run Uvicorn pointing directly to this main file's app instance
    # "app.backend.main:app" matches your structure inside your 'app' folder
    uvicorn.run("app.backend.main:app", host="0.0.0.0", port=production_port)