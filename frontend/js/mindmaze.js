import { soundEngine } from "./audio.js";
import { makeDraggable, bringToFront } from "./wiki_window.js";

/**
 * MindMaze Trivia Dungeon Canvas 2D Game Engine (Enhanced Bottleneck Maze Edition)
 */

class MindMazeGame {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.gridWidth = 15;
        this.gridHeight = 11;
        this.tileSize = 36;
        
        // Player state with lerped render position
        this.player = { x: 1, y: 1, renderX: 1, renderY: 1, dir: "down" };
        this.score = 0;
        this.doorsUnlocked = 0;
        this.totalDoors = 5;

        this.questions = [];
        this.currentDoorQuestionIndex = 0;
        this.pendingDoorTile = null;
        this.activeArticleTopic = "Microsoft Encarta";

        // Canvas Victory Particles System
        this.particles = [];
        this.isVictory = false;

        // Bottleneck Sequential Maze Layout (0: Floor, 1: Wall, 2: Door, 3: Goal)
        // All paths to Goal at (13, 9) strictly require unlocking sequential doors!
        this.map = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1],
            [1, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1],
            [1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1, 2, 1, 0, 0, 0, 1, 0, 1],
            [1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 2, 0, 1],
            [1, 0, 1, 0, 1, 1, 1, 2, 1, 1, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 3, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        ];

        this.initialMapState = JSON.parse(JSON.stringify(this.map));
    }

    init() {
        this.canvas = document.getElementById("mindmaze-canvas");
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext("2d");

        this.canvas.width = this.gridWidth * this.tileSize;
        this.canvas.height = this.gridHeight * this.tileSize;

        window.addEventListener("keydown", (e) => this.handleKeyDown(e));

        const windowModal = document.getElementById("mindmaze-modal");
        if (windowModal) {
            makeDraggable(windowModal);
            windowModal.addEventListener("mousedown", () => bringToFront(windowModal));
        }

        this.countTotalDoors();
        this.startLoop();
    }

    countTotalDoors() {
        let count = 0;
        for (let r = 0; r < this.gridHeight; r++) {
            for (let c = 0; c < this.gridWidth; c++) {
                if (this.map[r][c] === 2) count++;
            }
        }
        this.totalDoors = count > 0 ? count : 5;
    }

    setQuestions(questions, topicName) {
        if (questions && questions.length > 0) {
            this.questions = questions;
        } else {
            this.questions = [
                {
                    question: `What key discovery defined ${topicName}?`,
                    options: ["Empirical Observation", "Alchemy", "Mythology", "Pure Chance"],
                    correct_index: 0,
                    hint: "Scientific and historical inquiry relies on empirical evidence."
                }
            ];
        }
        this.activeArticleTopic = topicName || "Current Topic";
        this.resetGame();
    }

    resetGame() {
        this.player = { x: 1, y: 1, renderX: 1, renderY: 1, dir: "down" };
        this.score = 0;
        this.doorsUnlocked = 0;
        this.currentDoorQuestionIndex = 0;
        this.particles = [];
        this.isVictory = false;
        this.map = JSON.parse(JSON.stringify(this.initialMapState));
        this.countTotalDoors();
        this.updateHUD();
    }

    handleKeyDown(e) {
        const modal = document.getElementById("mindmaze-modal");
        const overlay = document.getElementById("mindmaze-trivia-overlay");
        if (!modal || modal.classList.contains("hidden")) return;
        if (overlay && !overlay.classList.contains("hidden")) return;

        let dx = 0;
        let dy = 0;

        if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {
            dy = -1;
            this.player.dir = "up";
        } else if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {
            dy = 1;
            this.player.dir = "down";
        } else if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") {
            dx = -1;
            this.player.dir = "left";
        } else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") {
            dx = 1;
            this.player.dir = "right";
        } else {
            return;
        }

        e.preventDefault();
        this.movePlayer(dx, dy);
    }

    movePlayer(dx, dy) {
        const nextX = this.player.x + dx;
        const nextY = this.player.y + dy;

        const tile = this.map[nextY][nextX];

        if (tile === 1) {
            soundEngine.playClick();
            return;
        }

        if (tile === 2) {
            this.pendingDoorTile = { x: nextX, y: nextY };
            this.triggerDoorTrivia();
            return;
        }

        if (tile === 3) {
            // Goal Reached! Trigger Victory Celebration!
            this.player.x = nextX;
            this.player.y = nextY;
            this.triggerVictoryCelebration();
            return;
        }

        this.player.x = nextX;
        this.player.y = nextY;
        soundEngine.playClick();
    }

    triggerDoorTrivia() {
        soundEngine.playWindowOpen();
        const overlay = document.getElementById("mindmaze-trivia-overlay");
        const questionText = document.getElementById("trivia-question-text");
        const optionsGrid = document.getElementById("trivia-options-grid");
        const hintBox = document.getElementById("trivia-hint-box");
        const topicHeader = document.getElementById("trivia-topic-header");

        if (!overlay || !questionText || !optionsGrid) return;

        overlay.classList.remove("hidden");
        hintBox.classList.add("hidden");

        const q = this.questions[this.currentDoorQuestionIndex % this.questions.length];
        
        const isTrueFalse = q.options.length === 2 && (q.options[0] === "True" || q.options[0] === "False");
        topicHeader.textContent = isTrueFalse
            ? `⚡ Speed Challenge: ${this.activeArticleTopic}`
            : `🚪 Castle Door Trivia (${this.doorsUnlocked + 1}/${this.totalDoors}): ${this.activeArticleTopic}`;

        questionText.textContent = q.question;

        optionsGrid.innerHTML = "";
        q.options.forEach((optText, idx) => {
            const btn = document.createElement("button");
            btn.className = "trivia-option-btn win95-outset";
            btn.textContent = `${String.fromCharCode(65 + idx)}) ${optText}`;
            btn.onclick = () => this.checkTriviaAnswer(idx, q);
            optionsGrid.appendChild(btn);
        });
    }

    checkTriviaAnswer(selectedIndex, q) {
        const hintBox = document.getElementById("trivia-hint-box");

        if (selectedIndex === q.correct_index) {
            soundEngine.playDoorFanfare();
            this.score += 150;
            this.doorsUnlocked += 1;

            if (this.pendingDoorTile) {
                this.spawnParticleBurst(
                    this.pendingDoorTile.x * this.tileSize + 18,
                    this.pendingDoorTile.y * this.tileSize + 18,
                    25
                );
                this.map[this.pendingDoorTile.y][this.pendingDoorTile.x] = 0;
            }

            this.currentDoorQuestionIndex++;
            document.getElementById("mindmaze-trivia-overlay").classList.add("hidden");
            this.updateHUD();
        } else {
            soundEngine.playBuzzer();
            hintBox.textContent = `💡 Hint: ${q.hint}`;
            hintBox.classList.remove("hidden");
        }
    }

    triggerVictoryCelebration() {
        this.isVictory = true;
        soundEngine.playVictoryBurst();

        for (let i = 0; i < 120; i++) {
            this.particles.push({
                x: this.canvas.width / 2,
                y: this.canvas.height / 2,
                vx: (Math.random() - 0.5) * 12,
                vy: (Math.random() - 0.5) * 12,
                color: ["#FFB703", "#00A896", "#38BDF8", "#F43F5E", "#FFFFFF"][Math.floor(Math.random() * 5)],
                alpha: 1.0,
                size: Math.random() * 6 + 3
            });
        }
    }

    spawnParticleBurst(cx, cy, count = 20) {
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: cx,
                y: cy,
                vx: (Math.random() - 0.5) * 6,
                vy: (Math.random() - 0.5) * 6,
                color: ["#FFB703", "#00A896", "#FFE082"][Math.floor(Math.random() * 3)],
                alpha: 1.0,
                size: Math.random() * 4 + 2
            });
        }
    }

    updateHUD() {
        const hudScore = document.getElementById("mm-score");
        const hudDoors = document.getElementById("mm-doors");
        const hudTopic = document.getElementById("mm-topic");

        if (hudScore) hudScore.textContent = `SCORE: ${this.score}`;
        if (hudDoors) hudDoors.textContent = `DOORS UNLOCKED: ${this.doorsUnlocked}/${this.totalDoors}`;
        if (hudTopic) hudTopic.textContent = `TOPIC: ${this.activeArticleTopic}`;
    }

    startLoop() {
        const loop = () => {
            this.update();
            this.render();
            requestAnimationFrame(loop);
        };
        loop();
    }

    update() {
        this.player.renderX += (this.player.x - this.player.renderX) * 0.3;
        this.player.renderY += (this.player.y - this.player.renderY) * 0.3;

        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.alpha -= 0.02;
            if (p.alpha <= 0) {
                this.particles.splice(i, 1);
            }
        }
    }

    render() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw Dungeon Map Grid
        for (let r = 0; r < this.gridHeight; r++) {
            for (let c = 0; c < this.gridWidth; c++) {
                const tile = this.map[r][c];
                const px = c * this.tileSize;
                const py = r * this.tileSize;

                if (tile === 1) {
                    // Wall Tile (Bevel Stone)
                    this.ctx.fillStyle = "#1E293B";
                    this.ctx.fillRect(px, py, this.tileSize, this.tileSize);
                    this.ctx.strokeStyle = "#475569";
                    this.ctx.strokeRect(px + 2, py + 2, this.tileSize - 4, this.tileSize - 4);
                } else if (tile === 0) {
                    // Floor Tile
                    this.ctx.fillStyle = "#0F172A";
                    this.ctx.fillRect(px, py, this.tileSize, this.tileSize);
                    this.ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
                    this.ctx.strokeRect(px, py, this.tileSize, this.tileSize);
                } else if (tile === 2) {
                    // Locked Door Tile
                    this.ctx.fillStyle = "#78350F";
                    this.ctx.fillRect(px, py, this.tileSize, this.tileSize);
                    this.ctx.fillStyle = "#FFB703";
                    this.ctx.font = "bold 16px monospace";
                    this.ctx.fillText("🚪", px + 8, py + 24);
                } else if (tile === 3) {
                    // Goal Chest
                    this.ctx.fillStyle = "#028090";
                    this.ctx.fillRect(px, py, this.tileSize, this.tileSize);
                    this.ctx.font = "bold 18px monospace";
                    this.ctx.fillText("🏆", px + 8, py + 24);
                }
            }
        }

        // Draw Lerped Pixel Knight Sprite
        const kx = this.player.renderX * this.tileSize;
        const ky = this.player.renderY * this.tileSize;

        this.ctx.fillStyle = "#00A896";
        this.ctx.beginPath();
        this.ctx.arc(kx + this.tileSize / 2, ky + this.tileSize / 2, this.tileSize / 2 - 4, 0, Math.PI * 2);
        this.ctx.fill();

        this.ctx.fillStyle = "#FFB703";
        this.ctx.font = "bold 14px monospace";
        this.ctx.fillText("🛡️", kx + 7, ky + 24);

        // Draw Canvas Particles
        this.particles.forEach(p => {
            this.ctx.save();
            this.ctx.globalAlpha = Math.max(0, p.alpha);
            this.ctx.fillStyle = p.color;
            this.ctx.fillRect(p.x, p.y, p.size, p.size);
            this.ctx.restore();
        });

        // Draw Victory Banner Overlay
        if (this.isVictory) {
            this.ctx.fillStyle = "rgba(2, 6, 23, 0.85)";
            this.ctx.fillRect(40, this.canvas.height / 2 - 40, this.canvas.width - 80, 80);
            this.ctx.strokeStyle = "#FFB703";
            this.ctx.lineWidth = 3;
            this.ctx.strokeRect(42, this.canvas.height / 2 - 38, this.canvas.width - 84, 76);

            this.ctx.fillStyle = "#FFB703";
            this.ctx.font = "bold 16px 'Press Start 2P', monospace";
            this.ctx.textAlign = "center";
            this.ctx.fillText("🏆 DUNGEON CLEARED! 🏆", this.canvas.width / 2, this.canvas.height / 2);

            this.ctx.fillStyle = "#00A896";
            this.ctx.font = "12px 'Share Tech Mono', monospace";
            this.ctx.fillText(`Score: ${this.score} pts | Topic: ${this.activeArticleTopic}`, this.canvas.width / 2, this.canvas.height / 2 + 22);
        }
    }
}

export const mindmaze = new MindMazeGame();

export function openMindMazeModal() {
    soundEngine.playWindowOpen();
    const modal = document.getElementById("mindmaze-modal");
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("window-animate-open");
        bringToFront(modal);
        mindmaze.init();
    }
}

export function closeMindMazeModal() {
    soundEngine.playWindowClose();
    const modal = document.getElementById("mindmaze-modal");
    if (modal) {
        modal.classList.add("hidden");
    }
}
