import { soundEngine } from "./audio.js";

/**
 * WebGL 3D Globe & Spatial Knowledge Graph Controller (Enhanced Interconnected Cluster Edition)
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

        // Fetch seed topics from backend API
        try {
            const res = await fetch("/api/seed-topics");
            if (res.ok) {
                const rawTopics = await res.json();
                this.buildGraphData(rawTopics);
            } else {
                this.buildFallbackGraphData();
            }
        } catch (err) {
            console.warn("[3D Graph Warning] API seed fetch error, using fallback data:", err);
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

        // Explicit knowledge bridge connections connecting Silk Road & Asia to Europe & Tech cluster
        const explicitBridges = [
            { source: "silk-road", target: "byzantine-empire", weight: 3, color: "rgba(255, 183, 3, 0.8)" },
            { source: "silk-road", target: "ancient-persia", weight: 3, color: "rgba(255, 183, 3, 0.8)" },
            { source: "byzantine-empire", target: "ancient-rome", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "ancient-persia", target: "ancient-egypt", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "silk-road", target: "age-of-discovery", weight: 3, color: "rgba(255, 183, 3, 0.8)" },
            { source: "age-of-discovery", target: "renaissance-florence", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "age-of-discovery", target: "industrial-revolution", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "industrial-revolution", target: "silicon-valley", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "silicon-valley", target: "microsoft-encarta", weight: 3, color: "rgba(0, 168, 150, 0.8)" },
            { source: "silicon-valley", target: "quantum-physics", weight: 3, color: "rgba(56, 189, 248, 0.8)" },
            { source: "quantum-physics", target: "space-exploration", weight: 3, color: "rgba(56, 189, 248, 0.8)" }
        ];

        explicitBridges.forEach(link => {
            if (this.nodesData.some(n => n.id === link.source) && this.nodesData.some(n => n.id === link.target)) {
                this.linksData.push(link);
            }
        });

        // Add category-shared secondary connections
        for (let i = 0; i < this.nodesData.length; i++) {
            for (let j = i + 1; j < this.nodesData.length; j++) {
                const n1 = this.nodesData[i];
                const n2 = this.nodesData[j];
                
                const exists = this.linksData.some(l => 
                    (l.source === n1.id && l.target === n2.id) || (l.source === n2.id && l.target === n1.id)
                );

                if (!exists && n1.category === n2.category) {
                    this.linksData.push({
                        source: n1.id,
                        target: n2.id,
                        weight: 1.5,
                        color: "rgba(0, 168, 150, 0.4)"
                    });
                }
            }
        }
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

    getCategoryIcon(cat) {
        switch (cat) {
            case "History": return "🏛️";
            case "Science": return "⚛️";
            case "Technology": return "💻";
            case "Art & Culture": return "🎨";
            case "Trade & Exploration": return "🧭";
            default: return "🌍";
        }
    }

    /**
     * Render custom 3D Sprite texture with unclipped radial soft glow aura for active node
     */
    createNodeSprite(node) {
        if (!window.THREE) return null;

        const isSelected = this.selectedNode && (this.selectedNode.id === node.id || this.selectedNode.title === node.title);

        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext("2d");

        const cx = 128;
        const cy = 100;

        // Active Node Soft Radial Glow Aura
        if (isSelected) {
            const glowGrad = ctx.createRadialGradient(cx, cy, 35, cx, cy, 68);
            glowGrad.addColorStop(0, "rgba(255, 183, 3, 0.8)");
            glowGrad.addColorStop(0.6, "rgba(0, 168, 150, 0.4)");
            glowGrad.addColorStop(1, "rgba(0, 168, 150, 0)");

            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(cx, cy, 68, 0, Math.PI * 2);
            ctx.fill();
        }

        // Inner Circle Badge
        ctx.fillStyle = isSelected ? "rgba(2, 6, 23, 0.95)" : "rgba(15, 23, 42, 0.9)";
        ctx.beginPath();
        ctx.arc(cx, cy, 38, 0, Math.PI * 2);
        ctx.fill();

        // Outer Ring Border
        ctx.strokeStyle = isSelected ? "#FFB703" : node.color;
        ctx.lineWidth = isSelected ? 5 : 3.5;
        ctx.stroke();

        // Category Emoji Icon
        ctx.font = "34px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(node.icon, cx, cy);

        // Title Label
        ctx.fillStyle = isSelected ? "#FFB703" : "#F8F9FA";
        ctx.font = isSelected ? "bold 18px 'Share Tech Mono', monospace" : "bold 15px 'Share Tech Mono', monospace";
        ctx.fillText(node.title, cx, 185);

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);

        const spriteScale = isSelected ? 34 : 26;
        sprite.scale.set(spriteScale, spriteScale, 1);

        return sprite;
    }

    renderGraph() {
        const container = document.getElementById(this.containerId);
        if (!window.ForceGraph3D) return;

        this.graph = window.ForceGraph3D()(container)
            .graphData({ nodes: this.nodesData, links: this.linksData })
            .nodeId("id")
            .nodeThreeObject(node => this.createNodeSprite(node))
            .nodeLabel(node => `
                <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid ${node.color}; padding: 8px 12px; font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #FFB703; box-shadow: 0 0 14px ${node.color};">
                    <div style="font-weight: bold; font-size: 13px;">${node.icon} ${node.title}</div>
                    <div style="color: #00A896; font-size: 11px;">${node.era}</div>
                    <div style="color: #F8F9FA; font-size: 11px; margin-top: 4px;">${node.summary_short}</div>
                </div>
            `)
            .linkCurvature(0.25)
            .linkColor(link => link.color)
            .linkWidth(link => (link.weight || 1) * 1.2)

            // Flowing Particle Stream Edges
            .linkDirectionalParticles(link => (link.weight || 1) * 2)
            .linkDirectionalParticleSpeed(0.006)
            .linkDirectionalParticleWidth(2.5)
            .linkDirectionalParticleColor(() => "#FFB703")

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

    focusTopicByTitle(title) {
        let target = this.nodesData.find(n => n.title.toLowerCase() === title.toLowerCase());
        if (!target) {
            target = {
                id: title.toLowerCase().replace(/\s+/g, "-"),
                title: title,
                category: "Knowledge Node",
                era: "Historical Epoch",
                lat: 20.0 + (hashString(title) % 50),
                lng: (hashString(title * 2) % 360) - 180,
                summary_short: `Newly added node: ${title}`,
                color: "#FFB703",
                icon: "📌"
            };
            this.nodesData.push(target);
            
            if (this.nodesData.length > 1) {
                this.linksData.push({
                    source: target.id,
                    target: this.nodesData[0].id,
                    weight: 2,
                    color: "#FFB703"
                });
            }

            if (this.graph) {
                this.graph.graphData({ nodes: this.nodesData, links: this.linksData });
            }
        }

        this.focusNode(target);
        if (this.onNodeSelect) {
            this.onNodeSelect(target.title);
        }
    }

    filterByCategory(category) {
        if (!this.nodesData) return;
        const filteredNodes = category === "All"
            ? this.nodesData
            : this.nodesData.filter(n => n.category === category);

        if (this.graph) {
            this.graph.graphData({
                nodes: filteredNodes,
                links: this.linksData.filter(l =>
                    filteredNodes.some(n => n.id === (l.source.id || l.source)) &&
                    filteredNodes.some(n => n.id === (l.target.id || l.target))
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
