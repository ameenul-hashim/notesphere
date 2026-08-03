(function () {
  "use strict";

  var STORAGE_KEY = "ns-theme";

  var THEMES = [
    { value: "classic_white", label: "Classic White", primary: "#18181b", bg: "#f7f7f8" },
    { value: "midnight_black", label: "Midnight Black", primary: "#fafafa", bg: "#09090b" },
    { value: "ocean_blue", label: "Ocean Blue", primary: "#0369a1", bg: "#f2f6fa" },
    { value: "emerald_green", label: "Emerald Green", primary: "#047857", bg: "#f3f9f6" },
    { value: "royal_purple", label: "Royal Purple", primary: "#8b5cf6", bg: "#14111f" },
    { value: "sunset_orange", label: "Sunset Orange", primary: "#c2410c", bg: "#fbf5ef" },
    { value: "rose_pink", label: "Rose Pink", primary: "#be123c", bg: "#faf3f5" },
    { value: "slate_gray", label: "Slate Gray", primary: "#cbd5e1", bg: "#0f172a" },
    { value: "cyber_neon", label: "Cyber Neon", primary: "#22d3ee", bg: "#04070f" },
    { value: "coffee_brown", label: "Coffee Brown", primary: "#6f4e28", bg: "#f5efe7" },
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
    var active = document.querySelectorAll(".theme-option.active");
    for (var i = 0; i < active.length; i++) {
      active[i].classList.remove("active");
    }
    var option = document.querySelector('.theme-option[data-value="' + value + '"]');
    if (option) option.classList.add("active");
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

  function buildMenu(menu) {
    THEMES.forEach(function (theme) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "theme-option";
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", "false");
      button.setAttribute("data-value", theme.value);
      button.dataset.themeOption = "";

      var swatch = document.createElement("span");
      swatch.className = "theme-swatch";
      swatch.style.background =
        "linear-gradient(135deg, " + theme.primary + " 0 45%, " + theme.bg + " 45% 100%)";
      swatch.setAttribute("aria-hidden", "true");

      var label = document.createElement("span");
      label.className = "theme-label";
      label.textContent = theme.label;

      button.appendChild(swatch);
      button.appendChild(label);
      menu.appendChild(button);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var picker = document.querySelector("[data-theme-picker]");
    if (!picker) return;

    var trigger = picker.querySelector("[data-theme-trigger]");
    var menu = picker.querySelector("[data-theme-menu]");

    buildMenu(menu);

    var value = currentTheme();
    var option = menu.querySelector('.theme-option[data-value="' + value + '"]');
    if (option) option.classList.add("active");

    trigger.addEventListener("click", function () {
      var open = !menu.hidden;
      menu.hidden = open;
      trigger.setAttribute("aria-expanded", String(!open));
      if (open) {
        var active = menu.querySelector(".theme-option.active");
        if (active) active.focus();
      }
    });

    menu.addEventListener("click", function (event) {
      var item = event.target.closest
        ? event.target.closest("[data-theme-option]")
        : null;
      if (!item) return;
      applyTheme(item.getAttribute("data-value"));
      persistTheme(item.getAttribute("data-value"));
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      trigger.focus();
    });

    menu.addEventListener("keydown", function (event) {
      var items = Array.prototype.slice.call(menu.querySelectorAll("[data-theme-option]"));
      var index = items.indexOf(document.activeElement);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        items[(index + 1) % items.length].focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        items[(index - 1 + items.length) % items.length].focus();
      }
    });

    document.addEventListener("click", function (event) {
      if (picker.contains(event.target)) return;
      if (!menu.hidden) {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !menu.hidden) {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        trigger.focus();
      }
    });
  });
})();
