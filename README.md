# Encarta 2.0

An interactive 3D knowledge graph and retro desktop interface inspired by Microsoft Encarta '95. Explore interconnected topics across history, science, tech, and art, read curated briefs, or play a retro trivia dungeon mini-game.

## Features

- **3D Knowledge Graph**: Interactive 3D spatial network (Three.js / 3d-force-graph) connecting topics across eras and disciplines with dynamic camera focus.
- **Dynamic Topic Generation**: Add new knowledge nodes on demand powered by Google Gemini / Gemma models.
- **Retro Desktop UI**: Windows 95 styled interface with draggable windows, custom WebAudio synthesizer sound effects, and embedded Wikipedia exploration.
- **MindMaze Mini-game**: 2D tile-based dungeon game where answering historical and scientific trivia unlocks doors to reach the exit.
- **Audio Narration**: Integrated text-to-speech reader with animated equalizer for topic summaries.
- **Mobile Friendly**: Responsive layout with draggable bottom sheets and touch gestures.

## Tech Stack

- **Frontend**: Vanilla JavaScript (ES Modules), HTML5 Canvas, Three.js, WebAudio API, CSS
- **Backend**: Python 3.12, FastAPI, SQLite, `google-genai`
- **Deployment**: Vercel (Static frontend + Serverless Python API)

## Getting Started

### Prerequisites

- Python 3.10+
- Google Gemini API Key (optional for exploring seeded nodes, required for generating new nodes)

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MemeGamerz/Encarta-2.0.git
   cd "Encarta 2.0"
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Start the application**:
   ```bash
   python3 -m backend.main
   ```

6. Open `http://localhost:8000` in your browser.
