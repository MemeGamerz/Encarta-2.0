import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List

from backend.models import ArticleResponse, SeedTopic
from backend.gemini_service import get_article

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

# Initial Seed Topics for 3D Spatial Knowledge Graph Globe (Interconnected Network)
SEED_TOPICS: List[SeedTopic] = [
    SeedTopic(
        id="microsoft-encarta",
        title="Microsoft Encarta",
        category="Technology",
        era="1993 – 2009",
        lat=47.6405,
        lng=-122.1297,
        summary_short="The legendary 90s CD-ROM multimedia digital encyclopedia pioneer."
    ),
    SeedTopic(
        id="ancient-rome",
        title="Ancient Rome",
        category="History",
        era="753 BCE – 476 CE",
        lat=41.9028,
        lng=12.4964,
        summary_short="The colossal empire that pioneered Roman law, roads, and aqueducts."
    ),
    SeedTopic(
        id="byzantine-empire",
        title="Byzantine Empire",
        category="History",
        era="330 CE – 1453 CE",
        lat=41.0082,
        lng=28.9784,
        summary_short="Constantinople crossroads connecting Western Europe and Silk Road trade."
    ),
    SeedTopic(
        id="silk-road",
        title="The Silk Road",
        category="Trade & Exploration",
        era="130 BCE – 1453 CE",
        lat=34.3416,
        lng=108.9398,
        summary_short="Ancient transcontinental trade network connecting Asia, Persia, and Europe."
    ),
    SeedTopic(
        id="ancient-persia",
        title="Ancient Persia",
        category="History",
        era="550 BCE – 330 BCE",
        lat=29.9352,
        lng=52.8906,
        summary_short="Persepolis empire linking Silk Road, Mesopotamia, and Mediterranean."
    ),
    SeedTopic(
        id="age-of-discovery",
        title="Age of Discovery",
        category="Trade & Exploration",
        era="1400 – 1700",
        lat=38.7223,
        lng=-9.1393,
        summary_short="Global maritime exploration linking Silk Road routes to the Americas."
    ),
    SeedTopic(
        id="silicon-valley",
        title="Silicon Valley",
        category="Technology",
        era="1939 – Present",
        lat=37.3875,
        lng=-122.0575,
        summary_short="Global epicenter of microchip innovation, personal computing, and AI."
    ),
    SeedTopic(
        id="quantum-physics",
        title="Quantum Physics",
        category="Science",
        era="1900 – Present",
        lat=52.5200,
        lng=13.4050,
        summary_short="The subatomic physics revolution of wave-particle duality and entanglement."
    ),
    SeedTopic(
        id="renaissance-florence",
        title="Renaissance Florence",
        category="Art & Culture",
        era="1300 – 1600",
        lat=43.7696,
        lng=11.2558,
        summary_short="Cradle of humanism, perspective painting, and Medici patronage."
    ),
    SeedTopic(
        id="industrial-revolution",
        title="Industrial Revolution",
        category="Technology",
        era="1760 – 1840",
        lat=53.4808,
        lng=-2.2426,
        summary_short="Mechanization, steam locomotives, and urban factory transformation."
    ),
    SeedTopic(
        id="ancient-egypt",
        title="Ancient Egypt",
        category="History",
        era="3100 BCE – 30 BCE",
        lat=29.9792,
        lng=31.1342,
        summary_short="Pyramids of Giza, hieroglyphics, and Pharaohs along the Nile."
    ),
    SeedTopic(
        id="space-exploration",
        title="Space Exploration",
        category="Science",
        era="1957 – Present",
        lat=28.5721,
        lng=-80.6480,
        summary_short="Sputnik, Apollo Moon landings, Mars rovers, and cosmic telescopes."
    )
]


@app.get("/api/seed-topics", response_model=List[SeedTopic])
def list_seed_topics():
    """Returns the list of initial seed topics with geographical coordinates for the 3D Globe."""
    return SEED_TOPICS


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
