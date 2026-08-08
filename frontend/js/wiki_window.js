import { soundEngine } from "./audio.js";

/**
 * Encarta 2.0 Nested Multi-Window Desktop Engine & Hyperlink Interceptor
 */

let windowCount = 0;
let highestZIndex = 800;
let activeDragWindow = null;
let dragOffsetX = 0;
let dragOffsetY = 0;

// Global mouse listeners for dragging retro desktop windows
window.addEventListener("mousemove", (e) => {
    if (!activeDragWindow) return;

    let left = e.clientX - dragOffsetX;
    let top = e.clientY - dragOffsetY;

    left = Math.max(0, Math.min(left, window.innerWidth - activeDragWindow.offsetWidth));
    top = Math.max(50, Math.min(top, window.innerHeight - 80));

    activeDragWindow.style.left = `${left}px`;
    activeDragWindow.style.top = `${top}px`;
});

window.addEventListener("mouseup", () => {
    activeDragWindow = null;
});

/**
 * Bring clicked window to top z-index stack
 */
export function bringToFront(windowElement) {
    highestZIndex += 1;
    windowElement.style.zIndex = highestZIndex.toString();

    document.querySelectorAll(".retro-window").forEach(win => {
        win.classList.remove("active-window");
    });
    windowElement.classList.add("active-window");
}

/**
 * Make window element draggable by its titlebar
 */
export function makeDraggable(windowElement) {
    const titlebar = windowElement.querySelector(".retro-window-titlebar");
    if (!titlebar) return;

    windowElement.addEventListener("mousedown", () => {
        bringToFront(windowElement);
    });

    titlebar.addEventListener("mousedown", (e) => {
        if (e.target.classList.contains("win-btn")) return;
        
        // Disable dragging on mobile where Bottom Sheets are used
        if (window.innerWidth <= 768) return;

        activeDragWindow = windowElement;
        const rect = windowElement.getBoundingClientRect();
        
        if (windowElement.classList.contains("modal-center")) {
            windowElement.classList.remove("modal-center");
            windowElement.style.left = `${rect.left}px`;
            windowElement.style.top = `${rect.top}px`;
        }
        
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
        bringToFront(windowElement);
    });
}

/**
 * Spawn a new independent, stacked Retro Wikipedia Window for a topic.
 */
export async function spawnWikiWindow(wikiQuery) {
    soundEngine.playWindowOpen();
    windowCount++;
    const winId = `wiki-win-${windowCount}`;
    const cleanQuery = wikiQuery.trim().replace(/\s+/g, "_");
    const displayTitle = cleanQuery.replace(/_/g, " ");

    // Calculate staggered offset for stacked multi-window layout
    const offsetIndex = (windowCount - 1) % 8;
    const topPos = 70 + offsetIndex * 28;
    const leftPos = Math.max(20, Math.min(window.innerWidth - 780, 160 + offsetIndex * 28));

    // Create Retro Window DOM Element
    const win = document.createElement("div");
    win.id = winId;
    win.className = "retro-window win95-outset glass-panel window-animate-open";
    win.style.width = "740px";
    win.style.height = "540px";
    win.style.top = `${topPos}px`;
    win.style.left = `${leftPos}px`;

    win.innerHTML = `
        <div class="retro-window-titlebar">
            <div class="retro-window-title">
                <span>📚</span>
                <span>Wikipedia Archives: ${displayTitle}</span>
            </div>
            <div class="window-controls">
                <button class="win-btn min-btn">_</button>
                <button class="win-btn max-btn">o</button>
                <button class="win-btn close-btn">X</button>
            </div>
        </div>
        <div class="wiki-modal-content-box win95-inset">
            <div class="flex flex-col items-center justify-center p-12 text-amber-400 font-mono">
                <div class="animate-spin text-3xl mb-4">⌛</div>
                <div>Consulting Encarta 2.0 Archival Network...</div>
                <div class="text-xs text-slate-400 mt-2">Fetching: https://en.wikipedia.org/api/rest_v1/page/html/${cleanQuery}</div>
            </div>
        </div>
    `;

    document.body.appendChild(win);
    makeDraggable(win);
    bringToFront(win);

    // Setup Window Controls
    const closeBtn = win.querySelector(".close-btn");
    const minBtn = win.querySelector(".min-btn");
    const maxBtn = win.querySelector(".max-btn");
    const contentBox = win.querySelector(".wiki-modal-content-box");

    closeBtn.onclick = () => closeWikiWindow(winId);
    minBtn.onclick = () => minimizeWikiWindow(winId);
    maxBtn.onclick = () => maximizeWikiWindow(winId);

    // Add Taskbar Item
    addTaskbarItem(winId, `Wiki: ${displayTitle}`);

    // Fetch Wikipedia REST API Content
    try {
        const response = await fetch(`https://en.wikipedia.org/api/rest_v1/page/html/${encodeURIComponent(cleanQuery)}`);
        
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);

        const htmlText = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlText, "text/html");

        // Comprehensive removal of Wikipedia clutter, edit buttons, and meta navigation
        doc.querySelectorAll(
            "script, style, link, nav, .mw-editsection, .mw-editsection-like, " +
            ".reference, .reflist, sup.reference, .noprint, .mw-jump-link, " +
            ".ambox, .navbox, .catlinks, .vector-menu, .mw-indicators, " +
            "a[href*='action=edit'], a[href*='veaction=edit'], a[title*='Edit this'], a[title*='Edit section']"
        ).forEach(el => el.remove());

        // 1. Sanitize raw HTML and inject into contentBox FIRST
        const rawHtml = doc.body.innerHTML;
        const cleanHtml = window.DOMPurify ? window.DOMPurify.sanitize(rawHtml, { ADD_ATTR: ['target'] }) : rawHtml;
        contentBox.innerHTML = cleanHtml;

        // 2. Attach click event interceptors to all <a> tags inside contentBox (AFTER DOM injection!)
        contentBox.querySelectorAll("a").forEach(a => {
            const href = a.getAttribute("href");
            if (!href || href.includes("action=edit")) {
                a.remove();
                return;
            }

            let topic = null;
            if (href.startsWith("./")) {
                topic = href.substring(2);
            } else if (href.startsWith("/wiki/")) {
                topic = href.substring(6);
            } else if (href.includes("wikipedia.org/wiki/")) {
                topic = href.split("wikipedia.org/wiki/")[1];
            }

            if (topic) {
                const cleanTopic = decodeURIComponent(topic.split("#")[0]).replace(/_/g, " ").trim();
                const isMetaOrSpecial = cleanTopic.includes(":") || 
                                       cleanTopic.startsWith("File") || 
                                       cleanTopic.startsWith("Special") || 
                                       cleanTopic.startsWith("Wikipedia") || 
                                       cleanTopic.startsWith("Help") || 
                                       cleanTopic.startsWith("Template") || 
                                       cleanTopic.startsWith("Category") || 
                                       cleanTopic.startsWith("Portal") || 
                                       cleanTopic.startsWith("Talk") ||
                                       href.includes("action=edit");

                if (cleanTopic && !isMetaOrSpecial) {
                    a.setAttribute("href", "#");
                    a.style.cursor = "pointer";
                    a.title = `Open Encarta 2.0 Archival Window for ${cleanTopic}`;
                    a.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        spawnWikiWindow(cleanTopic); // Spawns a NEW stacked retro window for clicked link!
                    });
                } else {
                    a.setAttribute("target", "_blank");
                }
            } else {
                a.setAttribute("target", "_blank");
            }
        });

    } catch (err) {
        console.warn("[Wikipedia API Fetch Warning]", err);
        contentBox.innerHTML = `
            <div class="p-6 text-center" style="background: rgba(15, 23, 42, 0.95); height: 100%;">
                <div class="text-5xl mb-3">🛸</div>
                <h3 class="text-amber-400 font-mono text-base font-bold mb-2">Error 404: Knowledge Node Not Found</h3>
                <p class="text-slate-300 text-xs mb-4">The archival network could not locate this backlink in Wikipedia records: <strong>"${displayTitle}"</strong></p>
                <div class="win95-inset bg-black p-3 text-left font-mono text-xs text-green-400 mb-4">
                    C:\\> DIR /S /B "${cleanQuery}"<br>
                    Searching Encyclopedia Archives...<br>
                    Error 404: File or Backlink Not Found.<br>
                    <br>
                    C:\\> _
                </div>
                <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(cleanQuery)}" target="_blank" class="retro-btn retro-btn-accent text-xs" style="display: inline-block; text-decoration: none;">
                    Search External Wikipedia 🌐
                </a>
            </div>
        `;
    }
}

export function closeWikiWindow(winId) {
    soundEngine.playWindowClose();
    const win = document.getElementById(winId);
    if (!win) return;

    win.classList.remove("window-animate-open");
    win.classList.add("window-animate-close");

    setTimeout(() => {
        win.remove();
        removeTaskbarItem(winId);
    }, 200);
}

export function minimizeWikiWindow(winId) {
    soundEngine.playClick();
    const win = document.getElementById(winId);
    if (!win) return;

    win.classList.add("window-animate-minimize");
    setTimeout(() => {
        win.classList.add("hidden");
        win.classList.remove("window-animate-minimize");
        const tbItem = document.getElementById(`tb-${winId}`);
        if (tbItem) tbItem.classList.remove("active");
    }, 280);
}

export function maximizeWikiWindow(winId) {
    soundEngine.playClick();
    const win = document.getElementById(winId);
    if (!win) return;

    if (win.classList.contains("fullscreen")) {
        win.classList.remove("fullscreen");
        win.style.width = "740px";
        win.style.height = "540px";
        win.style.top = "80px";
        win.style.left = "160px";
    } else {
        win.classList.add("fullscreen");
        win.style.width = "calc(100vw - 40px)";
        win.style.height = "calc(100vh - 100px)";
        win.style.top = "60px";
        win.style.left = "20px";
    }
}

// Backwards Compatibility triggers
export function openWikiModal(query) {
    spawnWikiWindow(query);
}

export function closeWikiModal() {
    document.querySelectorAll(".retro-window").forEach(win => {
        if (win.id.startsWith("wiki-win-")) {
            closeWikiWindow(win.id);
        }
    });
}

export function minimizeWikiModal() {}
export function maximizeWikiModal() {}

/* Taskbar Manager Helpers */
function addTaskbarItem(winId, label) {
    const taskbar = document.getElementById("taskbar");
    if (!taskbar) return;

    let item = document.getElementById(`tb-${winId}`);
    if (!item) {
        item = document.createElement("div");
        item.id = `tb-${winId}`;
        item.className = "taskbar-item active";
        item.textContent = label;
        item.onclick = () => {
            const win = document.getElementById(winId);
            if (win) {
                if (win.classList.contains("hidden")) {
                    win.classList.remove("hidden");
                    win.classList.add("window-animate-open");
                    bringToFront(win);
                    item.classList.add("active");
                } else {
                    win.classList.add("window-animate-minimize");
                    setTimeout(() => {
                        win.classList.add("hidden");
                        win.classList.remove("window-animate-minimize");
                        item.classList.remove("active");
                    }, 250);
                }
            }
        };
        taskbar.appendChild(item);
    }
}

function removeTaskbarItem(winId) {
    const item = document.getElementById(`tb-${winId}`);
    if (item) {
        item.remove();
    }
}
