/* NoteSphere — Diwali Festival Edition (progressive enhancement only).
 *
 * The decorations are fully usable without this file (pure CSS). This script
 * adds the floating golden particles, occasional fireworks and a richer set of
 * Diwali "cracker" effects (rockets, bombs, sparklers, fountains, chakris),
 * dismisses the one-time greeting, pauses animation work while the tab is
 * hidden and honours prefers-reduced-motion (or an explicit opt-out stored in
 * localStorage).
 */
(function () {
  "use strict";

  var body = document.body;
  if (!body || !body.hasAttribute("data-festival")) return;

  var reduceQuery = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;

  var optedOut = false;
  try {
    optedOut = window.localStorage.getItem("ns-diwali-motion") === "off";
  } catch (e) {
    optedOut = false;
  }

  var reduced = optedOut || (reduceQuery ? reduceQuery.matches : false);
  if (reduced) body.classList.add("diwali-reduced");

  /* ---------- One-time greeting (dismiss / auto-hide) ---------- */
  var greeting = document.querySelector("[data-diwali-greeting]");
  if (greeting) {
    var closed = false;
    var hideGreeting = function () {
      if (closed) return;
      closed = true;
      greeting.classList.add("is-hidden");
      window.setTimeout(function () {
        if (greeting.parentNode) greeting.parentNode.removeChild(greeting);
      }, reduced ? 0 : 420);
    };
    var closeBtn = greeting.querySelector("[data-diwali-greeting-close]");
    if (closeBtn) closeBtn.addEventListener("click", hideGreeting);
    window.setTimeout(hideGreeting, 12000);
  }

  if (reduced) return;

  var COLORS = ["#ffcf6b", "#ff9d3c", "#ff5f7e", "#b256ff", "#7dd3fc", "#a3e635", "#ffffff"];

  function pickColor() {
    return COLORS[Math.floor(Math.random() * COLORS.length)];
  }

  /* ---------- Floating golden particles ---------- */
  var particlesEl = document.querySelector("[data-diwali-particles]");
  if (particlesEl) {
    var count = window.innerWidth < 640 ? 12 : window.innerWidth < 1100 ? 20 : 30;
    var frag = document.createDocumentFragment();
    for (var i = 0; i < count; i++) {
      var p = document.createElement("span");
      var size = 2 + Math.random() * 4;
      p.className = "diwali-particle";
      p.style.left = Math.random() * 100 + "%";
      p.style.width = size + "px";
      p.style.height = size + "px";
      p.style.animationDuration = 9 + Math.random() * 10 + "s";
      p.style.animationDelay = -Math.random() * 12 + "s";
      p.style.opacity = (0.35 + Math.random() * 0.5).toFixed(2);
      frag.appendChild(p);
    }
    particlesEl.appendChild(frag);
  }

  /* ---------- Occasional lightweight fireworks ---------- */
  var fireworksEl = document.querySelector("[data-diwali-fireworks]");
  var fireTimer = null;

  function burst(x, y, dots, radius, color) {
    if (!fireworksEl || document.hidden) return;
    var burstEl = document.createElement("span");
    burstEl.className = "diwali-firework";
    burstEl.style.left = x + "%";
    burstEl.style.top = y + "%";

    var n = dots || (8 + Math.floor(Math.random() * 5));
    var r = radius || (18 + Math.random() * 30);
    var c = color || pickColor();
    var dotFrag = document.createDocumentFragment();
    for (var j = 0; j < n; j++) {
      var dot = document.createElement("span");
      var angle = (j / n) * Math.PI * 2 + Math.random() * 0.3;
      var dist = r * (0.7 + Math.random() * 0.6);
      dot.className = "diwali-firework-dot";
      dot.style.setProperty("--dx", (Math.cos(angle) * dist).toFixed(1) + "px");
      dot.style.setProperty("--dy", (Math.sin(angle) * dist).toFixed(1) + "px");
      dot.style.background = "radial-gradient(circle, #fff, " + c + " 55%, rgba(255,159,60,0) 72%)";
      dot.style.boxShadow = "0 0 8px 1px " + c;
      dot.style.animationDelay = (Math.random() * 0.12).toFixed(2) + "s";
      dotFrag.appendChild(dot);
    }
    burstEl.appendChild(dotFrag);
    fireworksEl.appendChild(burstEl);

    window.setTimeout(function () {
      if (burstEl.parentNode) burstEl.parentNode.removeChild(burstEl);
    }, 1700);
  }

  function scheduleBurst() {
    window.clearTimeout(fireTimer);
    if (document.hidden) return;
    fireTimer = window.setTimeout(function () {
      burst(10 + Math.random() * 80, 8 + Math.random() * 55);
      scheduleBurst();
    }, 4000 + Math.random() * 5000);
  }
  scheduleBurst();

  /* ---------- Crackers layer (rockets, bombs, sparklers, fountains, chakris) ---------- */
  var crackersEl = document.querySelector("[data-diwali-crackers]");

  function rocket() {
    if (!crackersEl || document.hidden) return;
    var r = document.createElement("span");
    r.className = "diwali-rocket";
    var startX = 8 + Math.random() * 84;
    r.style.left = startX + "%";
    var color = pickColor();
    r.style.setProperty("--rc", color);
    var trail = document.createElement("span");
    trail.className = "diwali-rocket-trail";
    r.appendChild(trail);
    var head = document.createElement("span");
    head.className = "diwali-rocket-head";
    head.style.background = color;
    head.style.boxShadow = "0 0 12px 3px " + color;
    r.appendChild(head);
    crackersEl.appendChild(r);

    var apexY = 8 + Math.random() * 30;
    var duration = 1200 + Math.random() * 600;
    // animate via JS for control
    var start = performance.now();
    var startY = 20;
    var endY = window.innerHeight * (apexY / 100 - 1);
    function step(now) {
      var t = Math.min(1, (now - start) / duration);
      var ease = 1 - Math.pow(1 - t, 3);
      var y = startY + (endY - startY) * ease;
      r.style.transform = "translateY(" + y + "px)";
      if (t < 1) {
        requestAnimationFrame(step);
      } else {
        // burst at apex
        burst(startX, apexY, 14 + Math.floor(Math.random() * 8), 30 + Math.random() * 30, color);
        // secondary smaller bursts
        window.setTimeout(function () {
          burst(startX + (Math.random() * 10 - 5), apexY + (Math.random() * 8 - 4), 8, 18, pickColor());
        }, 120);
        if (r.parentNode) r.parentNode.removeChild(r);
      }
    }
    requestAnimationFrame(step);
  }

  function bomb() {
    if (!crackersEl || document.hidden) return;
    var x = 15 + Math.random() * 70;
    var y = 12 + Math.random() * 40;
    var color = pickColor();
    // shockwave ring
    var ring = document.createElement("span");
    ring.className = "diwali-shockwave";
    ring.style.left = x + "%";
    ring.style.top = y + "%";
    ring.style.borderColor = color;
    crackersEl.appendChild(ring);
    window.setTimeout(function () {
      if (ring.parentNode) ring.parentNode.removeChild(ring);
    }, 900);
    // big burst
    burst(x, y, 22 + Math.floor(Math.random() * 10), 45 + Math.random() * 30, color);
    // extra colored bursts
    for (var i = 0; i < 3; i++) {
      (function (delay) {
        window.setTimeout(function () {
          burst(x + (Math.random() * 12 - 6), y + (Math.random() * 12 - 6), 10, 22, pickColor());
        }, delay);
      })(150 + i * 120);
    }
  }

  function sparkler() {
    if (!crackersEl || document.hidden) return;
    var s = document.createElement("span");
    s.className = "diwali-sparkler";
    var x = 5 + Math.random() * 90;
    var y = 60 + Math.random() * 30;
    s.style.left = x + "%";
    s.style.top = y + "%";
    var color = pickColor();
    s.style.setProperty("--sc", color);
    crackersEl.appendChild(s);
    // emit sparks
    var sparks = 18 + Math.floor(Math.random() * 12);
    for (var i = 0; i < sparks; i++) {
      (function (i) {
        window.setTimeout(function () {
          if (!s.parentNode) return;
          var sp = document.createElement("span");
          sp.className = "diwali-spark";
          var ang = Math.random() * Math.PI * 2;
          var dist = 20 + Math.random() * 40;
          sp.style.setProperty("--sx", (Math.cos(ang) * dist).toFixed(1) + "px");
          sp.style.setProperty("--sy", (Math.sin(ang) * dist).toFixed(1) + "px");
          sp.style.background = pickColor();
          s.appendChild(sp);
          window.setTimeout(function () {
            if (sp.parentNode) sp.parentNode.removeChild(sp);
          }, 700);
        }, i * 60);
      })(i);
    }
    window.setTimeout(function () {
      if (s.parentNode) s.parentNode.removeChild(s);
    }, sparks * 60 + 800);
  }

  function fountain() {
    if (!crackersEl || document.hidden) return;
    var f = document.createElement("span");
    f.className = "diwali-fountain";
    var x = 10 + Math.random() * 80;
    f.style.left = x + "%";
    var color = pickColor();
    f.style.setProperty("--fc", color);
    crackersEl.appendChild(f);
    var count = 24 + Math.floor(Math.random() * 16);
    for (var i = 0; i < count; i++) {
      (function (i) {
        window.setTimeout(function () {
          if (!f.parentNode) return;
          var sp = document.createElement("span");
          sp.className = "diwali-fountain-spark";
          var ang = -Math.PI / 2 + (Math.random() - 0.5) * 1.1;
          var dist = 60 + Math.random() * 90;
          sp.style.setProperty("--fx", (Math.cos(ang) * dist).toFixed(1) + "px");
          sp.style.setProperty("--fy", (Math.sin(ang) * dist).toFixed(1) + "px");
          sp.style.background = Math.random() < 0.5 ? color : pickColor();
          f.appendChild(sp);
          window.setTimeout(function () {
            if (sp.parentNode) sp.parentNode.removeChild(sp);
          }, 900);
        }, i * 40);
      })(i);
    }
    window.setTimeout(function () {
      if (f.parentNode) f.parentNode.removeChild(f);
    }, count * 40 + 1000);
  }

  function chakri() {
    if (!crackersEl || document.hidden) return;
    var c = document.createElement("span");
    c.className = "diwali-chakri";
    var x = 15 + Math.random() * 70;
    var y = 30 + Math.random() * 40;
    c.style.left = x + "%";
    c.style.top = y + "%";
    var color = pickColor();
    c.style.setProperty("--cc", color);
    crackersEl.appendChild(c);
    // sparks around ring
    var n = 16;
    for (var i = 0; i < n; i++) {
      var sp = document.createElement("span");
      sp.className = "diwali-chakri-spark";
      var ang = (i / n) * Math.PI * 2;
      var r = 34;
      sp.style.setProperty("--cx", (Math.cos(ang) * r).toFixed(1) + "px");
      sp.style.setProperty("--cy", (Math.sin(ang) * r).toFixed(1) + "px");
      sp.style.background = i % 2 === 0 ? color : pickColor();
      sp.style.animationDelay = (i * 0.05).toFixed(2) + "s";
      c.appendChild(sp);
    }
    window.setTimeout(function () {
      if (c.parentNode) c.parentNode.removeChild(c);
    }, 2200);
  }

  var crackerFns = [rocket, bomb, sparkler, fountain, chakri, function () { burst(10 + Math.random() * 80, 8 + Math.random() * 55); }];

  function scheduleCracker() {
    window.clearTimeout(crackerTimer);
    if (document.hidden) return;
    crackerTimer = window.setTimeout(function () {
      var fn = crackerFns[Math.floor(Math.random() * crackerFns.length)];
      try { fn(); } catch (e) {}
      scheduleCracker();
    }, 1800 + Math.random() * 2600);
  }
  var crackerTimer = null;
  scheduleCracker();

  // initial burst of crackers on load
  window.setTimeout(function () {
    rocket();
    window.setTimeout(fountain, 400);
    window.setTimeout(sparkler, 900);
  }, 600);

  /* ---------- Pause work while the tab is hidden ---------- */
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      body.classList.add("diwali-paused");
      window.clearTimeout(fireTimer);
      fireTimer = null;
      window.clearTimeout(crackerTimer);
      crackerTimer = null;
    } else {
      body.classList.remove("diwali-paused");
      if (!fireTimer) scheduleBurst();
      if (!crackerTimer) scheduleCracker();
    }
  });

  /* ---------- React to live reduced-motion changes ---------- */
  if (reduceQuery && reduceQuery.addEventListener) {
    reduceQuery.addEventListener("change", function (ev) {
      if (ev.matches) {
        body.classList.add("diwali-reduced");
        window.clearTimeout(fireTimer);
        fireTimer = null;
        window.clearTimeout(crackerTimer);
        crackerTimer = null;
        if (particlesEl) particlesEl.innerHTML = "";
        if (crackersEl) crackersEl.innerHTML = "";
        if (fireworksEl) fireworksEl.innerHTML = "";
      } else if (!optedOut) {
        body.classList.remove("diwali-reduced");
        if (!fireTimer) scheduleBurst();
        if (!crackerTimer) scheduleCracker();
      }
    });
  }
})();
