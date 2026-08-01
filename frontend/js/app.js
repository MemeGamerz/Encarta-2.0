import { soundEngine } from "./audio.js";
import { SpatialGraphController } from "./graph3d.js";
import { spawnWikiWindow } from "./wiki_window.js";
import { mindmaze, openMindMazeModal, closeMindMazeModal } from "./mindmaze.js";

/**
 * Encarta 2.0 SPA Main Application Coordinator (Dynamic Knowledge Expansion Edition)
 */

let spatialGraph = null;
let currentArticleData = null;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    // 1. Initialize 3D Spatial Knowledge Graph Globe
    spatialGraph = new SpatialGraphController("globe-container", (selectedTopicTitle) => {
        loadArticle(selectedTopicTitle);
    });
    await spatialGraph.init();

    // 2. Setup Header Controls & Sliders
    setupHeaderControls();
    setupReaderPanelControls();
    setupWindowControlButtons();

    // 3. Initial Seed Article Load ("Microsoft Encarta")
    loadArticle("Microsoft Encarta");
    setTimeout(() => {
        if (spatialGraph) {
            spatialGraph.focusTopicByTitle("Microsoft Encarta");
        }
    }, 600);

    // 4. Play startup chime on first user click
    const handleFirstClick = () => {
        soundEngine.playStartupChime();
        window.removeEventListener("click", handleFirstClick);
    };
    window.addEventListener("click", handleFirstClick);
}

/**
 * Fetch dynamic article payload from Python FastAPI backend `/api/article?topic=...`
 * Automatically syncs & persists new nodes into SQLite and 3D globe network.
 */
async function loadArticle(topicTitle) {
    soundEngine.playClick();
    const panel = document.getElementById("reader-panel");
    const titleEl = document.getElementById("reader-title");
    const eraEl = document.getElementById("reader-era");
    const summaryEl = document.getElementById("reader-summary");
    const timelineEl = document.getElementById("reader-timeline");
    const triviaEl = document.getElementById("reader-trivia");
    const relatedEl = document.getElementById("reader-related");
    
    const isExistingNode = spatialGraph && spatialGraph.nodesData && spatialGraph.nodesData.some(n => 
        n.title.toLowerCase() === topicTitle.toLowerCase() || 
        n.id === topicTitle.toLowerCase().trim().replace(/\s+/g, "-")
    );

    if (!isExistingNode && loaderModal && loaderTitle) {
        loaderTitle.textContent = `Generating Node: "${topicTitle}"...`;
        loaderModal.classList.remove("hidden");
    }

    if (panel) panel.classList.add("open");

    if (titleEl) titleEl.textContent = topicTitle;
    if (eraEl) eraEl.textContent = "Loading Archival Records...";
    if (summaryEl) summaryEl.textContent = "Generating node structure via Gemma 4 31B (High Thinking)...";

    try {
        const res = await fetch(`/api/article?topic=${encodeURIComponent(topicTitle)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        currentArticleData = data;


        // Render Article Details
        if (titleEl) titleEl.textContent = data.title;
        if (eraEl) eraEl.textContent = `ERA: ${data.era}`;
        if (summaryEl) summaryEl.textContent = data.summary;

        // Render Historical Milestones Timeline along Connected Line Axis
        if (timelineEl) {
            timelineEl.innerHTML = "";
            data.milestones.forEach(m => {
                const nodeItem = document.createElement("div");
                nodeItem.className = "timeline-node-item";
                nodeItem.innerHTML = `
                    <div class="timeline-dot"></div>
                    <div class="timeline-card win95-inset">
                        <div class="timeline-year">${m.year}</div>
                        <div class="timeline-event">${m.event}</div>
                    </div>
                `;
                timelineEl.appendChild(nodeItem);
            });
        }

        // Render Trivia Card
        if (triviaEl) {
            triviaEl.textContent = data.trivia;
        }

        // Render Related Topic Hyperlinks
        if (relatedEl) {
            relatedEl.innerHTML = "";
            data.related_topics.forEach(rel => {
                const pill = document.createElement("button");
                pill.className = "related-pill";
                pill.textContent = `📍 ${rel}`;
                pill.onclick = () => {
                    spatialGraph.focusTopicByTitle(rel);
                };
                relatedEl.appendChild(pill);
            });
        }

        // Update MindMaze trivia questions pool with this topic's questions
        mindmaze.setQuestions(data.mindmaze_questions, data.title);

        // Dynamically add/update node on 3D Globe network and calculate interconnect links!
        if (spatialGraph) {
            spatialGraph.addOrUpdateNode(data);
        }

    } catch (err) {
        console.error("[Encarta 2.0 API Error]", err);
        if (summaryEl) summaryEl.textContent = "Unable to fetch article data. Please ensure backend server is running.";
    } finally {
        if (loaderModal) {
            loaderModal.classList.add("hidden");
        }
    }
}

/**
 * Setup Top Bar Search, Sliders & Filters
 */
function setupHeaderControls() {
    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const soundBtn = document.getElementById("sound-toggle-btn");
    const mindmazeBtn = document.getElementById("open-mindmaze-btn");
    const volumeSlider = document.getElementById("volume-slider");
    const rotationSlider = document.getElementById("rotation-slider");

    if (searchBtn && searchInput) {
        const executeSearch = () => {
            const query = searchInput.value.trim();
            if (query) {
                loadArticle(query);
            }
        };
        searchBtn.onclick = executeSearch;
        searchInput.onkeydown = (e) => {
            if (e.key === "Enter") executeSearch();
        };
    }

    // Category Filter Pills
    document.querySelectorAll(".filter-pill").forEach(pill => {
        pill.onclick = () => {
            soundEngine.playClick();
            document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            const cat = pill.getAttribute("data-category");
            spatialGraph.filterByCategory(cat);
        };
    });

    // Volume Slider
    if (volumeSlider) {
        volumeSlider.oninput = (e) => {
            soundEngine.setVolume(e.target.value);
        };
    }

    // 3D Globe Rotation Speed Slider
    if (rotationSlider) {
        rotationSlider.oninput = (e) => {
            if (spatialGraph) {
                spatialGraph.setRotationSpeed(e.target.value);
            }
        };
    }

    // Sound Mute Toggle
    if (soundBtn) {
        soundBtn.onclick = () => {
            const muted = soundEngine.toggleMute();
            soundBtn.textContent = muted ? "🔇 Muted" : "🔊 Sound ON";
        };
    }

    // MindMaze Launcher
    if (mindmazeBtn) {
        mindmazeBtn.onclick = () => {
            openMindMazeModal();
        };
    }

    // Reset Database Button
    const resetBtn = document.getElementById("reset-db-btn");
    if (resetBtn) {
        resetBtn.onclick = async () => {
            if (!confirm("Are you sure you want to reset the Encarta database to initial seed nodes?")) return;
            soundEngine.playClick();
            try {
                const res = await fetch("/api/nodes/reset", { method: "POST" });
                if (res.ok) {
                    const data = await res.json();
                    if (spatialGraph && data.nodes) {
                        spatialGraph.setNodes(data.nodes);
                    }
                    loadArticle("Microsoft Encarta");
                }
            } catch (err) {
                console.error("Failed to reset database:", err);
            }
        };
    }
}

/**
 * Setup Reader Panel Action Buttons
 */
function setupReaderPanelControls() {
    const closePanelBtn = document.getElementById("close-panel-btn");
    const wikiBtn = document.getElementById("open-wiki-btn");
    const mindmazeReaderBtn = document.getElementById("reader-mindmaze-btn");

    if (closePanelBtn) {
        closePanelBtn.onclick = () => {
            soundEngine.playClick();
            document.getElementById("reader-panel").classList.remove("open");
        };
    }

    if (wikiBtn) {
        wikiBtn.onclick = () => {
            const query = currentArticleData ? (currentArticleData.wiki_query || currentArticleData.title) : "Microsoft Encarta";
            spawnWikiWindow(query);
        };
    }

    if (mindmazeReaderBtn) {
        mindmazeReaderBtn.onclick = () => {
            openMindMazeModal();
        };
    }
}

/**
 * Setup Retro Window Control Buttons
 */
function setupWindowControlButtons() {
    document.getElementById("mindmaze-close-btn")?.addEventListener("click", closeMindMazeModal);
}
