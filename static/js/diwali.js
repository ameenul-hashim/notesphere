/* NoteSphere — Diwali Festival Edition (progressive enhancement only).
 *
 * The decorations are fully usable without this file (pure CSS). This script
 * adds the floating golden particles and occasional fireworks, dismisses the
 * one-time greeting, pauses animation work while the tab is hidden and honours
 * prefers-reduced-motion (or an explicit opt-out stored in localStorage).
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

  /* ---------- Floating golden particles ---------- */
  var particlesEl = document.querySelector("[data-diwali-particles]");
  if (particlesEl) {
    var count = window.innerWidth < 640 ? 8 : window.innerWidth < 1100 ? 12 : 18;
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

  function burst() {
    if (!fireworksEl || document.hidden) return;
    var burstEl = document.createElement("span");
    burstEl.className = "diwali-firework";
    burstEl.style.left = 10 + Math.random() * 80 + "%";
    burstEl.style.top = 8 + Math.random() * 55 + "%";

    var dots = 8 + Math.floor(Math.random() * 5);
    var dotFrag = document.createDocumentFragment();
    for (var j = 0; j < dots; j++) {
      var dot = document.createElement("span");
      var angle = (j / dots) * Math.PI * 2;
      var dist = 18 + Math.random() * 30;
      dot.className = "diwali-firework-dot";
      dot.style.setProperty("--dx", (Math.cos(angle) * dist).toFixed(1) + "px");
      dot.style.setProperty("--dy", (Math.sin(angle) * dist).toFixed(1) + "px");
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
      burst();
      scheduleBurst();
    }, 6000 + Math.random() * 7000);
  }
  scheduleBurst();

  /* ---------- Pause work while the tab is hidden ---------- */
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      body.classList.add("diwali-paused");
      window.clearTimeout(fireTimer);
      fireTimer = null;
    } else {
      body.classList.remove("diwali-paused");
      if (!fireTimer) scheduleBurst();
    }
  });

  /* ---------- React to live reduced-motion changes ---------- */
  if (reduceQuery && reduceQuery.addEventListener) {
    reduceQuery.addEventListener("change", function (ev) {
      if (ev.matches) {
        body.classList.add("diwali-reduced");
        window.clearTimeout(fireTimer);
        fireTimer = null;
        if (particlesEl) particlesEl.innerHTML = "";
      } else if (!optedOut) {
        body.classList.remove("diwali-reduced");
        if (!fireTimer) scheduleBurst();
      }
    });
  }
})();
