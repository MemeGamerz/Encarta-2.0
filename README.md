# Encarta 2.0 (NewGen Retro Edition)

Encarta 2.0 is a full-stack web application that rebuilds Microsoft Encarta '95 for modern browsers. It pairs 90s cyber-nostalgia with WebGL spatial visualization, generative AI context, multi-window desktop management, and native WebAudio synthesis.

## Key Features

* **3D Spatial Knowledge Graph:** Interactive WebGL hub built with Three.js and `3d-force-graph`. Displays historical and scientific topics using category-specific 3D icons, glowing active halos, and flowing particle connections.
* **Generative AI Engine:** Backend powered by FastAPI and Google's Gemini API. Generates structured article summaries, horizontal timelines, and interactive trivia. Features an automatic SQLite local cache and a `MOCK_MODE=true` environment flag to run offline without API quota consumption.
* **Multi-Window Retro Desktop:** Glassmorphic UI with Win95 double-bevel borders. Intercepts Wikipedia REST API links to spawn nested, draggable, stackable, and minimizable floating windows inside the application.
* **MindMaze 2D Dungeon:** HTML5 Canvas RPG featuring smooth tile-based sprite movement, particle victory effects, and door trivia prompts pulled dynamically from article context.
* **WebAudio Sound Synthesizer:** Pure code-based synthesizer for UI clicks, window controls, door fanfares, and retro chime audio without external file dependencies.
* **Multi-Model Fallback Hierarchy:** Automatic backend failover logic (Gemini Flash → Pro → Mock JSON) to guarantee 100% uptime.

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Backend** | Python 3.11, FastAPI, `google-genai` SDK, SQLite3, Pydantic |
| **Frontend** | Vanilla JS (ES6 Modules), HTML5 Canvas, WebAudio API, Tailwind CSS, Retro CSS |
| **Graphics & Data** | Three.js, `3d-force-graph`, Wikipedia REST API |

## Quick Start

```
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --reload --port 8000

```

Open `http://localhost:8000` in your browser.
