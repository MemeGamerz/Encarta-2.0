import { soundEngine } from "./audio.js";

/**
 * WebGL 3D Globe & Spatial Knowledge Graph Controller (Single Unified Graph Cluster Edition)
 */

export class SpatialGraphController {
    constructor(containerId, onNodeSelectCallback) {
        this.containerId = containerId;
        this.onNodeSelect = onNodeSelectCallback;
        this.graph = null;
        this.nodesData = [];
        this.linksData = [];
        this.selectedNode = null;
        this.autoRotate = true;
        this.rotationSpeed = 0.8;
    }

    async init() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Fetch persistent knowledge nodes from backend SQLite database
        try {
            const res = await fetch("/api/nodes");
            if (res.ok) {
                const rawTopics = await res.json();
                this.buildGraphData(rawTopics);
            } else {
                this.buildFallbackGraphData();
            }
        } catch (err) {
            console.warn("[3D Graph Warning] API nodes fetch error, using fallback data:", err);
            this.buildFallbackGraphData();
        }

        this.renderGraph();
    }

    buildGraphData(topics) {
        this.nodesData = topics.map(t => ({
            id: t.id,
            title: t.title,
            category: t.category,
            era: t.era,
            lat: t.lat,
            lng: t.lng,
            summary_short: t.summary_short,
            color: this.getCategoryColor(t.category),
            icon: this.getCategoryIcon(t.category)
        }));

        this.linksData = [];

        // Explicit initial knowledge bridge connections (fixed baseline network)
        const explicitBridges = [
            { source: "silk-road", target: "byzantine-empire", weight: 3 },
            { source: "silk-road", target: "ancient-persia", weight: 3 },
            { source: "byzantine-empire", target: "ancient-rome", weight: 3 },
            { source: "ancient-persia", target: "ancient-egypt", weight: 3 },
            { source: "silk-road", target: "age-of-discovery", weight: 3 },
            { source: "age-of-discovery", target: "renaissance-florence", weight: 3 },
            { source: "age-of-discovery", target: "industrial-revolution", weight: 3 },
            { source: "industrial-revolution", target: "silicon-valley", weight: 3 },
            { source: "silicon-valley", target: "microsoft-encarta", weight: 3 },
            { source: "silicon-valley", target: "quantum-physics", weight: 3 },
            { source: "quantum-physics", target: "space-exploration", weight: 3 }
        ];

        explicitBridges.forEach(link => {
            const n1 = this.nodesData.find(n => n.id === link.source);
            const n2 = this.nodesData.find(n => n.id === link.target);
            if (n1 && n2) {
                const wireColor = this.getLinkColor(n1, n2);
                this.linksData.push({
                    source: link.source,
                    target: link.target,
                    weight: link.weight,
                    color: wireColor
                });
            }
        });

        // Ensure 100% single unified cluster connectivity (ZERO isolated islands or sub-clusters)
        this.ensureSingleUnifiedCluster();
    }

    buildFallbackGraphData() {
        this.buildGraphData([
            { id: "microsoft-encarta", title: "Microsoft Encarta", category: "Technology", era: "1993 – 2009", lat: 47.6405, lng: -122.1297, summary_short: "Digital CD-ROM encyclopedia." },
            { id: "ancient-rome", title: "Ancient Rome", category: "History", era: "753 BCE – 476 CE", lat: 41.9028, lng: 12.4964, summary_short: "Roman Law and Aqueducts." },
            { id: "byzantine-empire", title: "Byzantine Empire", category: "History", era: "330 CE – 1453 CE", lat: 41.0082, lng: 28.9784, summary_short: "Constantinople crossroads." },
            { id: "silk-road", title: "The Silk Road", category: "Trade & Exploration", era: "130 BCE – 1453 CE", lat: 34.3416, lng: 108.9398, summary_short: "Transcontinental trade." },
            { id: "silicon-valley", title: "Silicon Valley", category: "Technology", era: "1939 – Present", lat: 37.3875, lng: -122.0575, summary_short: "Microchip and AI epicenter." },
            { id: "quantum-physics", title: "Quantum Physics", category: "Science", era: "1900 – Present", lat: 52.5200, lng: 13.4050, summary_short: "Wave-particle duality." },
            { id: "renaissance-florence", title: "Renaissance Florence", category: "Art & Culture", era: "1300 – 1600", lat: 43.7696, lng: 11.2558, summary_short: "Brunelleschi and Medici patronage." },
            { id: "industrial-revolution", title: "Industrial Revolution", category: "Technology", era: "1760 – 1840", lat: 53.4808, lng: -2.2426, summary_short: "Steam power and mechanization." }
        ]);
    }

    /**
     * BFS Graph Connectivity Algorithm:
     * Guarantees that EVERY node and sub-cluster in the 3D WebGL universe belongs to
     * ONE single unified connected component rooted at 'microsoft-encarta'.
     * Eliminates isolated islands, pairs, and floating sub-clusters permanently.
     */
    ensureSingleUnifiedCluster() {
        if (!this.nodesData || this.nodesData.length <= 1) return;

        const mainRootId = "microsoft-encarta";
        const rootNode = this.nodesData.find(n => n.id === mainRootId) || this.nodesData[0];
        const rootId = rootNode.id;

        // BFS to find all node IDs reachable from rootId
        let visited = this.getReachableNodes(rootId);

        // Keep connecting isolated islands until all nodes belong to the main cluster
        let unvisitedNodes = this.nodesData.filter(n => !visited.has(n.id));

        while (unvisitedNodes.length > 0) {
            const islandNode = unvisitedNodes[0];

            // Find a target node in the main cluster (prefer matching category if possible)
            const targetInMainCluster = this.nodesData.find(n => visited.has(n.id) && n.category === islandNode.category) ||
                                        this.nodesData.find(n => visited.has(n.id)) ||
                                        rootNode;

            if (targetInMainCluster && targetInMainCluster.id !== islandNode.id) {
                this.linksData.push({
                    source: islandNode.id,
                    target: targetInMainCluster.id,
                    weight: 2,
                    color: this.getLinkColor(islandNode, targetInMainCluster)
                });
            }

            // Re-run BFS to update visited set with the newly bridged sub-cluster
            visited = this.getReachableNodes(rootId);
            unvisitedNodes = this.nodesData.filter(n => !visited.has(n.id));
        }
    }

    /**
     * Traverses links using BFS to find all node IDs connected to rootId
     */
    getReachableNodes(rootId) {
        const visited = new Set([rootId]);
        const queue = [rootId];

        while (queue.length > 0) {
            const curr = queue.shift();
            this.linksData.forEach(l => {
                const sId = typeof l.source === 'object' ? (l.source.id || l.source) : l.source;
                const tId = typeof l.target === 'object' ? (l.target.id || l.target) : l.target;

                if (sId === curr && !visited.has(tId)) {
                    visited.add(tId);
                    queue.push(tId);
                } else if (tId === curr && !visited.has(sId)) {
                    visited.add(sId);
                    queue.push(sId);
                }
            });
        }
        return visited;
    }

    getCategoryColor(cat) {
        switch (cat) {
            case "History": return "#FFB703"; // Gold
            case "Technology": return "#00A896"; // Encarta Teal
            case "Science": return "#38BDF8"; // Sky Blue
            case "Art & Culture": return "#F43F5E"; // Rose
            case "Trade & Exploration": return "#A855F7"; // Purple
            default: return "#10B981"; // Emerald
        }
    }

    getLinkColor(n1, n2) {
        if (n1.category === "Technology" && n2.category === "Technology") return "#00A896";
        if (n1.category === "History" && n2.category === "History") return "#FFB703";
        if (n1.category === "Science" && n2.category === "Science") return "#38BDF8";
        if (n1.category === "Art & Culture" && n2.category === "Art & Culture") return "#F43F5E";
        if (n1.category === "Trade & Exploration" && n2.category === "Trade & Exploration") return "#A855F7";
        return n1.color || "#00A896";
    }

    getCategoryIcon(cat) {
        switch (cat) {
            case "History": return "🏛️";
            case "Science": return "⚛️";
            case "Technology": return "💻";
            case "Art & Culture": return "🎨";
            case "Trade & Exploration": return "🧭";
            default: return "📌";
        }
    }

    /**
     * Render custom 3D Sprite texture with 100% transparent background (NO black box)
     */
    createNodeSprite(node) {
        if (!window.THREE) return null;

        const isSelected = this.selectedNode && (this.selectedNode.id === node.id || this.selectedNode.title === node.title);

        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext("2d");

        ctx.clearRect(0, 0, 256, 256);

        const cx = 128;
        const cy = 100;

        // Active Node Soft Radial Glow Aura
        if (isSelected) {
            const glowGrad = ctx.createRadialGradient(cx, cy, 32, cx, cy, 65);
            glowGrad.addColorStop(0, "rgba(255, 183, 3, 0.8)");
            glowGrad.addColorStop(0.5, "rgba(0, 168, 150, 0.4)");
            glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(cx, cy, 65, 0, Math.PI * 2);
            ctx.fill();
        }

        // Inner Circle Badge
        ctx.fillStyle = isSelected ? "rgba(2, 6, 23, 0.95)" : "rgba(15, 23, 42, 0.88)";
        ctx.beginPath();
        ctx.arc(cx, cy, 36, 0, Math.PI * 2);
        ctx.fill();

        // Outer Ring Border
        ctx.strokeStyle = isSelected ? "#FFB703" : node.color;
        ctx.lineWidth = isSelected ? 4.5 : 3;
        ctx.stroke();

        // Category Emoji Icon
        ctx.font = "32px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(node.icon, cx, cy);

        // Title Label
        ctx.fillStyle = isSelected ? "#FFB703" : "#F8F9FA";
        ctx.font = isSelected ? "bold 18px 'Share Tech Mono', monospace" : "bold 15px 'Share Tech Mono', monospace";
        ctx.fillText(node.title, cx, 180);

        const texture = new THREE.CanvasTexture(canvas);
        
        const material = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthWrite: false,
            alphaTest: 0.01
        });
        const sprite = new THREE.Sprite(material);

        const spriteScale = isSelected ? 32 : 25;
        sprite.scale.set(spriteScale, spriteScale, 1);

        return sprite;
    }

    /**
     * Sanitize link IDs to prevent 3d-force-graph internal object mutation crash
     */
    cleanLinks() {
        return this.linksData.map(l => ({
            source: typeof l.source === 'object' ? (l.source.id || l.source) : l.source,
            target: typeof l.target === 'object' ? (l.target.id || l.target) : l.target,
            weight: l.weight || 1,
            color: l.color || "#00A896"
        }));
    }

    renderGraph() {
        const container = document.getElementById(this.containerId);
        if (!window.ForceGraph3D) return;

        this.graph = window.ForceGraph3D()(container)
            .graphData({ nodes: this.nodesData, links: this.cleanLinks() })
            .nodeId("id")
            .nodeThreeObject(node => this.createNodeSprite(node))
            .nodeLabel(node => `
                <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid ${node.color}; padding: 8px 12px; font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #FFB703; box-shadow: 0 0 14px ${node.color};">
                    <div style="font-weight: bold; font-size: 13px;">${node.icon} ${node.title}</div>
                    <div style="color: #00A896; font-size: 11px;">${node.era}</div>
                    <div style="color: #F8F9FA; font-size: 11px; margin-top: 4px;">${node.summary_short}</div>
                </div>
            `)
            .linkDirectionalParticles(0)
            .linkThreeObject(link => {
                const color = link.color || "#00A896";
                const lineMat = new THREE.LineDashedMaterial({
                    color: new THREE.Color(color),
                    dashSize: 10,
                    gapSize: 14,
                    linewidth: 2,
                    transparent: true,
                    opacity: 0.85
                });
                const geometry = new THREE.BufferGeometry();
                geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(6), 3));
                const line = new THREE.Line(geometry, lineMat);
                return line;
            })
            .linkPositionUpdate((line, { start, end }) => {
                const positions = line.geometry.attributes.position.array;
                positions[0] = start.x;
                positions[1] = start.y;
                positions[2] = start.z;
                positions[3] = end.x;
                positions[4] = end.y;
                positions[5] = end.z;

                line.geometry.attributes.position.needsUpdate = true;
                line.geometry.computeBoundingSphere();
                
                if (line.material) {
                    line.material.dashOffset -= 0.15;
                }
                return true;
            })

            .onNodeClick(node => {
                soundEngine.playNodeFocus();
                this.focusNode(node);
                if (this.onNodeSelect) {
                    this.onNodeSelect(node.title);
                }
            })
            .onNodeHover(node => {
                container.style.cursor = node ? "pointer" : "default";
            });

        // Camera Initial Position
        this.graph.cameraPosition({ x: 0, y: 0, z: 280 });

        // Auto Rotation Settings
        if (this.graph.controls && this.graph.controls()) {
            this.graph.controls().autoRotate = this.autoRotate;
            this.graph.controls().autoRotateSpeed = this.rotationSpeed;
        }
    }

    /**
     * Smoothly fly camera to focused node and trigger glowing halo refresh
     */
    focusNode(node) {
        if (!this.graph || !node) return;
        this.selectedNode = node;

        soundEngine.playNodeBirthChime();

        this.graph.nodeThreeObject(n => this.createNodeSprite(n));

        const distance = 150;
        const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);

        this.graph.cameraPosition(
            { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
            { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
            1800
        );
    }

    /**
     * Replace active graph dataset with reset raw topics from DB
     */
    setNodes(rawTopics) {
        if (!rawTopics || !Array.isArray(rawTopics)) return;
        this.buildGraphData(rawTopics);
        if (this.graph) {
            this.graph.graphData({
                nodes: this.nodesData,
                links: this.cleanLinks()
            });
        }
    }

    /**
     * Dynamically add or update a knowledge node.
     * ZERO isolated sub-clusters allowed! Connects new nodes and unifies all components into 1 cluster.
     */
    addOrUpdateNode(article) {
        if (!article || !article.title) return;
        const title = article.title.trim();
        const nodeId = title.toLowerCase().replace(/\s+/g, "-");
        const category = article.category || "Knowledge Node";
        const coords = article.coordinates || {};
        const lat = coords.lat !== undefined ? coords.lat : (20.0 + (hashString(title) % 50));
        const lng = coords.lng !== undefined ? coords.lng : ((hashString(title * 2) % 360) - 180);
        const summary = article.summary || "";
        const summary_short = summary.length > 110 ? (summary.substring(0, 110) + "...") : summary;

        let node = this.nodesData.find(n => n.id === nodeId || n.title.toLowerCase() === title.toLowerCase());
        
        if (node) {
            // Node ALREADY exists! Unify cluster and focus
            this.ensureSingleUnifiedCluster();
            this.focusNode(node);
            return;
        }

        // Create BRAND NEW Node
        node = {
            id: nodeId,
            title: title,
            category: category,
            era: article.era || "Historical Epoch",
            lat: lat,
            lng: lng,
            summary_short: summary_short,
            color: this.getCategoryColor(category),
            icon: this.getCategoryIcon(category)
        };
        this.nodesData.push(node);

        // Add 1 primary connection wire for the new node
        let connected = false;
        if (article.related_topics && Array.isArray(article.related_topics)) {
            for (const relTitle of article.related_topics) {
                const relNode = this.nodesData.find(n => n.title.toLowerCase() === relTitle.toLowerCase());
                if (relNode && relNode.id !== node.id) {
                    this.linksData.push({
                        source: node.id,
                        target: relNode.id,
                        weight: 2,
                        color: this.getLinkColor(node, relNode)
                    });
                    connected = true;
                    break;
                }
            }
        }

        // Run BFS Single Unified Cluster check to bridge any isolated sub-clusters to main root
        this.ensureSingleUnifiedCluster();

        // Refresh 3D Graph dataset
        if (this.graph) {
            this.graph.graphData({ nodes: this.nodesData, links: this.cleanLinks() });
        }

        this.focusNode(node);
    }

    focusTopicByTitle(title) {
        let target = this.nodesData.find(n => n.title.toLowerCase() === title.toLowerCase());
        if (target) {
            this.focusNode(target);
            if (this.onNodeSelect) {
                this.onNodeSelect(target.title);
            }
        } else {
            // Trigger article load which will dynamically add the node
            if (this.onNodeSelect) {
                this.onNodeSelect(title);
            }
        }
    }

    filterByCategory(category) {
        if (!this.nodesData) return;
        const filteredNodes = category === "All"
            ? this.nodesData
            : this.nodesData.filter(n => n.category === category);

        const cleanLinksList = this.cleanLinks();

        if (this.graph) {
            this.graph.graphData({
                nodes: filteredNodes,
                links: cleanLinksList.filter(l =>
                    filteredNodes.some(n => n.id === l.source) &&
                    filteredNodes.some(n => n.id === l.target)
                )
            });
        }
    }

    toggleAutoRotate() {
        this.autoRotate = !this.autoRotate;
        if (this.graph && this.graph.controls && this.graph.controls()) {
            this.graph.controls().autoRotate = this.autoRotate;
        }
        return this.autoRotate;
    }

    setRotationSpeed(speedVal) {
        this.rotationSpeed = parseFloat(speedVal);
        if (this.graph && this.graph.controls && this.graph.controls()) {
            this.graph.controls().autoRotateSpeed = this.rotationSpeed;
        }
    }
}

function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}
