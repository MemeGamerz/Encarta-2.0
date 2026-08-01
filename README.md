# Encarta 2.0 (NewGen Retro Edition) 🏛️⚡

> **Hackathon Edition** — Reimagining 1995's legendary **Microsoft Encarta** as an endlessly expanding 3D WebGL knowledge universe powered by **Gemma 4 31B**, **Gemini 2.5 Flash**, and retro Win95 cyber-aesthetics.

---

## 🌟 Key Features

* 🌐 **3D Spatial Knowledge Universe (`Three.js` + `3d-force-graph`)**:
  - Category-specific 3D sprite badges (🏛️ History, ⚛️ Science, 💻 Tech, 🎨 Art, 🧭 Trade).
  - Unclipped radial soft glow halos for active focused nodes with lerped camera fly-to transitions.
  - **Color-Coded Animated Light-Beam Wires**: Flowing laser-beam pulses traveling along category-coded wires.
  - **BFS Single Unified Cluster Engine**: Uses Breadth-First Search (BFS) graph traversal to guarantee 100% full graph connectivity with zero isolated floating islands.

* 🧠 **Dual Generative AI Pipeline**:
  - **Gemma 4 31B (High Thinking)**: Structures user search topics into node metadata, coordinates, categories, era stamps, historical milestones, and trivia facts.
  - **Gemini 2.5 Flash**: Generates interactive multiple-choice and true/false trivia questions for the MindMaze dungeon game.

* 💾 **Persistent SQLite Knowledge Database**:
  - Every topic searched by users is saved into SQLite (`encarta_cache.db`), automatically expanding the permanent 3D knowledge network over time.
  - Includes a real-time `🔄 Reset DB` button to clean and re-seed the initial canonical 12 knowledge nodes.

* 🖥️ **Multi-Window Retro Desktop Engine**:
  - Glassmorphic Win95 double-bevel floating windows with stack management, z-index layering, and taskbar integration.
  - **Wikipedia Hyperlink Interceptor**: Intercepts internal Wikipedia REST API links to spawn nested retro windows on click!

* 🏰 **MindMaze 2D Trivia Dungeon**:
  - HTML5 Canvas RPG with lerped knight movement and sequential bottleneck map design (requiring 5 unlocked trivia doors to reach the victory trophy chamber).

* 🔊 **WebAudio Synthesizer Engine**:
  - Zero-asset WebAudio synthesizer generating retro UI clicks, startup chime chord sweeps, node birth chimes, door fanfares, and victory bursts.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **AI Models** | Gemma 4 31B (High Thinking), Gemini 2.5 Flash |
| **Backend** | Python 3.12, FastAPI, `google-genai` SDK, SQLite3, Pydantic |
| **Frontend** | Vanilla JS (ES6 Modules), HTML5 Canvas 2D, WebAudio API, Retro CSS |
| **3D & Data** | Three.js, `3d-force-graph`, Wikipedia REST API |
| **Deployment** | Vercel (Python Serverless Functions + Static WebGL) |

---

## ⚡ Quick Start

```bash
# 1. Clone repo & create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch FastAPI server
python3 -m backend.main
```

Open **`http://localhost:8000`** in your browser!

---
