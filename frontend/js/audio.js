/**
 * Encarta 2.0 Native WebAudio API Synthesizer Engine
 * Zero external audio file dependencies. Synthesizes retro 90s sound effects on-the-fly.
 */

class RetroAudioEngine {
    constructor() {
        this.ctx = null;
        // Default to unmuted with rich 0.8 volume
        this.isMuted = localStorage.getItem("encarta_muted") === "true";
        const savedVol = localStorage.getItem("encarta_volume");
        this.masterVolume = savedVol !== null ? parseFloat(savedVol) : 0.8;
    }

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                this.ctx = new AudioCtx();
            }
        }
        if (this.ctx && this.ctx.state === "suspended") {
            this.ctx.resume();
        }
        return this.ctx;
    }

    setVolume(val) {
        this.masterVolume = Math.max(0, Math.min(1, parseFloat(val)));
        localStorage.setItem("encarta_volume", this.masterVolume.toString());
        if (this.isMuted && this.masterVolume > 0) {
            this.isMuted = false;
            localStorage.setItem("encarta_muted", "false");
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        localStorage.setItem("encarta_muted", this.isMuted.toString());
        if (!this.isMuted) {
            this.init();
        }
        return this.isMuted;
    }

    createGainNode(volume = 0.3) {
        this.init();
        if (!this.ctx) return null;
        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(volume * this.masterVolume, this.ctx.currentTime);
        return gain;
    }

    playClick() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.createGainNode(0.28);
        if (!gain) return;

        osc.type = "square";
        osc.frequency.setValueAtTime(900, now);
        osc.frequency.exponentialRampToValueAtTime(300, now + 0.05);

        gain.gain.setValueAtTime(0.28 * this.masterVolume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.05);
    }

    playStartupChime() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const notes = [261.63, 329.63, 392.00, 523.25, 659.25]; // C4, E4, G4, C5, E5
        const now = this.ctx.currentTime;

        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.createGainNode(0.18);
            if (!gain) return;

            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);

            gain.gain.setValueAtTime(0, now + idx * 0.08);
            gain.gain.linearRampToValueAtTime(0.18 * this.masterVolume, now + idx * 0.08 + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 1.2);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 1.3);
        });
    }

    playNodeBirthChime() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const notes = [523.25, 783.99, 1046.50]; // C5, G5, C6
        const now = this.ctx.currentTime;

        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.createGainNode(0.15);
            if (!gain) return;

            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.06);

            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.06 + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + idx * 0.06);
            osc.stop(now + idx * 0.06 + 0.35);
        });
    }

    playNodeFocus() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.createGainNode(0.15);
        if (!gain) return;
        const now = this.ctx.currentTime;

        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);

        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.18);
    }

    playDoorFanfare() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
        const now = this.ctx.currentTime;

        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.createGainNode(0.2);
            if (!gain) return;

            osc.type = "triangle";
            osc.frequency.setValueAtTime(freq, now + idx * 0.07);

            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.07 + 0.4);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + idx * 0.07);
            osc.stop(now + idx * 0.07 + 0.45);
        });
    }

    playVictoryBurst() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const notes = [523.25, 659.25, 783.99, 987.77, 1046.50, 1318.51]; // C, E, G, B, C, E
        const now = this.ctx.currentTime;

        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.createGainNode(0.25);
            if (!gain) return;

            osc.type = "square";
            osc.frequency.setValueAtTime(freq, now + idx * 0.05);

            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.05 + 0.5);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + idx * 0.05);
            osc.stop(now + idx * 0.05 + 0.55);
        });
    }

    playBuzzer() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.createGainNode(0.2);
        if (!gain) return;
        const now = this.ctx.currentTime;

        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.setValueAtTime(110, now + 0.1);

        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.3);
    }

    playWindowOpen() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.createGainNode(0.12);
        if (!gain) return;
        const now = this.ctx.currentTime;

        osc.type = "sine";
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.exponentialRampToValueAtTime(600, now + 0.1);

        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.12);
    }

    playWindowClose() {
        if (this.isMuted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.createGainNode(0.12);
        if (!gain) return;
        const now = this.ctx.currentTime;

        osc.type = "sine";
        osc.frequency.setValueAtTime(600, now);
        osc.frequency.exponentialRampToValueAtTime(250, now + 0.1);

        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.12);
    }
}

export const soundEngine = new RetroAudioEngine();
