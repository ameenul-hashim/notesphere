(function () {
  "use strict";

  var STORAGE_KEY = "ns-theme";

  var THEMES = [
    { value: "classic_white", label: "Classic White", bg: "#f6f6f7", surface: "#ffffff", sidebar: "#ffffff", primary: "#6366f1", text: "#18181b" },
    { value: "midnight_black", label: "Midnight Black", bg: "#09090b", surface: "#131316", sidebar: "#0e0e11", primary: "#818cf8", text: "#fafafa" },
    { value: "ocean_blue", label: "Ocean Blue", bg: "#f2f6fa", surface: "#ffffff", sidebar: "#ffffff", primary: "#0284c7", text: "#0f1b2d" },
    { value: "emerald_green", label: "Emerald Green", bg: "#f3f9f6", surface: "#ffffff", sidebar: "#ffffff", primary: "#059669", text: "#0e1f17" },
    { value: "royal_purple", label: "Royal Purple", bg: "#14111f", surface: "#1e1931", sidebar: "#191529", primary: "#a78bfa", text: "#f4f2ff" },
    { value: "sunset_orange", label: "Sunset Orange", bg: "#fbf5ef", surface: "#ffffff", sidebar: "#ffffff", primary: "#ea580c", text: "#2a1a0f" },
    { value: "rose_pink", label: "Rose Pink", bg: "#faf3f5", surface: "#ffffff", sidebar: "#ffffff", primary: "#e11d48", text: "#31131c" },
    { value: "slate_gray", label: "Slate Gray", bg: "#0f172a", surface: "#1e293b", sidebar: "#172033", primary: "#94a3b8", text: "#f1f5f9" },
    { value: "cyber_neon", label: "Cyber Neon", bg: "#04070f", surface: "#0b1122", sidebar: "#070b17", primary: "#22d3ee", text: "#e9f7ff" },
    { value: "coffee_brown", label: "Coffee Brown", bg: "#f5efe7", surface: "#fffdf8", sidebar: "#fffdf8", primary: "#92400e", text: "#2b1f15" },
    { value: "navy_dark", label: "Navy Dark", bg: "#0b1020", surface: "#131a2e", sidebar: "#0d1324", primary: "#5b7cfa", text: "#e8ecf8" },
    { value: "forest_teal", label: "Forest Teal", bg: "#0a1514", surface: "#122120", sidebar: "#0d1a18", primary: "#2dd4bf", text: "#e3f2ef" },
    { value: "crimson_red", label: "Crimson Red", bg: "#160b0d", surface: "#201214", sidebar: "#180c0e", primary: "#f43f5e", text: "#f5e9ea" },
    { value: "lavender_light", label: "Lavender", bg: "#f6f4fb", surface: "#ffffff", sidebar: "#ffffff", primary: "#7c3aed", text: "#211d33" },
    { value: "mint_light", label: "Mint", bg: "#f2f8f4", surface: "#ffffff", sidebar: "#ffffff", primary: "#0d9488", text: "#14281d" },
  ];

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "classic_white";
  }

  function applyTheme(value) {
    document.documentElement.setAttribute("data-theme", value);
    var cards = document.querySelectorAll("[data-theme-option]");
    for (var i = 0; i < cards.length; i++) {
      var active = cards[i].getAttribute("data-value") === value;
      cards[i].classList.toggle("active", active);
      cards[i].setAttribute("aria-selected", active ? "true" : "false");
    }
  }

  function persistTheme(value) {
    var html = document.documentElement;
    if (html.getAttribute("data-auth") === "true") {
      var picker = document.querySelector("[data-theme-picker]");
      var url = picker ? picker.getAttribute("data-save-url") : "";
      if (url) {
        var body = new URLSearchParams();
        body.append("theme", value);
        fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRFToken": csrfToken(),
          },
          body: body.toString(),
          credentials: "same-origin",
        }).catch(function () {
          /* non-fatal: theme still applies for this session */
        });
      }
    } else {
      try {
        localStorage.setItem(STORAGE_KEY, value);
      } catch (e) {}
    }
  }

  function buildCard(theme) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "theme-card";
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("data-value", theme.value);
    button.dataset.themeOption = "";

    var preview = document.createElement("span");
    preview.className = "theme-preview";
    preview.style.setProperty("--tp-bg", theme.bg);
    preview.style.setProperty("--tp-surface", theme.surface);
    preview.style.setProperty("--tp-sidebar", theme.sidebar);
    preview.style.setProperty("--tp-primary", theme.primary);
    preview.style.setProperty("--tp-text", theme.text);
    preview.setAttribute("aria-hidden", "true");

    var sidebar = document.createElement("span");
    sidebar.className = "tp-sidebar";
    sidebar.innerHTML =
      '<span class="tp-brand"></span><span class="tp-nav"></span><span class="tp-nav tp-nav-on"></span>';
    var main = document.createElement("span");
    main.className = "tp-main";
    var topbar = document.createElement("span");
    topbar.className = "tp-topbar";
    topbar.innerHTML =
      '<span class="tp-bread"></span><span class="tp-dot"></span><span class="tp-avatar"></span>';
    var cards = document.createElement("span");
    cards.className = "tp-cards";
    cards.innerHTML = '<span class="tp-card"><span class="tp-line"></span><span class="tp-btn"></span></span><span class="tp-card"></span>';
    main.appendChild(topbar);
    main.appendChild(cards);

    preview.appendChild(sidebar);
    preview.appendChild(main);

    var name = document.createElement("span");
    name.className = "theme-card-name";
    name.textContent = theme.label;

    var check = document.createElement("span");
    check.className = "theme-card-check";
    check.setAttribute("aria-hidden", "true");
    check.innerHTML =
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';

    button.appendChild(preview);
    button.appendChild(name);
    button.appendChild(check);
    return button;
  }

  function initThemePicker(picker) {
    if (!picker) return;

    var trigger = picker.querySelector("[data-theme-trigger]");
    var menu = picker.querySelector("[data-theme-menu]");
    var grid = menu.querySelector(".theme-grid");

    THEMES.forEach(function (theme) {
      grid.appendChild(buildCard(theme));
    });

    var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-theme-option]"));
    applyTheme(currentTheme());

    function openMenu() {
      menu.classList.add("open");
      menu.setAttribute("aria-hidden", "false");
      trigger.setAttribute("aria-expanded", "true");
      var active = grid.querySelector(".theme-card.active");
      if (active) active.focus();
    }

    function closeMenu(refocus) {
      menu.classList.remove("open");
      menu.setAttribute("aria-hidden", "true");
      trigger.setAttribute("aria-expanded", "false");
      if (refocus) trigger.focus();
    }

    trigger.addEventListener("click", function () {
      if (menu.classList.contains("open")) {
        closeMenu(true);
      } else {
        openMenu();
      }
    });

    grid.addEventListener("click", function (event) {
      var card = event.target.closest ? event.target.closest("[data-theme-option]") : null;
      if (!card) return;
      var value = card.getAttribute("data-value");
      applyTheme(value);
      persistTheme(value);
      closeMenu(true);
    });

    grid.addEventListener("keydown", function (event) {
      var index = cards.indexOf(document.activeElement);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        cards[(index + 1) % cards.length].focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        cards[(index - 1 + cards.length) % cards.length].focus();
      } else if (event.key === "Home") {
        event.preventDefault();
        cards[0].focus();
      } else if (event.key === "End") {
        event.preventDefault();
        cards[cards.length - 1].focus();
      }
    });

    document.addEventListener("click", function (event) {
      if (picker.contains(event.target)) return;
      if (menu.classList.contains("open")) closeMenu(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menu.classList.contains("open")) {
        closeMenu(true);
      }
    });
  }

  /* ---------- Full-page Appearance settings ---------- */
  function initThemePage() {
    var page = document.querySelector("[data-theme-page]");
    if (!page) return;
    var grid = page.querySelector(".theme-page-grid");
    if (!grid) return;

    THEMES.forEach(function (theme) {
      var card = buildCard(theme);
      card.className = "theme-card theme-card-lg";
      grid.appendChild(card);
    });

    var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-theme-option]"));
    applyTheme(currentTheme());

    grid.addEventListener("click", function (event) {
      var card = event.target.closest ? event.target.closest("[data-theme-option]") : null;
      if (!card) return;
      var value = card.getAttribute("data-value");
      applyTheme(value);
      persistTheme(value);
      if (typeof window.showToast === "function") {
        var label = "";
        for (var i = 0; i < THEMES.length; i++) {
          if (THEMES[i].value === value) {
            label = THEMES[i].label;
            break;
          }
        }
        window.showToast("success", label + " theme applied");
      }
    });

    grid.addEventListener("keydown", function (event) {
      var index = cards.indexOf(document.activeElement);
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        cards[(index + 1) % cards.length].focus();
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        cards[(index - 1 + cards.length) % cards.length].focus();
      } else if (event.key === "Home") {
        event.preventDefault();
        cards[0].focus();
      } else if (event.key === "End") {
        event.preventDefault();
        cards[cards.length - 1].focus();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initThemePage();
    var picker = document.querySelector("[data-theme-picker]");
    if (picker) initThemePicker(picker);
  });
})();
