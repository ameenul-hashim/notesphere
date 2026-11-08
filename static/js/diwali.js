/* NoteSphere — Diwali Festival Edition: heavy realistic fireworks (canvas).
 * Transparent canvas so the page background stays visible. Global via base.html.
 */
(function () {
  "use strict";

  var body = document.body;
  if (!body || !body.hasAttribute("data-festival")) return;

  var reduceQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var optedOut = false;
  try { optedOut = window.localStorage.getItem("ns-diwali-motion") === "off"; } catch (e) {}
  var reduced = optedOut || (reduceQuery ? reduceQuery.matches : false);
  if (reduced) body.classList.add("diwali-reduced");

  var greeting = document.querySelector("[data-diwali-greeting]");
  if (greeting) {
    var closed = false;
    var hideGreeting = function () {
      if (closed) return;
      closed = true;
      greeting.classList.add("is-hidden");
      window.setTimeout(function () { if (greeting.parentNode) greeting.parentNode.removeChild(greeting); }, reduced ? 0 : 420);
    };
    var closeBtn = greeting.querySelector("[data-diwali-greeting-close]");
    if (closeBtn) closeBtn.addEventListener("click", hideGreeting);
    window.setTimeout(hideGreeting, 12000);
  }
  if (reduced) return;

  var canvas = document.querySelector("[data-diwali-canvas]");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0;
  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  window.addEventListener("resize", resize);

  var COLORS = ["#ffcf6b","#ff9d3c","#ff5f7e","#b256ff","#7dd3fc","#a3e635","#ffffff","#ffd700","#ff8c00"];
  function pickColor() { return COLORS[Math.floor(Math.random() * COLORS.length)]; }

  var particles = [];
  var rockets = [];

  function Particle(x, y, vx, vy, color, life, size, type) {
    this.x = x; this.y = y; this.vx = vx; this.vy = vy;
    this.color = color; this.life = life; this.maxLife = life;
    this.size = size; this.type = type || "spark";
    this.alpha = 1; this.trail = [];
  }

  function Rocket(x) {
    this.x = x; this.y = H + 10;
    this.vx = (Math.random() - 0.5) * 1.2;
    this.vy = -(9 + Math.random() * 4);
    this.color = pickColor();
    this.trail = [];
    this.exploded = false;
    this.targetY = H * (0.15 + Math.random() * 0.45);
  }

  Rocket.prototype.update = function () {
    this.trail.push({ x: this.x, y: this.y });
    if (this.trail.length > 12) this.trail.shift();
    this.x += this.vx;
    this.y += this.vy;
    this.vy += 0.06;
    if (this.vy >= 0 || this.y <= this.targetY) { this.explode(); this.exploded = true; }
  };

  Rocket.prototype.explode = function () {
    var x = this.x, y = this.y, color = this.color;
    var count = Math.floor(40 + Math.random() * 40);
    var type = Math.random();
    if (type < 0.12) {
      for (var i = 0; i < count; i++) {
        var a = (i / count) * Math.PI * 2;
        var sp = 3 + Math.random() * 2;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp, pickColor(), 60 + Math.random() * 20, 2, "ring"));
      }
    } else if (type < 0.25) {
      for (var i = 0; i < count; i++) {
        var a = Math.random() * Math.PI * 2;
        var sp = Math.random() * 4;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp - 1, Math.random() < 0.5 ? color : pickColor(), 90 + Math.random() * 40, 1.6, "willow"));
      }
    } else if (type < 0.38) {
      for (var i = 0; i < count; i++) {
        var a = (i / count) * Math.PI * 2;
        var sp = 2 + Math.random() * 5;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp, "#ffcf6b", 50 + Math.random() * 20, 2, "palm"));
      }
      for (var t = 0; t < 12; t++) particles.push(new Particle(x, y, (Math.random() - 0.5) * 1.5, 2 + Math.random() * 3, "#ff9d3c", 30, 1.4, "spark"));
    } else if (type < 0.5) {
      for (var i = 0; i < count; i++) {
        var a = Math.random() * Math.PI * 2;
        var b = Math.random() * Math.PI;
        var sp = 1 + Math.random() * 5;
        particles.push(new Particle(x, y, Math.cos(a) * Math.sin(b) * sp, Math.sin(a) * Math.sin(b) * sp, pickColor(), 55 + Math.random() * 25, 1.8, "chrys"));
      }
    } else if (type < 0.62) {
      for (var i = 0; i < count; i++) {
        var a = Math.random() * Math.PI * 2;
        var sp = Math.random() * 6;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp, "#ffd700", 70 + Math.random() * 30, 1.2, "glitter"));
      }
    } else if (type < 0.74) {
      for (var m = 0; m < 3; m++) {
        (function (delay, ox, oy) {
          window.setTimeout(function () {
            var c2 = pickColor();
            for (var i = 0; i < 25; i++) {
              var a = Math.random() * Math.PI * 2;
              var sp = Math.random() * 4;
              particles.push(new Particle(ox + (Math.random() - 0.5) * 20, oy + (Math.random() - 0.5) * 20, Math.cos(a) * sp, Math.sin(a) * sp, c2, 50, 1.6, "spark"));
            }
          }, delay);
        })(m * 120, x + (Math.random() - 0.5) * 40, y + (Math.random() - 0.5) * 40);
      }
    } else if (type < 0.86) {
      for (var i = 0; i < count; i++) {
        var a = Math.random() * Math.PI * 2;
        var sp = 1 + Math.random() * 4.5;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp, pickColor(), 60 + Math.random() * 20, 1.8, "peony"));
      }
    } else {
      for (var i = 0; i < count; i++) {
        var a = Math.random() * Math.PI * 2;
        var sp = Math.random() * 5;
        particles.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp, "#fff8dc", 65, 1.4, "champagne"));
      }
    }
    particles.push(new Particle(x, y, 0, 0, "#ffffff", 12, 6, "flash"));
  };

  Rocket.prototype.draw = function () {
    ctx.beginPath();
    for (var i = 0; i < this.trail.length; i++) {
      var t = this.trail[i];
      if (i === 0) ctx.moveTo(t.x, t.y); else ctx.lineTo(t.x, t.y);
    }
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.7;
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.beginPath();
    ctx.arc(this.x, this.y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;
  };

  function updateParticle(p) {
    p.trail.push({ x: p.x, y: p.y });
    if (p.trail.length > (p.type === "willow" ? 8 : 4)) p.trail.shift();
    p.x += p.vx; p.y += p.vy;
    if (p.type === "willow" || p.type === "palm") p.vy += 0.05;
    else if (p.type !== "flash") p.vy += 0.035;
    p.vx *= 0.985; p.vy *= 0.985;
    p.life--;
    p.alpha = Math.max(0, p.life / p.maxLife);
  }

  function drawParticle(p) {
    var a = p.alpha;
    if (a <= 0) return;
    ctx.globalAlpha = a;
    if (p.type === "flash") {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * (1 - p.life / p.maxLife + 0.5), 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 20;
      ctx.fill();
      ctx.shadowBlur = 0;
    } else {
      if (p.trail.length > 1) {
        ctx.beginPath();
        for (var i = 0; i < p.trail.length; i++) {
          var t = p.trail[i];
          if (i === 0) ctx.moveTo(t.x, t.y); else ctx.lineTo(t.x, t.y);
        }
        ctx.strokeStyle = p.color;
        ctx.lineWidth = p.size * 0.6;
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    ctx.globalAlpha = 1;
  }

  var lastLaunch = 0;
  function scheduleLaunch(now) {
    var interval = 400 + Math.random() * 700;
    if (now - lastLaunch > interval) {
      lastLaunch = now;
      var count = 2 + Math.floor(Math.random() * 3);
      for (var i = 0; i < count; i++) {
        rockets.push(new Rocket(Math.random() * W));
      }
    }
  }

  var running = true;
  var paused = false;
  var lastTime = performance.now();

  function loop(now) {
    if (!running) return;
    if (paused || document.hidden) { lastTime = now; requestAnimationFrame(loop); return; }
    lastTime = now;
    ctx.clearRect(0, 0, W, H);

    for (var i = rockets.length - 1; i >= 0; i--) {
      rockets[i].update();
      rockets[i].draw();
      if (rockets[i].exploded) rockets.splice(i, 1);
    }
    for (var j = particles.length - 1; j >= 0; j--) {
      updateParticle(particles[j]);
      drawParticle(particles[j]);
      if (particles[j].life <= 0) particles.splice(j, 1);
    }
    if (particles.length > 1400) particles.splice(0, particles.length - 1400);

    scheduleLaunch(now);
    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { paused = true; body.classList.add("diwali-paused"); }
    else { paused = false; body.classList.remove("diwali-paused"); lastTime = performance.now(); }
  });

  if (reduceQuery && reduceQuery.addEventListener) {
    reduceQuery.addEventListener("change", function (ev) {
      if (ev.matches) {
        running = false;
        body.classList.add("diwali-reduced");
        particles.length = 0; rockets.length = 0;
        ctx.clearRect(0, 0, W, H);
      }
    });
  }
})();
