/* ═══════════════════════════════════════════════════════════
   LearnSphere – Interactive Particle System
   Floating particles that react to mouse cursor movement.
   Inspired by Antigravity-style interactive background.
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const canvas = document.createElement('canvas');
    canvas.id = 'particle-canvas';
    canvas.style.cssText = `
        position: fixed;
        inset: 0;
        width: 100%;
        height: 100%;
        z-index: 0;
        pointer-events: none;
    `;
    document.body.prepend(canvas);

    const ctx = canvas.getContext('2d');
    let W, H;
    let mouse = { x: -9999, y: -9999 };
    let particles = [];

    /* ── Config ── */
    const CFG = {
        count: 200,
        minR: 1.5,
        maxR: 3.5,
        speed: 0.35,
        linkDist: 160,
        linkAlpha: 0.25,
        mouseRadius: 180,
        mouseForce: 0.06,
        colors: [
            '#e0c3fc',   // soft lavender
            '#8ec5fc',   // sky blue
            '#c4b5fd',   // violet
            '#67e8f9',   // cyan
            '#a5f3fc',   // light cyan
            '#f0abfc',   // pink-violet
        ],
        lineColor: [244, 114, 182],  // rose-pink rgb for lines
    };

    /* ── Resize ── */
    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    /* ── Particle class ── */
    class Particle {
        constructor() {
            this.x = Math.random() * W;
            this.y = Math.random() * H;
            this.r = CFG.minR + Math.random() * (CFG.maxR - CFG.minR);
            this.vx = (Math.random() - 0.5) * CFG.speed * 2;
            this.vy = (Math.random() - 0.5) * CFG.speed * 2;
            this.color = CFG.colors[Math.floor(Math.random() * CFG.colors.length)];
            this.baseAlpha = 0.4 + Math.random() * 0.5;
            this.alpha = this.baseAlpha;
        }

        update() {
            // Mouse interaction – push away
            const dx = this.x - mouse.x;
            const dy = this.y - mouse.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < CFG.mouseRadius && dist > 0) {
                const force = (1 - dist / CFG.mouseRadius) * CFG.mouseForce;
                this.vx += (dx / dist) * force;
                this.vy += (dy / dist) * force;
                // Glow effect near cursor
                this.alpha = Math.min(1, this.baseAlpha + (1 - dist / CFG.mouseRadius) * 0.6);
            } else {
                this.alpha += (this.baseAlpha - this.alpha) * 0.05;
            }

            // Friction
            this.vx *= 0.99;
            this.vy *= 0.99;

            // Move
            this.x += this.vx;
            this.y += this.vy;

            // Wrap edges
            if (this.x < -20) this.x = W + 20;
            if (this.x > W + 20) this.x = -20;
            if (this.y < -20) this.y = H + 20;
            if (this.y > H + 20) this.y = -20;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.globalAlpha = this.alpha;
            ctx.fill();
            ctx.globalAlpha = 1;
        }
    }

    /* ── Create particles ── */
    function init() {
        resize();
        particles = [];
        for (let i = 0; i < CFG.count; i++) {
            particles.push(new Particle());
        }
    }

    /* ── Draw connecting lines ── */
    function drawLinks() {
        const [lr, lg, lb] = CFG.lineColor;
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < CFG.linkDist) {
                    const alpha = (1 - dist / CFG.linkDist) * CFG.linkAlpha;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(${lr},${lg},${lb},${alpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }

        // Lines from cursor to nearby particles
        for (let i = 0; i < particles.length; i++) {
            const dx = particles[i].x - mouse.x;
            const dy = particles[i].y - mouse.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < CFG.mouseRadius) {
                const alpha = (1 - dist / CFG.mouseRadius) * 0.35;
                ctx.beginPath();
                ctx.moveTo(mouse.x, mouse.y);
                ctx.lineTo(particles[i].x, particles[i].y);
                ctx.strokeStyle = `rgba(${lr},${lg},${lb},${alpha})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    }

    /* ── Animation loop ── */
    function animate() {
        ctx.clearRect(0, 0, W, H);

        for (const p of particles) {
            p.update();
            p.draw();
        }

        drawLinks();
        requestAnimationFrame(animate);
    }

    /* ── Mouse tracking (on body, not canvas) ── */
    document.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    document.addEventListener('mouseleave', () => {
        mouse.x = -9999;
        mouse.y = -9999;
    });

    // Touch support
    document.addEventListener('touchmove', (e) => {
        if (e.touches.length > 0) {
            mouse.x = e.touches[0].clientX;
            mouse.y = e.touches[0].clientY;
        }
    }, { passive: true });

    document.addEventListener('touchend', () => {
        mouse.x = -9999;
        mouse.y = -9999;
    });

    /* ── Start ── */
    window.addEventListener('resize', () => {
        resize();
        // Re-create particles on large resize to avoid empty areas
        if (particles.length < CFG.count * 0.8) {
            init();
        }
    });

    init();
    animate();
})();
