import { soundEngine } from "./audio.js";
import { SpatialGraphController } from "./graph3d.js";
import { spawnWikiWindow, makeDraggable, bringToFront } from "./wiki_window.js";
import { mindmaze, openMindMazeModal, closeMindMazeModal } from "./mindmaze.js";

/**
 * Encarta 2.0 SPA Main Application Coordinator (Dynamic Knowledge Expansion Edition)
 */

let spatialGraph = null;
let currentArticleData = null;
let isSpeaking = false;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    const loaderModal = document.getElementById("node-loader-modal");
    if (loaderModal) makeDraggable(loaderModal);
});

async function initApp() {
    // 1. Initialize 3D Spatial Knowledge Graph Globe
    spatialGraph = new SpatialGraphController("globe-container", (selectedTopicTitle) => {
        loadArticle(selectedTopicTitle);
    });
    await spatialGraph.init();

    // 2. Setup Header Controls, Hotkeys & UI Engines
    setupHeaderControls();
    setupStarfield();
    setupReaderPanelControls();
    setupWindowControlButtons();
    setupKeyboardShortcuts();
    setupMobileBottomSheetGestures();

    // 3. Initial Seed Article Load ("Microsoft Encarta")
    loadArticle("Microsoft Encarta");
    setTimeout(() => {
        if (spatialGraph) {
            spatialGraph.focusTopicByTitle("Microsoft Encarta");
        }
    }, 600);

    // 4. Ensure WebAudio unlocks on first user interaction gesture (pointerdown, click, touch, keydown)
    const unlockAudio = () => {
        soundEngine.init();
        soundEngine.playStartupChime();
        window.removeEventListener("pointerdown", unlockAudio);
        window.removeEventListener("keydown", unlockAudio);
        window.removeEventListener("click", unlockAudio);
    };
    window.addEventListener("pointerdown", unlockAudio, { once: true });
    window.addEventListener("keydown", unlockAudio, { once: true });
    window.addEventListener("click", unlockAudio, { once: true });
}

/**
 * Fetch dynamic article payload from Python FastAPI backend `/api/article?topic=...`
 * Automatically syncs & persists new nodes into SQLite and 3D globe network.
 */
async function loadArticle(topicTitle, wikiQuery = "") {
    soundEngine.playClick();
    const panel = document.getElementById("reader-panel");
    const titleEl = document.getElementById("reader-title");
    const eraEl = document.getElementById("reader-era");
    const summaryEl = document.getElementById("reader-summary");
    const timelineEl = document.getElementById("reader-timeline");
    const triviaEl = document.getElementById("reader-trivia");
    const relatedEl = document.getElementById("reader-related");
    
    const loaderModal = document.getElementById("node-loader-modal");
    const loaderTitle = document.getElementById("loader-topic-title");
    
    const isExistingNode = spatialGraph && spatialGraph.nodesData && spatialGraph.nodesData.some(n => 
        n.title.toLowerCase() === topicTitle.toLowerCase() || 
        n.id === topicTitle.toLowerCase().trim().replace(/\s+/g, "-")
    );

    if (!isExistingNode && loaderModal && loaderTitle) {
        loaderTitle.textContent = `Generating Node: "${topicTitle}"...`;
        loaderModal.classList.remove("hidden");
        bringToFront(loaderModal);
    }

    if (panel) panel.classList.add("open");

    if (titleEl) titleEl.textContent = topicTitle;
    if (eraEl) eraEl.textContent = "Loading Archival Records...";
    if (summaryEl) summaryEl.textContent = "Synthesizing node structure...";

    try {
        let url = `/api/article?topic=${encodeURIComponent(topicTitle)}`;
        if (wikiQuery) {
            url += `&wiki=${encodeURIComponent(wikiQuery)}`;
        }
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        currentArticleData = data;

        // Open Reader Panel and hide mobile FAB if open
        if (panel) {
            panel.classList.add("open");
            const mobileFab = document.getElementById("mobile-open-brief-btn");
            if (mobileFab) mobileFab.classList.add("hidden");
        }

        // CRT Flicker effect
        if (panel) {
            panel.classList.remove("crt-flicker-active");
            void panel.offsetWidth; // Trigger DOM reflow to restart animation
            panel.classList.add("crt-flicker-active");
        }

        // Render Article Details
        if (titleEl) titleEl.textContent = data.title;
        if (eraEl) eraEl.textContent = `ERA: ${data.era}`;
        
        // Typewriter Effect for Summary
        if (summaryEl) {
            summaryEl.textContent = "";
            let i = 0;
            const text = data.summary;
            if (window.typewriterInterval) clearInterval(window.typewriterInterval);
            window.typewriterInterval = setInterval(() => {
                summaryEl.textContent += text.charAt(i);
                i++;
                if (i >= text.length) clearInterval(window.typewriterInterval);
            }, 10);
        }
        
        // Dynamically update the browser tab title
        document.title = `Encarta 2.0 - ${data.title}`;

        // Render Historical Milestones Timeline along Connected Line Axis
        if (timelineEl) {
            timelineEl.innerHTML = "";
            data.milestones.forEach((m, index) => {
                const nodeItem = document.createElement("div");
                nodeItem.className = "timeline-node-item";
                nodeItem.style.animationDelay = `${index * 0.15}s`;
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
        if (timelineEl) timelineEl.innerHTML = "";
        if (triviaEl) triviaEl.textContent = "";
        if (relatedEl) relatedEl.innerHTML = "";
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
    const addNodeBtn = document.getElementById("add-node-btn");
    const soundBtn = document.getElementById("sound-toggle-btn");
    const mindmazeBtn = document.getElementById("open-mindmaze-btn");
    const volumeSlider = document.getElementById("volume-slider");
    const rotationSlider = document.getElementById("rotation-slider");

    const autocompleteList = document.getElementById("search-autocomplete");

    if (searchBtn && searchInput) {
        const executeSearch = (queryOverride) => {
            const query = queryOverride || searchInput.value.trim();
            if (query) {
                if (autocompleteList) autocompleteList.classList.add("hidden");
                loadArticle(query);
            }
        };
        searchBtn.onclick = () => executeSearch();
        
        searchInput.onkeydown = (e) => {
            if (e.key === "Enter") executeSearch();
        };

        if (autocompleteList) {
            searchInput.oninput = (e) => {
                const val = e.target.value.toLowerCase().trim();
                autocompleteList.innerHTML = "";
                
                if (!val) {
                    autocompleteList.classList.add("hidden");
                    return;
                }

                // Filter local nodes data
                if (!spatialGraph || !spatialGraph.nodesData) return;
                
                const matches = spatialGraph.nodesData.filter(n => n.title.toLowerCase().includes(val));
                
                if (matches.length > 0) {
                    matches.slice(0, 5).forEach(m => {
                        const li = document.createElement("li");
                        li.textContent = m.title;
                        li.onmousedown = () => { // mousedown fires before blur
                            searchInput.value = m.title;
                            executeSearch(m.title);
                        };
                        autocompleteList.appendChild(li);
                    });
                    autocompleteList.classList.remove("hidden");
                } else {
                    autocompleteList.classList.add("hidden");
                }
            };

            searchInput.onblur = () => {
                // Delay hiding slightly so mousedown on list item can fire
                setTimeout(() => autocompleteList.classList.add("hidden"), 150);
            };
            
            searchInput.onfocus = () => {
                if (searchInput.value.trim() && autocompleteList.children.length > 0) {
                    autocompleteList.classList.remove("hidden");
                }
            };
        }
    }

    if (addNodeBtn) {
        const dialogOverlay = document.getElementById("add-node-dialog-overlay");
        const closeBtn = document.getElementById("add-node-close-btn");
        const cancelBtn = document.getElementById("add-node-cancel-btn");
        const submitBtn = document.getElementById("add-node-submit-btn");
        const inputField = document.getElementById("add-node-input");

        const wikiField = document.getElementById("add-node-wiki-input");

        const closeDialog = () => {
            if (dialogOverlay) dialogOverlay.classList.add("hidden");
            if (inputField) inputField.value = "";
            if (wikiField) wikiField.value = "";
        };

        const submitNode = () => {
            if (inputField && inputField.value.trim()) {
                const newTopic = inputField.value.trim();
                const wikiQuery = wikiField ? wikiField.value.trim() : "";
                closeDialog();
                loadArticle(newTopic, wikiQuery);
            }
        };

        if (dialogOverlay) {
            makeDraggable(dialogOverlay);
            
            addNodeBtn.onclick = () => {
                dialogOverlay.classList.remove("hidden");
                bringToFront(dialogOverlay);
                if (inputField) inputField.focus();
            };

            closeBtn.onclick = closeDialog;
            cancelBtn.onclick = closeDialog;
            submitBtn.onclick = submitNode;

            if (inputField) {
                inputField.onkeydown = (e) => {
                    if (e.key === "Enter") submitNode();
                    if (e.key === "Escape") closeDialog();
                };
            }
        }
    }

    // Surprise Me Random Discovery Button
    const randomBtn = document.getElementById("random-dive-btn");
    if (randomBtn) {
        randomBtn.onclick = () => {
            triggerSurpriseMe();
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
        soundBtn.textContent = soundEngine.isMuted ? "🔇 Muted" : "🔊 Sound ON";
        soundBtn.onclick = () => {
            const muted = soundEngine.toggleMute();
            soundBtn.textContent = muted ? "🔇 Muted" : "🔊 Sound ON";
            if (!muted) {
                soundEngine.playClick();
            }
        };
    }

    // MindMaze Launcher
    if (mindmazeBtn) {
        mindmazeBtn.onclick = () => {
            openMindMazeModal();
        };
    }
}

/**
 * Trigger Random Dive / Surprise Me
 */
function triggerSurpriseMe() {
    if (!spatialGraph || !spatialGraph.nodesData || spatialGraph.nodesData.length === 0) return;
    soundEngine.playNodeBirthChime();

    const currentTitle = currentArticleData ? currentArticleData.title.toLowerCase() : "";
    const available = spatialGraph.nodesData.filter(n => n.title.toLowerCase() !== currentTitle);
    const pool = available.length > 0 ? available : spatialGraph.nodesData;
    const randomNode = pool[Math.floor(Math.random() * pool.length)];

    if (randomNode) {
        spatialGraph.focusTopicByTitle(randomNode.title);
        loadArticle(randomNode.title);
    }
}

/**
 * Power-User Global Keyboard Shortcuts
 */
function setupKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
        // Ignore hotkeys when typing in search or input fields
        const tag = e.target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea") return;

        if (e.code === "Space") {
            e.preventDefault();
            if (spatialGraph) {
                spatialGraph.autoRotate = !spatialGraph.autoRotate;
                soundEngine.playClick();
            }
        } else if (e.key === "r" || e.key === "R") {
            triggerSurpriseMe();
        } else if (e.key === "m" || e.key === "M") {
            openMindMazeModal();
        } else if (e.key === "Escape") {
            document.getElementById("reader-panel")?.classList.remove("open");
            closeMindMazeModal();
            document.getElementById("add-node-dialog-overlay")?.classList.add("hidden");
        } else if (["1", "2", "3", "4", "5"].includes(e.key)) {
            const idx = parseInt(e.key) - 1;
            const pills = document.querySelectorAll(".filter-pill");
            if (pills[idx]) {
                pills[idx].click();
            }
        }
    });
}

/**
 * Setup Dynamic Starfield Background
 */
function setupStarfield() {
    const canvas = document.getElementById("starfield");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width, height;
    let stars = [];

    const resize = () => {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
        initStars();
    };

    const initStars = () => {
        stars = [];
        const numStars = Math.floor((width * height) / 3000); // adjust density
        for (let i = 0; i < numStars; i++) {
            stars.push({
                x: Math.random() * width,
                y: Math.random() * height,
                z: Math.random() * 2,
                o: Math.random() * 0.8 + 0.2
            });
        }
    };

    const animate = () => {
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "white";
        for (let i = 0; i < stars.length; i++) {
            let s = stars[i];
            ctx.globalAlpha = s.o;
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.z, 0, Math.PI * 2);
            ctx.fill();

            // Move star
            s.x -= (s.z * 0.2); // Parallax speed based on depth
            if (s.x < 0) {
                s.x = width;
                s.y = Math.random() * height;
            }
        }
        requestAnimationFrame(animate);
    };

    window.addEventListener("resize", resize);
    resize();
    animate();
}

/**
 * Setup Reader Panel Action Buttons & Audio Synthesizer Player Bar
 */
function setupReaderPanelControls() {
    const closePanelBtn = document.getElementById("close-panel-btn");
    const speakBtn = document.getElementById("speak-summary-btn");
    const speakBtnText = document.getElementById("speak-btn-text");
    const speechIndicator = document.getElementById("speech-indicator");
    const wikiBtn = document.getElementById("open-wiki-btn");
    const mindmazeReaderBtn = document.getElementById("reader-mindmaze-btn");
    const mobileBriefFab = document.getElementById("mobile-open-brief-btn");

    if (closePanelBtn) {
        closePanelBtn.onclick = () => {
            soundEngine.playClick();
            stopSpeech();
            document.getElementById("reader-panel").classList.remove("open");
            if (window.innerWidth <= 768 && mobileBriefFab) {
                mobileBriefFab.classList.remove("hidden");
            }
        };
    }

    if (mobileBriefFab) {
        mobileBriefFab.onclick = () => {
            soundEngine.playWindowOpen();
            const panel = document.getElementById("reader-panel");
            if (panel) panel.classList.add("open");
            mobileBriefFab.classList.add("hidden");
        };
    }

    if (speakBtn) {
        speakBtn.onclick = () => {
            if (!window.speechSynthesis) return;

            if (isSpeaking) {
                stopSpeech();
            } else {
                startSpeech();
            }
        };
    }

    function startSpeech() {
        if (!currentArticleData || !currentArticleData.summary) return;
        window.speechSynthesis.cancel();
        soundEngine.playNodeBirthChime();

        const utterance = new SpeechSynthesisUtterance(currentArticleData.summary);
        utterance.rate = 0.95;
        utterance.pitch = 1.05;

        utterance.onstart = () => {
            isSpeaking = true;
            if (speakBtnText) speakBtnText.textContent = "Stop";
            if (speechIndicator) speechIndicator.classList.remove("hidden");
        };

        utterance.onend = () => {
            stopSpeech();
        };

        utterance.onerror = () => {
            stopSpeech();
        };

        window.speechSynthesis.speak(utterance);
    }

    function stopSpeech() {
        window.speechSynthesis?.cancel();
        isSpeaking = false;
        if (speakBtnText) speakBtnText.textContent = "Read Aloud";
        if (speechIndicator) speechIndicator.classList.add("hidden");
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
 * Real-Time 60 FPS Drag Handlers for Mobile Bottom Sheet
 */
function setupMobileBottomSheetGestures() {
    const handle = document.getElementById("bottom-sheet-handle");
    const panelHeader = document.querySelector("#reader-panel .panel-header");
    const panel = document.getElementById("reader-panel");
    if (!panel) return;

    let startY = 0;
    let currentY = 0;
    let isDragging = false;

    const onDragStart = (clientY) => {
        if (window.innerWidth > 768) return;
        startY = clientY;
        currentY = clientY;
        isDragging = true;
        panel.classList.add("dragging");
    };

    const onDragMove = (clientY) => {
        if (!isDragging) return;
        currentY = clientY;
        const delta = Math.max(0, currentY - startY);
        // Direct CSS transform with real-time hardware acceleration
        panel.style.transform = `translateY(${delta}px)`;
    };

    const onDragEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        panel.classList.remove("dragging");
        const delta = currentY - startY;
        panel.style.transform = "";

        if (delta > 70) {
            panel.classList.remove("open");
            soundEngine.playWindowClose();
            const mobileBriefFab = document.getElementById("mobile-open-brief-btn");
            if (mobileBriefFab) mobileBriefFab.classList.remove("hidden");
        } else {
            panel.classList.add("open");
        }
    };

    const dragHandles = [handle, panelHeader].filter(Boolean);
    dragHandles.forEach(target => {
        target.addEventListener("touchstart", (e) => {
            onDragStart(e.touches[0].clientY);
        }, { passive: true });

        target.addEventListener("mousedown", (e) => {
            onDragStart(e.clientY);
        });
    });

    window.addEventListener("touchmove", (e) => {
        if (isDragging) {
            onDragMove(e.touches[0].clientY);
        }
    }, { passive: true });

    window.addEventListener("mousemove", (e) => {
        if (isDragging) {
            onDragMove(e.clientY);
        }
    });

    window.addEventListener("touchend", onDragEnd);
    window.addEventListener("mouseup", onDragEnd);
}

/**
 * Setup Retro Window Control Buttons
 */
function setupWindowControlButtons() {
    document.getElementById("mindmaze-close-btn")?.addEventListener("click", closeMindMazeModal);
}
