"""
SuperKalam FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from app.config import settings
from app.database import create_tables
from app.routes import evaluate, model_answer, topics, attempts

# Create SQLite tables
create_tables()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

# CORS (allow frontend if separated)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(evaluate.router, prefix="/api", tags=["Evaluation"])
app.include_router(model_answer.router, prefix="/api", tags=["Model Answer"])
app.include_router(topics.router, prefix="/api", tags=["Browse"])
app.include_router(attempts.router, prefix="/api", tags=["History"])

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files for the web UI
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the UI."""
    return RedirectResponse(url="/ui/")
