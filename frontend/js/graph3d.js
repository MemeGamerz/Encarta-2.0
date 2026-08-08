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
        this.threeDisposables = [];
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
            {
                        "id": "mesopotamia",
                        "title": "Mesopotamia",
                        "category": "History",
                        "era": "4000 BCE \u2013 539 BCE",
                        "lat": 32.5364,
                        "lng": 44.4208,
                        "summary_short": "Mesopotamia, situated between the Tigris and Euphrates rivers in modern-day Iraq, is widely regarded as the Cr..."
            },
            {
                        "id": "mayan-civilization",
                        "title": "Mayan Civilization",
                        "category": "History",
                        "era": "2000 BCE \u2013 1697 CE",
                        "lat": 20.6843,
                        "lng": -88.5678,
                        "summary_short": "The Maya civilization flourished across Mesoamerica, renowned for its sophisticated logo-syllabic writing syst..."
            },
            {
                        "id": "french-revolution",
                        "title": "French Revolution",
                        "category": "History",
                        "era": "1789 \u2013 1799",
                        "lat": 48.8566,
                        "lng": 2.3522,
                        "summary_short": "The French Revolution was a period of radical political and societal change in France that began with the Esta..."
            },
            {
                        "id": "ottoman-empire",
                        "title": "Ottoman Empire",
                        "category": "History",
                        "era": "1299 \u2013 1922",
                        "lat": 41.0082,
                        "lng": 28.9784,
                        "summary_short": "Spanning Southeast Europe, Western Asia, and North Africa for over six centuries, the Ottoman Empire served as..."
            },
            {
                        "id": "viking-age",
                        "title": "Viking Age",
                        "category": "History",
                        "era": "793 \u2013 1066 CE",
                        "lat": 59.9139,
                        "lng": 10.7522,
                        "summary_short": "The Viking Age was a period of Scandinavian maritime exploration, trade, and settlement. Norse seafarers navig..."
            },
            {
                        "id": "mongol-empire",
                        "title": "Mongol Empire",
                        "category": "History",
                        "era": "1206 \u2013 1368",
                        "lat": 47.9188,
                        "lng": 106.9176,
                        "summary_short": "Founded by Genghis Khan, the Mongol Empire became the largest contiguous land empire in history. Its Pax Mongo..."
            },
            {
                        "id": "cryptography-&-enigma",
                        "title": "Cryptography & Enigma",
                        "category": "Technology",
                        "era": "1900 \u2013 Present",
                        "lat": 51.9977,
                        "lng": -0.7407,
                        "summary_short": "Cryptography is the science of secure communication. From wartime cipher machines like Enigma to Alan Turing's..."
            },
            {
                        "id": "world-wide-web",
                        "title": "World Wide Web",
                        "category": "Technology",
                        "era": "1989 \u2013 Present",
                        "lat": 46.233,
                        "lng": 6.0557,
                        "summary_short": "The World Wide Web is an information system enabling document retrieval via HTTP links over the Internet. Inve..."
            },
            {
                        "id": "quantum-computing",
                        "title": "Quantum Computing",
                        "category": "Technology",
                        "era": "1980 \u2013 Present",
                        "lat": 37.403,
                        "lng": -122.0322,
                        "summary_short": "Quantum computing harnesses quantum mechanical phenomena like superposition and entanglement to perform comple..."
            },
            {
                        "id": "the-telegraph",
                        "title": "The Telegraph",
                        "category": "Technology",
                        "era": "1837 \u2013 1950s",
                        "lat": 40.7128,
                        "lng": -74.006,
                        "summary_short": "The electrical telegraph was the first technology to enable instant long-distance text transmission via Morse ..."
            },
            {
                        "id": "dna-double-helix",
                        "title": "DNA Double Helix",
                        "category": "Science",
                        "era": "1953 \u2013 Present",
                        "lat": 52.2053,
                        "lng": 0.1218,
                        "summary_short": "The discovery of the double-helical structure of Deoxyribonucleic Acid (DNA) unlocked the molecular code of bi..."
            },
            {
                        "id": "theory-of-evolution",
                        "title": "Theory of Evolution",
                        "category": "Science",
                        "era": "1859 \u2013 Present",
                        "lat": -0.9538,
                        "lng": -90.9656,
                        "summary_short": "Formulated by Charles Darwin, the theory of evolution by natural selection explains how biological organisms a..."
            },
            {
                        "id": "james-webb-telescope",
                        "title": "James Webb Telescope",
                        "category": "Science",
                        "era": "2021 \u2013 Present",
                        "lat": 28.5721,
                        "lng": -80.648,
                        "summary_short": "NASA's premier space science observatory, the James Webb Space Telescope uses high-resolution infrared instrum..."
            },
            {
                        "id": "large-hadron-collider",
                        "title": "Large Hadron Collider",
                        "category": "Science",
                        "era": "2008 \u2013 Present",
                        "lat": 46.233,
                        "lng": 6.0557,
                        "summary_short": "The Large Hadron Collider (LHC) at CERN is the world's largest high-energy particle accelerator, built in a 27..."
            },
            {
                        "id": "discovery-of-penicillin",
                        "title": "Discovery of Penicillin",
                        "category": "Science",
                        "era": "1928 \u2013 Present",
                        "lat": 51.5147,
                        "lng": -0.1748,
                        "summary_short": "The accidental discovery of penicillin by Alexander Fleming marked the beginning of modern antibiotics, saving..."
            },
            {
                        "id": "human-neuroscience",
                        "title": "Human Neuroscience",
                        "category": "Science",
                        "era": "1890 \u2013 Present",
                        "lat": 40.4168,
                        "lng": -3.7038,
                        "summary_short": "Neuroscience explores the structure and function of the brain and nervous system. Santiago Ram\u00f3n y Cajal's neu..."
            },
            {
                        "id": "greek-philosophy",
                        "title": "Greek Philosophy",
                        "category": "Art & Culture",
                        "era": "600 BCE \u2013 300 BCE",
                        "lat": 37.9838,
                        "lng": 23.7275,
                        "summary_short": "Classical Greek philosophy in Athens laid the foundational framework of Western rational thought, political et..."
            },
            {
                        "id": "baroque-music-&-bach",
                        "title": "Baroque Music & Bach",
                        "category": "Art & Culture",
                        "era": "1600 \u2013 1750",
                        "lat": 51.3397,
                        "lng": 12.3731,
                        "summary_short": "Baroque music brought complex counterpoint, fugal polyphony, and opera to Western classical music, defined by ..."
            },
            {
                        "id": "surrealism-&-dal\u00ed",
                        "title": "Surrealism & Dal\u00ed",
                        "category": "Art & Culture",
                        "era": "1920 \u2013 1950",
                        "lat": 48.8566,
                        "lng": 2.3522,
                        "summary_short": "Surrealism was an avant-garde cultural movement that sought to release the uninhibited imagery of the subconsc..."
            },
            {
                        "id": "cinema-pioneers",
                        "title": "Cinema Pioneers",
                        "category": "Art & Culture",
                        "era": "1895 \u2013 1930",
                        "lat": 45.764,
                        "lng": 4.8357,
                        "summary_short": "The birth of motion pictures transformed global storytelling. Pioneers Auguste and Louis Lumi\u00e8re and illusioni..."
            },
            {
                        "id": "transatlantic-voyages",
                        "title": "Transatlantic Voyages",
                        "category": "Trade & Exploration",
                        "era": "1492 \u2013 1900s",
                        "lat": 25.0343,
                        "lng": -77.3963,
                        "summary_short": "Oceanic transatlantic routes linked Afro-Eurasia with the Americas, sparking the Columbian Exchange of crops, ..."
            },
            {
                        "id": "the-spice-trade",
                        "title": "The Spice Trade",
                        "category": "Trade & Exploration",
                        "era": "1000 BCE \u2013 1700 CE",
                        "lat": -4.5624,
                        "lng": 129.9042,
                        "summary_short": "The spice trade was a historical maritime network exchanging cinnamon, black pepper, and nutmeg between Asia, ..."
            },
            {
                        "id": "antarctic-expeditions",
                        "title": "Antarctic Expeditions",
                        "category": "Trade & Exploration",
                        "era": "1820 \u2013 Present",
                        "lat": -75.2509,
                        "lng": -0.0713,
                        "summary_short": "Polar exploration of Earth's southernmost continent saw explorers brave extreme freezing environments, culmina..."
            },
            {
                        "id": "deep-sea-exploration",
                        "title": "Deep Sea Exploration",
                        "category": "Trade & Exploration",
                        "era": "1960 \u2013 Present",
                        "lat": 11.3493,
                        "lng": 142.1996,
                        "summary_short": "Deep sea exploration uses pressurized submersibles to investigate Earth's deepest abyssal trenches and hydroth..."
            },
            {
                        "id": "microsoft-encarta",
                        "title": "Microsoft Encarta",
                        "category": "Technology",
                        "era": "1993 \u2013 2009",
                        "lat": 47.6405,
                        "lng": -122.1297,
                        "summary_short": "Microsoft Encarta was a digital multimedia encyclopedia published by Microsoft from 1993 to 2009. Originally r..."
            },
            {
                        "id": "the-silk-road",
                        "title": "The Silk Road",
                        "category": "Trade & Exploration",
                        "era": "130 BCE \u2013 1453 CE",
                        "lat": 34.3416,
                        "lng": 108.9398,
                        "summary_short": "The Silk Road was a network of Eurasian trade routes active from the second century BCE until the mid-15th cen..."
            },
            {
                        "id": "byzantine-empire",
                        "title": "Byzantine Empire",
                        "category": "History",
                        "era": "330 CE \u2013 1453 CE",
                        "lat": 41.0082,
                        "lng": 28.9784,
                        "summary_short": "The Byzantine Empire, also referred to as the Eastern Roman Empire, was the continuation of the Roman Empire p..."
            },
            {
                        "id": "ancient-rome",
                        "title": "Ancient Rome",
                        "category": "History",
                        "era": "753 BCE \u2013 476 CE",
                        "lat": 41.9028,
                        "lng": 12.4964,
                        "summary_short": "Ancient Rome evolved from an iron-age agrarian settlement on the Italian Peninsula into one of the largest emp..."
            },
            {
                        "id": "ancient-persia",
                        "title": "Ancient Persia",
                        "category": "History",
                        "era": "550 BCE \u2013 330 BCE",
                        "lat": 29.9344,
                        "lng": 52.8911,
                        "summary_short": "The Achaemenid Empire, also known as the First Persian Empire, was an ancient Iranian empire founded by Cyrus ..."
            },
            {
                        "id": "age-of-discovery",
                        "title": "Age of Discovery",
                        "category": "Trade & Exploration",
                        "era": "1400 \u2013 1600",
                        "lat": 38.7223,
                        "lng": -9.1393,
                        "summary_short": "The Age of Discovery was a period of extensive overseas exploration driven by European powers seeking new trad..."
            },
            {
                        "id": "renaissance-florence",
                        "title": "Renaissance Florence",
                        "category": "Art & Culture",
                        "era": "1300 \u2013 1600",
                        "lat": 43.7696,
                        "lng": 11.2558,
                        "summary_short": "Florence is widely regarded as the birthplace of the Renaissance, a fervent period of European cultural, artis..."
            },
            {
                        "id": "industrial-revolution",
                        "title": "Industrial Revolution",
                        "category": "Technology",
                        "era": "1760 \u2013 1840",
                        "lat": 53.4808,
                        "lng": -2.2426,
                        "summary_short": "The Industrial Revolution marked the transition from agrarian, handicraft economies to machine-driven industri..."
            },
            {
                        "id": "ancient-egypt",
                        "title": "Ancient Egypt",
                        "category": "History",
                        "era": "3100 BCE \u2013 30 BCE",
                        "lat": 29.9792,
                        "lng": 31.1342,
                        "summary_short": "Ancient Egypt was a civilization of ancient North Africa along the lower reaches of the Nile River. Famous for..."
            },
            {
                        "id": "space-exploration",
                        "title": "Space Exploration",
                        "category": "Science",
                        "era": "1957 \u2013 Present",
                        "lat": 28.5721,
                        "lng": -80.648,
                        "summary_short": "Space Exploration is the discovery and exploration of celestial structures in outer space by means of evolving..."
            },
            {
                        "id": "quantum-physics",
                        "title": "Quantum Physics",
                        "category": "Science",
                        "era": "1900 \u2013 Present",
                        "lat": 52.52,
                        "lng": 13.405,
                        "summary_short": "Quantum Mechanics is a fundamental theory in physics that provides a description of the physical properties of..."
            },
            {
                        "id": "silicon-valley",
                        "title": "Silicon Valley",
                        "category": "Technology",
                        "era": "1939 \u2013 Present",
                        "lat": 37.3875,
                        "lng": -122.0575,
                        "summary_short": "Silicon Valley is a region in Northern California that serves as a global center for high technology and innov..."
            },
            {
                        "id": "artificial-intelligence",
                        "title": "Artificial Intelligence",
                        "category": "Technology",
                        "era": "1956 \u2013 Present",
                        "lat": 43.7001,
                        "lng": -72.2894,
                        "summary_short": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence ..."
            },
            {
                        "id": "impressionism",
                        "title": "Impressionism",
                        "category": "Art & Culture",
                        "era": "1860s \u2013 1890s",
                        "lat": 48.8606,
                        "lng": 2.3376,
                        "summary_short": "Impressionism is a 19th-century art movement characterized by relatively small, thin, yet visible brush stroke..."
            },
            {
                        "id": "dna-structure",
                        "title": "DNA Structure",
                        "category": "Science",
                        "era": "1953 \u2013 Present",
                        "lat": 52.2053,
                        "lng": 0.1218,
                        "summary_short": "Deoxyribonucleic acid (DNA) is a polymer composed of two polynucleotide chains that coil around each other to ..."
            },
            {
                        "id": "world-war-ii",
                        "title": "World War II",
                        "category": "History",
                        "era": "1939 \u2013 1945",
                        "lat": 52.52,
                        "lng": 13.405,
                        "summary_short": "World War II was a global conflict that lasted from 1939 to 1945. It involved the vast majority of the world's..."
            },
            {
                        "id": "the-internet",
                        "title": "The Internet",
                        "category": "Technology",
                        "era": "1969 \u2013 Present",
                        "lat": 38.8951,
                        "lng": -77.0364,
                        "summary_short": "The Internet is the global system of interconnected computer networks that uses the Internet protocol suite (T..."
            },
            {
                        "id": "the-beatles",
                        "title": "The Beatles",
                        "category": "Art & Culture",
                        "era": "1960 \u2013 1970",
                        "lat": 53.4084,
                        "lng": -2.9916,
                        "summary_short": "The Beatles were an English rock band formed in Liverpool in 1960. Comprising John Lennon, Paul McCartney, Geo..."
            },
            {
                        "id": "cyberpunk",
                        "title": "Cyberpunk",
                        "category": "Art & Culture",
                        "era": "1980s \u2013 Present",
                        "lat": 35.6762,
                        "lng": 139.6503,
                        "summary_short": "Cyberpunk is a subgenre of science fiction in a dystopian futuristic setting that tends to focus on a 'combina..."
            }
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
     * Render custom 3D Node with mathematically exact circular hitbox matching the glow area
     */
    createNodeSprite(node) {
        if (!window.THREE) return null;

        const isSelected = this.selectedNode && (this.selectedNode.id === node.id || this.selectedNode.title === node.title);

        const group = new THREE.Group();
        group.__data = node;

        // 1. Exact Circular Hitbox Sphere (Interactive Mesh matching circular glow boundary)
        const hitRadius = isSelected ? 8.5 : 7.0;
        const hitGeo = new THREE.SphereGeometry(hitRadius, 16, 16);
        const hitMat = new THREE.MeshBasicMaterial({
            transparent: true,
            opacity: 0,
            depthWrite: false
        });
        const hitMesh = new THREE.Mesh(hitGeo, hitMat);
        hitMesh.__data = node;
        group.add(hitMesh);
        this.threeDisposables.push(hitGeo, hitMat);

        // 2. High-Res Circular Badge & Soft Radial Glow Sprite
        const dpr = window.devicePixelRatio || 1;
        const badgeSize = 128;
        
        const canvas = document.createElement("canvas");
        canvas.width = badgeSize * dpr;
        canvas.height = badgeSize * dpr;
        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, badgeSize, badgeSize);

        const cx = badgeSize / 2;
        const cy = badgeSize / 2;

        // Active Node Soft Radial Glow Aura
        if (isSelected) {
            const glowGrad = ctx.createRadialGradient(cx, cy, 18, cx, cy, 58);
            glowGrad.addColorStop(0, "rgba(255, 183, 3, 0.9)");
            glowGrad.addColorStop(0.5, "rgba(0, 168, 150, 0.45)");
            glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(cx, cy, 58, 0, Math.PI * 2);
            ctx.fill();
        } else {
            const glowGrad = ctx.createRadialGradient(cx, cy, 16, cx, cy, 48);
            glowGrad.addColorStop(0, `${node.color}55`);
            glowGrad.addColorStop(0.6, `${node.color}22`);
            glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(cx, cy, 48, 0, Math.PI * 2);
            ctx.fill();
        }

        // Inner Circle Badge
        ctx.fillStyle = isSelected ? "rgba(2, 6, 23, 0.95)" : "rgba(15, 23, 42, 0.88)";
        ctx.beginPath();
        ctx.arc(cx, cy, 26, 0, Math.PI * 2);
        ctx.fill();

        // Outer Ring Border
        ctx.strokeStyle = isSelected ? "#FFB703" : node.color;
        ctx.lineWidth = isSelected ? 3.5 : 2.5;
        ctx.stroke();

        // Category Emoji Icon
        ctx.font = "24px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(node.icon, cx, cy);

        const badgeTexture = new THREE.CanvasTexture(canvas);
        const badgeMat = new THREE.SpriteMaterial({
            map: badgeTexture,
            transparent: true,
            depthWrite: false
        });
        const badgeSprite = new THREE.Sprite(badgeMat);
        const spriteScale = isSelected ? 22 : 18;
        badgeSprite.scale.set(spriteScale, spriteScale, 1);
        badgeSprite.__data = node;
        group.add(badgeSprite);
        this.threeDisposables.push(badgeTexture, badgeMat);

        // 3. Crisp Text Label Sprite (placed directly below the circular badge)
        const textCanvas = document.createElement("canvas");
        textCanvas.width = 256 * dpr;
        textCanvas.height = 48 * dpr;
        const tCtx = textCanvas.getContext("2d");
        tCtx.scale(dpr, dpr);

        tCtx.fillStyle = isSelected ? "#FFB703" : "#F8F9FA";
        tCtx.font = isSelected ? "bold 15px 'Share Tech Mono', monospace" : "bold 13px 'Share Tech Mono', monospace";
        tCtx.textAlign = "center";
        tCtx.textBaseline = "middle";
        tCtx.fillText(node.title, 128, 24);

        const textTexture = new THREE.CanvasTexture(textCanvas);
        const textMat = new THREE.SpriteMaterial({
            map: textTexture,
            transparent: true,
            depthWrite: false
        });
        const textSprite = new THREE.Sprite(textMat);
        textSprite.scale.set(28, 6, 1);
        textSprite.position.set(0, -11, 0);
        textSprite.raycast = () => {}; // Text label does not intercept click/hover raycasts
        group.add(textSprite);
        this.threeDisposables.push(textTexture, textMat);

        return group;
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

    createNodeLabelHTML(node) {
        if (!node || !node.title) return "";
        const color = node.color || "#00A896";
        return `
            <div style="background: rgba(15, 23, 42, 0.96); border: 2px solid ${color}; padding: 8px 12px; font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #FFB703; box-shadow: 0 4px 20px rgba(0,0,0,0.95), 0 0 16px ${color}; border-radius: 4px; max-width: 260px; pointer-events: none;">
                <div style="font-weight: bold; font-size: 13px; display: flex; align-items: center; gap: 6px;">${node.icon || '🏛️'} ${node.title}</div>
                <div style="color: #00A896; font-size: 11px; margin-top: 2px;">${node.era || ''}</div>
                <div style="color: #F8F9FA; font-size: 11px; margin-top: 4px; line-height: 1.4;">${node.summary_short || ''}</div>
            </div>
        `;
    }

    renderGraph() {
        const container = document.getElementById(this.containerId);
        if (!window.ForceGraph3D) return;

        this.graph = window.ForceGraph3D()(container)
            .graphData({ nodes: this.nodesData, links: this.cleanLinks() })
            .nodeId("id")
            .nodeThreeObject(node => this.createNodeSprite(node))
            .nodeLabel(() => "")
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
                
                this.threeDisposables.push(lineMat, geometry);
                
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
            });

        // Enable High-DPI Rendering for Retina displays
        this.graph.renderer().setPixelRatio(window.devicePixelRatio || 1);

        this.graph.onNodeClick(node => {
                soundEngine.playNodeFocus();
                this.focusNode(node);
                if (this.onNodeSelect) {
                    this.onNodeSelect(node.title);
                }
            })
            .onNodeHover(node => {
                container.style.cursor = node ? "pointer" : "default";
                const tooltip = document.getElementById("globe-3d-tooltip");
                if (node && tooltip) {
                    const coords = this.graph.graph2ScreenCoords(node.x, node.y, node.z);
                    if (coords && typeof coords.x === 'number') {
                        tooltip.innerHTML = `
                            <div style="font-weight: bold; font-size: 13px; color: #FFB703; display: flex; align-items: center; gap: 6px;">${node.icon || '🏛️'} ${node.title}</div>
                            <div style="color: #00A896; font-size: 11px; margin-top: 2px;">${node.era || ''}</div>
                            <div style="color: #F8F9FA; font-size: 11px; margin-top: 4px; line-height: 1.4;">${node.summary_short || ''}</div>
                        `;
                        tooltip.style.left = `${Math.min(window.innerWidth - 280, Math.max(10, coords.x))}px`;
                        tooltip.style.top = `${Math.min(window.innerHeight - 120, Math.max(70, coords.y))}px`;
                        tooltip.style.borderColor = node.color || '#00A896';
                        tooltip.classList.remove("hidden");
                    }
                } else if (tooltip) {
                    tooltip.classList.add("hidden");
                }
            });

        // Hide tooltip immediately when pointer leaves 3D globe or enters UI panels
        container.addEventListener("mouseleave", () => {
            const tooltip = document.getElementById("globe-3d-tooltip");
            if (tooltip) tooltip.classList.add("hidden");
        });

        ["app-header", "reader-panel", "taskbar", "mindmaze-modal", "add-node-dialog-overlay"].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener("mouseenter", () => {
                    const tooltip = document.getElementById("globe-3d-tooltip");
                    if (tooltip) tooltip.classList.add("hidden");
                }, { passive: true });
            }
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

        // Garbage Collect old Three.js objects before regenerating them
        this.disposeThreeObjects();

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
            this.disposeThreeObjects();
            this.graph.graphData({
                nodes: this.nodesData,
                links: this.cleanLinks()
            });
        }
    }
    
    disposeThreeObjects() {
        if (this.threeDisposables && this.threeDisposables.length > 0) {
            this.threeDisposables.forEach(obj => {
                if (obj && typeof obj.dispose === 'function') {
                    obj.dispose();
                }
            });
            this.threeDisposables = [];
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
