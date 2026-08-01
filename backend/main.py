import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict, Any

from backend.models import ArticleResponse, KnowledgeNode
from backend.gemini_service import get_article, get_all_nodes, init_db

app = FastAPI(
    title="Encarta 2.0 API Server",
    description="Backend API for Encarta 2.0 (NewGen Retro Edition)",
    version="2.0.0"
)

# Enable CORS for cross-origin development requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/nodes/reset")
def reset_knowledge_nodes():
    """Resets SQLite database tables cleanly and re-seeds initial knowledge nodes."""
    init_db(force_reset=True)
    nodes = get_all_nodes()
    return {"status": "success", "message": "Database reset cleanly", "nodes": nodes}



@app.get("/api/seed-topics", response_model=List[KnowledgeNode])
@app.get("/api/nodes", response_model=List[KnowledgeNode])
def list_knowledge_nodes():
    """Returns all persistent knowledge nodes stored in SQLite database."""
    nodes = get_all_nodes()
    return nodes


@app.post("/api/nodes/add")
def add_knowledge_node(topic: str = Query(..., description="Topic name to create and add")):
    """Explicitly generates, stores in SQLite, and returns a new knowledge node."""
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic parameter cannot be empty.")
    article = get_article(topic)
    nodes = get_all_nodes()
    return {"status": "success", "article": article, "nodes": nodes}


@app.get("/api/article", response_model=ArticleResponse)
def fetch_article(topic: str = Query(..., description="Topic name to retrieve")):
    """Fetches structured article summary, timeline, trivia, and MindMaze questions for a topic."""
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic query parameter cannot be empty.")
    return get_article(topic)


# Resolve frontend static directory path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/")
    @app.get("/index.html")
    def read_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
