import os
from fastapi import FastAPI, HTTPException, Query, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
import urllib.request
import urllib.error

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
def fetch_article(
    topic: str = Query(..., description="Topic name to retrieve"),
    wiki: str = Query(None, description="Optional Wikipedia URL/Title")
):
    """Fetches structured article summary, timeline, trivia, and MindMaze questions for a topic."""
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic query parameter cannot be empty.")
        
    if wiki and wiki.startswith("http"):
        try:
            req = urllib.request.Request(wiki, method="HEAD", headers={'User-Agent': 'Mozilla/5.0'})
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or unreachable Wikipedia URL provided: {str(e)}")
            
    return get_article(topic, wiki=wiki)


# Resolve frontend static directory path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/")
    @app.get("/index.html")
    def read_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            four_o_four_path = os.path.join(FRONTEND_DIR, "404.html")
            if os.path.exists(four_o_four_path):
                return FileResponse(four_o_four_path, status_code=404)
        return FileResponse(os.path.join(FRONTEND_DIR, "404.html"), status_code=404)

    @app.get("/{full_path:path}")
    async def catch_all_routes(full_path: str):
        # Always serve the retro 404 page for unmatched routes
        four_o_four_path = os.path.join(FRONTEND_DIR, "404.html")
        if os.path.exists(four_o_four_path):
            return FileResponse(four_o_four_path, status_code=404)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
